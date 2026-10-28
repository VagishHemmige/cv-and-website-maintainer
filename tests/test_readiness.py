"""Readiness probes use synthetic failures; live checks require explicit test runtimes."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import readiness as m

class ReadinessTests(unittest.TestCase):
    def rows(self, report):
        return {row['component']:row for row in report['rows']}

    def fake(self, argv, env):
        if '--version' in argv:return '3.12.1',None
        if '--vanilla' in argv:
            return 'AR_READY_LIBS\t/synthetic/library\nAR_READY_PACKAGE\tyaml\tready\t2.3.10\nAR_READY_PACKAGE\tofficer\tblocked\t0.6.4\nAR_READY_PACKAGE\tRefManageR\tready\t1.4.0\n',None
        if '-I' in argv:return '{"pypdf":{"status":"ready","version":"6.0.0"}}',None
        raise AssertionError(argv)

    def test_goals_do_not_require_unselected_tools(self):
        with patch.object(m,'run',side_effect=self.fake),patch.object(m.setup,'executable',return_value=Path(sys.executable)):
            result=m.report(['records'],rscript=sys.executable)
        rows=self.rows(result)
        self.assertEqual(rows['Quarto']['status'],'not needed')
        self.assertEqual(rows['Git']['status'],'not needed')
        self.assertEqual(rows['R: yaml']['status'],'ready')
        self.assertFalse(result['network_checked'])

    def test_missing_candidate_is_not_global_absence(self):
        item,exe=m.tool('R',None,[],{},m.LINKS['r'])
        self.assertEqual(item['status'],'missing');self.assertIn('scope',item['detail'])
        self.assertIsNone(exe)

    def test_invalid_explicit_path_never_falls_back(self):
        with patch.object(m.shutil,'which') as search:
            self.assertEqual(m.selected('/missing/explicit','Rscript'),'/missing/explicit')
            search.assert_not_called()
        item,exe=m.tool('R','relative',[],{},m.LINKS['r'])
        self.assertEqual(item['status'],'blocked')

    def test_timeout_and_launch_failure_do_not_echo_exception(self):
        for error in [subprocess.TimeoutExpired(['SECRET'],30),PermissionError('SECRET')]:
            with self.subTest(error=type(error)),patch.object(m.subprocess,'run',side_effect=error):
                out,reason=m.run(['SYNTHETIC'],{})
                self.assertIsNone(out);self.assertNotIn('SECRET',reason)

    def test_failed_command_hides_stdout_and_stderr(self):
        with patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],1,b'SECRET',b'SECRET')):
            self.assertNotIn('SECRET',str(m.run([],{})))

    def test_corrupt_version_blocks(self):
        with patch.object(m.setup,'executable',return_value=Path(sys.executable)),patch.object(m,'run',return_value=('not a version',None)):
            self.assertEqual(m.tool('R',sys.executable,[],{},m.LINKS['r'])[0]['status'],'blocked')

    def test_officer_capability_failure_is_blocked_without_version_pin(self):
        with patch.object(m.setup,'executable',return_value=Path(sys.executable)),patch.object(m,'run',side_effect=self.fake):
            rows=self.rows(m.report(['cv'],rscript=sys.executable,packages=[]))
        self.assertEqual(rows['R: officer']['status'],'blocked')
        self.assertEqual(rows['R: RefManageR']['status'],'ready')

    def test_malformed_pdf_probe_is_blocked(self):
        for output in ['invalid','[]','{"pypdf": null}']:
            def fake(argv,env):
                return ('3.12.1',None) if '--version' in argv else (output,None)
            with self.subTest(output=output),patch.object(m.setup,'executable',return_value=Path(sys.executable)),patch.object(m,'run',side_effect=fake):
                self.assertEqual(self.rows(m.report(['pdf']))['pypdf']['status'],'blocked')

    def test_r_probe_failure_cannot_claim_loaded_packages(self):
        def fake(argv,env):
            return ('3.12.1',None) if '--version' in argv else (None,'blocked')
        with patch.object(m.setup,'executable',return_value=Path(sys.executable)),patch.object(m,'run',side_effect=fake):
            rows=self.rows(m.report(['records'],rscript=sys.executable))
        self.assertEqual(rows['R: yaml']['status'],'blocked')

    def test_alternate_r_library_and_safe_commands(self):
        calls=[]
        def fake(argv,env):
            calls.append((argv,env.copy()));return self.fake(argv,env)
        with patch.object(m.setup,'executable',return_value=Path(sys.executable)),patch.object(m,'run',side_effect=fake):
            m.report(['records','pdf','site'],rscript=sys.executable,r_library='/selected/library',quarto=sys.executable)
        rcall=next(x for x in calls if '--vanilla' in x[0])
        self.assertEqual(rcall[1]['ACADEMIC_READINESS_LIBRARY'],'/selected/library')
        self.assertNotIn('\n',rcall[0][-1])
        self.assertNotIn('"',rcall[0][-1])
        self.assertFalse(any('render' in argv or 'install' in argv for argv,env in calls))
        self.assertTrue(all('http' not in str(argv) for argv,env in calls))

    def test_git_reuses_preflight_and_hides_identity(self):
        for failure in [None,ValueError('Git name/email SECRET'),ValueError('Git signing SECRET')]:
            with patch.object(m.setup,'executable',return_value=Path(sys.executable)),patch.object(m,'run',side_effect=self.fake),patch.object(m.setup,'git_preflight',side_effect=failure) as check:
                result=m.report(['git'],git=sys.executable);check.assert_called_once()
                self.assertNotIn('SECRET',json.dumps(result))
                self.assertEqual(self.rows(result)['Git identity/signing']['status'],'blocked' if failure else 'ready')

    def test_environment_removes_git_redirects_and_no_prompt(self):
        with patch.dict(os.environ,{'GIT_DIR':'SECRET'}):
            env=m.environment()
        self.assertNotIn('GIT_DIR',env);self.assertEqual(env['GIT_TERMINAL_PROMPT'],'0')

    def test_invalid_inputs_rejected(self):
        for kwargs in [dict(goals=['unknown']),dict(packages=['system("x")']),dict(legacy_ppt=True)]:
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):m.report(**kwargs)

    def test_table_handles_newlines_and_pipe(self):
        text=m.table({'rows':[m.row('a|b','blocked','line\nnext',link=m.LINKS['r'])]})
        self.assertIn('a/b',text);self.assertIn('line next',text);self.assertIn(m.LINKS['r'],text)

    def test_real_python_pdf_import(self):
        rows=self.rows(m.report(['pdf'],python=sys.executable))
        self.assertEqual(rows['Python']['status'],'ready')
        self.assertEqual(rows['pypdf']['status'],'ready')

    def test_real_r_selected_library_and_officer_capability(self):
        exe=os.environ.get('TEST_RSCRIPT')
        if not exe:self.skipTest('TEST_RSCRIPT not configured')
        rows=self.rows(m.report(['cv'],rscript=exe,r_library=os.environ.get('TEST_R_LIBRARY')))
        for name in ['R','R libraries','R: yaml','R: officer','R: RefManageR']:
            self.assertEqual(rows[name]['status'],'ready',rows[name])

    def test_real_quarto_version_only(self):
        exe=os.environ.get('TEST_QUARTO')
        if not exe:self.skipTest('TEST_QUARTO not configured')
        rows=self.rows(m.report(['site'],rscript=os.environ.get('TEST_RSCRIPT'),r_library=os.environ.get('TEST_R_LIBRARY'),quarto=exe,packages=['yaml']))
        self.assertEqual(rows['Quarto']['status'],'ready')

    def test_real_git_synthetic_identity_no_repo_or_config_mutation(self):
        exe=os.environ.get('TEST_GIT')
        if not exe:self.skipTest('TEST_GIT not configured')
        with tempfile.TemporaryDirectory(dir=os.environ.get('TEST_TMP_ROOT')) as tmp:
            config=Path(tmp)/'gitconfig';config.write_text('[commit]\n gpgsign = false\n')
            before=config.read_bytes()
            env=dict(GIT_CONFIG_GLOBAL=str(config),GIT_CONFIG_NOSYSTEM='1',
                     GIT_AUTHOR_NAME='Synthetic',GIT_AUTHOR_EMAIL='test@example.invalid',
                     GIT_COMMITTER_NAME='Synthetic',GIT_COMMITTER_EMAIL='test@example.invalid')
            with patch.dict(os.environ,env):
                result=m.report(['git'],git=exe)
            self.assertEqual(self.rows(result)['Git identity/signing']['status'],'ready')
            self.assertEqual(config.read_bytes(),before)
            self.assertEqual(list(Path(tmp).iterdir()),[config])
            self.assertNotIn('test@example.invalid',json.dumps(result))
