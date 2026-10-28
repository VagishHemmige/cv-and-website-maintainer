"""Synthetic CV metadata and output-observation tests; no private CV content."""
import datetime as dt
import importlib.util
import contextlib
import io
import json
import os
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
import test_private_state as fixtures

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('cv_output_target', ROOT / 'scripts/cv_output.py')
cv = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cv)
helper = fixtures.helper


class CVOutputTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.PrivateStateTests('runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.directory = self.fixture.project / 'cv'
        self.directory.mkdir()
        self.prefs = {'cv_locator': {'directory': str(self.directory), 'filename_pattern': 'Example CV *.docx'}}
        self.epoch = int(helper.now().timestamp()) - 86400

    def output(self, name, offset=0):
        path = self.directory / name
        path.write_bytes(b'Synthetic CV sentinel; not a real document')
        os.utime(path, (self.epoch + offset, self.epoch + offset))
        return path

    def snapshot(self):
        return {str(p):p.read_bytes() for p in self.fixture.base.rglob('*') if p.is_file()}

    def test_latest_matching_file_selected_without_writes(self):
        self.output('Example CV old.docx')
        latest = self.output('Example CV new.docx', 60)
        self.output('cv-styles.docx', 100)
        self.output('~$Example CV temporary.docx', 200)
        archive = self.directory / 'Archive'; archive.mkdir()
        (archive / 'Example CV historical.docx').write_bytes(b'Archive')
        before = self.snapshot()
        result = cv.resolve(self.prefs)
        self.assertEqual(result['selected']['path'], str(latest))
        self.assertEqual(result['selected']['sha256'], helper.file_hash(latest))
        self.assertEqual(len(result['candidates']), 2)
        self.assertFalse(result['content_verified'])
        self.assertEqual(result['freshness'], 'unverified')
        self.assertEqual(self.snapshot(), before)

    def test_missing_and_ambiguous_are_explicit(self):
        self.assertEqual(cv.resolve(self.prefs)['status'], 'missing')
        self.output('Example CV one.docx'); self.output('Example CV two.docx')
        result = cv.resolve(self.prefs)
        self.assertEqual(result['status'], 'ambiguous')
        self.assertNotIn('selected', result)

    def test_fixed_link_never_infers_new_pattern(self):
        old = self.output('Example CV old.docx')
        self.output('Example CV new.docx', 60)
        result = cv.resolve({'cv_link': str(old)})
        self.assertEqual(result['selected']['path'], str(old))
        self.assertEqual(len(result['candidates']), 1)

    def test_timestamp_freshness_does_not_certify_contents(self):
        self.output('Example CV one.docx')
        before = dt.datetime.fromtimestamp(self.epoch - 60, dt.timezone.utc).isoformat()
        after = dt.datetime.fromtimestamp(self.epoch + 60, dt.timezone.utc).isoformat()
        self.assertEqual(cv.resolve(self.prefs, after)['freshness'], 'stale_by_timestamp')
        result = cv.resolve(self.prefs, before)
        self.assertEqual(result['freshness'], 'modified_at_or_after_save_contents_unverified')
        self.assertFalse(result['content_verified'])

    def test_unconfigured_and_remote_do_not_scan_or_fetch(self):
        self.assertEqual(cv.resolve({})['status'], 'not_configured')
        self.assertEqual(cv.resolve({'cv_link':'https://example.invalid/cv.pdf'})['status'], 'remote_unverified')

    def test_unsafe_patterns_and_redirected_paths_are_refused(self):
        for pattern in ('../*.docx', '**.docx', 'Archive/*.docx', '*', '*.exe'):
            with self.assertRaises(ValueError):
                cv.resolve({'cv_locator': {'directory':str(self.directory), 'filename_pattern':pattern}})
        original = Path.is_symlink
        with patch.object(Path, 'is_symlink', lambda p: p == self.directory or original(p)):
            with self.assertRaisesRegex(ValueError, 'Redirected'):
                cv.resolve(self.prefs)

    def test_access_failure_is_not_no_output(self):
        with patch.object(Path, 'iterdir', side_effect=PermissionError('Synthetic')):
            self.assertEqual(cv.resolve(self.prefs)['status'], 'inaccessible')

    def test_future_save_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            cv.resolve(self.prefs, (helper.now() + dt.timedelta(days=1)).isoformat())

    def test_changed_file_during_hash_is_not_selected(self):
        path = self.output('Example CV one.docx')
        original = cv.hashlib.sha256
        changed_time = self.epoch + 5
        class ChangingHash:
            def __init__(self):
                self.digest = original()
            def update(self, block):
                self.digest.update(block)
                os.utime(path, (changed_time, changed_time))
            def hexdigest(self):
                return self.digest.hexdigest()
        with patch.object(cv.hashlib, 'sha256', ChangingHash):
            result = cv.resolve(self.prefs)
        self.assertEqual(result['status'], 'changed_during_observation')
        self.assertNotIn('selected', result)

    def test_cli_uses_profile_pattern_and_prints_only_metadata(self):
        output_file = self.output('Example CV one.docx')
        self.fixture.config['review'] = {'check_in': self.prefs}
        self.fixture.config_path.write_bytes(helper.encoded(self.fixture.config))
        before = self.snapshot()
        output = io.StringIO()
        with patch.object(sys, 'argv', ['cv_output.py', str(self.fixture.state)]), contextlib.redirect_stdout(output):
            cv.main()
        self.assertEqual(json.loads(output.getvalue())['selected']['path'], str(output_file))
        self.assertNotIn('Synthetic CV sentinel', output.getvalue())
        self.assertEqual(self.snapshot(), before)


class OutputObservationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.PrivateStateTests('runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.state = self.fixture.state

    def event(self, kind='cv', revision=0):
        report = self.state / ('observation-' + helper.uuid.uuid4().hex + '.json')
        report.write_bytes(helper.encoded({'kind':kind, 'status':'synthetic observation, not content verification'}))
        return dict(event_id=helper.uuid.uuid4().hex, cycle_id='cycle-1', expected_revision=revision,
                    action='output_observed', actor='system', reference='Synthetic inspection evidence',
                    occurred_at=helper.now().isoformat(), output_observation=dict(kind=kind,
                    report_path=str(report), report_sha256=helper.file_hash(report)))

    def snapshot(self):
        return {str(p):p.read_bytes() for p in self.state.rglob('*') if p.is_file()}

    def test_observation_is_retrievable_without_closing_or_completing_review(self):
        before = self.fixture.config_path.read_bytes()
        event = self.event()
        helper.record_check_in(self.state, event)
        status = helper.check_in_status(self.state)
        saved = status['output_observations']['cv']
        self.assertEqual(saved['event_id'], event['event_id'])
        self.assertEqual(saved['evidence_status'], 'matches_saved_report')
        self.assertEqual(saved['output_freshness'], 'must_recheck_current_output')
        cycle = status['state']['cycles']['cycle-1']
        self.assertEqual(cycle['manual_submission_state'], 'pending')
        self.assertEqual(cycle['broader_review_state'], 'not_recorded')
        self.assertEqual(self.fixture.config_path.read_bytes(), before)

    def test_latest_event_per_kind_and_changed_report_detected(self):
        first = self.event(); helper.record_check_in(self.state, first)
        second = self.event(revision=1); helper.record_check_in(self.state, second)
        website = self.event('website', 2); helper.record_check_in(self.state, website)
        Path(second['output_observation']['report_path']).write_bytes(b'Changed')
        before = self.snapshot()
        status = helper.check_in_status(self.state)
        self.assertEqual(status['output_observations']['cv']['event_id'], second['event_id'])
        self.assertEqual(status['output_observations']['cv']['evidence_status'], 'missing_or_changed_report')
        self.assertIn('website', status['output_observations'])
        self.assertEqual(self.snapshot(), before)

    def test_missing_wrong_hash_outside_report_refused(self):
        for failure in ('missing', 'wrong_hash', 'outside'):
            event = self.event()
            if failure == 'missing':
                Path(event['output_observation']['report_path']).unlink()
            elif failure == 'wrong_hash':
                event['output_observation']['report_sha256'] = '0' * 64
            else:
                event['output_observation']['report_path'] = str(self.fixture.project / 'report.json')
            before = self.snapshot()
            with self.assertRaises(ValueError):
                helper.record_check_in(self.state, event)
            self.assertEqual(self.snapshot(), before)

    def test_report_change_before_commit_retains_prior_state(self):
        event = self.event()
        original = helper.commit
        def change(*args, **kwargs):
            Path(event['output_observation']['report_path']).write_bytes(b'Changed before commit')
            return original(*args, **kwargs)
        with patch.object(helper, 'commit', side_effect=change):
            with self.assertRaisesRegex(ValueError, 'report changed'):
                helper.record_check_in(self.state, event)
        self.assertFalse((self.state / 'reviews/check-in-state.json').exists())

    def test_replay_is_idempotent_and_other_actions_reject_observation_payload(self):
        event = self.event(); helper.record_check_in(self.state, event)
        before = self.snapshot()
        self.assertEqual(helper.record_check_in(self.state, event)['status'], 'already_recorded')
        self.assertEqual(self.snapshot(), before)
        event['action'] = 'dispatched'
        with self.assertRaisesRegex(ValueError, 'applies only'):
            helper.record_check_in(self.state, event)

    def test_output_after_closeout_does_not_reopen_cycle(self):
        event = self.event()
        dispatch = {k:v for k,v in event.items() if k != 'output_observation'}
        dispatch.update(event_id=helper.uuid.uuid4().hex, action='dispatched')
        helper.record_check_in(self.state, dispatch)
        closed = dict(dispatch, event_id=helper.uuid.uuid4().hex, action='closed', actor='user',
                      occurred_at=helper.now().isoformat(), expected_revision=1)
        helper.record_check_in(self.state, closed)
        event.update(expected_revision=2, occurred_at=helper.now().isoformat())
        helper.record_check_in(self.state, event)
        self.assertEqual(helper.check_in_status(self.state)['state']['cycles']['cycle-1']['manual_submission_state'], 'closed')


if __name__ == '__main__':
    unittest.main()
