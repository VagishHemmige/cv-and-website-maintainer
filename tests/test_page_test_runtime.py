"""Test-only R selection, including honest skip before any page staging."""
import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import test_page_adaptation as target

class PageRuntimeTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(dir=os.environ.get('TEST_TMP_ROOT'));self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name).resolve();self.rscript=self.root/'Rscript.exe';self.rscript.write_bytes(b'SYNTHETIC path fixture; never executed')
    def test_explicit_bin_overrides_other_runtime(self):
        with patch.dict(os.environ,{'TEST_R_BIN':str(self.root),'TEST_RSCRIPT':'missing'},clear=True):
            self.assertEqual(target.configured_quarto_r(),str(self.root))
    def test_derives_bin_from_explicit_rscript(self):
        with patch.dict(os.environ,{'TEST_RSCRIPT':str(self.rscript)},clear=True):
            self.assertEqual(target.configured_quarto_r(),str(self.root))
    def test_invalid_explicit_configuration_skips_without_host_fallback(self):
        for env in ({'TEST_R_BIN':'relative'},{'TEST_R_BIN':str(self.root/'missing')},{'TEST_RSCRIPT':str(self.root/'missing.exe')},{'TEST_RSCRIPT':'Rscript'}):
            with self.subTest(env=env),patch.dict(os.environ,env,clear=True),self.assertRaises(unittest.SkipTest):
                target.configured_quarto_r()
    def test_missing_runtime_skips_page_test_before_staging_or_commands(self):
        case=target.PageAdaptationTests('test_add_grants_hide_mentoring_empty_and_synthetic')
        result=unittest.TestResult()
        with patch.dict(os.environ,{'TEST_QUARTO':'SYNTHETIC not executed'},clear=True),patch.object(target.tempfile,'TemporaryDirectory') as stage,patch.object(target.subprocess,'run') as command:
            case.run(result);stage.assert_not_called();command.assert_not_called()
        self.assertEqual(len(result.skipped),1)
        self.assertIn('Set TEST_R_BIN or TEST_RSCRIPT',result.skipped[0][1])
        self.assertEqual(result.errors,[]);self.assertEqual(result.failures,[])
