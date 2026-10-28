"""Synthetic regression tests. Approval assertions never authorize real records.

Run: python -B -m unittest discover -s tests -v
Set TEST_RSCRIPT and optional TEST_R_LIBRARY for real R/yaml integration tests.
Set TEST_TMP_ROOT to an authorized short scratch directory when OS temp is restricted.
"""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from approval_fixture import approval_file

SPEC = importlib.util.spec_from_file_location('proposal_tests_target',
    Path(__file__).resolve().parents[1] / 'scripts' / 'proposals.py')
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)
REAL_VALIDATE = helper.validate


def records(with_media):
    values = {
        'education': dict(id='e', institution='Example University', degree='MD', degree_date='2010', start_date='2006'),
        'training': dict(id='t', institution='Example Hospital', role='Fellow', start_date='2013'),
        'appointments': dict(id='a', title='Professor', institution='Example University', start_date='2016'),
        'certifications': dict(id='c', title='Certification', board='Example Board', specialty='Medicine', start_date='2016'),
        'memberships': dict(id='m', society='Example Society', start_date='2010'),
        'honors': dict(id='h', title='Teaching award', institution='Example University', date='2024'),
        'service': dict(id='s', category='intramural', role='Member', activity='Committee', institution='Example University', start_date='2021'),
        'grants': dict(id='g', sponsor='Example Foundation', title='Research', role='Investigator', start_date='2023', total_support=100),
        'abstracts': dict(title='Example abstract', authors='Scholar A.', meeting='Example Meeting', date='2025-05-12', type='poster'),
        'talks': dict(title='Example talk', role='Lecturer', venue='Example University', date='2025-06-15', category='invited'),
        'teaching': dict(title='Example teaching', venue='Example Seminar', dates=['2024-04-15', '2025-04-14']),
        'mentoring': dict(name='Example Learner', status='Active'),
        'projects': dict(title='Example Project', theme='Education', description='Synthetic fixture', status='active'),
    }
    if with_media:
        values['media'] = dict(id='media-example', section='printed_news', title='Example coverage',
                               date=None, url='https://example.invalid/story', embed=None)
    return values


class ProposalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TEST_TMP_ROOT'))
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'p'
        self.data = self.root / 'data'
        self.data.mkdir(parents=True)
        self.state = self.base / 's'
        self.state.mkdir()
        self.rscript = os.environ.get('TEST_RSCRIPT', 'fixture-validator')
        self.library = os.environ.get('TEST_R_LIBRARY')
        self.stub = patch.object(helper, 'validate', return_value='Synthetic unit validator stub')
        self.stub.start()
        self.addCleanup(self.stub.stop)

    def fixture(self, media=False):
        for name, value in records(media).items():
            (self.data / (name + '.yml')).write_text(json.dumps([value], indent=2) + '\n', encoding='utf-8')
        (self.data / 'library.bib').write_text('@article{example, title={Synthetic}, year={2025}}\n', encoding='utf-8')
        self.config = dict(project_root=str(self.root), data_root=str(self.data),
                           approved_files=list(helper.source_files(self.data)),
                           approval_policy='per_change', bibliography_file='library.bib')
        self.save_config()

    def save_config(self):
        (self.state / 'config.json').write_text(json.dumps(self.config), encoding='utf-8')

    def cli(self, *args):
        output = io.StringIO()
        with patch.object(sys, 'argv', ['proposals.py', *map(str, args)]), contextlib.redirect_stdout(output):
            helper.main()
        return json.loads(output.getvalue())

    def runtime(self):
        return [self.rscript] + (['--r-library', self.library] if self.library else [])

    def propose(self, filename='teaching.yml'):
        text = (self.data / filename).read_text(encoding='utf-8')
        candidate = self.base / 'candidate.yml'
        candidate.write_text(text.replace('Example teaching', 'Approved teaching').replace('Example coverage', 'Approved coverage'), encoding='utf-8')
        return self.cli('propose', self.state, self.data, filename, candidate, *self.runtime())['id']

    def apply(self, ident):
        # SIMULATED FIXTURE APPROVAL ONLY. No real user data is available to this suite.
        _, item = helper.read_proposal(self.state, ident)
        evidence = approval_file(self.state, 'yaml', ident, item['candidate_sha256'], self.data / item['file'])
        return self.cli('apply', self.state, ident, '--approval', ident, '--approval-evidence', evidence, *self.runtime())

    def receipt(self, ident):
        return self.state / 'proposals' / ident / 'applied.json'

    def mutate_after_live_validation(self, action):
        def validate(root, *args):
            if Path(root) == self.data:
                action()
            return 'Synthetic unit validator stub'
        return patch.object(helper, 'validate', side_effect=validate)

    def interrupted(self, ident):
        def interrupt():
            raise ValueError('Synthetic post-write interruption')
        with self.mutate_after_live_validation(interrupt), self.assertRaises(ValueError):
            self.apply(ident)
        self.assertEqual(helper.proposal_status(self.state, ident), 'saved_unverified')

    def test_normal_13_file_save(self):
        self.fixture()
        ident = self.propose()
        self.assertEqual(self.apply(ident)['status'], 'verified_saved')
        details = self.cli('status', self.state, ident)
        self.assertTrue(details['historical_save_verified'])
        self.assertTrue(details['current_snapshot_matches'])

    def test_optional_media_update(self):
        self.fixture(media=True)
        ident = self.propose('media.yml')
        self.apply(ident)
        self.assertIn('Approved coverage', (self.data / 'media.yml').read_text())
        self.assertEqual(len(helper.source_files(self.data)), 14)

    def test_target_change_during_final_validation(self):
        self.fixture()
        ident = self.propose()
        target = self.data / 'teaching.yml'
        def change():
            target.write_text(target.read_text().replace('Approved teaching', 'Concurrent teaching'))
        with self.mutate_after_live_validation(change), self.assertRaisesRegex(ValueError, 'Snapshot changed'):
            self.apply(ident)
        self.assertFalse(self.receipt(ident).exists())
        self.assertEqual(helper.proposal_status(self.state, ident), 'conflict')

    def test_bibliography_change_during_final_validation(self):
        self.fixture()
        ident = self.propose()
        bib = self.data / 'library.bib'
        with self.mutate_after_live_validation(lambda: bib.write_text(bib.read_text() + '% concurrent export\n')), self.assertRaisesRegex(ValueError, 'Snapshot changed'):
            self.apply(ident)
        self.assertFalse(self.receipt(ident).exists())
        details = self.cli('status', self.state, ident)
        self.assertEqual(details['status'], 'saved_unverified')
        self.assertIn('library.bib', details['changed_files'])

    def test_optional_media_change_during_final_validation(self):
        self.fixture(media=True)
        ident = self.propose()
        media = self.data / 'media.yml'
        with self.mutate_after_live_validation(lambda: media.write_text(media.read_text().replace('Example coverage', 'Concurrent coverage'))), self.assertRaisesRegex(ValueError, 'media.yml'):
            self.apply(ident)
        self.assertFalse(self.receipt(ident).exists())

    def test_optional_layout_change_during_final_validation(self):
        self.fixture()
        ident = self.propose()
        with self.mutate_after_live_validation(lambda: (self.data / 'media.yml').write_text('[]\n')), self.assertRaisesRegex(ValueError, 'source-file-layout'):
            self.apply(ident)
        self.assertFalse(self.receipt(ident).exists())

    def test_current_scope_revoked_during_final_validation(self):
        self.fixture()
        ident = self.propose()
        def revoke():
            self.config['approved_files'].remove('teaching.yml')
            self.save_config()
        with self.mutate_after_live_validation(revoke), self.assertRaisesRegex(ValueError, 'not approved'):
            self.apply(ident)
        self.assertFalse(self.receipt(ident).exists())

    def test_stale_sources_are_refused(self):
        self.fixture()
        ident = self.propose()
        target = self.data / 'talks.yml'
        target.write_text(target.read_text() + '\n')
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.apply(ident)
        self.assertIn('Example teaching', (self.data / 'teaching.yml').read_text())

    def test_changed_staged_candidate_is_refused(self):
        self.fixture()
        ident = self.propose()
        staged = self.state / 'proposals' / ident / 'staged' / 'teaching.yml'
        staged.write_text(staged.read_text() + '\n')
        with self.assertRaisesRegex(ValueError, 'Staged proposal changed'):
            self.apply(ident)
        self.assertIn('Example teaching', (self.data / 'teaching.yml').read_text())

    def test_staged_change_during_validation_is_refused_before_write(self):
        self.fixture()
        ident = self.propose()
        def mutate(root, *args):
            path = Path(root) / 'teaching.yml'
            path.write_text(path.read_text() + '\n')
            return 'Synthetic validator stub'
        with patch.object(helper, 'validate', side_effect=mutate), self.assertRaisesRegex(ValueError, 'Snapshot changed'):
            self.apply(ident)
        self.assertIn('Example teaching', (self.data / 'teaching.yml').read_text())

    def test_recovery_requires_current_allowlist(self):
        self.fixture()
        ident = self.propose()
        self.interrupted(ident)
        before = helper.digest(self.data / 'teaching.yml')
        self.config['approved_files'].remove('teaching.yml')
        self.save_config()
        with self.assertRaisesRegex(ValueError, 'not approved'):
            self.cli('verify', self.state, ident, *self.runtime())
        self.assertFalse(self.receipt(ident).exists())
        self.assertEqual(before, helper.digest(self.data / 'teaching.yml'))

    def test_recovery_does_not_rewrite_record(self):
        self.fixture(media=True)
        ident = self.propose()
        self.interrupted(ident)
        before = helper.digest(self.data / 'teaching.yml')
        outcome = self.cli('verify', self.state, ident, *self.runtime())
        self.assertEqual(outcome['status'], 'verified_saved')
        self.assertFalse(outcome['record_rewritten'])
        self.assertEqual(before, helper.digest(self.data / 'teaching.yml'))

    def test_existing_receipt_does_not_bypass_current_allowlist(self):
        self.fixture()
        ident = self.propose()
        self.apply(ident)
        receipt_before = self.receipt(ident).read_bytes()
        self.config['approved_files'].remove('teaching.yml')
        self.save_config()
        with self.assertRaisesRegex(ValueError, 'not approved'):
            self.cli('verify', self.state, ident, *self.runtime())
        self.assertEqual(receipt_before, self.receipt(ident).read_bytes())
        details = self.cli('status', self.state, ident)
        self.assertTrue(details['historical_save_verified'])
        self.assertFalse(details['target_currently_approved'])

    def test_later_bibliography_change_preserves_history_but_reports_drift(self):
        self.fixture()
        ident = self.propose()
        self.apply(ident)
        original_receipt = self.receipt(ident).read_bytes()
        bib = self.data / 'library.bib'
        bib.write_text(bib.read_text() + '% later export\n')
        details = self.cli('status', self.state, ident)
        self.assertTrue(details['historical_save_verified'])
        self.assertFalse(details['current_snapshot_matches'])
        self.assertIn('library.bib', details['changed_files'])
        with self.assertRaisesRegex(ValueError, 'Snapshot changed'):
            self.cli('verify', self.state, ident, *self.runtime())
        self.assertEqual(original_receipt, self.receipt(ident).read_bytes())

    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT'), 'Set TEST_RSCRIPT for real R/yaml integration')
    def test_real_r_validation_13_and_14_files(self):
        self.stub.stop()
        self.fixture()
        ident = self.propose()
        self.assertEqual(self.apply(ident)['status'], 'verified_saved')
        self.fixture(media=True)
        ident = self.propose('media.yml')
        self.assertEqual(self.apply(ident)['status'], 'verified_saved')

    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT'), 'Set TEST_RSCRIPT for real R/yaml integration')
    def test_real_r_final_validation_race(self):
        self.fixture(media=True)
        self.stub.stop()
        ident = self.propose()
        bib = self.data / 'library.bib'
        def concurrent(root, *args):
            output = REAL_VALIDATE(root, *args)
            if Path(root) == self.data:
                bib.write_text(bib.read_text() + '% concurrent synthetic export\n')
            return output
        with patch.object(helper, 'validate', side_effect=concurrent), self.assertRaisesRegex(ValueError, 'Snapshot changed'):
            self.apply(ident)
        self.assertFalse(self.receipt(ident).exists())


if __name__ == '__main__':
    unittest.main()
