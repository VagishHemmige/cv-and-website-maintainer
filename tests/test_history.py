"""F4: save history and closed pending items, using disposable fixture data."""
import contextlib
import io
import json
import os
import sys
import unittest
from unittest.mock import patch
import test_proposals as base

helper = base.helper


class HistoryTests(unittest.TestCase):
    setUp = base.ProposalTests.setUp
    fixture = base.ProposalTests.fixture
    save_config = base.ProposalTests.save_config
    cli = base.ProposalTests.cli
    runtime = base.ProposalTests.runtime
    propose = base.ProposalTests.propose
    apply = base.ProposalTests.apply
    receipt = base.ProposalTests.receipt

    def pending(self, proposal, terminal=None):
        payload = self.base / 'pending-input.json'
        payload.write_text(json.dumps(dict(kind='teaching', facts={},
            missing_fields=['venue'], questions=['Which venue?'], sources=['synthetic fixture'])))
        ident = self.cli('remember', self.state, payload)['id']
        helper.event_pending(self.state, ident, dict(status='awaiting_approval',
            proposal_id=proposal, missing_fields=[], questions=[]))
        if terminal:
            helper.event_pending(self.state, ident, dict(status=terminal))
        return ident

    def second_save(self):
        candidate = self.base / 'second.yml'
        candidate.write_text((self.data / 'teaching.yml').read_text().replace(
            'Approved teaching', 'Later approved teaching'))
        ident = self.cli('propose', self.state, self.data, 'teaching.yml',
                         candidate, *self.runtime())['id']
        self.apply(ident)
        return ident

    def private_bytes(self):
        return {str(p.relative_to(self.state)): p.read_bytes()
                for p in self.state.rglob('*') if p.is_file()}

    def test_successive_saves_preserve_history_and_receipt(self):
        self.fixture()
        first = self.propose()
        self.apply(first)
        receipt = self.receipt(first).read_bytes()
        second = self.second_save()
        details = self.cli('status', self.state, first)
        self.assertEqual(details['status'], 'changed_after_save')
        self.assertTrue(details['historical_save_verified'])
        self.assertFalse(details['current_snapshot_matches'])
        self.assertIn('teaching.yml', details['changed_files'])
        self.assertEqual(self.receipt(first).read_bytes(), receipt)
        self.assertEqual(self.cli('status', self.state, second)['status'], 'verified_saved')

    def test_recorded_applied_item_cannot_reopen_after_later_save(self):
        self.fixture()
        first = self.propose()
        self.apply(first)
        pending = self.pending(first, 'applied')
        self.second_save()
        before = self.private_bytes()
        with self.assertRaisesRegex(ValueError, 'Terminal item cannot be reopened'):
            helper.event_pending(self.state, pending, dict(status='needs_information'))
        self.assertEqual(helper.read_pending(self.state, pending)['status'], 'applied')
        self.assertEqual(self.private_bytes(), before)

    def test_receipt_closes_linked_item_even_without_explicit_applied_event(self):
        self.fixture()
        first = self.propose()
        pending = self.pending(first)
        self.apply(first)
        self.second_save()
        item = helper.read_pending(self.state, pending)
        self.assertEqual(item['status'], 'applied')
        self.assertEqual(item['proposal_status'], 'changed_after_save')
        with self.assertRaisesRegex(ValueError, 'Terminal item cannot be reopened'):
            helper.event_pending(self.state, pending, dict(status='needs_information'))

    def test_rejected_and_superseded_stay_closed_with_history_details(self):
        self.fixture()
        first = self.propose()
        rejected = self.pending(first, 'rejected')
        superseded = self.pending(first, 'superseded')
        self.apply(first)
        self.second_save()
        for ident, expected in ((rejected, 'rejected'), (superseded, 'superseded')):
            with self.subTest(status=expected):
                item = helper.read_pending(self.state, ident)
                self.assertEqual(item['status'], expected)
                self.assertTrue(item['historical_save_verified'])
                with self.assertRaisesRegex(ValueError, 'Terminal item cannot be reopened'):
                    helper.event_pending(self.state, ident, dict(status='awaiting_approval'))

    def test_unreceipted_conflict_still_requires_review(self):
        self.fixture()
        first = self.propose()
        pending = self.pending(first)
        target = self.data / 'teaching.yml'
        target.write_text(target.read_text().replace('Example teaching', 'Unexpected teaching'))
        self.assertEqual(self.cli('status', self.state, first)['status'], 'conflict')
        self.assertFalse(self.receipt(first).exists())
        self.assertEqual(helper.read_pending(self.state, pending)['status'], 'needs_review')

    def test_legacy_reopening_events_do_not_override_terminal_history(self):
        self.fixture()
        proposal = self.propose()
        self.apply(proposal)
        for terminal in ('applied', 'rejected', 'superseded'):
            with self.subTest(status=terminal):
                # Construct the rejected/superseded case without a linked receipt,
                # so protection comes from event history rather than save inference.
                payload = self.base / 'legacy-input.json'
                payload.write_text(json.dumps(dict(kind='teaching', facts={},
                    missing_fields=['venue'], questions=['Which venue?'], sources=[])))
                ident = self.cli('remember', self.state, payload)['id']
                if terminal == 'applied':
                    helper.event_pending(self.state, ident, dict(status='applied', proposal_id=proposal))
                else:
                    helper.event_pending(self.state, ident, dict(status=terminal))
                invalid = self.state / 'events' / ident / 'zz-legacy-reopen.json'
                invalid.write_text(json.dumps(dict(status='needs_information', created='legacy fixture')))
                before = self.private_bytes()
                item = helper.read_pending(self.state, ident)
                self.assertEqual(item['status'], terminal)
                self.assertEqual(item['ignored_reopen_events'], [invalid.name])
                self.assertEqual(self.private_bytes(), before)

    def test_missing_saved_file_reports_drift_without_reopening_completed_item(self):
        self.fixture()
        first = self.propose()
        self.apply(first)
        pending = self.pending(first, 'applied')
        (self.data / 'teaching.yml').unlink()
        details = helper.proposal_details(self.state, first)
        self.assertEqual(details['status'], 'changed_after_save')
        self.assertIn('teaching.yml', details['changed_files'])
        self.assertEqual(helper.read_pending(self.state, pending)['status'], 'applied')

    def test_reverting_to_original_bytes_keeps_verified_history(self):
        self.fixture()
        original = (self.data / 'teaching.yml').read_bytes()
        first = self.propose()
        self.apply(first)
        (self.data / 'teaching.yml').write_bytes(original)
        self.assertEqual(helper.proposal_status(self.state, first), 'changed_after_save')

    def test_status_and_list_do_not_rewrite_records_or_history(self):
        self.fixture()
        first = self.propose()
        self.apply(first)
        self.pending(first, 'applied')
        self.second_save()
        before = self.private_bytes()
        records = {p.name: p.read_bytes() for p in self.data.iterdir()}
        self.cli('status', self.state, first)
        output = io.StringIO()
        with patch.object(sys, 'argv', ['proposals.py', 'list', str(self.state)]), contextlib.redirect_stdout(output):
            helper.main()
        self.assertIn('changed_after_save', output.getvalue())
        self.assertNotIn('needs_review', output.getvalue())
        self.assertEqual(self.private_bytes(), before)
        self.assertEqual({p.name: p.read_bytes() for p in self.data.iterdir()}, records)

    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT'), 'Set TEST_RSCRIPT for real R/yaml integration')
    def test_real_r_successive_saves_keep_completed_item_closed(self):
        self.fixture()
        self.stub.stop()
        first = self.propose()
        pending = self.pending(first)
        self.apply(first)
        self.second_save()
        self.assertEqual(self.cli('status', self.state, first)['status'], 'changed_after_save')
        self.assertEqual(helper.read_pending(self.state, pending)['status'], 'applied')
        with self.assertRaisesRegex(ValueError, 'Terminal item cannot be reopened'):
            helper.event_pending(self.state, pending, dict(status='needs_information'))
