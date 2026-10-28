"""Synthetic approvals only; no test grants access to real records."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import test_proposals as records
from approval_fixture import approval_file

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('approved_save_tests', ROOT / 'scripts/approved_save.py')
save = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(save)


class ApprovedSaveTests(unittest.TestCase):
    setUp = records.ProposalTests.setUp
    fixture = records.ProposalTests.fixture
    save_config = records.ProposalTests.save_config
    cli = records.ProposalTests.cli
    runtime = records.ProposalTests.runtime
    propose = records.ProposalTests.propose
    receipt = records.ProposalTests.receipt
    mutate_after_live_validation = records.ProposalTests.mutate_after_live_validation

    def context(self, ident):
        _, item = records.helper.read_proposal(self.state, ident)
        path = approval_file(self.state, 'yaml', ident, item['candidate_sha256'],
                             self.data / item['file'])
        value = json.loads(path.read_text(encoding='utf-8'))
        del value['recorded_at']
        path.write_text(json.dumps(value), encoding='utf-8')
        return path, value

    def delegate(self, command, **kwargs):
        self.command = command
        try:
            result = self.cli(*command[3:])
            return subprocess.CompletedProcess(command, 0, json.dumps(result), '')
        except (ValueError, OSError) as error:
            return subprocess.CompletedProcess(command, 1, '', str(error))

    def execute(self, ident, path):
        output = io.StringIO()
        with patch.object(save, 'records', records.helper), \
                patch.object(save.subprocess, 'run', side_effect=self.delegate), \
                contextlib.redirect_stdout(output):
            code, result = save.apply(self.state, ident, path, self.rscript, self.library)
        return code, result, output.getvalue()

    def test_capture_delegates_existing_apply_and_retains_real_context(self):
        self.fixture(); ident = self.propose(); path, value = self.context(ident)
        before = path.read_bytes()
        original_target = (self.data/'teaching.yml').read_bytes()
        unrelated = {p: p.read_bytes() for p in self.data.iterdir() if p.name != 'teaching.yml'}
        config_before = (self.state/'config.json').read_bytes()
        code, result, output = self.execute(ident, path)
        self.assertEqual(code, 0)
        self.assertEqual(result['current']['status'], 'verified_saved')
        evidence = json.loads(Path(result['approval_evidence']).read_text(encoding='utf-8'))
        self.assertEqual(evidence['response'], value['response'])
        self.assertEqual(evidence['approvals'], value['approvals'])
        self.assertIsNone(evidence['approved_at'])
        self.assertEqual(evidence['timestamp_source'], 'message_time_unavailable')
        self.assertTrue(evidence['recorded_at'])
        self.assertEqual(path.read_bytes(), before)
        self.assertNotIn(value['response'], output)
        self.assertFalse(json.loads(output)['save_verified'])
        self.assertIn('--approval-evidence', self.command)
        self.assertEqual((self.receipt(ident).parent/'backup/teaching.yml').read_bytes(),
                         original_target)
        retained = self.receipt(ident).parent/'approval-evidence.json'
        self.assertEqual(retained.read_bytes(), Path(result['approval_evidence']).read_bytes())
        self.assertFalse((self.state/'events').exists())
        self.assertEqual((self.state/'config.json').read_bytes(), config_before)
        for source, raw in unrelated.items():
            self.assertEqual(source.read_bytes(), raw, source.name)

    def test_mismatched_id_hash_destination_and_nonapproval_are_refused_before_capture(self):
        self.fixture(); ident = self.propose(); path, value = self.context(ident)
        before = (self.data/'teaching.yml').read_bytes()
        variants = []
        for field, bad in (('id', 'b'*32), ('sha256', '0'*64),
                           ('destination', str(self.root/'different.yml'))):
            changed = json.loads(json.dumps(value)); changed['approvals'][0][field] = bad
            variants.append(changed)
        for field, bad in (('decision', 'declined'), ('message_reference', ''),
                           ('proposal_reference', ''), ('response', '')):
            changed = dict(value); changed[field] = bad; variants.append(changed)
        for changed in variants:
            with self.subTest(changed=changed):
                path.write_text(json.dumps(changed), encoding='utf-8')
                with self.assertRaises(ValueError):
                    self.execute(ident, path)
                self.assertFalse((self.state/'approval-inputs').exists())
                self.assertEqual((self.data/'teaching.yml').read_bytes(), before)

    def test_duplicate_oversized_or_extra_context_fields_are_refused(self):
        self.fixture(); ident = self.propose(); path, value = self.context(ident)
        for raw in (b'{"response":"a","response":"b"}', b' '*65537,
                    json.dumps(dict(value, recorded_at='invented')).encode()):
            path.write_bytes(raw)
            with self.assertRaises(ValueError):
                self.execute(ident, path)
        self.assertFalse((self.state/'approval-inputs').exists())

    def test_context_outside_private_state_is_refused(self):
        self.fixture(); ident = self.propose(); path, _ = self.context(ident)
        external = self.base/'external.json'; external.write_bytes(path.read_bytes())
        with self.assertRaisesRegex(ValueError, 'inside the private state'):
            self.execute(ident, external)
        self.assertFalse((self.state/'approval-inputs').exists())

    def test_known_message_time_is_preserved_not_replaced_with_capture_time(self):
        self.fixture(); ident = self.propose(); path, value = self.context(ident)
        value.update(approved_at='2026-10-17T11:00:00+00:00',
                     timestamp_source='host_message_timestamp')
        path.write_text(json.dumps(value), encoding='utf-8')
        code, result, _ = self.execute(ident, path)
        self.assertEqual(code, 0)
        captured = json.loads(Path(result['approval_evidence']).read_text())
        self.assertEqual(captured['approved_at'], value['approved_at'])
        self.assertEqual(captured['message_reference'], value['message_reference'])

    def test_already_stale_source_is_refused_before_capture(self):
        self.fixture(); ident = self.propose(); path, _ = self.context(ident)
        target = self.data/'teaching.yml'; before = target.read_bytes()
        (self.data/'service.yml').write_bytes((self.data/'service.yml').read_bytes()+b'\n')
        with self.assertRaisesRegex(ValueError, 'existing status.*stale'):
            self.execute(ident, path)
        self.assertFalse((self.state/'approval-inputs').exists())
        self.assertEqual(target.read_bytes(), before)
        self.assertFalse(self.receipt(ident).exists())

    def test_source_change_after_capture_keeps_evidence_without_claiming_saved(self):
        self.fixture(); ident = self.propose(); path, _ = self.context(ident)
        target = self.data/'teaching.yml'; before = target.read_bytes()
        original = self.delegate
        def race(command, **kwargs):
            source = self.data/'service.yml'
            source.write_bytes(source.read_bytes()+b'\n')
            return original(command, **kwargs)
        with patch.object(self, 'delegate', side_effect=race):
            code, result, output = self.execute(ident, path)
        self.assertNotEqual(code, 0)
        self.assertIn('stale', result['error'])
        self.assertEqual(result['current']['status'], 'stale')
        self.assertEqual(target.read_bytes(), before)
        self.assertTrue(Path(result['approval_evidence']).is_file())
        self.assertFalse(json.loads(output)['save_verified'])
        self.assertFalse(self.receipt(ident).exists())

    def test_tampered_staged_bytes_and_current_allowlist_still_block_save(self):
        for kind in ('staged', 'allowlist'):
            with self.subTest(kind=kind):
                self.fixture(); ident = self.propose(); path, _ = self.context(ident)
                before = (self.data/'teaching.yml').read_bytes()
                if kind == 'staged':
                    staged = self.state/'proposals'/ident/'staged/teaching.yml'
                    staged.write_bytes(staged.read_bytes()+b'\n')
                else:
                    self.config['approved_files'].remove('teaching.yml'); self.save_config()
                code, result, _ = self.execute(ident, path)
                self.assertNotEqual(code, 0)
                self.assertEqual((self.data/'teaching.yml').read_bytes(), before)
                self.assertFalse(self.receipt(ident).exists())

    def test_post_write_interruption_reports_saved_unverified_and_refuses_retry(self):
        self.fixture(); ident = self.propose(); path, _ = self.context(ident)
        def interrupt():
            raise ValueError('Synthetic post-write interruption')
        with self.mutate_after_live_validation(interrupt):
            code, result, _ = self.execute(ident, path)
        self.assertNotEqual(code, 0)
        self.assertEqual(result['current']['status'], 'saved_unverified')
        self.assertIn(b'Approved teaching', (self.data/'teaching.yml').read_bytes())
        self.assertFalse(self.receipt(ident).exists())
        captured = list((self.state/'approval-inputs').iterdir())
        with self.assertRaisesRegex(ValueError, 'existing status'):
            self.execute(ident, path)
        self.assertEqual(list((self.state/'approval-inputs').iterdir()), captured)

    def test_failed_before_write_cannot_be_reapplied(self):
        self.fixture(); ident = self.propose(); path, _ = self.context(ident)
        before = (self.data/'teaching.yml').read_bytes()
        with patch.object(records.helper, 'atomic_write', side_effect=OSError('Synthetic write failure')):
            code, result, _ = self.execute(ident, path)
        self.assertNotEqual(code, 0)
        self.assertEqual(result['current']['status'], 'failed_before_write')
        self.assertEqual((self.data/'teaching.yml').read_bytes(), before)
        with self.assertRaisesRegex(ValueError, 'existing status'):
            self.execute(ident, path)

    def test_process_launch_failure_retains_captured_evidence(self):
        self.fixture(); ident = self.propose(); path, _ = self.context(ident)
        output = io.StringIO()
        with patch.object(save, 'records', records.helper), \
                patch.object(save.subprocess, 'run', side_effect=OSError('Synthetic launch failure')), \
                contextlib.redirect_stdout(output), self.assertRaises(OSError):
            save.apply(self.state, ident, path, self.rscript)
        event = json.loads(output.getvalue())
        self.assertTrue(Path(event['approval_evidence']).is_file())
        self.assertFalse(event['save_verified'])
        self.assertFalse(self.receipt(ident).exists())

    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT'), 'Set TEST_RSCRIPT for real R integration')
    def test_real_r_subprocess_cli_retains_exact_unicode_reply_and_validates_save(self):
        self.fixture(); self.stub.stop(); ident = self.propose(); path, value = self.context(ident)
        value['response'] = 'SYNTHETIC ONLY — approve this exact fixture'
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        command = [os.sys.executable, '-B', str(ROOT/'scripts/approved_save.py'),
                   str(self.state), ident, str(path), *self.runtime()]
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr+result.stdout)
        event_line, rest = result.stdout.split('\n', 1)
        self.assertFalse(json.loads(event_line)['save_verified'])
        result_value = json.loads(rest)
        self.assertEqual(result_value['current']['status'], 'verified_saved')
        self.assertEqual(result_value['current']['approval_evidence_status'], 'recorded')
        self.assertNotIn(value['response'], result.stdout)
        captured = json.loads(Path(result_value['approval_evidence']).read_text(encoding='utf-8'))
        self.assertEqual(captured['response'], value['response'])


class RoutineSaveGuidanceTests(unittest.TestCase):
    def test_reuse_requires_matching_hashes_fields_dependencies_and_instructions(self):
        doc = (ROOT/'references/routine-save.md').read_text(encoding='utf-8')
        for phrase in ('once per run', 'Before reuse, hash', 'new\nfield, dependency',
                       'changed instruction requires', 'No validator\nresult is cached',
                       'An uninspected file', 'Do not reuse a cache across runs'):
            self.assertIn(phrase, doc)

    def test_existing_confirmation_store_and_pending_boundaries_remain(self):
        doc = (ROOT/'references/routine-save.md').read_text(encoding='utf-8')
        for phrase in ('confirmations.py stage and flush', 'Pending\nevents remain separate',
                       'not executable code', 'one YAML proposal'):
            self.assertIn(phrase, doc)
        skill = (ROOT/'skills/update-academic-records/SKILL.md').read_text(encoding='utf-8')
        self.assertIn('routine-save.md', skill)
