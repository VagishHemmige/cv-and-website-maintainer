"""Synthetic batching tests: private staging, atomic flush and no completion inference."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import test_private_state as fixtures

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('confirmations_target', ROOT / 'scripts/confirmations.py')
batch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(batch)
helper = batch.helper


class ConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.PrivateStateTests('runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.state = self.fixture.state
        self.stage_dir = self.fixture.base / 'private-run-staging'; self.stage_dir.mkdir()
        self.source = self.fixture.project / 'projects.yml'; self.source.write_bytes(b'- title: Synthetic\n  status: active\n')
        self.target = self.state / 'reviews/no-change-confirmations.json'

    def answer(self, category='Projects', cycle='cycle-1'):
        return dict(id=helper.uuid.uuid4().hex, cycle_id=cycle, category=category, outcome='no_changes',
                    response='All remain active', reference='Synthetic actual question/list and user reply',
                    source_hashes={str(self.source): helper.file_hash(self.source)})

    def stage(self, answer=None):
        answer = answer or self.answer()
        return answer, batch.stage(self.state, self.stage_dir, answer)

    def snapshot(self):
        return {str(p):p.read_bytes() for p in self.state.rglob('*') if p.is_file()}

    def test_stage_retains_answer_without_canonical_write(self):
        before = self.snapshot()
        answer, result = self.stage()
        self.assertEqual(helper.decode(Path(result['path']).read_bytes())['answer'], answer)
        self.assertFalse(result['canonical_history_saved'])
        self.assertEqual(self.snapshot(), before)

    def test_stage_restart_replay_preserves_original_and_conflict_refused(self):
        answer, result = self.stage()
        before = Path(result['path']).read_bytes()
        self.assertEqual(batch.stage(self.state, self.stage_dir, answer)['status'], 'already_staged')
        self.assertEqual(Path(result['path']).read_bytes(), before)
        answer['response'] = 'Different response'
        with self.assertRaisesRegex(ValueError, 'different answer'):
            batch.stage(self.state, self.stage_dir, answer)
        self.assertEqual(Path(result['path']).read_bytes(), before)

    def test_two_answers_use_one_commit_and_no_review_completion(self):
        one, _ = self.stage()
        two, _ = self.stage(self.answer('Grants'))
        config_before = self.fixture.config_path.read_bytes()
        result = batch.flush(self.state, self.stage_dir, 'cycle-1', 0)
        self.assertEqual(set(result['saved_ids']), {one['id'], two['id']})
        self.assertEqual(len(list((self.state / 'state-history').iterdir())), 1)
        status = helper.check_in_status(self.state)
        self.assertEqual(set(status['no_change_confirmations']['state']['confirmations']), {one['id'], two['id']})
        self.assertEqual(status['state']['cycles'], {})
        self.assertEqual(self.fixture.config_path.read_bytes(), config_before)

    def test_flush_replay_does_not_duplicate_even_after_later_source_change(self):
        self.stage(); batch.flush(self.state, self.stage_dir, 'cycle-1', 0)
        self.source.write_bytes(b'Later changed records')
        before = self.snapshot()
        self.assertEqual(batch.flush(self.state, self.stage_dir, 'cycle-1', 0)['status'], 'no_pending_confirmations')
        self.assertEqual(self.snapshot(), before)

    def test_stale_sources_block_entire_batch(self):
        self.stage(); self.stage(self.answer('Grants'))
        self.source.write_bytes(b'Changed before batch flush')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'Displayed source changed'):
            batch.flush(self.state, self.stage_dir, 'cycle-1', 0)
        self.assertEqual(self.snapshot(), before)

    def test_stale_profile_and_history_revision_refused(self):
        self.stage()
        config = json.loads(self.fixture.config_path.read_bytes())
        config['identity'] = {'full_name':'Changed identity'}
        self.fixture.config_path.write_bytes(helper.encoded(config))
        with self.assertRaisesRegex(ValueError, 'Profile scope changed'):
            batch.flush(self.state, self.stage_dir, 'cycle-1', 0)
        self.fixture.config_path.write_bytes(helper.encoded(self.fixture.config))
        batch.flush(self.state, self.stage_dir, 'cycle-1', 0)
        self.stage(self.answer('Grants'))
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'history changed'):
            batch.flush(self.state, self.stage_dir, 'cycle-1', 0)
        self.assertEqual(self.snapshot(), before)

    def test_other_cycles_remain_staged(self):
        one, _ = self.stage()
        two, result = self.stage(self.answer(cycle='cycle-2'))
        batch.flush(self.state, self.stage_dir, 'cycle-1', 0)
        self.assertEqual(set(helper.decode(self.target.read_bytes())['confirmations']), {one['id']})
        self.assertTrue(Path(result['path']).exists())
        self.assertNotIn(two['id'], helper.decode(self.target.read_bytes())['confirmations'])

    def test_no_changes_only_not_deferral_or_approval(self):
        for outcome in ('deferred', 'approved', 'changed', 'broader_completed'):
            answer = self.answer(); answer['outcome'] = outcome
            with self.assertRaisesRegex(ValueError, 'no_changes'):
                batch.stage(self.state, self.stage_dir, answer)
        answer = self.answer(); answer['approval'] = 'yes'
        with self.assertRaises(ValueError):
            batch.stage(self.state, self.stage_dir, answer)
        self.assertEqual(list(self.stage_dir.iterdir()), [])

    def test_public_staging_and_external_source_paths_refused(self):
        public = self.fixture.project / 'staging'; public.mkdir()
        with self.assertRaisesRegex(ValueError, 'outside the project'):
            batch.stage(self.state, public, self.answer())
        answer = self.answer(); answer['source_hashes'] = {str(self.fixture.config_path): helper.file_hash(self.fixture.config_path)}
        with self.assertRaisesRegex(ValueError, 'within the configured project'):
            batch.stage(self.state, self.stage_dir, answer)

    def test_precommit_staging_change_prevents_canonical_commit(self):
        _, result = self.stage()
        original = helper.commit
        def change(*args, **kwargs):
            Path(result['path']).write_bytes(b'Changed staging')
            return original(*args, **kwargs)
        with patch.object(helper, 'commit', side_effect=change):
            with self.assertRaisesRegex(ValueError, 'Staged confirmation changed'):
                batch.flush(self.state, self.stage_dir, 'cycle-1', 0)
        self.assertFalse(self.target.exists())

    def test_post_replace_interruption_inspected_and_verified_without_resave(self):
        self.stage()
        original = helper.exclusive
        def interrupt(path, raw):
            if path.name == 'committed.json':
                raise OSError('Synthetic post-replace receipt interruption')
            return original(path, raw)
        with patch.object(helper, 'exclusive', side_effect=interrupt):
            with self.assertRaisesRegex(ValueError, 'bytes may already be committed'):
                batch.flush(self.state, self.stage_dir, 'cycle-1', 0)
        operation = next((self.state / 'state-history').iterdir()).name
        self.assertEqual(helper.operation_status(self.state, operation)[2]['status'], 'committed_unverified')
        before = self.target.read_bytes()
        self.assertFalse(helper.verify_operation(self.state, operation)['state_rewritten'])
        self.assertEqual(self.target.read_bytes(), before)
        self.assertEqual(batch.flush(self.state, self.stage_dir, 'cycle-1', 0)['status'], 'no_pending_confirmations')

    def test_malformed_history_and_staging_preserved(self):
        self.stage()
        self.target.parent.mkdir(); self.target.write_bytes(b'{broken')
        before = self.snapshot()
        with self.assertRaises(ValueError):
            batch.flush(self.state, self.stage_dir, 'cycle-1', 0)
        self.assertEqual(self.snapshot(), before)
        with self.assertRaises(ValueError):
            helper.check_in_status(self.state)

    def test_cli_stage_and_flush(self):
        answer = self.answer()
        incoming = self.fixture.base / 'answer.json'; incoming.write_bytes(helper.encoded(answer))
        for args in (['stage', str(self.state), str(self.stage_dir), str(incoming)],
                     ['flush', str(self.state), str(self.stage_dir), '--cycle', 'cycle-1', '--expected-revision', '0']):
            output = io.StringIO()
            with patch.object(sys, 'argv', ['confirmations.py', *args]), contextlib.redirect_stdout(output):
                batch.main()
            self.assertIn('status', json.loads(output.getvalue()))
        self.assertIn(answer['id'], helper.decode(self.target.read_bytes())['confirmations'])


if __name__ == '__main__':
    unittest.main()
