"""Synthetic publication setup; no real Zotero/PubMed access or library writes."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('publication_setup_target',Path(__file__).resolve().parents[1]/'scripts/publication_setup.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)

class PublicationSetupTests(unittest.TestCase):
    def observations(self,count=0):
        return dict(reference='SYNTHETIC mock connector observations',desktop='running',account='none',sync_requested=False,
                    integration={'available':True,'read':True,'import':True,'export':False},inventory={'complete':True,'item_count':count},
                    destination_verified=True,export_side_effects_reviewed=True)
    def test_no_account_empty_local_library_can_prepare_reviewed_proposal(self):
        report=h.assess(self.observations())
        self.assertEqual(report['library'],'empty');self.assertEqual(report['import_proposal'],'ready_for_review')
        self.assertFalse(report['writes_authorized']);self.assertEqual(report['publication_outputs'],'pending')
    def test_existing_library_reconciles_instead_of_resetting(self):
        report=h.assess(self.observations(12))
        self.assertEqual(report['library'],'existing')
        self.assertTrue(any('Reconcile' in a for a in report['next_actions']))
        self.assertFalse(report['writes_authorized'])
    def test_missing_or_stopped_desktop_holds_only_connection_work(self):
        for status in ('missing','stopped','unknown'):
            value=self.observations();value['desktop']=status
            report=h.assess(value)
            self.assertEqual(report['connection'],'pending');self.assertEqual(report['library'],'unknown')
            self.assertTrue(any('candidate reconciliation' in a for a in report['next_actions']))
    def test_missing_or_read_only_integration_does_not_authorize_import(self):
        for key in ('available','read','import'):
            value=self.observations();value['integration'][key]=False
            report=h.assess(value)
            self.assertEqual(report['import_proposal'],'pending');self.assertFalse(report['writes_authorized'])
    def test_partial_inventory_cannot_establish_empty_library(self):
        value=self.observations();value['inventory']['complete']=False
        self.assertEqual(h.assess(value)['library'],'unknown')
    def test_unknown_destination_or_export_side_effects_holds_import(self):
        for key in ('destination_verified','export_side_effects_reviewed'):
            value=self.observations();value[key]=None
            self.assertEqual(h.assess(value)['import_proposal'],'pending')
    def test_scoped_native_export_can_be_verified_without_better_bibtex(self):
        value=self.observations(2);value['export']={key:True for key in ('scope_verified','citation_keys_verified','consumer_path_verified','format_verified','outputs_verified')}
        self.assertFalse(value['integration']['export'])
        self.assertEqual(h.assess(value)['publication_outputs'],'verified_observations')
        value['export']['scope_verified']=False
        self.assertEqual(h.assess(value)['publication_outputs'],'pending')
    def test_optional_sync_does_not_block_local_proposal(self):
        value=self.observations();value['sync_requested']=True
        report=h.assess(value)
        self.assertEqual(report['import_proposal'],'ready_for_review');self.assertEqual(report['sync'],'requested_separate_setup')
    def test_invalid_or_secret_fields_are_refused(self):
        for key,val in [('token','secret'),('destination_verified','yes')]:
            value=self.observations();value[key]=val
            with self.assertRaises(ValueError):h.assess(value)
        value=self.observations();value['inventory']['item_count']=True
        with self.assertRaises(ValueError):h.assess(value)
        value=self.observations();value['reference']=''
        with self.assertRaises(ValueError):h.assess(value)
    def test_assessment_does_not_mutate_observations(self):
        value=self.observations();before=copy.deepcopy(value)
        h.assess(value);self.assertEqual(value,before)
    def test_private_staging_resumes_without_creating_project_or_profile(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TEST_TMP_ROOT')) as temp:
            state=Path(temp).resolve()/'private';state.mkdir()
            h.init.start(state,True,'SYNTHETIC storage')
            result=h.stage(state,self.observations())
            self.assertTrue(Path(result['readiness_path']).is_file())
            self.assertFalse((state/'config.json').exists())
            operations=h.init.status(state)['staged_operations']
            self.assertEqual(len(operations),1);self.assertEqual(operations[0]['result']['readiness_path'],result['readiness_path'])
            self.assertFalse(result['writes_authorized'])
    def test_interrupted_private_report_is_not_completed(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(dir=os.environ.get('TEST_TMP_ROOT')) as temp:
            state=Path(temp).resolve()/'private';state.mkdir();h.init.start(state,True,'SYNTHETIC storage')
            real=h.init.exclusive
            def fail(path,raw):
                if path.name=='readiness.json':raise OSError('SYNTHETIC disk failure')
                return real(path,raw)
            with patch.object(h.init,'exclusive',side_effect=fail):
                with self.assertRaises(OSError):h.stage(state,self.observations())
            self.assertEqual(h.init.status(state)['staged_operations'][0]['status'],'interrupted_or_in_progress')
    def test_publication_candidates_stay_private_and_unimported_on_resume(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TEST_TMP_ROOT')) as temp:
            base=Path(temp).resolve();state=base/'private';state.mkdir();h.init.start(state,True,'SYNTHETIC storage')
            source=base/'CV.txt';source.write_text('Example article\nUncertain chapter\n',encoding='utf-8')
            h.init.answer(state,dict(key='cv_source',value=str(source),response='SYNTHETIC source',reference='SYNTHETIC request'))
            extracted=h.init.extract(state,source,True,'not_flagged','SYNTHETIC processing')
            path=Path(extracted['folder'])/'extracted.json';data=json.loads(path.read_text());ids=[s['id'] for s in data['segments']]
            ledger=dict(source_sha256=data['source_sha256'],coverage=[dict(source_id=ids[0],disposition='candidate',candidate_ids=['existing'],reason='Synthetic existing match'),dict(source_id=ids[1],disposition='candidate',candidate_ids=['chapter'],reason='Synthetic uncertain source')],candidates=[dict(id='existing',source_ids=[ids[0]],target='zotero',record={'title':'Example article'},publication_disposition='matched_existing'),dict(id='chapter',source_ids=[ids[1]],target='zotero',record={'title':'Uncertain chapter','itemType':'bookSection'},publication_disposition='uncertain')])
            result=h.init.stage_ledger(state,path,ledger)
            self.assertFalse(result['imported']);self.assertFalse((state/'config.json').exists())
            saved=json.loads((Path(result['folder'])/'ledger.json').read_text())
            self.assertEqual(saved['candidates'][0]['publication_disposition'],'matched_existing')
            self.assertEqual(saved['candidates'][1]['publication_disposition'],'uncertain')
            self.assertEqual(len(h.init.status(state)['staged_operations']),2)

class PublicationExportIntegrationTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT') and os.environ.get('TEST_QUARTO'),'Set TEST_RSCRIPT and TEST_QUARTO for real consumers')
    def test_mock_metadata_export_reaches_real_cv_and_website_without_library_write(self):
        import zipfile
        with tempfile.TemporaryDirectory(dir=os.environ.get('TEST_TMP_ROOT')) as temp:
            base=Path(temp).resolve();state=base/'private';state.mkdir();h.init.start(state,True,'SYNTHETIC storage')
            staged=h.init.stage_starter(state,'SYNTHETIC starter request');project=base/'project'
            shutil.copytree(staged['project_source_root'],project)
            # Mock export: this never calls Zotero. Existing generated keys are preserved.
            bib='@article{syntheticPublication2024,\n title={SYNTHETIC PUBLICATION PIPELINE 928},\n author={Example, Alex and Researcher, Casey},\n journal={Synthetic Journal},\n year={2024},\n volume={1},\n pages={1--2}\n}\n'
            export=state/'scoped-export.bib';export.write_text(bib,encoding='utf-8')
            shutil.copyfile(export,project/'data/publications.bib')
            verify=base/'verify-bib.R'
            verify.write_text('b <- RefManageR::ReadBib("data/publications.bib", check=FALSE)\nstopifnot(length(b)==1L, !anyDuplicated(names(b)), identical(names(b), "syntheticPublication2024"))\n',encoding='utf-8')
            env=dict(os.environ,R_LIBS_USER=os.environ.get('TEST_R_LIBRARY',''),QUARTO_R=str(Path(os.environ['TEST_RSCRIPT']).parent))
            for argv in [[os.environ['TEST_RSCRIPT'],str(verify)],[os.environ['TEST_RSCRIPT'],'R/cv.R'],[os.environ['TEST_QUARTO'],'render']]:
                proc=subprocess.run(argv,cwd=project,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
                self.assertEqual(proc.returncode,0,proc.stdout[-2500:]+proc.stderr[-2500:])
            with zipfile.ZipFile(next((project/'cv').glob('*.docx'))) as z:xml=z.read('word/document.xml').decode()
            self.assertIn('SYNTHETIC PUBLICATION PIPELINE 928',xml)
            html=(project/'docs/manuscripts.html').read_text(encoding='utf-8')
            self.assertIn('SYNTHETIC PUBLICATION PIPELINE 928',html)
            self.assertIn('syntheticPublication2024',html)
            self.assertEqual(export.read_text(encoding='utf-8'),bib)
            self.assertFalse((state/'config.json').exists())

if __name__=='__main__':unittest.main()
