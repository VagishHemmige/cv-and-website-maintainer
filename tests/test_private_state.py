"""F5 state safeguards. All approvals and source searches are synthetic assertions."""
import contextlib
import datetime as dt
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from approval_fixture import approval_file

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'private_state.py'
SPEC = importlib.util.spec_from_file_location('private_state_target', SCRIPT)
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


class PrivateStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TEST_TMP_ROOT'))
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.project = self.base / 'project'; self.project.mkdir()
        self.state = self.base / 'private'; self.state.mkdir()
        self.config_path = self.state / 'config.json'
        self.checkpoints = self.state / 'reviews' / 'discovery-checkpoints.json'
        self.config = dict(project_root=str(self.project), unknown={'preserve': 7},
            discovery=dict(initial_window_days=30, overlap_days=14, checkpoint_path=str(self.checkpoints)))
        self.config_path.write_bytes(helper.encoded(self.config))
        self.provenance = dict(source='Synthetic user answer', recorded_at='2026-10-17T10:00:00+00:00')
        self.end = (helper.now() - dt.timedelta(days=1)).isoformat()

    def propose(self, value=60):
        return helper.propose_profile(self.state, {'discovery': {'initial_window_days': value}}, self.provenance)

    def apply(self, proposal):
        path = self.state / 'profile-proposals' / proposal['id'] / 'after.json'
        evidence = approval_file(self.state, 'profile', proposal['id'], helper.sha(path.read_bytes()), self.config_path)
        return helper.apply_profile(self.state, proposal['id'], proposal['id'], 'Synthetic fixture approval', evidence)

    def request(self, identity='fixture-account', scope='v1'):
        return dict(source=dict(provider='fixture', identity=identity, scope_version=scope, query='academic updates'),
                    cycle_id='fixture-cycle', end=self.end, timezone_interpretation='UTC inclusive instants',
                    subqueries=['abstracts', 'presentations'])

    def begin(self, request=None):
        return helper.begin_checkpoint(self.state, request or self.request(), source_approved=True)['run']

    def completion(self, run, count=0):
        report = self.state / ('report-' + run['id'] + '.json')
        report.write_bytes(helper.encoded(dict(run_id=run['id'], result_count=count, summary='Synthetic discovery report')))
        return dict(window_start=run['window_start'], window_end=run['window_end'],
            results_durably_saved=True, result_count=count, report_path=str(report),
            result_paths=[str(report)] if count else [],
            pagination=[dict(query_id=q, pages=1, exhausted=True) for q in run['subqueries']])

    def document(self):
        return helper.decode(self.checkpoints.read_bytes())

    def test_profile_proposal_does_not_change_live_preferences(self):
        before = self.config_path.read_bytes()
        proposal = self.propose()
        self.assertEqual(self.config_path.read_bytes(), before)
        self.assertEqual(proposal['before']['discovery']['initial_window_days'], 30)
        self.assertEqual(proposal['after']['discovery']['initial_window_days'], 60)
        self.assertIn('config.json (proposed)', proposal['diff'])
        self.assertEqual(proposal['provenance'], self.provenance)

    def test_profile_apply_preserves_unknown_keys_and_verified_backup(self):
        before = self.config_path.read_bytes()
        proposal = self.propose(); result = self.apply(proposal)
        config = helper.decode(self.config_path.read_bytes())
        self.assertEqual(config['unknown'], {'preserve':7})
        self.assertEqual(config['discovery']['overlap_days'], 14)
        self.assertEqual(config['discovery']['initial_window_days'], 60)
        folder = self.state / 'state-history' / result['operation_id']
        self.assertEqual((folder / 'before.json').read_bytes(), before)
        self.assertEqual(helper.operation_status(self.state, result['operation_id'])[2]['status'], 'committed_verified')

    def test_wrong_approval_blocks_profile_write(self):
        proposal = self.propose(); before = self.config_path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Approval must identify'):
            helper.apply_profile(self.state, proposal['id'], 'wrong', 'Synthetic')
        self.assertEqual(self.config_path.read_bytes(), before)

    def test_changed_profile_requires_new_proposal(self):
        proposal = self.propose()
        self.config['unknown']['other'] = 8
        self.config_path.write_bytes(helper.encoded(self.config))
        before = self.config_path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Profile changed'):
            self.apply(proposal)
        self.assertEqual(self.config_path.read_bytes(), before)

    def test_changed_staged_preferences_are_not_approved(self):
        proposal = self.propose(); before = self.config_path.read_bytes()
        path = self.state / 'profile-proposals' / proposal['id'] / 'after.json'
        path.write_bytes(helper.encoded({'project_root': str(self.project), 'unexpected':True}))
        with self.assertRaisesRegex(ValueError, 'proposal changed'):
            self.apply(proposal)
        self.assertEqual(self.config_path.read_bytes(), before)

    def test_initial_creation_is_reviewed_and_exclusive(self):
        self.config_path.unlink()
        proposal = helper.propose_profile(self.state, self.config, self.provenance, create=True)
        self.assertFalse(self.config_path.exists())
        self.apply(proposal)
        self.assertEqual(helper.decode(self.config_path.read_bytes()), self.config)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            helper.propose_profile(self.state, self.config, self.provenance, create=True)

    def test_malformed_profile_and_duplicate_keys_do_not_get_replaced(self):
        self.config_path.write_text('{"duplicate":1,"duplicate":2}')
        before = self.config_path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
            self.propose()
        self.assertEqual(self.config_path.read_bytes(), before)

    def test_unresolved_discovery_settings_are_not_treated_as_setup(self):
        self.config['discovery'] = None
        self.config_path.write_bytes(helper.encoded(self.config))
        before = self.config_path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Discovery settings are unresolved'):
            self.begin()
        self.assertFalse(self.checkpoints.exists())
        self.assertEqual(self.config_path.read_bytes(), before)

    def test_malformed_checkpoint_history_is_not_replaced(self):
        self.checkpoints.parent.mkdir()
        self.checkpoints.write_bytes(helper.encoded(dict(schema_version=1, sources={}, runs={'broken':None})))
        before = self.checkpoints.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Malformed source/run state'):
            self.begin()
        self.assertEqual(self.checkpoints.read_bytes(), before)

    def test_completion_requires_exactly_one_structured_outcome(self):
        run = self.begin(); before = self.checkpoints.read_bytes()
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            helper.finish_checkpoint(self.state, run['id'])
        with self.assertRaisesRegex(ValueError, 'JSON object'):
            helper.finish_checkpoint(self.state, run['id'], completion=[])
        self.assertEqual(self.checkpoints.read_bytes(), before)

    def test_redirected_private_paths_are_refused(self):
        original = Path.is_symlink
        def redirected(path):
            return path == self.state or original(path)
        with patch.object(Path, 'is_symlink', redirected):
            with self.assertRaisesRegex(ValueError, 'Redirected state/evidence path refused'):
                self.propose()
        self.assertFalse((self.state / 'profile-proposals').exists())

    def test_public_state_refused_before_lock_or_proposal_creation(self):
        public_state = self.project / 'private'; public_state.mkdir()
        with self.assertRaisesRegex(ValueError, 'outside the project'):
            helper.propose_profile(public_state, self.config, self.provenance, create=True)
        self.assertEqual(list(public_state.iterdir()), [])

    def test_unknown_stale_lock_is_not_broken(self):
        lock = self.state / '.private-state-writer.lock'; lock.write_text('interrupted writer')
        with self.assertRaisesRegex(ValueError, 'writer is locked'):
            self.propose()
        self.assertEqual(lock.read_text(), 'interrupted writer')

    def test_two_processes_cannot_both_apply_same_base(self):
        first = self.propose(60); second = self.propose(90)
        def command(item):
            path = self.state / 'profile-proposals' / item['id'] / 'after.json'
            evidence = approval_file(self.state, 'profile', item['id'], helper.sha(path.read_bytes()), self.config_path)
            return [sys.executable, '-B', str(SCRIPT), 'profile-apply', str(self.state), item['id'],
                    '--approval', item['id'], '--approval-reference', 'Synthetic process approval',
                    '--approval-evidence', str(evidence)]
        one = subprocess.Popen(command(first), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        two = subprocess.Popen(command(second), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        one.communicate(timeout=20); two.communicate(timeout=20)
        self.assertEqual(sorted([one.returncode, two.returncode]), [0,1])
        self.assertIn(helper.decode(self.config_path.read_bytes())['discovery']['initial_window_days'], [60,90])
        self.assertEqual(len(list((self.state / 'state-history').glob('*/committed.json'))), 1)

    def test_failed_replace_preserves_old_bytes_and_backup(self):
        proposal = self.propose(); before = self.config_path.read_bytes()
        with patch.object(helper.os, 'replace', side_effect=OSError('Synthetic replace failure')):
            with self.assertRaisesRegex(ValueError, 'bytes may already be committed'):
                self.apply(proposal)
        self.assertEqual(self.config_path.read_bytes(), before)
        folder = next((self.state / 'state-history').iterdir())
        self.assertEqual((folder / 'before.json').read_bytes(), before)
        self.assertEqual(helper.operation_status(self.state, folder.name)[2]['status'], 'not_committed')
        self.assertEqual(list(self.state.glob('.private-state-*.tmp')), [])

    def test_postwrite_interruption_can_verify_without_rewriting(self):
        proposal = self.propose()
        real = helper.exclusive
        def fail_receipt(path, raw):
            if path.name == 'committed.json':
                raise OSError('Synthetic postwrite interruption')
            return real(path, raw)
        with patch.object(helper, 'exclusive', side_effect=fail_receipt):
            with self.assertRaisesRegex(ValueError, 'Inspect status before retry'):
                self.apply(proposal)
        folder = next((self.state / 'state-history').iterdir())
        self.assertEqual(helper.operation_status(self.state, folder.name)[2]['status'], 'committed_unverified')
        before = self.config_path.read_bytes()
        self.assertFalse(helper.verify_operation(self.state, folder.name)['state_rewritten'])
        self.assertEqual(self.config_path.read_bytes(), before)
        with self.assertRaisesRegex(ValueError, 'already applied'):
            self.apply(proposal)

    def test_external_change_at_replace_boundary_is_detected(self):
        proposal = self.propose()
        real = helper.atomic_install
        changed = helper.encoded({**self.config, 'external':True})
        def concurrent(target, raw, expected):
            target.write_bytes(changed)
            return real(target, raw, expected)
        with patch.object(helper, 'atomic_install', side_effect=concurrent):
            with self.assertRaisesRegex(ValueError, 'Concurrent state change'):
                self.apply(proposal)
        self.assertEqual(self.config_path.read_bytes(), changed)

    def test_begin_captures_fixed_window_but_never_success(self):
        run = self.begin()
        self.assertEqual(run['window_end'], helper.timestamp(self.end).isoformat())
        self.assertEqual(helper.timestamp(run['window_end']) - helper.timestamp(run['window_start']), dt.timedelta(days=30))
        self.assertNotIn('last_successful_cutoff', self.document()['sources'][run['source_key']])
        self.assertEqual(self.document()['runs'][run['id']]['status'], 'running')

    def test_no_source_approval_or_unknown_initial_window_cannot_begin(self):
        with self.assertRaisesRegex(ValueError, 'source/scope approval'):
            helper.begin_checkpoint(self.state, self.request())
        self.config['discovery']['initial_window_days'] = None
        self.config_path.write_bytes(helper.encoded(self.config))
        with self.assertRaisesRegex(ValueError, 'initial_window_days'):
            self.begin()
        self.assertFalse(self.checkpoints.exists())

    def test_future_or_timezone_free_cutoff_is_refused(self):
        request = self.request(); request['end'] = (helper.now() + dt.timedelta(days=1)).isoformat()
        with self.assertRaisesRegex(ValueError, 'future'):
            self.begin(request)
        request['end'] = '2026-10-10T10:00:00'
        with self.assertRaisesRegex(ValueError, 'explicit timezone'):
            self.begin(request)
        self.assertFalse(self.checkpoints.exists())

    def test_successful_zero_results_advances_exact_fixed_cutoff(self):
        run = self.begin(); completion = self.completion(run)
        result = helper.finish_checkpoint(self.state, run['id'], completion=completion)
        self.assertEqual(result['last_successful_cutoff'], run['window_end'])
        self.assertEqual(self.document()['runs'][run['id']]['completion']['result_count'], 0)
        self.assertIn('evidence', self.document()['runs'][run['id']])

    def test_next_window_uses_prior_success_minus_overlap(self):
        first = self.begin(); helper.finish_checkpoint(self.state, first['id'], completion=self.completion(first))
        self.end = (helper.timestamp(self.end) + dt.timedelta(hours=1)).isoformat()
        second = self.begin()
        self.assertEqual(helper.timestamp(second['window_start']), helper.timestamp(first['window_end']) - dt.timedelta(days=14))
        self.assertEqual(second['previous_successful_cutoff'], first['window_end'])

    def test_failed_first_search_retains_earliest_intended_coverage(self):
        self.end = (helper.now() - dt.timedelta(days=20)).isoformat()
        first = self.begin()
        helper.finish_checkpoint(self.state, first['id'], failure=dict(outcome='partial', reason='Synthetic partial first run'))
        self.end = (helper.timestamp(self.end) + dt.timedelta(days=7)).isoformat()
        second = self.begin()
        self.assertEqual(second['window_start'], first['window_start'])
        self.assertGreater(helper.timestamp(second['window_end']), helper.timestamp(first['window_end']))
        self.assertIsNone(second['previous_successful_cutoff'])

    def test_unknown_window_policy_is_not_silently_interpreted(self):
        self.config['discovery']['window_policy'] = 'future-unsupported-policy'
        self.config_path.write_bytes(helper.encoded(self.config))
        with self.assertRaisesRegex(ValueError, 'Unsupported search window policy'):
            self.begin()
        self.assertFalse(self.checkpoints.exists())

    def test_profile_or_checkpoint_file_cannot_stand_in_for_report(self):
        run = self.begin(); completion = self.completion(run)
        completion['report_path'] = str(self.checkpoints)
        before = self.checkpoints.read_bytes()
        with self.assertRaisesRegex(ValueError, 'not a discovery report'):
            helper.finish_checkpoint(self.state, run['id'], completion=completion)
        self.assertEqual(self.checkpoints.read_bytes(), before)

    def test_corrupt_completion_receipt_is_not_certified(self):
        proposal = self.propose(); operation = self.apply(proposal)['operation_id']
        receipt = self.state / 'state-history' / operation / 'committed.json'
        receipt.write_bytes(helper.encoded(dict(id=operation, after_sha256='wrong')))
        with self.assertRaisesRegex(ValueError, 'receipt does not match'):
            helper.operation_status(self.state, operation)

    def test_recovery_refuses_changed_evidence_without_advancing_again(self):
        run = self.begin(); completion = self.completion(run)
        real = helper.exclusive
        def interrupt(path, raw):
            if path.name == 'committed.json': raise OSError('Synthetic interruption')
            return real(path, raw)
        with patch.object(helper, 'exclusive', side_effect=interrupt):
            with self.assertRaises(ValueError):
                helper.finish_checkpoint(self.state, run['id'], completion=completion)
        folder = next(p.parent for p in (self.state / 'state-history').glob('*/intent.json')
                      if helper.decode(p.read_bytes())['kind'] == 'checkpoint_finish')
        Path(completion['report_path']).write_text('Changed fixture report')
        before = self.checkpoints.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Saved evidence changed'):
            helper.verify_operation(self.state, folder.name)
        self.assertFalse((folder / 'committed.json').exists())
        self.assertEqual(self.checkpoints.read_bytes(), before)

    def test_failures_retain_previous_success_and_record_attempt(self):
        first = self.begin(); helper.finish_checkpoint(self.state, first['id'], completion=self.completion(first))
        self.end = (helper.timestamp(self.end) + dt.timedelta(hours=1)).isoformat()
        for outcome in ('failed','partial','unauthorized','unavailable','rate_limited','interrupted','save_failed'):
            with self.subTest(outcome=outcome):
                run = self.begin()
                result = helper.finish_checkpoint(self.state, run['id'], failure=dict(outcome=outcome, reason='Synthetic failure'))
                self.assertEqual(result['last_successful_cutoff'], first['window_end'])
                self.assertEqual(self.document()['runs'][run['id']]['status'], outcome)

    def test_missing_or_empty_report_never_advances(self):
        run = self.begin(); completion = self.completion(run)
        report = Path(completion['report_path']); report.unlink()
        before = self.checkpoints.read_bytes()
        with self.assertRaisesRegex(ValueError, 'saved report/results'):
            helper.finish_checkpoint(self.state, run['id'], completion=completion)
        self.assertEqual(self.checkpoints.read_bytes(), before)
        report.write_text('')
        with self.assertRaisesRegex(ValueError, 'saved report/results'):
            helper.finish_checkpoint(self.state, run['id'], completion=completion)
        self.assertEqual(self.checkpoints.read_bytes(), before)

    def test_incomplete_pagination_or_missing_subquery_retains_cutoff(self):
        run = self.begin(); completion = self.completion(run); before = self.checkpoints.read_bytes()
        completion['pagination'][0]['exhausted'] = False
        with self.assertRaisesRegex(ValueError, 'All pages'):
            helper.finish_checkpoint(self.state, run['id'], completion=completion)
        completion['pagination'] = completion['pagination'][1:]
        with self.assertRaisesRegex(ValueError, 'every declared subquery'):
            helper.finish_checkpoint(self.state, run['id'], completion=completion)
        self.assertEqual(self.checkpoints.read_bytes(), before)

    def test_extended_completion_window_is_refused(self):
        run = self.begin(); completion = self.completion(run); before = self.checkpoints.read_bytes()
        completion['window_end'] = helper.now().isoformat()
        with self.assertRaisesRegex(ValueError, 'fixed window_end'):
            helper.finish_checkpoint(self.state, run['id'], completion=completion)
        self.assertEqual(self.checkpoints.read_bytes(), before)

    def test_nonzero_results_need_saved_result_files(self):
        run = self.begin(); completion = self.completion(run, count=2)
        completion['result_paths'] = []
        with self.assertRaisesRegex(ValueError, 'durable result_paths'):
            helper.finish_checkpoint(self.state, run['id'], completion=completion)
        self.assertNotIn('last_successful_cutoff', self.document()['sources'][run['source_key']])

    def test_scope_and_account_keys_never_share_success(self):
        first = self.begin(); helper.finish_checkpoint(self.state, first['id'], completion=self.completion(first))
        account = self.begin(self.request(identity='other-account'))
        scope = helper.begin_checkpoint(self.state, self.request(scope='v2'), source_approved=True,
                                        acknowledge_new_scope=True,
                                        scope_change_reference='Synthetic intentional v2 scope approval')['run']
        self.assertEqual(len({first['source_key'], account['source_key'], scope['source_key']}), 3)
        self.assertIsNone(account['previous_successful_cutoff'])
        self.assertIsNone(scope['previous_successful_cutoff'])

    def test_new_subquery_cannot_reuse_unexamined_successful_coverage(self):
        run = self.begin(); helper.finish_checkpoint(self.state, run['id'], completion=self.completion(run))
        self.end = (helper.timestamp(self.end) + dt.timedelta(hours=1)).isoformat()
        request = self.request(); request['subqueries'].append('new-activity-category')
        before = self.checkpoints.read_bytes()
        with self.assertRaisesRegex(ValueError, 'subquery scope changed'):
            self.begin(request)
        self.assertEqual(self.checkpoints.read_bytes(), before)

    def test_unsaved_result_assertion_never_advances(self):
        run = self.begin(); completion = self.completion(run)
        completion['results_durably_saved'] = False
        before = self.checkpoints.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Durable results assertion required'):
            helper.finish_checkpoint(self.state, run['id'], completion=completion)
        self.assertEqual(self.checkpoints.read_bytes(), before)

    @unittest.skipUnless(os.name == 'nt', 'Windows non-overwriting rename contract')
    def test_initial_creation_never_overwrites_concurrent_creator(self):
        self.config_path.unlink()
        proposal = helper.propose_profile(self.state, self.config, self.provenance, create=True)
        other = helper.encoded({**self.config, 'concurrent_creator':True})
        real = helper.os.rename
        def race(source, target):
            target.write_bytes(other)
            return real(source, target)
        with patch.object(helper.os, 'rename', side_effect=race):
            with self.assertRaisesRegex(ValueError, 'update interrupted'):
                self.apply(proposal)
        self.assertEqual(self.config_path.read_bytes(), other)

    def test_active_run_and_closed_run_cannot_be_reused(self):
        run = self.begin()
        with self.assertRaisesRegex(ValueError, 'active run'):
            self.begin()
        helper.finish_checkpoint(self.state, run['id'], failure=dict(outcome='partial', reason='Fixture'))
        with self.assertRaisesRegex(ValueError, 'already closed'):
            helper.finish_checkpoint(self.state, run['id'], completion=self.completion(run))

    def test_changed_profile_blocks_advancement_but_failure_can_close_attempt(self):
        run = self.begin(); completion = self.completion(run)
        self.config['discovery']['sources'] = []
        self.config_path.write_bytes(helper.encoded(self.config))
        with self.assertRaisesRegex(ValueError, 'Profile changed during search'):
            helper.finish_checkpoint(self.state, run['id'], completion=completion)
        result = helper.finish_checkpoint(self.state, run['id'], failure=dict(outcome='unauthorized', reason='Scope changed'))
        self.assertIsNone(result['last_successful_cutoff'])

    def test_checkpoint_replace_failure_retains_running_state_and_old_cutoff(self):
        run = self.begin(); completion = self.completion(run); before = self.checkpoints.read_bytes()
        with patch.object(helper.os, 'replace', side_effect=OSError('Synthetic save failure')):
            with self.assertRaisesRegex(ValueError, 'update interrupted'):
                helper.finish_checkpoint(self.state, run['id'], completion=completion)
        self.assertEqual(self.checkpoints.read_bytes(), before)
        self.assertEqual(self.document()['runs'][run['id']]['status'], 'running')

    def test_checkpoint_postwrite_interruption_is_truthfully_recoverable(self):
        run = self.begin(); completion = self.completion(run)
        real = helper.exclusive
        def interrupt(path, raw):
            if path.name == 'committed.json': raise OSError('Synthetic completion receipt failure')
            return real(path, raw)
        with patch.object(helper, 'exclusive', side_effect=interrupt):
            with self.assertRaisesRegex(ValueError, 'bytes may already be committed'):
                helper.finish_checkpoint(self.state, run['id'], completion=completion)
        operations = [p.parent for p in (self.state / 'state-history').glob('*/intent.json')
                      if helper.decode(p.read_bytes())['kind'] == 'checkpoint_finish']
        folder = operations[0]
        self.assertEqual(helper.operation_status(self.state, folder.name)[2]['status'], 'committed_unverified')
        before = self.checkpoints.read_bytes()
        self.assertFalse(helper.verify_operation(self.state, folder.name)['state_rewritten'])
        self.assertEqual(self.checkpoints.read_bytes(), before)
        self.assertEqual(self.document()['sources'][run['source_key']]['last_successful_cutoff'], run['window_end'])

    def test_evidence_change_before_commit_blocks_advancement(self):
        run = self.begin(); completion = self.completion(run); before = self.checkpoints.read_bytes()
        real = helper.commit
        def change(*args, **kwargs):
            Path(completion['report_path']).write_text('Changed synthetic report')
            return real(*args, **kwargs)
        with patch.object(helper, 'commit', side_effect=change):
            with self.assertRaisesRegex(ValueError, 'evidence changed'):
                helper.finish_checkpoint(self.state, run['id'], completion=completion)
        self.assertEqual(self.checkpoints.read_bytes(), before)

    def test_legacy_empty_document_preserves_unknown_keys(self):
        self.checkpoints.parent.mkdir()
        self.checkpoints.write_bytes(helper.encoded(dict(schema_version=1, sources={}, note='Legacy setup note')))
        self.begin()
        self.assertEqual(self.document()['note'], 'Legacy setup note')

    def test_evidence_and_checkpoint_paths_cannot_escape_private_state(self):
        run = self.begin(); completion = self.completion(run)
        public = self.project / 'report.txt'; public.write_text('Synthetic report')
        completion['report_path'] = str(public)
        with self.assertRaisesRegex(ValueError, 'inside the private state'):
            helper.finish_checkpoint(self.state, run['id'], completion=completion)
        self.config['discovery']['checkpoint_path'] = str(self.project / 'checkpoints.json')
        self.config_path.write_bytes(helper.encoded(self.config))
        with self.assertRaisesRegex(ValueError, 'inside the private state'):
            self.begin()

    def test_status_is_read_only_and_reports_later_state_changes(self):
        proposal = self.propose(); operation = self.apply(proposal)['operation_id']
        self.config_path.write_bytes(helper.encoded(self.config))
        before = {str(p):p.read_bytes() for p in self.state.rglob('*') if p.is_file()}
        self.assertEqual(helper.operation_status(self.state, operation)[2]['status'], 'changed_after_commit')
        self.assertEqual({str(p):p.read_bytes() for p in self.state.rglob('*') if p.is_file()}, before)

    def test_cli_profile_propose_and_checkpoint_cycle(self):
        request = self.base / 'request.json'; request.write_bytes(helper.encoded(self.request()))
        output = io.StringIO()
        with patch.object(sys, 'argv', ['private_state.py','checkpoint-begin',str(self.state),str(request),'--source-approved']), contextlib.redirect_stdout(output):
            helper.main()
        run = json.loads(output.getvalue())['run']
        evidence = self.base / 'coverage.json'; evidence.write_bytes(helper.encoded(self.completion(run)))
        output = io.StringIO()
        with patch.object(sys, 'argv', ['private_state.py','checkpoint-complete',str(self.state),run['id'],str(evidence)]), contextlib.redirect_stdout(output):
            helper.main()
        self.assertEqual(json.loads(output.getvalue())['last_successful_cutoff'], run['window_end'])


if __name__ == '__main__':
    unittest.main()
