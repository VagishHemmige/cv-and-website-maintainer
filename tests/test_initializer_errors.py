"""Initializer blockers preserve sources and existing state; no installation/cleanup."""
import json,os,subprocess,sys,unittest
from pathlib import Path
from unittest.mock import patch
import test_initialize as base

h=base.h
SCRIPT=Path(__file__).resolve().parents[1]/'scripts/initialize.py'

class InitializerErrorTests(unittest.TestCase):
    setUp=base.InitializationTests.setUp
    start=base.InitializationTests.start
    answer=base.InitializationTests.answer
    def pdf_source(self):
        self.start();source=self.base/'synthetic.pdf';source.write_bytes(b'%PDF- SYNTHETIC source only; parser must not be reached')
        self.answer('cv_source',str(source));return source
    def test_missing_pypdf_is_actionable_without_staging_or_source_change(self):
        source=self.pdf_source();before=source.read_bytes();state=(self.state/'initialization.json').read_bytes()
        with patch.dict(sys.modules,{'pypdf':None}),self.assertRaisesRegex(ValueError,'working pypdf installation.*No packages were installed'):
            h.extract(self.state,source,True,'not_flagged','SYNTHETIC approval')
        self.assertEqual(source.read_bytes(),before);self.assertEqual((self.state/'initialization.json').read_bytes(),state)
        self.assertFalse((self.state/'initialization-staging').exists())
        self.assertFalse((self.state/'.initialization-writer.lock').exists())
    def test_existing_lock_is_actionable_and_untouched(self):
        self.start();path=self.state/'.initialization-writer.lock';path.write_bytes(b'SYNTHETIC preserved lock')
        before=(self.state/'initialization.json').read_bytes()
        with self.assertRaisesRegex(FileExistsError,'may be active or interrupted.*Preserve the lock and history'):
            self.answer('outputs','cv')
        self.assertEqual(path.read_bytes(),b'SYNTHETIC preserved lock')
        self.assertEqual((self.state/'initialization.json').read_bytes(),before)
    def test_cli_missing_pypdf_has_no_traceback(self):
        source=self.pdf_source()
        code='import sys,runpy; sys.modules["pypdf"]=None; sys.argv='+repr([str(SCRIPT),'extract',str(self.state),str(source),'--private-processing-approved','--source-screening','not_flagged','--reference','SYNTHETIC approval'])+'; runpy.run_path('+repr(str(SCRIPT))+',run_name="__main__")'
        result=subprocess.run([sys.executable,'-B','-c',code],capture_output=True,text=True,timeout=30)
        self.assertNotEqual(result.returncode,0);self.assertIn('working pypdf installation',result.stderr)
        self.assertNotIn('Traceback',result.stderr);self.assertNotIn('ModuleNotFoundError',result.stderr)
        self.assertFalse((self.state/'initialization-staging').exists())
    def test_cli_existing_lock_has_clear_blocker_without_traceback(self):
        marker=self.state/'.initialization-writer.lock';marker.write_text('SYNTHETIC other worker')
        result=subprocess.run([sys.executable,'-B',str(SCRIPT),'start',str(self.state),'--private-storage-confirmed','--reference','SYNTHETIC storage'],capture_output=True,text=True,timeout=30)
        self.assertNotEqual(result.returncode,0);self.assertIn('writer lock already exists',result.stderr)
        self.assertIn('Do not delete the lock',result.stderr);self.assertNotIn('Traceback',result.stderr)
        self.assertEqual(marker.read_text(),'SYNTHETIC other worker')
        self.assertFalse((self.state/'initialization.json').exists())
