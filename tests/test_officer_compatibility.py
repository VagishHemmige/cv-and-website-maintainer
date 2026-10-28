"""Minimal starter capability check; no package installs or user library changes."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]

class OfficerCompatibilityTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(dir=os.environ.get('TEST_TMP_ROOT'));self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name).resolve()
        with zipfile.ZipFile(ROOT/'assets/starter.zip') as archive:
            self.cv=archive.read('starter/R/cv.R').decode('utf-8').replace('\r\n','\n').replace('\r','')
            self.dependencies=archive.read('starter/DEPENDENCIES.md').decode('utf-8')

    def run_r(self,script):
        env=os.environ.copy()
        if env.get('TEST_R_LIBRARY'):env['R_LIBS_USER']=env['TEST_R_LIBRARY']
        path=self.root/'fixture.R';path.write_text(script,encoding='utf-8')
        return subprocess.run([os.environ['TEST_RSCRIPT'],str(path)],cwd=self.root,env=env,capture_output=True,text=True,timeout=45)

    def test_guard_precedes_inputs_and_output_creation_without_installer(self):
        check=self.cv.index('getNamespaceExports("officer")')
        self.assertLess(self.cv.index('library(officer)'),check)
        self.assertLess(check,self.cv.index('source("R/citations.R")'))
        self.assertLess(check,self.cv.index('dir.create("cv"'))
        self.assertNotIn('install.packages(',self.cv)
        self.assertIn('Missing packages keep R',self.dependencies)
        self.assertIn('Other package versions are not pinned',self.dependencies)

    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT'),'Set TEST_RSCRIPT for real R compatibility checks')
    def test_real_r_missing_export_blocks_before_any_project_input_or_output(self):
        (self.root/'cv.R').write_text(self.cv,encoding='utf-8')
        # Actual R/officer load; suppress one export at the observation boundary only.
        result=self.run_r('local({ getNamespaceExports <- function(ns) setdiff(base::getNamespaceExports(ns), "run_tab"); source("cv.R", local=environment()) })')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('requires officer::run_tab',result.stderr)
        self.assertIn('No packages were installed',result.stderr)
        self.assertNotIn('citations.R',result.stderr)
        self.assertFalse((self.root/'cv').exists())
        self.assertFalse(list(self.root.rglob('*.docx')))

    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT'),'Set TEST_RSCRIPT for real R compatibility checks')
    def test_real_r_available_export_passes_early_guard(self):
        prefix=self.cv.split('library(yaml)',1)[0]
        result=self.run_r(prefix+'\ncat("OFFICER_CAPABILITY_OK")\n')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('OFFICER_CAPABILITY_OK',result.stdout)
        self.assertFalse((self.root/'cv').exists())
