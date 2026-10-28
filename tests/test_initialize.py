"""New-user bootstrap and import staging on disposable synthetic fixtures only."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('initializer_test_target',Path(__file__).resolve().parents[1]/'scripts/initialize.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)


class InitializationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('TEST_TMP_ROOT'));self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve();self.state=self.base/'private';self.state.mkdir();self.project=self.base/'project'
    def start(self):return h.start(self.state,True,'SYNTHETIC storage choice')
    def answer(self,key,value):return h.answer(self.state,dict(key=key,value=value,response='SYNTHETIC answer',reference='SYNTHETIC conversation'))
    def extract(self,text='Education\nExample University MD 2010\n'):
        self.start();source=self.base/'CV.txt';source.write_text(text,encoding='utf-8');self.answer('cv_source',str(source))
        result=h.extract(self.state,source,True,'not_flagged','SYNTHETIC private approval')
        path=Path(result['folder'])/'extracted.json';return path,json.loads(path.read_text())
    def ledger(self,source):
        return dict(source_sha256=source['source_sha256'],coverage=[dict(source_id=s['id'],disposition='context',reason='SYNTHETIC context') for s in source['segments']],candidates=[])

    def test_start_does_not_need_or_create_project_profile(self):
        result=self.start();self.assertEqual(result['next_question']['id'],'outputs')
        self.assertFalse(self.project.exists());self.assertFalse((self.state/'config.json').exists())
    def test_resume_returns_only_next_unanswered_question(self):
        self.start();self.answer('outputs','both');self.assertEqual(h.status(self.state)['next_question']['id'],'starting_point')
    def test_answer_change_preserves_prior_bytes_and_actual_references(self):
        self.start();self.answer('outputs','cv');old=(self.state/'initialization.json').read_bytes();self.answer('outputs','both')
        self.assertIn(old,[p.read_bytes() for p in (self.state/'initialization-history').iterdir()])
        self.assertEqual(h.load(self.state)['history'][-1]['response'],'SYNTHETIC answer')
    def test_existing_profile_is_never_reinitialized(self):
        original=b'{"existing":true}';(self.state/'config.json').write_bytes(original)
        with self.assertRaisesRegex(ValueError,'Existing profile'):self.start()
        self.assertEqual((self.state/'config.json').read_bytes(),original)
    def test_second_start_preserves_existing_bootstrap(self):
        self.start();old=(self.state/'initialization.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'already exists'):self.start()
        self.assertEqual((self.state/'initialization.json').read_bytes(),old)
    def test_confirmed_private_storage_required(self):
        with self.assertRaises(ValueError):h.start(self.state,False,'SYNTHETIC')
        self.assertFalse((self.state/'initialization.json').exists())
    def test_git_checkout_is_not_private_bootstrap_storage(self):
        (self.base/'.git').mkdir()
        with self.assertRaisesRegex(ValueError,'outside a Git'):self.start()
    def test_project_cannot_contain_or_be_private_state(self):
        self.start()
        for path in (self.state,self.base,self.state/'nested'):
            with self.subTest(path=path),self.assertRaisesRegex(ValueError,'separate'):self.answer('project_path',str(path))
    def test_invalid_choices_and_unreferenced_answers_are_refused(self):
        self.start()
        with self.assertRaises(ValueError):self.answer('outputs','unknown')
        with self.assertRaises(ValueError):h.answer(self.state,dict(key='outputs',value='cv',response='',reference=''))
        with self.assertRaises(ValueError):self.answer('integrations',['unsupported'])
    def test_questionnaire_complete_is_not_capability_ready(self):
        self.start()
        values=['cv','fresh','no','docx',None,None,'guidance','not_needed',[]]
        for (key,_,_),value in zip(h.QUESTIONS,values):self.answer(key,value)
        result=h.status(self.state);self.assertTrue(result['questionnaire_complete']);self.assertFalse(result['profile_created'])
        self.assertEqual(result['state']['readiness']['project'],'pending')
    def test_writer_lock_refuses_overlapping_writer_without_removing_other_lock(self):
        marker=self.state/'.initialization-writer.lock';marker.write_text('SYNTHETIC other writer')
        with self.assertRaises(FileExistsError):self.start()
        self.assertEqual(marker.read_text(),'SYNTHETIC other writer')
    def test_private_text_extraction_preserves_original_and_returns_locations(self):
        path,source=self.extract();self.assertEqual(source['segments'][0]['id'],'S00001')
        self.assertEqual(source['segments'][1]['location'],'line-2');self.assertFalse(source['public_use_approved'])
        self.assertEqual((self.base/'CV.txt').read_text(),'Education\nExample University MD 2010\n');self.assertFalse(self.project.exists())
    def test_flagged_or_unapproved_extraction_makes_no_staged_copy(self):
        self.start();source=self.base/'CV.txt';source.write_text('SYNTHETIC');self.answer('cv_source',str(source))
        for approved,screening in ((False,'not_flagged'),(True,'flagged')):
            with self.subTest(approved=approved),self.assertRaisesRegex(ValueError,'Screen source'):h.extract(self.state,source,approved,screening,'SYNTHETIC')
        self.assertFalse((self.state/'initialization-staging').exists())
    def test_unselected_or_empty_source_is_refused(self):
        self.start();source=self.base/'CV.txt';source.write_text('')
        with self.assertRaisesRegex(ValueError,'Confirm this CV'):h.extract(self.state,source,True,'not_flagged','SYNTHETIC')
        self.answer('cv_source',str(source))
        with self.assertRaisesRegex(ValueError,'No extractable'):h.extract(self.state,source,True,'not_flagged','SYNTHETIC')
    def test_docx_tables_and_header_have_explicit_source_locations(self):
        self.start();source=self.base/'CV.docx'
        ns='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
        with zipfile.ZipFile(source,'w') as z:
            z.writestr('word/document.xml',f'<w:document xmlns:w="{ns}"><w:body><w:tbl><w:tr><w:tc><w:p><w:r><w:t>SYNTHETIC table entry</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
            z.writestr('word/header1.xml',f'<w:hdr xmlns:w="{ns}"><w:p><w:r><w:t>SYNTHETIC header</w:t></w:r></w:p></w:hdr>')
        self.answer('cv_source',str(source));result=h.extract(self.state,source,True,'not_flagged','SYNTHETIC')
        data=json.loads((Path(result['folder'])/'extracted.json').read_text());self.assertEqual(len(data['segments']),2)
        self.assertTrue(any('header1' in s['location'] for s in data['segments']))
    def test_scanned_pdf_is_not_silently_empty_cv(self):
        from pypdf import PdfWriter
        self.start();source=self.base/'CV.pdf';writer=PdfWriter();writer.add_blank_page(width=72,height=72)
        with source.open('wb') as f:writer.write(f)
        self.answer('cv_source',str(source))
        with self.assertRaisesRegex(ValueError,'No extractable'):h.extract(self.state,source,True,'not_flagged','SYNTHETIC')
    def test_ledger_requires_every_source_segment_once(self):
        path,source=self.extract();ledger=self.ledger(source);ledger['coverage'].pop()
        with self.assertRaisesRegex(ValueError,'accounted for once'):h.stage_ledger(self.state,path,ledger)
    def test_ledger_missing_fact_fields_is_staged_not_imported(self):
        path,source=self.extract();ledger=self.ledger(source);s=source['segments'][1]['id']
        ledger['coverage'][1].update(disposition='candidate',candidate_ids=['entry-1'])
        ledger['candidates']=[dict(id='entry-1',source_ids=[s],target='education.yml',record={'institution':'Example University'})]
        result=h.stage_ledger(self.state,path,ledger);self.assertFalse(result['imported']);self.assertEqual(result['candidate_count'],1)
    def output_ledger(self,assessments=None,goals='both'):
        path,source=self.extract()
        self.answer('outputs',goals)
        ledger=self.ledger(source);sid=source['segments'][1]['id']
        ledger['coverage'][1].update(disposition='candidate',candidate_ids=['teaching-1'])
        candidate=dict(id='teaching-1',source_ids=[sid],target='teaching.yml',record={'title':'SYNTHETIC session'})
        if assessments is not None:candidate['output_coverage']=assessments
        ledger['candidates']=[candidate]
        return path,ledger
    def assessment(self,status):
        return dict(status=status,reason='SYNTHETIC inspected consumer behavior',reference='SYNTHETIC staged consumer lines')
    def test_missing_output_assessment_remains_pending_without_changing_record(self):
        path,ledger=self.output_ledger();original=json.dumps(ledger,sort_keys=True)
        result=h.stage_ledger(self.state,path,ledger)
        report=json.loads(Path(result['output_coverage_path']).read_text())
        self.assertEqual(report['rows'][0]['display'],'Pending')
        self.assertEqual(report['rows'][0]['outputs']['cv']['status'],'pending')
        self.assertEqual(json.dumps(ledger,sort_keys=True),original)
        self.assertFalse(result['imported']);self.assertEqual(result['output_review_status'],'pending')
    def test_teaching_website_only_is_visible_in_private_report(self):
        path,ledger=self.output_ledger(dict(cv=self.assessment('unsupported'),website=self.assessment('included')))
        result=h.stage_ledger(self.state,path,ledger)
        report=json.loads(Path(result['output_coverage_path']).read_text())
        self.assertEqual(report['rows'][0]['display'],'Website only')
        self.assertEqual(report['rows'][0]['outputs']['cv']['status'],'unsupported')
        self.assertNotIn('output_coverage',ledger['candidates'][0]['record'])
        self.assertIn('pending',report['user_review']);self.assertFalse(self.project.exists())
    def test_cv_only_does_not_treat_unrequested_website_as_omission(self):
        path,ledger=self.output_ledger(dict(cv=self.assessment('included')),goals='cv')
        result=h.stage_ledger(self.state,path,ledger)
        row=json.loads(Path(result['output_coverage_path']).read_text())['rows'][0]
        self.assertEqual(row['display'],'CV only');self.assertEqual(row['outputs']['website']['status'],'not_requested')
    def test_invalid_output_assessment_creates_no_ledger_transaction(self):
        path,ledger=self.output_ledger(dict(cv=dict(status='included',reason='No evidence',reference='')))
        before=set((self.state/'initialization-staging').iterdir())
        with self.assertRaisesRegex(ValueError,'references'):h.stage_ledger(self.state,path,ledger)
        self.assertEqual(set((self.state/'initialization-staging').iterdir()),before)
    def test_coverage_label_distinguishes_both_neither_and_unknown_goal(self):
        candidate=dict(id='one',target='honors.yml',output_coverage=dict(cv=self.assessment('included'),website=self.assessment('included')))
        self.assertEqual(h.output_coverage_report([candidate],'both')['rows'][0]['display'],'Both')
        candidate['output_coverage']=dict(cv=self.assessment('excluded'),website=self.assessment('unsupported'))
        self.assertEqual(h.output_coverage_report([candidate],'both')['rows'][0]['display'],'Neither')
        self.assertEqual(h.output_coverage_report([candidate],None)['rows'][0]['display'],'Pending')
    def test_unknown_output_status_is_refused(self):
        candidate=dict(id='one',target='honors.yml',output_coverage=dict(cv=self.assessment('render_verified')))
        with self.assertRaisesRegex(ValueError,'status'):h.output_coverage_report([candidate],'cv')
    def test_candidate_and_coverage_must_link_reciprocally(self):
        path,source=self.extract();ledger=self.ledger(source)
        ledger['candidates']=[dict(id='entry-1',source_ids=[source['segments'][0]['id']],target='honors.yml',record={})]
        with self.assertRaisesRegex(ValueError,'reciprocal'):h.stage_ledger(self.state,path,ledger)
    def test_different_source_hash_blocks_ledger(self):
        path,source=self.extract();ledger=self.ledger(source);ledger['source_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'different source'):h.stage_ledger(self.state,path,ledger)
    def test_starter_stages_privately_without_creating_project(self):
        self.start();result=h.stage_starter(self.state,'SYNTHETIC request')
        folder=Path(result['folder']);self.assertTrue((folder/'starter/data/education.yml').is_file())
        self.assertEqual((folder/'starter/data/education.yml').read_text().strip(),'[]')
        self.assertFalse(result['project_created']);self.assertFalse(self.project.exists());self.assertFalse((self.state/'config.json').exists())
    def test_staged_project_source_is_usable_and_separate_from_private_receipts(self):
        self.start();result=h.stage_starter(self.state,'SYNTHETIC request')
        source=Path(result['project_source_root']);metadata=Path(result['metadata_folder'])
        self.assertTrue((source/'_quarto.yml').is_file());self.assertTrue((source/'R/cv.R').is_file())
        self.assertEqual(result['folder'],str(metadata));self.assertEqual(source.parent,metadata)
        self.assertTrue((metadata/'operation.json').is_file());self.assertTrue((metadata/'completed.json').is_file())
        self.assertFalse((source/'operation.json').exists());self.assertFalse((source/'completed.json').exists())
        receipt=(metadata/'completed.json').read_bytes()
        resumed=h.status(self.state)['staged_operations'][0]['result']
        self.assertEqual(resumed['project_source_root'],str(source))
        self.assertEqual(resumed['metadata_folder'],str(metadata))
        self.assertEqual((metadata/'completed.json').read_bytes(),receipt)
        self.assertFalse(self.project.exists());self.assertFalse((self.state/'config.json').exists())
    def test_missing_project_layout_is_not_completed_staging(self):
        self.start();broken=self.base/'broken.zip'
        with zipfile.ZipFile(broken,'w') as z:z.writestr('starter/README.md','Incomplete synthetic archive')
        archive=zipfile.ZipFile(broken)
        with patch.object(h.zipfile,'ZipFile',return_value=archive):
            with self.assertRaisesRegex(ValueError,'expected project source root'):
                h.stage_starter(self.state,'SYNTHETIC request')
        operations=h.status(self.state)['staged_operations']
        self.assertEqual(len(operations),1);self.assertEqual(operations[0]['status'],'interrupted_or_in_progress')
        self.assertFalse((Path(operations[0]['folder'])/'completed.json').exists())
        self.assertFalse(self.project.exists())
    def test_duplicate_json_and_nonfinite_values_are_refused(self):
        for raw in (b'{"a":1,"a":2}',b'{"a":NaN}'):
            with self.assertRaises(ValueError):h.decode(raw)
    def test_probe_installs_nothing_and_does_not_claim_runtime_ready(self):
        with patch.object(h.shutil,'which',return_value=None):result=h.probes()
        self.assertTrue(result['installed_nothing']);self.assertIn('not account',result['github_account']);self.assertIn('require read-only probes',result['status'])
    def test_resume_exposes_saved_staging_without_reextracting(self):
        path,source=self.extract();result=h.status(self.state)
        self.assertEqual(len(result['staged_operations']),1)
        self.assertEqual(result['staged_operations'][0]['status'],'staged')
        self.assertNotIn('Education',json.dumps(result['staged_operations']))
    def test_interrupted_stage_is_not_reported_as_success(self):
        self.start();folder=self.state/'initialization-staging/interrupted';folder.mkdir(parents=True)
        (folder/'operation.json').write_text('{"status":"started"}')
        result=h.status(self.state);self.assertEqual(result['staged_operations'][0]['status'],'interrupted_or_in_progress')
    def test_profile_creation_stops_bootstrap_answer_mutations(self):
        self.start();before=(self.state/'initialization.json').read_bytes();(self.state/'config.json').write_text('{"canonical":true}')
        with self.assertRaisesRegex(ValueError,'Profile now exists'):self.answer('outputs','cv')
        self.assertEqual((self.state/'initialization.json').read_bytes(),before)
    def test_invalid_answer_container_and_path_type_are_refused(self):
        self.start()
        with self.assertRaises(ValueError):h.answer(self.state,[])
        with self.assertRaises(ValueError):self.answer('cv_source',123)
