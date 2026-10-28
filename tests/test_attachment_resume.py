"""C2: interruptions use synthetic PDFs and evidence, never owner files."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import test_attachments as base
from approval_fixture import approval_file
h=base.helper

class AttachmentResumeTests(unittest.TestCase):
    setUp=base.AttachmentTests.setUp
    cli=base.AttachmentTests.cli
    stage_pdf=base.AttachmentTests.stage_pdf
    save=base.AttachmentTests.save

    def interrupted(self):
        item=self.stage_pdf();real=h.write_json
        def fail(path,value):
            result=real(path,value)
            if path.name=='save-attempt.json':raise OSError('SYNTHETIC interrupted before copy')
            return result
        with patch.object(h,'write_json',side_effect=fail):
            with self.assertRaises(OSError):self.save(item,'--privacy-reviewed','--public-approved')
        self.assertFalse(self.target.exists())
        return item

    def resume(self,item):
        return self.save(item,'--privacy-reviewed','--public-approved','--resume')

    def test_interrupted_status_and_explicit_resume_reuse_exact_private_pdf_and_attempt(self):
        item=self.interrupted();folder=Path(item['staged_pdf']).parent
        before={p.name:p.read_bytes() for p in folder.iterdir() if p.is_file()}
        status=self.cli('status',self.state,item['id'])
        self.assertEqual(status['status'],'save_interrupted_before_copy')
        self.assertTrue(status['resume_available'])
        self.assertEqual(before,{p.name:p.read_bytes() for p in folder.iterdir() if p.is_file()})
        with self.assertRaisesRegex(ValueError,'--resume'):self.save(item,'--privacy-reviewed','--public-approved')
        result=self.resume(item)
        self.assertEqual(result['status'],'saved_bytes_verified')
        self.assertEqual(self.target.read_bytes(),Path(item['staged_pdf']).read_bytes())
        for name,raw in before.items():self.assertEqual((folder/name).read_bytes(),raw)
        self.assertEqual(len(list((self.state/'attachments').iterdir())),1)
        self.assertTrue((folder/'saved.json').is_file())

    def test_changed_scope_prevents_resume(self):
        item=self.interrupted()
        self.config['attachments']['routes']['teaching']='other'
        (self.state/'config.json').write_text(json.dumps(self.config))
        self.assertFalse(self.cli('status',self.state,item['id'])['resume_available'])
        with self.assertRaisesRegex(ValueError,'settings changed'):self.resume(item)
        self.assertFalse(self.target.exists())

    def test_partial_destination_never_overwritten_or_deleted(self):
        item=self.interrupted();self.target.write_bytes(b'%PDF-partial')
        with self.assertRaisesRegex(ValueError,'destination_conflict'):self.resume(item)
        self.assertEqual(self.target.read_bytes(),b'%PDF-partial')

    def test_matching_destination_does_not_gain_a_receipt_by_resume(self):
        item=self.interrupted();self.target.write_bytes(Path(item['staged_pdf']).read_bytes())
        folder=Path(item['staged_pdf']).parent;before=self.target.read_bytes()
        with self.assertRaisesRegex(ValueError,'saved_bytes_verified'):self.resume(item)
        self.assertEqual(self.target.read_bytes(),before)
        self.assertFalse((folder/'saved.json').exists())

    def test_changed_or_incomplete_attempt_cannot_resume(self):
        item=self.interrupted();path=Path(item['staged_pdf']).parent/'save-attempt.json'
        original=json.loads(path.read_text())
        for field,value in [('destination','wrong'),('pdf_sha256','0'*64),
                            ('privacy_review_assertion',False),('public_use_assertion',False)]:
            with self.subTest(field=field):
                path.write_text(json.dumps({**original,field:value}))
                self.assertEqual(self.cli('status',self.state,item['id'])['status'],'save_attempt_invalid')
                with self.assertRaisesRegex(ValueError,'save_attempt_invalid'):self.resume(item)
                self.assertFalse(self.target.exists())
        path.write_text('{')
        self.assertEqual(self.cli('status',self.state,item['id'])['status'],'save_attempt_invalid')

    def test_changed_stored_or_supplied_approval_evidence_is_not_reused(self):
        item=self.interrupted();folder=Path(item['staged_pdf']).parent
        evidence=approval_file(self.state,'attachment',item['id'],item['pdf_sha256'],self.target)
        value=json.loads(evidence.read_text());value['response']='DIFFERENT SYNTHETIC RESPONSE'
        evidence.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'Existing approval evidence differs'):
            self.cli('save',self.state,item['id'],'--approval',item['id'],'--approval-evidence',evidence,
                     '--privacy-reviewed','--public-approved','--resume')
        self.assertFalse(self.target.exists())
        stored=folder/h.approvals.FILENAME;stored.write_text('changed')
        self.assertEqual(self.cli('status',self.state,item['id'])['status'],'save_attempt_invalid')

    def test_staged_bytes_change_prevents_resume(self):
        item=self.interrupted();Path(item['staged_pdf']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'staged_changed'):self.resume(item)
        self.assertFalse(self.target.exists())

    def test_unknown_writer_lock_is_not_removed_or_bypassed(self):
        item=self.interrupted();lock=self.state/'.private-state-writer.lock';lock.write_text('SYNTHETIC unknown writer')
        with self.assertRaisesRegex(ValueError,'writer is locked'):self.resume(item)
        self.assertFalse(self.target.exists());self.assertEqual(lock.read_text(),'SYNTHETIC unknown writer')

if __name__=='__main__':unittest.main()

