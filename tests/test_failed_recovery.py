"""Interrupted-apply recovery on disposable records; approvals are synthetic."""
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import test_proposals as baseline
from approval_fixture import approval_file

helper = baseline.helper


class FailedRecoveryTests(unittest.TestCase):
    setUp = baseline.ProposalTests.setUp
    fixture = baseline.ProposalTests.fixture
    save_config = baseline.ProposalTests.save_config
    cli = baseline.ProposalTests.cli
    runtime = baseline.ProposalTests.runtime
    propose = baseline.ProposalTests.propose
    apply = baseline.ProposalTests.apply
    receipt = baseline.ProposalTests.receipt

    def fail_copy(self):
        self.fixture()
        ident = self.propose()
        before = (self.data/'teaching.yml').read_bytes()
        with patch.object(helper.shutil, 'copy2', side_effect=OSError('Synthetic backup copy failure')):
            with self.assertRaisesRegex(ValueError, 'fresh proposal') as error:
                self.apply(ident)
        self.assertIn('outcome=failed_before_write', str(error.exception))
        self.assertIn('new exact approval', str(error.exception))
        self.assertEqual((self.data/'teaching.yml').read_bytes(), before)
        self.assertEqual(helper.proposal_status(self.state, ident), 'failed_before_write')
        return ident

    def snapshot(self, folder):
        return {str(p.relative_to(folder)):p.read_bytes() for p in folder.rglob('*') if p.is_file()}

    def test_empty_backup_failure_refuses_reapply_and_preserves_evidence(self):
        ident = self.fail_copy()
        folder, _ = helper.read_proposal(self.state, ident)
        self.assertTrue((folder/'backup').is_dir())
        before = self.snapshot(folder)
        with self.assertRaisesRegex(ValueError, 'cannot be reapplied'):
            self.apply(ident)
        self.assertEqual(self.snapshot(folder), before)
        self.assertFalse(self.receipt(ident).exists())

    def test_matching_backup_does_not_enable_retry(self):
        self.fixture()
        ident = self.propose()
        real_atomic = helper.atomic_write
        target = self.data/'teaching.yml'
        def fail_target(path, content):
            if Path(path) == target:
                raise OSError('Synthetic target write refusal')
            return real_atomic(path, content)
        with patch.object(helper, 'atomic_write', side_effect=fail_target):
            with self.assertRaisesRegex(ValueError, 'failed_before_write'):
                self.apply(ident)
        folder, item = helper.read_proposal(self.state, ident)
        self.assertEqual(helper.digest(folder/'backup/teaching.yml'), item['before']['teaching.yml'])
        before = self.snapshot(folder)
        with self.assertRaisesRegex(ValueError, 'cannot be reapplied'):
            self.apply(ident)
        self.assertEqual(self.snapshot(folder), before)

    def test_fresh_identical_diff_needs_new_approval_then_saves(self):
        old = self.fail_copy()
        folder, item = helper.read_proposal(self.state, old)
        history = self.snapshot(folder)
        new = self.propose()
        new_folder, new_item = helper.read_proposal(self.state, new)
        self.assertNotEqual(new, old)
        self.assertEqual((folder/'diff.txt').read_bytes(), (new_folder/'diff.txt').read_bytes())
        evidence = approval_file(self.state, 'yaml', old, item['candidate_sha256'], self.data/item['file'])
        with self.assertRaises(ValueError):
            self.cli('apply', self.state, new, '--approval', new, '--approval-evidence', evidence, *self.runtime())
        self.assertEqual(helper.proposal_status(self.state, new), 'awaiting_approval')
        self.assertEqual(self.apply(new)['status'], 'verified_saved')
        self.assertEqual(self.snapshot(folder), history)
        # The old failed attempt must not acquire status/history from the newer save.
        self.assertEqual(helper.proposal_status(self.state, old), 'failed_before_write')
        self.assertFalse(self.receipt(old).exists())

    def test_fresh_proposal_uses_current_sources(self):
        old = self.fail_copy()
        talks = self.data/'talks.yml'
        talks.write_text(talks.read_text().replace('Example talk', 'Later talk'), encoding='utf-8')
        new = self.propose()
        _, item = helper.read_proposal(self.state, new)
        self.assertEqual(item['before']['talks.yml'], helper.digest(talks))
        self.assertEqual(self.apply(new)['status'], 'verified_saved')
        self.assertIn('Later talk', talks.read_text())

    def test_failed_attempt_cannot_use_verify(self):
        ident = self.fail_copy()
        with self.assertRaisesRegex(ValueError, 'Verification requires saved_unverified'):
            self.cli('verify', self.state, ident, *self.runtime())
        self.assertFalse(self.receipt(ident).exists())

    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT'), 'Set TEST_RSCRIPT for real R/yaml integration')
    def test_real_r_fresh_proposal_after_backup_failure(self):
        self.stub.stop()
        old = self.fail_copy()
        folder, _ = helper.read_proposal(self.state, old)
        history = self.snapshot(folder)
        new = self.propose()
        self.assertEqual(self.apply(new)['status'], 'verified_saved')
        self.assertEqual(self.snapshot(folder), history)



    def test_identical_other_save_inside_prewrite_window_is_failed_before_write(self):
        import json
        self.fixture()
        old=self.propose();new=self.propose()
        old_folder,old_item=helper.read_proposal(self.state,old)
        payload=self.base/'pending-race.json'
        payload.write_text(json.dumps(dict(kind='teaching',facts={},missing_fields=['venue'],questions=['Which venue?'],sources=['synthetic'])))
        pending=self.cli('remember',self.state,payload)['id']
        helper.event_pending(self.state,pending,dict(status='awaiting_approval',proposal_id=old,missing_fields=[],questions=[]))
        real_copy=helper.shutil.copy2
        written=[]
        def other_save(source,destination,*args,**kwargs):
            result=real_copy(source,destination,*args,**kwargs)
            if Path(destination)==old_folder/'backup/teaching.yml':
                written.append(self.apply(new)['status'])
            return result
        with patch.object(helper.shutil,'copy2',side_effect=other_save):
            with self.assertRaisesRegex(ValueError,'outcome=failed_before_write') as error:
                self.apply(old)
        self.assertIn('Source changed before write',str(error.exception))
        self.assertEqual(written,['verified_saved'])
        attempt=json.loads(next((old_folder/'attempts').glob('*.json')).read_text())
        self.assertEqual(attempt['status'],'failed_before_write')
        self.assertFalse(attempt['target_write_confirmed'])
        self.assertEqual(helper.proposal_status(self.state,old),'failed_before_write')
        self.assertEqual(helper.proposal_status(self.state,new),'verified_saved')
        self.assertEqual(helper.read_pending(self.state,pending)['status'],'needs_review')
        self.assertFalse(self.receipt(old).exists())
        before=self.snapshot(old_folder);data=self.snapshot(self.data)
        with self.assertRaisesRegex(ValueError,'Verification requires saved_unverified'):
            self.cli('verify',self.state,old,*self.runtime())
        self.assertEqual(self.snapshot(old_folder),before)
        self.assertEqual(self.snapshot(self.data),data)

    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT'),'Set TEST_RSCRIPT for real R/yaml integration')
    def test_real_r_identical_other_save_inside_prewrite_window(self):
        self.stub.stop()
        self.test_identical_other_save_inside_prewrite_window_is_failed_before_write()


if __name__ == '__main__':
    unittest.main()

