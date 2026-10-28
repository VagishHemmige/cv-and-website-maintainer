"""Offline source reuse/scope acknowledgement tests; no live private state."""
import contextlib
import datetime as dt
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import test_private_state as fixtures

helper = fixtures.helper


class CheckpointSourceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.PrivateStateTests('runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.state = self.fixture.state

    def snapshot(self):
        return {p.relative_to(self.state).as_posix(): p.read_bytes()
                for p in self.state.rglob('*') if p.is_file()}

    def successful(self):
        run = self.fixture.begin()
        helper.finish_checkpoint(self.state, run['id'], completion=self.fixture.completion(run))
        return run

    def test_empty_listing_creates_nothing(self):
        before = self.snapshot()
        self.assertEqual(helper.checkpoint_sources(self.state)['sources'], [])
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.fixture.checkpoints.exists())

    def test_listing_returns_exact_saved_definition_and_is_read_only(self):
        run = self.fixture.begin()
        before = self.snapshot()
        result = helper.checkpoint_sources(self.state)
        saved = result['sources'][0]
        self.assertEqual(saved['source_key'], run['source_key'])
        self.assertEqual(saved['definition'], self.fixture.document()['sources'][run['source_key']])
        self.assertEqual(saved['active_run_ids'], [run['id']])
        self.assertEqual(self.snapshot(), before)

    def test_reusing_listed_definition_resumes_successful_cutoff(self):
        first = self.successful()
        saved = helper.checkpoint_sources(self.state)['sources'][0]['definition']
        request = self.fixture.request()
        request.update(source=saved['source'], subqueries=saved['subqueries'])
        request['end'] = (helper.timestamp(first['window_end']) + dt.timedelta(hours=1)).isoformat()
        run = self.fixture.begin(request)
        self.assertEqual(run['source_key'], first['source_key'])
        self.assertEqual(run['previous_successful_cutoff'], first['window_end'])
        self.assertEqual(helper.timestamp(run['window_start']),
                         helper.timestamp(first['window_end']) - dt.timedelta(days=14))
        self.assertNotIn('scope_change_assertion', run)

    def test_reworded_query_is_blocked_without_state_changes(self):
        self.successful()
        request = self.fixture.request()
        request['source']['query'] = 'The same academic updates in different words'
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'New search definition.*existing provider/account'):
            self.fixture.begin(request)
        self.assertEqual(self.snapshot(), before)

    def test_version_change_also_requires_acknowledgement(self):
        self.successful()
        with self.assertRaisesRegex(ValueError, 'checkpoint-sources'):
            self.fixture.begin(self.fixture.request(scope='v2'))

    def test_acknowledgement_requires_nonempty_reference(self):
        self.successful()
        before = self.snapshot()
        for reference in (None, '', '   '):
            with self.assertRaises(ValueError):
                helper.begin_checkpoint(self.state, self.fixture.request(scope='v2'),
                                        source_approved=True, acknowledge_new_scope=True,
                                        scope_change_reference=reference)
        self.assertEqual(self.snapshot(), before)

    def test_intentional_new_scope_retains_old_coverage_and_records_assertion(self):
        old = self.successful()
        result = helper.begin_checkpoint(self.state, self.fixture.request(scope='v2'),
                                         source_approved=True, acknowledge_new_scope=True,
                                         scope_change_reference='Synthetic user scope approval reference')
        run = result['run']
        self.assertIsNone(run['previous_successful_cutoff'])
        self.assertEqual(helper.timestamp(run['window_start']), helper.timestamp(run['window_end']) - dt.timedelta(days=30))
        assertion = run['scope_change_assertion']
        self.assertEqual(assertion['related_source_keys'], [old['source_key']])
        intent = json.loads((self.state / 'state-history' / result['operation_id'] / 'intent.json').read_text())
        self.assertIn('Synthetic user scope approval reference', json.dumps(intent))
        self.assertEqual(self.fixture.document()['sources'][old['source_key']]['last_successful_cutoff'], old['window_end'])

    def test_new_account_or_provider_is_not_a_scope_collision(self):
        self.successful()
        other = self.fixture.begin(self.fixture.request(identity='other-account'))
        request = self.fixture.request()
        request['source']['provider'] = 'another-provider'
        provider = self.fixture.begin(request)
        self.assertNotIn('scope_change_assertion', other)
        self.assertNotIn('scope_change_assertion', provider)

    def test_scope_acknowledgement_does_not_bypass_source_approval(self):
        self.successful()
        with self.assertRaisesRegex(ValueError, 'Actual source/scope approval'):
            helper.begin_checkpoint(self.state, self.fixture.request(scope='v2'),
                                    acknowledge_new_scope=True, scope_change_reference='Synthetic')

    def test_existing_key_still_rejects_undeclared_subquery_change(self):
        self.successful()
        request = self.fixture.request()
        request['subqueries'].append('extra')
        with self.assertRaisesRegex(ValueError, 'subquery scope changed'):
            helper.begin_checkpoint(self.state, request, source_approved=True,
                                    acknowledge_new_scope=True, scope_change_reference='Synthetic')

    def test_cli_listing_and_acknowledgement(self):
        self.successful()
        output = io.StringIO()
        before = self.snapshot()
        with patch.object(sys, 'argv', ['private_state.py', 'checkpoint-sources', str(self.state)]), contextlib.redirect_stdout(output):
            helper.main()
        self.assertEqual(len(json.loads(output.getvalue())['sources']), 1)
        self.assertEqual(self.snapshot(), before)
        request = self.fixture.base / 'new-scope.json'
        request.write_bytes(helper.encoded(self.fixture.request(scope='v2')))
        output = io.StringIO()
        with patch.object(sys, 'argv', ['private_state.py', 'checkpoint-begin', str(self.state), str(request),
                                      '--source-approved', '--acknowledge-new-scope',
                                      '--scope-change-reference', 'Synthetic CLI approval']), contextlib.redirect_stdout(output):
            helper.main()
        self.assertTrue(json.loads(output.getvalue())['run']['scope_change_assertion']['acknowledged'])

    def test_listing_preserves_malformed_state_for_review(self):
        self.fixture.checkpoints.parent.mkdir()
        self.fixture.checkpoints.write_bytes(b'{invalid JSON')
        before = self.snapshot()
        with self.assertRaises(ValueError):
            helper.checkpoint_sources(self.state)
        self.assertEqual(self.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
