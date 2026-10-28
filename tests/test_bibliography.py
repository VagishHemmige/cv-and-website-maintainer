"""F3 regressions: disposable records and simulated approval assertions only."""
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import test_proposals as base
helper = base.helper
REAL_VALIDATE = base.REAL_VALIDATE


class BibliographyTests(unittest.TestCase):
    setUp = base.ProposalTests.setUp
    fixture = base.ProposalTests.fixture
    save_config = base.ProposalTests.save_config
    cli = base.ProposalTests.cli
    runtime = base.ProposalTests.runtime
    propose = base.ProposalTests.propose
    apply = base.ProposalTests.apply
    receipt = base.ProposalTests.receipt
    interrupted = base.ProposalTests.interrupted
    mutate_after_live_validation = base.ProposalTests.mutate_after_live_validation
    def export(self, text='% unrelated export\n'):
        bib = self.data / 'library.bib'
        bib.write_text(bib.read_text(encoding='utf-8') + text, encoding='utf-8')

    def test_export_before_approval_preserves_exact_candidate_and_staging(self):
        self.fixture()
        ident = self.propose()
        folder = self.state / 'proposals' / ident
        staged = folder / 'staged' / 'library.bib'
        before = staged.read_bytes()
        self.export()
        self.assertEqual(self.apply(ident)['status'], 'verified_saved')
        self.assertEqual(staged.read_bytes(), before)
        item = json.loads((folder / 'proposal.json').read_text())
        self.assertEqual(helper.digest(self.data / 'teaching.yml'), item['candidate_sha256'])
        receipt = json.loads(self.receipt(ident).read_text())
        self.assertEqual(receipt['validated_bibliography_sha256'], helper.digest(self.data / 'library.bib'))
        self.assertTrue(self.cli('status', self.state, ident)['current_snapshot_matches'])

    def test_changed_warnings_block_before_any_write_or_attempt(self):
        self.fixture()
        ident = self.propose()
        self.export()
        before = (self.data / 'teaching.yml').read_bytes()
        def changed(root, *args):
            return 'WARNING: Unmatched citation key: example' if Path(root).name.startswith('bibliography-check-') else 'stub'
        with patch.object(helper, 'validate', side_effect=changed), self.assertRaisesRegex(ValueError, 'renewed review'):
            self.apply(ident)
        self.assertEqual((self.data / 'teaching.yml').read_bytes(), before)
        self.assertFalse((self.state / 'proposals' / ident / 'attempts').exists())
        self.assertFalse(self.receipt(ident).exists())

    def test_one_export_during_postwrite_validation_is_revalidated(self):
        self.fixture()
        ident = self.propose()
        calls = []
        def once(root, *args):
            if Path(root) == self.data:
                calls.append(1)
                if len(calls) == 1:
                    self.export()
            return 'stub'
        with patch.object(helper, 'validate', side_effect=once):
            self.assertEqual(self.apply(ident)['status'], 'verified_saved')
        self.assertEqual(len(calls), 2)

    def test_export_during_prewrite_validation_retries(self):
        self.fixture()
        ident = self.propose()
        calls = []
        def once(root, *args):
            if Path(root).name.startswith('bibliography-check-'):
                calls.append(1)
                if len(calls) == 1:
                    self.export()
            return 'stub'
        with patch.object(helper, 'validate', side_effect=once):
            self.apply(ident)
        self.assertEqual(len(calls), 2)

    def test_new_warnings_after_write_leave_recoverable_unverified_save(self):
        self.fixture()
        ident = self.propose()
        def changed(root, *args):
            return 'WARNING: Unmatched citation key: example' if Path(root) == self.data else 'stub'
        with patch.object(helper, 'validate', side_effect=changed), self.assertRaisesRegex(ValueError, 'renewed review'):
            self.apply(ident)
        self.assertFalse(self.receipt(ident).exists())
        self.assertEqual(helper.proposal_status(self.state, ident), 'saved_unverified')
        before = helper.digest(self.data / 'teaching.yml')
        self.export()
        self.assertFalse(self.cli('verify', self.state, ident, *self.runtime())['record_rewritten'])
        self.assertEqual(helper.digest(self.data / 'teaching.yml'), before)

    def test_stable_validation_error_is_not_ignored(self):
        self.fixture()
        ident = self.propose()
        def error(root, *args):
            if Path(root).name.startswith('bibliography-check-'):
                raise ValueError('Validation failed. synthetic error')
            return 'stub'
        with patch.object(helper, 'validate', side_effect=error), self.assertRaisesRegex(ValueError, 'Validation failed'):
            self.apply(ident)
        self.assertFalse(self.receipt(ident).exists())
        self.assertIn('Example teaching', (self.data / 'teaching.yml').read_text())

    def test_validation_error_during_export_retries_stable_generation(self):
        self.fixture()
        ident = self.propose()
        calls = []
        def error_once(root, *args):
            if Path(root).name.startswith('bibliography-check-'):
                calls.append(1)
                if len(calls) == 1:
                    self.export()
                    raise ValueError('Transient partial export')
            return 'stub'
        with patch.object(helper, 'validate', side_effect=error_once):
            self.apply(ident)
        self.assertEqual(len(calls), 2)

    def test_staged_bibliography_tampering_still_refused(self):
        self.fixture()
        ident = self.propose()
        staged = self.state / 'proposals' / ident / 'staged' / 'library.bib'
        staged.write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'Staged bibliography changed'):
            self.apply(ident)

    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT'), 'Set TEST_RSCRIPT for real R/yaml integration')
    def test_real_r_export_before_approval(self):
        self.fixture()
        self.stub.stop()
        mentor = self.data / 'mentoring.yml'
        rows = json.loads(mentor.read_text())
        rows[0]['manuscripts'] = ['example']
        mentor.write_text(json.dumps(rows))
        ident = self.propose()
        self.export('@article{another, title={Another}, year={2026}}\n')
        self.assertEqual(self.apply(ident)['status'], 'verified_saved')

    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT'), 'Set TEST_RSCRIPT for real R/yaml integration')
    def test_real_r_citation_removal_requires_renewed_review(self):
        self.fixture()
        self.stub.stop()
        mentor = self.data / 'mentoring.yml'
        rows = json.loads(mentor.read_text())
        rows[0]['manuscripts'] = ['example']
        mentor.write_text(json.dumps(rows))
        ident = self.propose()
        before = (self.data / 'teaching.yml').read_bytes()
        (self.data / 'library.bib').write_text('@article{another, title={Another}}\n')
        with self.assertRaisesRegex(ValueError, 'WARNING: Unmatched citation key: example'):
            self.apply(ident)
        self.assertEqual((self.data / 'teaching.yml').read_bytes(), before)
        self.assertFalse(self.receipt(ident).exists())

    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT'), 'Set TEST_RSCRIPT for real R/yaml integration')
    def test_real_r_one_export_during_saving(self):
        self.fixture()
        self.stub.stop()
        ident = self.propose()
        calls = []
        def once(root, *args):
            output = REAL_VALIDATE(root, *args)
            if Path(root) == self.data:
                calls.append(1)
                if len(calls) == 1:
                    self.export()
            return output
        with patch.object(helper, 'validate', side_effect=once):
            self.apply(ident)
        self.assertEqual(len(calls), 2)

    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT'), 'Set TEST_RSCRIPT for real R/yaml integration')
    def test_real_r_recovery_after_export_does_not_rewrite_records(self):
        self.fixture()
        self.stub.stop()
        ident = self.propose()
        self.interrupted(ident)
        self.export()
        before = helper.digest(self.data / 'teaching.yml')
        self.assertFalse(self.cli('verify', self.state, ident, *self.runtime())['record_rewritten'])
        self.assertEqual(helper.digest(self.data / 'teaching.yml'), before)

    def null_bibliography_fixture(self, default_exists=True):
        self.fixture()
        self.stub.stop()
        self.config['bibliography_file'] = None
        self.save_config()
        if default_exists:
            (self.data / 'publications.bib').write_bytes((self.data / 'library.bib').read_bytes())
        mentor = self.data / 'mentoring.yml'
        rows = json.loads(mentor.read_text())
        rows[0]['manuscripts'] = ['example']
        mentor.write_text(json.dumps(rows), encoding='utf-8')

    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT'), 'Set TEST_RSCRIPT for real R/yaml integration')
    def test_real_r_null_bibliography_with_default_file_can_verify_save(self):
        self.null_bibliography_fixture()
        before = (self.state / 'config.json').read_bytes()
        bib_before = (self.data / 'publications.bib').read_bytes()
        ident = self.propose()
        self.assertEqual(self.apply(ident)['status'], 'verified_saved')
        receipt = json.loads(self.receipt(ident).read_text())
        self.assertIn('BibTeX unavailable', receipt['validation'])
        self.assertEqual((self.state / 'config.json').read_bytes(), before)
        self.assertEqual((self.data / 'publications.bib').read_bytes(), bib_before)

    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT'), 'Set TEST_RSCRIPT for real R/yaml integration')
    def test_real_r_default_file_appearing_after_proposal_does_not_change_null_scope(self):
        self.null_bibliography_fixture(default_exists=False)
        ident = self.propose()
        (self.data / 'publications.bib').write_bytes((self.data / 'library.bib').read_bytes())
        self.assertEqual(self.apply(ident)['status'], 'verified_saved')

    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT'), 'Set TEST_RSCRIPT for real R/yaml integration')
    def test_real_r_null_bibliography_recovery_keeps_warnings_and_does_not_rewrite(self):
        self.null_bibliography_fixture()
        ident = self.propose()
        real = helper.write_json
        def interrupted_receipt(path, value):
            if path.name == 'applied.json':
                raise OSError('Synthetic receipt interruption')
            return real(path, value)
        with patch.object(helper, 'write_json', side_effect=interrupted_receipt), self.assertRaises(ValueError):
            self.apply(ident)
        before = (self.data / 'teaching.yml').read_bytes()
        result = self.cli('verify', self.state, ident, *self.runtime())
        self.assertEqual(result['status'], 'verified_saved')
        self.assertFalse(result['record_rewritten'])
        self.assertEqual((self.data / 'teaching.yml').read_bytes(), before)

    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT'), 'Set TEST_RSCRIPT for real R/yaml integration')
    def test_real_r_standalone_validator_keeps_default_bibliography_behavior(self):
        import subprocess
        self.null_bibliography_fixture()
        env = os.environ.copy()
        if self.library:
            env['R_LIBS_USER'] = self.library
        result = subprocess.run([self.rscript, str(Path(helper.__file__).with_name('validate.R')), str(self.data)],
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('BibTeX unavailable', result.stdout)
        self.assertIn('BibTeX unavailable', REAL_VALIDATE(self.data, self.rscript, self.library, None))


