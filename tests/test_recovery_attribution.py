"""Recovery attribution on disposable records; approvals/evidence are synthetic."""
import json
import contextlib
import io
import sys
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import test_failed_recovery as base
import test_proposals as fixtures

h=fixtures.helper

class RecoveryAttributionTests(unittest.TestCase):
    setUp = base.FailedRecoveryTests.setUp
    fixture = base.FailedRecoveryTests.fixture
    save_config = base.FailedRecoveryTests.save_config
    cli = base.FailedRecoveryTests.cli
    runtime = base.FailedRecoveryTests.runtime
    propose = base.FailedRecoveryTests.propose
    apply = base.FailedRecoveryTests.apply
    receipt = base.FailedRecoveryTests.receipt
    snapshot = base.FailedRecoveryTests.snapshot
    def fail_target(self):
        self.fixture();ident=self.propose();target=self.data/'teaching.yml';real=h.atomic_write
        def fail(path,content):
            if Path(path)==target:raise OSError('SYNTHETIC refusal before replacement')
            return real(path,content)
        with patch.object(h,'atomic_write',side_effect=fail):
            with self.assertRaises(ValueError):self.apply(ident)
        return ident
    def test_failed_target_write_cannot_borrow_identical_later_save(self):
        old=self.fail_target();folder,_=h.read_proposal(self.state,old)
        history=self.snapshot(folder)
        new=self.propose();self.assertEqual(self.apply(new)['status'],'verified_saved')
        before=self.snapshot(self.data)
        self.assertEqual(h.proposal_status(self.state,old),'failed_before_write')
        with self.assertRaisesRegex(ValueError,'Verification requires saved_unverified'):
            self.cli('verify',self.state,old,*self.runtime())
        self.assertEqual(self.snapshot(self.data),before);self.assertEqual(self.snapshot(folder),history)
        self.assertFalse(self.receipt(old).exists())
        self.assertFalse(self.cli('status',self.state,old)['historical_save_verified'])
    def test_legacy_matching_bytes_without_write_evidence_cannot_create_receipt(self):
        self.fixture();ident=self.propose()
        with fixtures.ProposalTests.mutate_after_live_validation(self,lambda: (_ for _ in ()).throw(ValueError('SYNTHETIC after write'))):
            with self.assertRaises(ValueError):self.apply(ident)
        folder,_=h.read_proposal(self.state,ident)
        for p in (folder/'attempts').glob('*.json'):
            value=json.loads(p.read_text())
            for key in ('write_evidence_version','target_write_confirmed','target_written_sha256'):
                value.pop(key,None)
            p.write_text(json.dumps(value),encoding='utf-8')
        before=self.snapshot(folder);data=self.snapshot(self.data)
        with self.assertRaisesRegex(ValueError,'confirmed target write'):
            self.cli('verify',self.state,ident,*self.runtime())
        self.assertFalse(self.receipt(ident).exists());self.assertEqual(self.snapshot(folder),before)
        self.assertEqual(self.snapshot(self.data),data)
    def test_preexisting_bad_recovery_receipt_is_flagged_without_rewriting_it(self):
        ident=self.fail_target();folder,_=h.read_proposal(self.state,ident)
        new=self.propose();self.apply(new)
        self.receipt(ident).write_text(json.dumps(dict(recovered=True,approval_assertion=ident)),encoding='utf-8')
        before=self.snapshot(folder)
        details=self.cli('status',self.state,ident)
        self.assertEqual(details['status'],'conflict')
        self.assertFalse(details['historical_save_verified'])
        self.assertEqual(details['write_attribution'],'contradictory_recovery_history')
        self.assertEqual(self.snapshot(folder),before)
    def test_confirmed_write_then_external_restore_is_conflict_not_prewrite_failure(self):
        self.fixture();ident=self.propose()
        def interrupt():raise ValueError('SYNTHETIC post-write interruption')
        with fixtures.ProposalTests.mutate_after_live_validation(self,interrupt):
            with self.assertRaises(ValueError):self.apply(ident)
        folder,item=h.read_proposal(self.state,ident)
        attempt=json.loads(next((folder/'attempts').glob('*.json')).read_text())
        self.assertTrue(attempt['target_write_confirmed'])
        self.assertEqual(attempt['target_written_sha256'],item['candidate_sha256'])
        (self.data/'teaching.yml').write_bytes((folder/'backup/teaching.yml').read_bytes())
        self.assertEqual(h.proposal_status(self.state,ident),'conflict')
        self.assertFalse(self.receipt(ident).exists())
    def test_pending_failed_proposal_is_not_closed_by_identical_later_save(self):
        old=self.fail_target()
        payload=self.base/'pending.json'
        payload.write_text(json.dumps(dict(kind='teaching',facts={},missing_fields=['venue'],questions=['Which venue?'],sources=['synthetic'])))
        pending=self.cli('remember',self.state,payload)['id']
        h.event_pending(self.state,pending,dict(status='awaiting_approval',proposal_id=old,missing_fields=[],questions=[]))
        new=self.propose();self.apply(new)
        row=h.read_pending(self.state,pending)
        self.assertEqual(row['status'],'needs_review')
        self.assertFalse(row['historical_save_verified'])
        self.assertFalse(self.receipt(old).exists())
    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT'),'Set TEST_RSCRIPT for real R/yaml')
    def test_real_r_failed_target_cannot_borrow_identical_later_save(self):
        self.stub.stop();self.test_failed_target_write_cannot_borrow_identical_later_save()


    def legacy_recovered(self, status='applying'):
        ident=self.fail_target();folder,item=h.read_proposal(self.state,ident)
        new=self.propose();self.apply(new)
        for path in (folder/'attempts').glob('*.json'):
            attempt=json.loads(path.read_text(encoding='utf-8'))
            for key in ('write_evidence_version','target_write_confirmed','target_written_sha256'):
                attempt.pop(key,None)
            attempt.update(status=status,error='Source changed before write: teaching.yml')
            path.write_text(json.dumps(attempt),encoding='utf-8')
        self.receipt(ident).write_text(json.dumps(dict(recovered=True,approval_assertion=ident)),encoding='utf-8')
        return ident

    def test_legacy_applying_and_saved_unverified_receipts_are_uncertain_read_only(self):
        for status in ('applying','saved_unverified'):
            with self.subTest(status=status):
                # Each proposal history is synthetic; matching bytes came from another save.
                if status=='saved_unverified':
                    self.fixture()
                ident=self.legacy_recovered(status);folder,_=h.read_proposal(self.state,ident)
                before=self.snapshot(folder);data=self.snapshot(self.data)
                details=self.cli('status',self.state,ident)
                self.assertEqual(details['status'],'legacy_recovery_unattributed')
                self.assertEqual(details['write_attribution'],'legacy_recovery_unattributed')
                self.assertFalse(details['historical_save_verified'])
                with self.assertRaisesRegex(ValueError,'legacy_recovery_unattributed'):
                    self.cli('verify',self.state,ident,*self.runtime())
                self.assertEqual(self.snapshot(folder),before);self.assertEqual(self.snapshot(self.data),data)

    def test_legacy_recovered_receipt_without_attempts_stays_uncertain_after_drift(self):
        self.fixture();ident=self.propose();folder,_=h.read_proposal(self.state,ident)
        self.receipt(ident).write_text('{"recovered":true}',encoding='utf-8')
        details=self.cli('status',self.state,ident)
        self.assertFalse(details['historical_save_verified'])
        self.assertEqual(details['write_attribution'],'legacy_recovery_unattributed')

    def test_normal_legacy_nonrecovered_receipt_retains_historical_success(self):
        self.fixture();ident=self.propose();self.apply(ident)
        folder,_=h.read_proposal(self.state,ident)
        for path in (folder/'attempts').glob('*.json'):
            value=json.loads(path.read_text())
            for key in ('write_evidence_version','target_write_confirmed','target_written_sha256'):value.pop(key,None)
            path.write_text(json.dumps(value),encoding='utf-8')
        before=self.snapshot(folder)
        self.assertTrue(self.cli('status',self.state,ident)['historical_save_verified'])
        self.assertEqual(self.snapshot(folder),before)

    def test_evidenced_recovery_receipt_still_verifies(self):
        self.fixture();ident=self.propose()
        with fixtures.ProposalTests.mutate_after_live_validation(self,lambda: (_ for _ in ()).throw(ValueError('SYNTHETIC interruption'))):
            with self.assertRaises(ValueError):self.apply(ident)
        self.cli('verify',self.state,ident,*self.runtime())
        details=self.cli('status',self.state,ident)
        self.assertEqual(details['status'],'verified_saved')
        self.assertTrue(details['historical_save_verified'])

    def test_pending_list_does_not_certify_legacy_receipt_or_rewrite_terminal_history(self):
        ident=self.legacy_recovered()
        payload=self.base/'pending-legacy.json'
        payload.write_text(json.dumps(dict(kind='teaching',facts={},missing_fields=['venue'],questions=['Which venue?'],sources=['synthetic'])))
        pending=self.cli('remember',self.state,payload)['id']
        h.event_pending(self.state,pending,dict(status='awaiting_approval',proposal_id=ident,missing_fields=[],questions=[]))
        before=self.snapshot(self.state)
        row=h.read_pending(self.state,pending)
        self.assertEqual(row['status'],'needs_review')
        self.assertFalse(row['historical_save_verified'])
        self.assertTrue(row['historical_reconciliation_required'])
        output=io.StringIO()
        with patch.object(sys,'argv',['proposals.py','list',str(self.state)]), contextlib.redirect_stdout(output):
            h.main()
        self.assertIn('needs_review',output.getvalue())
        self.assertEqual(self.snapshot(self.state),before)
        # Preserve an explicit historical terminal event while flagging its unsupported receipt.
        with self.assertRaisesRegex(ValueError,'Cannot mark applied'):
            h.event_pending(self.state,pending,dict(status='applied'))
        # Construct a pre-existing legacy event, not a newly authorized applied transition.
        h.append_pending_event(self.state,pending,dict(status='applied',proposal_id=ident))
        before=self.snapshot(self.state);row=h.read_pending(self.state,pending)
        self.assertEqual(row['status'],'applied')
        self.assertTrue(row['historical_reconciliation_required'])
        self.assertFalse(row['historical_save_verified'])
        self.assertEqual(self.snapshot(self.state),before)

    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT'),'Set TEST_RSCRIPT for real R/yaml')
    def test_real_r_legacy_recovery_does_not_borrow_identical_save(self):
        self.stub.stop()
        self.test_legacy_applying_and_saved_unverified_receipts_are_uncertain_read_only()


if __name__=='__main__':unittest.main()
