"""Real R generation with synthetic dates and exact approved setup outputs."""
import os,json,subprocess,unittest
from pathlib import Path
import test_starter_cleanup as fixtures
import test_setup_execution as setup
from unittest.mock import patch

@unittest.skipUnless(os.environ.get('TEST_RSCRIPT'),'Set TEST_RSCRIPT for real CV filename tests')
class CVFilenameTests(unittest.TestCase):
    setUp=fixtures.StarterCleanupTests.setUp
    project=fixtures.StarterCleanupTests.project
    def run_r(self,prefix):
        return subprocess.run([os.environ['TEST_RSCRIPT'],'-e',prefix+'; source("R/cv.R", encoding="UTF-8")'],cwd=self.root,env=self.env,capture_output=True,text=True,timeout=120)
    def test_real_r_pinned_name_does_not_consult_execution_date(self):
        result=self.run_r('options(academic_records.cv_filename="approved-CV.docx"); Sys.Date <- function() stop("Execution date must not choose pinned output")')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual([p.name for p in (self.root/'cv').glob('*.docx')],['approved-CV.docx'])
    def test_real_r_manual_run_keeps_dated_default(self):
        result=self.run_r('Sys.Date <- function() as.Date("2040-01-02")')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        files=list((self.root/'cv').glob('*.docx'));self.assertEqual(len(files),1)
        self.assertTrue(files[0].name.endswith('-CV-2040-01-02.docx'))
    def test_real_r_pinned_existing_file_never_overwritten(self):
        (self.root/'cv').mkdir(exist_ok=True);target=self.root/'cv/approved-CV.docx';target.write_bytes(b'SYNTHETIC existing output')
        before=target.read_bytes();result=self.run_r('options(academic_records.cv_filename="approved-CV.docx")')
        self.assertNotEqual(result.returncode,0);self.assertIn('CV output already exists',result.stderr)
        self.assertEqual(target.read_bytes(),before)
        self.assertEqual(list((self.root/'cv').glob('*.docx')),[target])
    def test_real_r_output_name_cannot_escape_cv_or_change_extension(self):
        for name in ('../outside.docx',str(self.base/'outside.docx'),'..\\outside.docx','nested/file.docx','bad.pdf',''):
            with self.subTest(name=name):
                result=self.run_r('options(academic_records.cv_filename='+json.dumps(name)+')')
                self.assertNotEqual(result.returncode,0);self.assertIn('simple .docx filename inside cv/',result.stderr)
                self.assertEqual(list((self.root/'cv').glob('*.docx')),[])
                self.assertFalse((self.base/'outside.docx').exists())

@unittest.skipUnless(os.environ.get('TEST_RSCRIPT'),'Set TEST_RSCRIPT for real setup date-boundary test')
class SetupDateBoundaryTests(unittest.TestCase):
    setUp=setup.SetupExecutionTests.setUp
    plan=setup.SetupExecutionTests.plan
    evidence=setup.SetupExecutionTests.evidence
    execute=setup.SetupExecutionTests.execute
    def test_real_r_setup_expected_file_survives_next_day_execution(self):
        staged=setup.h.init.stage_starter(self.state,'SYNTHETIC starter staging')
        self.spec['source']=staged['project_source_root']
        filename='approved-CV-2040-01-01.docx'
        code='options(academic_records.cv_filename="'+filename+'"); Sys.Date <- function() as.Date("2040-01-02"); source("R/cv.R", encoding="UTF-8")'
        self.spec['steps']=[dict(name='generate_cv',argv=[os.environ['TEST_RSCRIPT'],'-e',code],expected_files=['cv/'+filename])]
        plan=self.plan()
        self.assertFalse(self.project.exists())
        with patch.dict(os.environ,{'R_LIBS_USER':os.environ.get('TEST_R_LIBRARY','')}):result=self.execute(plan)
        self.assertTrue(result['local_commands_verified'])
        self.assertEqual([p.name for p in (self.project/'cv').glob('*.docx')],[filename])
        self.assertFalse((self.project/'cv/approved-CV-2040-01-02.docx').exists())
