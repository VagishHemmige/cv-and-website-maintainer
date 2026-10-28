"""Real starter output coverage; synthetic teaching remains website-only."""
import importlib.util
import json
import os
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

spec=importlib.util.spec_from_file_location('coverage_initializer',Path(__file__).resolve().parents[1]/'scripts/initialize.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)

class InitialOutputCoverageTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT') and os.environ.get('TEST_QUARTO'),'Set TEST_RSCRIPT and TEST_QUARTO for real output checks')
    def test_teaching_website_only_assessment_matches_real_starter_outputs(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TEST_TMP_ROOT')) as temp:
            base=Path(temp).resolve();state=base/'private';state.mkdir()
            h.start(state,True,'SYNTHETIC private storage')
            def answer(key,value):
                h.answer(state,dict(key=key,value=value,response='SYNTHETIC choice',reference='SYNTHETIC test conversation'))
            answer('outputs','both')
            source=base/'CV.txt';source.write_text('SYNTHETIC-COVERAGE-TEACHING-928 session',encoding='utf-8')
            answer('cv_source',str(source))
            extracted=h.extract(state,source,True,'not_flagged','SYNTHETIC private processing')
            extracted_path=Path(extracted['folder'])/'extracted.json'
            data=json.loads(extracted_path.read_text());sid=data['segments'][0]['id']
            staged=h.stage_starter(state,'SYNTHETIC stage request')
            project=base/'project'
            shutil.copytree(Path(staged['project_source_root']),project)
            record=dict(title='SYNTHETIC-COVERAGE-TEACHING-928',venue='Example hospital',dates=['2024-01-01'],target='Residents',description='Synthetic only',category='teaching',slides=None,link=None)
            # Direct construction is a disposable fixture, never a real approved import.
            (project/'data/teaching.yml').write_text('- title: SYNTHETIC-COVERAGE-TEACHING-928\n  venue: Example hospital\n  dates: [2024-01-01]\n  target: Residents\n  description: Synthetic only\n  category: teaching\n  slides: null\n  link: null\n',encoding='utf-8')
            ledger=dict(source_sha256=data['source_sha256'],coverage=[dict(source_id=sid,disposition='candidate',candidate_ids=['session'],reason='Synthetic source session')],candidates=[dict(id='session',source_ids=[sid],target='teaching.yml',record=record,output_coverage=dict(cv=dict(status='unsupported',reason='Starter CV consumer has no teaching section',reference='SYNTHETIC inspected R/cv.R'),website=dict(status='included',reason='Teaching page consumes this session',reference='SYNTHETIC inspected teaching.qmd')))])
            result=h.stage_ledger(state,extracted_path,ledger)
            report=json.loads(Path(result['output_coverage_path']).read_text())
            self.assertEqual(report['rows'][0]['display'],'Website only')
            self.assertEqual(result['output_review_status'],'pending');self.assertFalse(result['imported'])
            env=dict(os.environ,R_LIBS_USER=os.environ.get('TEST_R_LIBRARY',''),QUARTO_R=str(Path(os.environ['TEST_RSCRIPT']).parent))
            for argv in [[os.environ['TEST_RSCRIPT'],'R/cv.R'],[os.environ['TEST_QUARTO'],'render']]:
                proc=subprocess.run(argv,cwd=project,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
                self.assertEqual(proc.returncode,0,proc.stdout[-3000:]+proc.stderr[-3000:])
            cv=list((project/'cv').glob('*.docx'));self.assertEqual(len(cv),1)
            with zipfile.ZipFile(cv[0]) as z:xml=z.read('word/document.xml').decode('utf-8')
            self.assertNotIn(record['title'],xml)
            self.assertIn(record['title'],(project/'docs/teaching.html').read_text(encoding='utf-8'))
            self.assertNotIn('output_coverage',(project/'data/teaching.yml').read_text())
            self.assertFalse((state/'config.json').exists())
            self.assertEqual(json.loads(Path(result['output_coverage_path']).read_text()),report)

if __name__=='__main__':unittest.main()
