"""Synthetic checkpoint commits; no real searches or live history are touched."""
import unittest
from unittest.mock import patch

import test_private_state as state_tests

helper = state_tests.helper
PLACEHOLDER = 'No successful discovery searches recorded; first-search look-back remains pending.'


class CheckpointNoteTests(unittest.TestCase):
    setUp = state_tests.PrivateStateTests.setUp
    request = state_tests.PrivateStateTests.request
    begin = state_tests.PrivateStateTests.begin
    completion = state_tests.PrivateStateTests.completion
    document = state_tests.PrivateStateTests.document

    def seed(self, note=PLACEHOLDER):
        self.checkpoints.parent.mkdir()
        self.checkpoints.write_bytes(helper.encoded(dict(
            schema_version=1, sources={}, runs={}, note=note,
            owner_context={'preserve': ['unknown', 'keys']})))

    def test_begin_retains_placeholder_without_claiming_completed_coverage(self):
        self.seed(); config = self.config_path.read_bytes()
        run = self.begin()
        doc = self.document()
        self.assertEqual(doc['note'], PLACEHOLDER)
        self.assertEqual(doc['runs'][run['id']]['status'], 'running')
        self.assertIsNone(doc['sources'][run['source_key']].get('last_successful_cutoff'))
        self.assertEqual(self.config_path.read_bytes(), config)

    def test_complete_zero_results_removes_only_placeholder_in_same_verified_commit(self):
        self.seed(); config = self.config_path.read_bytes(); run = self.begin()
        before = self.checkpoints.read_bytes()
        result = helper.finish_checkpoint(self.state, run['id'], completion=self.completion(run))
        doc = self.document()
        self.assertNotIn('note', doc)
        self.assertEqual(doc['owner_context'], {'preserve': ['unknown', 'keys']})
        self.assertEqual(doc['runs'][run['id']]['status'], 'complete')
        self.assertEqual(doc['runs'][run['id']]['completion']['result_count'], 0)
        self.assertEqual(doc['sources'][run['source_key']]['last_successful_cutoff'], run['window_end'])
        history = self.state/'state-history'/result['operation_id']
        self.assertEqual((history/'before.json').read_bytes(), before)
        self.assertEqual(helper.decode((history/'before.json').read_bytes())['note'], PLACEHOLDER)
        self.assertEqual(helper.operation_status(self.state, result['operation_id'])[2]['status'],
                         'committed_verified')
        self.assertEqual(self.config_path.read_bytes(), config)

    def test_nonzero_completed_search_also_removes_placeholder(self):
        self.seed(); run = self.begin()
        helper.finish_checkpoint(self.state, run['id'], completion=self.completion(run, count=2))
        self.assertNotIn('note', self.document())
        self.assertEqual(self.document()['runs'][run['id']]['completion']['result_count'], 2)

    def test_unrelated_note_with_same_prefix_and_unknown_keys_are_preserved(self):
        note = PLACEHOLDER + ' Owner annotation to retain.'
        self.seed(note); run = self.begin()
        helper.finish_checkpoint(self.state, run['id'], completion=self.completion(run))
        self.assertEqual(self.document()['note'], note)
        self.assertEqual(self.document()['owner_context'], {'preserve': ['unknown', 'keys']})

    def test_all_failure_outcomes_preserve_placeholder_and_do_not_advance(self):
        self.seed()
        for outcome in ('failed', 'partial', 'unauthorized', 'unavailable',
                        'rate_limited', 'interrupted', 'save_failed'):
            with self.subTest(outcome=outcome):
                run = self.begin()
                helper.finish_checkpoint(self.state, run['id'],
                    failure=dict(outcome=outcome, reason='Synthetic failure only'))
                doc = self.document()
                self.assertEqual(doc['note'], PLACEHOLDER)
                self.assertIsNone(doc['sources'][run['source_key']].get('last_successful_cutoff'))
                self.assertEqual(doc['runs'][run['id']]['status'], outcome)

    def test_incomplete_pagination_preserves_exact_checkpoint_bytes(self):
        self.seed(); run = self.begin(); completion = self.completion(run)
        completion['pagination'][0]['exhausted'] = False
        before = self.checkpoints.read_bytes()
        with self.assertRaisesRegex(ValueError, 'All pages'):
            helper.finish_checkpoint(self.state, run['id'], completion=completion)
        self.assertEqual(self.checkpoints.read_bytes(), before)
        self.assertEqual(self.document()['note'], PLACEHOLDER)

    def test_replace_failure_keeps_placeholder_and_running_cutoff_state(self):
        self.seed(); run = self.begin(); completion = self.completion(run)
        before = self.checkpoints.read_bytes()
        with patch.object(helper.os, 'replace', side_effect=OSError('Synthetic replacement failure')):
            with self.assertRaisesRegex(ValueError, 'update interrupted'):
                helper.finish_checkpoint(self.state, run['id'], completion=completion)
        self.assertEqual(self.checkpoints.read_bytes(), before)
        self.assertEqual(self.document()['note'], PLACEHOLDER)
        self.assertEqual(self.document()['runs'][run['id']]['status'], 'running')

    def test_post_replacement_receipt_interruption_retains_atomic_note_removal(self):
        self.seed(); run = self.begin(); completion = self.completion(run)
        original = helper.exclusive
        def interrupt(path, raw):
            if path.name == 'committed.json':
                raise OSError('Synthetic completion receipt interruption')
            return original(path, raw)
        with patch.object(helper, 'exclusive', side_effect=interrupt):
            with self.assertRaisesRegex(ValueError, 'bytes may already be committed'):
                helper.finish_checkpoint(self.state, run['id'], completion=completion)
        self.assertNotIn('note', self.document())
        self.assertEqual(self.document()['sources'][run['source_key']]['last_successful_cutoff'],
                         run['window_end'])
        operations = [p.parent for p in (self.state/'state-history').glob('*/intent.json')
                      if helper.decode(p.read_bytes())['kind'] == 'checkpoint_finish']
        operation = operations[0]
        self.assertEqual(helper.decode((operation/'before.json').read_bytes())['note'], PLACEHOLDER)
        self.assertEqual(helper.operation_status(self.state, operation.name)[2]['status'],
                         'committed_unverified')
        saved = self.checkpoints.read_bytes()
        result = helper.verify_operation(self.state, operation.name)
        self.assertFalse(result['state_rewritten'])
        self.assertEqual(self.checkpoints.read_bytes(), saved)


if __name__ == '__main__':
    unittest.main()
