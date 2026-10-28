"""Synthetic attachment tests; no clinical content, real account writes or Office automation.

PowerPoint/LibreOffice conversion processes are mocked; PDF parsing and fixture file I/O are real.
"""
import contextlib
import zipfile
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pypdf import PdfWriter
from approval_fixture import approval_file

spec=importlib.util.spec_from_file_location('attachment_test_target',Path(__file__).resolve().parents[1]/'scripts/attachments.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

def pdf(path,pages=1,password=None):
    writer=PdfWriter()
    for _ in range(pages):writer.add_blank_page(width=72,height=72)
    if password:writer.encrypt(password)
    with Path(path).open('wb') as out:writer.write(out)


def deck(path, overrides=None):
    parts={
      '[Content_Types].xml':'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/></Types>',
      '_rels/.rels':'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/></Relationships>',
      'ppt/presentation.xml':'<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>'}
    parts.update(overrides or {})
    with zipfile.ZipFile(path,'w') as archive:
        for name,content in parts.items():
            if content is not None:archive.writestr(name,content)

class AttachmentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('TEST_TMP_ROOT'))
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve();self.root=self.base/'p';self.state=self.base/'s'
        (self.root/'teaching').mkdir(parents=True);self.state.mkdir()
        self.config={'project_root':str(self.root),'approval_policy':'per_change','attachments':{'approved_pdf_dirs':['teaching'],'routes':{'teaching':'teaching'}},'runtime':{}}
        (self.state/'config.json').write_text(json.dumps(self.config),encoding='utf-8')
        self.source=self.base/'synthetic.pdf';pdf(self.source)
        self.deck=self.base/'synthetic.pptx';deck(self.deck)
        self.target=self.root/'teaching/material.pdf'
    def cli(self,*args):
        output=io.StringIO()
        with patch.object(sys,'argv',['attachments.py',*map(str,args)]),contextlib.redirect_stdout(output),contextlib.redirect_stderr(io.StringIO()):
            helper.main()
        return json.loads(output.getvalue())
    def stage_pdf(self):return self.cli('stage',self.state,self.source,'teaching/material.pdf','--source-screening','not_flagged')
    def stage_deck(self,*extra):return self.cli('stage',self.state,self.deck,'teaching/material.pdf',*extra)
    def save(self,item,*extra):
        evidence=approval_file(self.state,'attachment',item['id'],item['pdf_sha256'],self.root/item['relative_pdf'])
        return self.cli('save',self.state,item['id'],'--approval',item['id'],'--approval-evidence',evidence,*extra)
    def flags(self):return ('--source-screening','not_flagged','--private-copy-approved')
    def private_folder(self):return next((self.state/'attachments').iterdir())
    def assert_no_preparation(self,probe):
        self.assertFalse((self.state/'attachments').exists());self.assertFalse(self.target.exists());probe.assert_not_called()
    def successful_powerpoint(self,args,**kwargs):
        pdf(Path(args[args.index('-Destination')+1]));return SimpleNamespace(returncode=0)
    def test_pdf_stage_and_save_real_pdf(self):
        item=self.stage_pdf();self.assertEqual(item['pages'],1)
        result=self.save(item,'--privacy-reviewed','--public-approved')
        self.assertEqual(result['status'],'saved_bytes_verified');self.assertEqual(self.target.read_bytes(),self.source.read_bytes())
    def test_powerpoint_missing_copy_ack_blocks_before_any_copy_or_probe(self):
        with patch.object(helper,'powerpoint_shell') as probe:
            with self.assertRaisesRegex(ValueError,'explicit private-copy approval'):
                self.stage_deck('--source-screening','not_flagged')
            self.assert_no_preparation(probe)
    def test_powerpoint_missing_source_screen_blocks_before_copy_or_probe(self):
        with patch.object(helper,'powerpoint_shell') as probe:
            with self.assertRaisesRegex(ValueError,'source-screen assertion'):
                self.stage_deck('--private-copy-approved')
            self.assert_no_preparation(probe)
    def test_flagged_powerpoint_cannot_be_overridden_by_copy_ack(self):
        with patch.object(helper,'powerpoint_shell') as probe:
            with self.assertRaisesRegex(ValueError,'Source is flagged'):
                self.stage_deck('--source-screening','flagged','--private-copy-approved')
            self.assert_no_preparation(probe)
    def test_flagged_pdf_is_refused_before_copy(self):
        with patch.object(helper,'powerpoint_shell') as probe:
            with self.assertRaisesRegex(ValueError,'Source is flagged'):
                self.cli('stage',self.state,self.source,'teaching/material.pdf','--source-screening','flagged')
            self.assert_no_preparation(probe)
    def test_approved_powerpoint_conversion_remains_pending_review(self):
        original=self.deck.read_bytes()
        with patch.object(helper,'powerpoint_shell',return_value='mock-pwsh'),patch.object(helper.shutil,'which',return_value=None),patch.object(helper.subprocess,'run',side_effect=self.successful_powerpoint):
            item=self.stage_deck(*self.flags())
        self.assertEqual(item['review_status'],'pending_visual_privacy_review')
        self.assertTrue(item['private_copy_approval_assertion']);self.assertEqual(item['source_screening_assertion'],'not_flagged')
        folder=Path(item['staged_pdf']).parent
        self.assertEqual((folder/'original.pptx').read_bytes(),original);self.assertEqual(self.deck.read_bytes(),original)
        self.assertFalse(self.target.exists())
        receipt=json.loads((folder/'staging.json').read_text(encoding='utf-8'))
        self.assertEqual(receipt['review_status'],'pending_visual_privacy_review')
    def test_powerpoint_copy_ack_is_not_public_save_review(self):
        with patch.object(helper,'powerpoint_shell',return_value='mock-pwsh'),patch.object(helper.shutil,'which',return_value=None),patch.object(helper.subprocess,'run',side_effect=self.successful_powerpoint):
            item=self.stage_deck(*self.flags())
        with self.assertRaises(SystemExit):self.save(item,'--public-approved')
        self.assertFalse(self.target.exists())
    def test_libreoffice_conversion_path_with_mocked_engine(self):
        def convert(executable,source,dest):pdf(dest)
        with patch.object(helper,'powerpoint_shell',return_value=None),patch.object(helper.shutil,'which',return_value='mock-soffice'),patch.object(helper,'convert_libreoffice',side_effect=convert) as engine:
            item=self.stage_deck(*self.flags())
        engine.assert_called_once();self.assertEqual(item['review_status'],'pending_visual_privacy_review')
        self.assertIn('LibreOffice',item['method'])
    def test_conversion_failure_reports_and_preserves_private_original(self):
        with patch.object(helper,'powerpoint_shell',return_value='mock-pwsh'),patch.object(helper.shutil,'which',return_value=None),patch.object(helper.subprocess,'run',return_value=SimpleNamespace(returncode=1)):
            with self.assertRaisesRegex(ValueError,'private files may remain at') as caught:self.stage_deck(*self.flags())
        folder=self.private_folder();self.assertIn(str(folder),str(caught.exception))
        self.assertTrue((folder/'original.pptx').is_file());self.assertFalse(self.target.exists())
        receipt=json.loads((folder/'staging-failed.json').read_text(encoding='utf-8'))
        self.assertEqual(receipt['failure_phase'],'powerpoint_conversion')
        self.assertFalse((folder/'manifest.json').exists())
    def test_converter_timeout_does_not_leak_captured_output(self):
        err=subprocess.TimeoutExpired(['mock'],180,output='SENSITIVE_SENTINEL',stderr='SENSITIVE_SENTINEL')
        with patch.object(helper,'powerpoint_shell',return_value='mock-pwsh'),patch.object(helper.shutil,'which',return_value=None),patch.object(helper.subprocess,'run',side_effect=err):
            with self.assertRaises(ValueError) as caught:self.stage_deck(*self.flags())
        self.assertNotIn('SENSITIVE_SENTINEL',str(caught.exception))
        receipt=(self.private_folder()/'staging-failed.json').read_text(encoding='utf-8')
        self.assertNotIn('SENSITIVE_SENTINEL',receipt);self.assertIn('TimeoutExpired',receipt)
        self.assertFalse(self.target.exists())
    def test_missing_converter_reports_retained_copy_without_false_success(self):
        with patch.object(helper,'powerpoint_shell',return_value=None),patch.object(helper.shutil,'which',return_value=None):
            with self.assertRaisesRegex(ValueError,'converter_discovery'):self.stage_deck(*self.flags())
        self.assertTrue((self.private_folder()/'original.pptx').exists());self.assertFalse(self.target.exists())
    def test_invalid_converted_pdf_is_not_successful(self):
        def invalid(args,**kwargs):
            Path(args[args.index('-Destination')+1]).write_bytes(b'%PDF-invalid');return SimpleNamespace(returncode=0)
        with patch.object(helper,'powerpoint_shell',return_value='mock-pwsh'),patch.object(helper.shutil,'which',return_value=None),patch.object(helper.subprocess,'run',side_effect=invalid):
            with self.assertRaisesRegex(ValueError,'pdf_validation'):self.stage_deck(*self.flags())
        self.assertFalse((self.private_folder()/'manifest.json').exists());self.assertFalse(self.target.exists())
    def test_pdf_privacy_save_flag_required(self):
        item=self.stage_pdf()
        with self.assertRaises(SystemExit):self.save(item,'--public-approved')
        self.assertFalse(self.target.exists())
    def test_pdf_public_use_save_flag_required(self):
        item=self.stage_pdf()
        with self.assertRaises(SystemExit):self.save(item,'--privacy-reviewed')
        self.assertFalse(self.target.exists())
    def test_wrong_approval_cannot_save(self):
        item=self.stage_pdf()
        with self.assertRaisesRegex(ValueError,'exact reviewed attachment'):
            self.cli('save',self.state,item['id'],'--approval','f'*32,'--approval-evidence',self.state/'unused.json','--privacy-reviewed','--public-approved')
        self.assertFalse(self.target.exists())
    def test_changed_staged_bytes_refused(self):
        item=self.stage_pdf();Path(item['staged_pdf']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'staged_changed'):self.save(item,'--privacy-reviewed','--public-approved')
        self.assertFalse(self.target.exists())
    def test_existing_destination_not_overwritten_at_stage(self):
        self.target.write_bytes(b'existing')
        with self.assertRaisesRegex(ValueError,'Destination already exists'):self.stage_pdf()
        self.assertEqual(self.target.read_bytes(),b'existing');self.assertFalse((self.state/'attachments').exists())
    def test_destination_created_after_stage_not_overwritten(self):
        item=self.stage_pdf();self.target.write_bytes(b'other writer')
        with self.assertRaisesRegex(ValueError,'destination_conflict'):self.save(item,'--privacy-reviewed','--public-approved')
        self.assertEqual(self.target.read_bytes(),b'other writer')
    def test_path_rules_refuse_escapes_and_unapproved_routes(self):
        for route in ('../material.pdf','teaching/../material.pdf','/teaching/material.pdf','teaching\\material.pdf','images/material.pdf','teaching/sub/material.pdf','teaching/material.pptx'):
            with self.subTest(route=route),self.assertRaises(ValueError):self.cli('stage',self.state,self.source,route)
        self.assertFalse((self.state/'attachments').exists())
    def test_redirected_directory_flag_refused(self):
        with patch.object(Path,'is_symlink',return_value=True),self.assertRaisesRegex(ValueError,'redirected'):
            helper.destination(self.root,self.config['attachments'],'teaching/material.pdf')
    def test_private_state_inside_project_refused(self):
        inside=self.root/'private';inside.mkdir();(inside/'config.json').write_text(json.dumps(self.config),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'outside the project'):self.cli('stage',inside,self.source,'teaching/material.pdf')
    def test_encrypted_and_empty_pdfs_do_not_stage_successfully(self):
        for pages,password in ((1,'synthetic-password'),(0,None)):
            with self.subTest(pages=pages,password=bool(password)):
                pdf(self.source,pages=pages,password=password)
                with self.assertRaisesRegex(ValueError,'pdf_validation'):self.stage_pdf()
        self.assertFalse(self.target.exists())
    def test_source_change_during_copy_preserves_failure_evidence(self):
        real_copy=helper.shutil.copyfile
        def changed(source,dest,*args,**kwargs):
            result=real_copy(source,dest,*args,**kwargs)
            if Path(source)==self.source:self.source.write_bytes(b'changed source')
            return result
        with patch.object(helper.shutil,'copyfile',side_effect=changed),self.assertRaisesRegex(ValueError,'source_copy'):self.stage_pdf()
        self.assertTrue((self.private_folder()/'staging-failed.json').exists());self.assertFalse(self.target.exists())
    def test_status_is_read_only_and_reports_saved_bytes(self):
        item=self.stage_pdf();self.save(item,'--privacy-reviewed','--public-approved')
        before=self.target.read_bytes();receipt=(Path(item['staged_pdf']).parent/'saved.json').read_bytes()
        status=self.cli('status',self.state,item['id'])
        self.assertEqual(status['status'],'saved_bytes_verified');self.assertEqual(self.target.read_bytes(),before)
        self.assertEqual((Path(item['staged_pdf']).parent/'saved.json').read_bytes(),receipt)


    def test_pdf_without_screening_stops_before_private_preparation(self):
        with patch.object(helper.shutil,'copyfile') as copy, patch.object(helper,'pdf_pages') as parse, patch.object(helper,'powerpoint_shell') as probe:
            with self.assertRaisesRegex(ValueError,'PDF requires.*source-screen assertion'):
                self.cli('stage',self.state,self.source,'teaching/material.pdf')
            self.assertFalse((self.state/'attachments').exists())
            self.assertFalse(self.target.exists())
            copy.assert_not_called();parse.assert_not_called();probe.assert_not_called()

    def test_pdf_explicit_not_screened_cannot_be_overridden_by_copy_approval(self):
        with patch.object(helper.shutil,'copyfile') as copy:
            with self.assertRaisesRegex(ValueError,'source-screen assertion'):
                self.cli('stage',self.state,self.source,'teaching/material.pdf',
                         '--source-screening','not_screened','--private-copy-approved')
            copy.assert_not_called()
        self.assertFalse((self.state/'attachments').exists())

    def test_flagged_pdf_stops_before_copy_even_with_private_copy_approval(self):
        with patch.object(helper.shutil,'copyfile') as copy, patch.object(helper,'pdf_pages') as parse:
            with self.assertRaisesRegex(ValueError,'Source is flagged'):
                self.cli('stage',self.state,self.source,'teaching/material.pdf',
                         '--source-screening','flagged','--private-copy-approved')
            copy.assert_not_called();parse.assert_not_called()
        self.assertFalse((self.state/'attachments').exists())
        self.assertFalse(self.target.exists())

    def test_screened_pdf_is_still_pending_final_privacy_and_public_review(self):
        item=self.stage_pdf()
        self.assertEqual(item['source_screening_assertion'],'not_flagged')
        self.assertEqual(item['review_status'],'pending_visual_privacy_review')
        self.assertFalse(self.target.exists())
        with self.assertRaises(SystemExit):
            self.save(item,'--public-approved')
        self.assertFalse(self.target.exists())


if __name__=='__main__':unittest.main()
