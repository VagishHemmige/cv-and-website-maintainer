"""Real-R date diagnostics and disposable proposal saves; never run a user's CV."""
import json
import os
from pathlib import Path
import subprocess
import unittest
import zipfile
import test_proposals as fixtures

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get('TEST_RSCRIPT'), 'Set TEST_RSCRIPT for real R date tests')
class DatePaddingTests(unittest.TestCase):
    fixture = fixtures.ProposalTests.fixture
    save_config = fixtures.ProposalTests.save_config
    cli = fixtures.ProposalTests.cli
    runtime = fixtures.ProposalTests.runtime
    apply = fixtures.ProposalTests.apply
    receipt = fixtures.ProposalTests.receipt

    def setUp(self):
        fixtures.ProposalTests.setUp(self)
        self.stub.stop()
        self.fixture()

    def update(self, name, **fields):
        path = self.data/(name+'.yml')
        records = json.loads(path.read_text(encoding='utf-8'))
        records[0].update(fields)
        path.write_text(json.dumps(records, indent=2)+'\n', encoding='utf-8')

    def run_r(self, script, *args):
        environment = dict(os.environ)
        if self.library:
            environment['R_LIBS_USER'] = self.library
        return subprocess.run([self.rscript, str(script), *map(str,args)],
                              capture_output=True, text=True, env=environment)

    def validate(self):
        before = {p:p.read_bytes() for p in self.data.iterdir() if p.is_file()}
        result = self.run_r(ROOT/'scripts/validate.R', self.data, self.data/'library.bib')
        self.assertIn('AR_VALIDATION_V1', result.stdout, result.stderr)
        for path, original in before.items():
            self.assertEqual(path.read_bytes(), original, path.name)
        return result

    def test_valid_unpadded_scalar_and_session_dates_warn_without_rewriting(self):
        self.update('abstracts', date='2026-2-9')
        self.update('talks', date='2026-04-3')
        self.update('teaching', dates=['2026-4-24', '2026-05-01'])
        self.update('education', start_date='2006-9', degree_date='2010-5-3')
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        messages = [line for line in result.stdout.splitlines() if 'not zero-padded' in line]
        self.assertEqual(len(messages), 5, messages)
        for expected in ('2026-02-09', '2026-04-03', '2026-04-24', '2006-09', '2010-05-03'):
            self.assertTrue(any('suggested '+expected+' at the same precision' in line for line in messages), expected)
        self.assertTrue(any('teaching[1] dates[1]' in line for line in messages))

    def test_padded_dates_year_month_precision_null_and_present_do_not_warn(self):
        self.update('education', start_date='2006', degree_date='2010-05')
        self.update('appointments', end_date='present')
        self.update('abstracts', date='2026-02-09')
        self.update('talks', date='2026-04-24')
        self.update('teaching', dates=['2026-04-24'])
        self.update('memberships', end_date=None)
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertNotIn('not zero-padded', result.stdout)

    def test_invalid_calendar_date_remains_error_without_format_only_suggestion(self):
        self.update('abstracts', date='2026-2-30')
        result = self.validate()
        self.assertEqual(result.returncode, 1)
        self.assertIn('abstracts[1] date invalid date/precision', result.stdout)
        self.assertNotIn('not zero-padded', result.stdout)

    def test_missing_required_full_date_remains_error_without_invented_day(self):
        self.update('abstracts', date='2026-2')
        result = self.validate()
        self.assertEqual(result.returncode, 1)
        self.assertIn('abstracts[1] date invalid date/precision', result.stdout)
        self.assertNotIn('not zero-padded', result.stdout)

    def test_starter_date_sort_orders_padded_dates_and_preserves_ties(self):
        with zipfile.ZipFile(ROOT/'assets/starter.zip') as archive:
            source = archive.read('starter/R/cv.R')
        script_source = self.base/'starter-source.R'
        script_source.write_bytes(source)
        check = self.base/'sort-check.R'
        code = """
env <- new.env(parent = baseenv())
for (expr in parse(SOURCE)) {
  if (is.call(expr) && identical(expr[[1]], as.name("<-")) &&
      is.symbol(expr[[2]]) && as.character(expr[[2]]) %in% c("%||%", "sort_by_date"))
    eval(expr, envir = env)
}
stopifnot(exists("sort_by_date", envir = env, inherits = FALSE))
records <- list(list(title="October", date="2026-10-01"),
                list(title="April first", date="2026-04-24"),
                list(title="February", date="2026-02-09"),
                list(title="April second", date="2026-04-24"))
got <- vapply(env$sort_by_date(records, "date"), function(r) r$title, character(1))
stopifnot(identical(got, c("February", "April first", "April second", "October")))
cat("Padded-date chronology and stable ties verified; CV generator not run\\n")
"""
        code = code.replace('SOURCE', json.dumps(str(script_source)))
        check.write_text(code, encoding='utf-8')
        result = self.run_r(check)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertIn('CV generator not run', result.stdout)
        self.assertFalse(any(self.base.rglob('*.docx')))

    def test_real_proposal_can_review_and_save_padding_correction_with_warning_resolved(self):
        self.update('abstracts', date='2026-2-9')
        target = self.data/'abstracts.yml'; original = target.read_bytes()
        candidate = self.base/'abstract-candidate.yml'
        candidate.write_bytes(original.replace(b'2026-2-9', b'2026-02-09'))
        proposal = self.cli('propose', self.state, self.data, 'abstracts.yml', candidate, *self.runtime())
        self.assertIn('not zero-padded', proposal['baseline_validation'])
        self.assertNotIn('not zero-padded', proposal['proposed_validation'])
        self.assertEqual(target.read_bytes(), original)
        result = self.apply(proposal['id'])
        self.assertEqual(result['status'], 'verified_saved')
        self.assertEqual(target.read_bytes(), candidate.read_bytes())
        self.assertEqual((self.receipt(proposal['id']).parent/'backup/abstracts.yml').read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
