"""Exercise actual proposal/apply commands on disposable LF and CRLF records."""
import os
from pathlib import Path
import unittest
import test_proposals as fixtures

helper = fixtures.helper


class ProposalDiffNewlineTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ProposalTests('runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.fixture()

    def proposal(self, ending):
        before = ending.join([
            '- title: "Example teaching"',
            '  venue: "Example Seminar"',
            '  dates:',
            '    - "2025-04-14"',
            '  description: "Unchanged context"',
            '']).encode('utf-8')
        after = before.replace(b'Example teaching', 'Reviewed teaching – café'.encode('utf-8')).replace(
            b'Example Seminar', b'Reviewed Seminar')
        target = self.fixture.data / 'teaching.yml'
        target.write_bytes(before)
        candidate = self.fixture.base / 'candidate.yml'; candidate.write_bytes(after)
        ident = self.fixture.cli('propose', self.fixture.state, self.fixture.data,
                                 'teaching.yml', candidate, *self.fixture.runtime())['id']
        folder = self.fixture.state / 'proposals' / ident
        return ident, folder, before, after

    def assert_minimal_diff(self, folder, before, after):
        raw = (folder / 'diff.txt').read_bytes()
        self.assertNotIn(b'\r\r', raw)
        lines = raw.decode('utf-8').splitlines()
        removed = [line[1:] for line in lines if line.startswith('-') and not line.startswith('---')]
        added = [line[1:] for line in lines if line.startswith('+') and not line.startswith('+++')]
        self.assertEqual(removed, ['- title: "Example teaching"', '  venue: "Example Seminar"'])
        self.assertEqual(added, ['- title: "Reviewed teaching – café"', '  venue: "Reviewed Seminar"'])
        self.assertIn('   description: "Unchanged context"', lines)
        self.assertEqual((folder / 'staged/teaching.yml').read_bytes(), after)
        self.assertEqual((self.fixture.data / 'teaching.yml').read_bytes(), before)

    def test_crlf_two_line_edit_is_minimal_and_staging_is_byte_exact(self):
        _, folder, before, after = self.proposal('\r\n')
        self.assert_minimal_diff(folder, before, after)
        self.assertIn(b'\r\n', (folder / 'diff.txt').read_bytes())

    def test_lf_two_line_edit_does_not_gain_windows_carriage_returns(self):
        _, folder, before, after = self.proposal('\n')
        self.assert_minimal_diff(folder, before, after)
        self.assertNotIn(b'\r', (folder / 'diff.txt').read_bytes())

    def test_apply_preserves_crlf_candidate_and_verified_backup(self):
        ident, folder, before, after = self.proposal('\r\n')
        self.assertEqual(self.fixture.apply(ident)['status'], 'verified_saved')
        self.assertEqual((self.fixture.data / 'teaching.yml').read_bytes(), after)
        backups = [p for p in (folder / 'backup').rglob('teaching.yml')]
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), before)

    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT'), 'Set TEST_RSCRIPT for real R validation')
    def test_real_r_crlf_propose_and_apply(self):
        self.fixture.stub.stop()
        ident, folder, before, after = self.proposal('\r\n')
        self.assert_minimal_diff(folder, before, after)
        self.assertEqual(self.fixture.apply(ident)['status'], 'verified_saved')
        self.assertEqual((self.fixture.data / 'teaching.yml').read_bytes(), after)


if __name__ == '__main__':
    unittest.main()
