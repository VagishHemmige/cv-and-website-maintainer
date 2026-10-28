"""B4: disposable Git preflight gates; no user Git config/key changes."""
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import test_setup_execution as base
h=base.h

class GitPreflightTests(unittest.TestCase):
    setUp=base.SetupExecutionTests.setUp
    plan=base.SetupExecutionTests.plan
    evidence=base.SetupExecutionTests.evidence
    execute=base.SetupExecutionTests.execute
    configure_git=base.SetupExecutionTests.configure_git

    def test_missing_name_or_email_blocks_plan_before_destination(self):
        self.configure_git()
        for values in ({'GIT_AUTHOR_NAME':'','GIT_COMMITTER_NAME':''},
                       {'GIT_AUTHOR_EMAIL':'','GIT_COMMITTER_EMAIL':''}):
            with self.subTest(values=values),patch.dict(os.environ,values):
                with self.assertRaisesRegex(ValueError,'name/email'):
                    self.plan()
                self.assertFalse(self.project.exists())
                self.assertFalse((self.state/'setup-plans').exists())

    def test_identity_loss_at_execution_leaves_plan_retryable_and_no_outputs(self):
        self.configure_git();plan=self.plan();folder=self.state/'setup-plans'/plan['id']
        with patch.dict(os.environ,{'GIT_COMMITTER_EMAIL':''}):
            with self.assertRaisesRegex(ValueError,'name/email'):
                self.execute(plan)
        self.assertFalse(self.project.exists())
        self.assertFalse((folder/'started.json').exists())
        result=self.execute(plan)
        self.assertIsNotNone(result['commit'])
        self.assertEqual((self.project/'index.txt').read_text(),'SYNTHETIC public content')

    def test_enabled_signing_holds_without_disabling_or_using_keys(self):
        self.configure_git()
        config=Path(os.environ['GIT_CONFIG_GLOBAL']);config.write_text('[commit]\n gpgsign = true\n')
        before=config.read_bytes()
        with self.assertRaisesRegex(ValueError,'signing is enabled'):
            self.plan()
        self.assertFalse(self.project.exists())
        self.assertEqual(config.read_bytes(),before)

    def test_signing_enabled_after_plan_blocks_before_started_marker(self):
        self.configure_git();plan=self.plan();config=Path(os.environ['GIT_CONFIG_GLOBAL'])
        config.write_text('[commit]\n gpgsign = true\n')
        with self.assertRaisesRegex(ValueError,'signing is enabled'):self.execute(plan)
        self.assertFalse(self.project.exists())
        self.assertFalse((self.state/'setup-plans'/plan['id']/'started.json').exists())

    def test_git_free_setup_does_not_probe_identity(self):
        with patch.object(h,'git_preflight',side_effect=AssertionError('Git-free setup must not probe Git')):
            result=self.execute(self.plan())
        self.assertIsNone(result['commit'])

    def test_probe_timeout_blocks_before_creating_destination(self):
        self.configure_git()
        with patch.object(h.subprocess,'run',side_effect=h.subprocess.TimeoutExpired('synthetic git',30)):
            with self.assertRaisesRegex(ValueError,'preflight could not run'):self.plan()
        self.assertFalse(self.project.exists())

if __name__=='__main__':unittest.main()

