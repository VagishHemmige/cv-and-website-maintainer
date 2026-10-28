"""Offline catalogue/planner and real private-state integration; no mail access."""
import copy
import datetime as dt
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
import test_private_state as state_tests

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('email_queries_target', ROOT / 'scripts/email_queries.py')
email = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(email)
state = state_tests.helper


class EmailQueriesTests(unittest.TestCase):
    def setUp(self):
        self.catalogue = json.loads(email.CATALOGUE.read_text(encoding='utf-8'))

    def test_every_supported_group_has_body_capable_queries(self):
        expected = {'abstracts', 'talks', 'teaching', 'honors', 'grants', 'appointments',
                    'service', 'memberships_certifications', 'mentoring_projects', 'publications', 'media'}
        self.assertEqual(set(self.catalogue['categories']), expected)
        prepared = email.prepare('fixture-account', sorted(expected))
        self.assertEqual(set(prepared['subqueries']), expected)
        for item in prepared['queries']:
            self.assertNotIn('subject:', item['query'])
            self.assertNotIn('after:', item['query'])
            self.assertNotIn('before:', item['query'])
        self.assertEqual(prepared['unselected_categories'], [])

    def test_selection_does_not_expand_account_or_categories(self):
        result = email.prepare('fixture-account', ['abstracts'])
        self.assertEqual(result['source']['identity'], 'fixture-account')
        self.assertEqual(result['subqueries'], ['abstracts'])
        self.assertNotIn('service', result['source']['query'])
        self.assertIn('service', result['unselected_categories'])
        self.assertIn('not all mail', result['coverage_limit'])

    def test_stable_order_and_exact_queries_survive_source_serialization(self):
        one = email.prepare('fixture-account', ['talks', 'abstracts'])
        two = email.prepare('fixture-account', ['abstracts', 'talks'])
        self.assertEqual(one, two)
        self.assertEqual(json.loads(one['source']['query'])['queries'], one['queries'])

    def test_material_changes_get_different_source_keys(self):
        initial = email.prepare('fixture-account', ['abstracts'])
        key = state.source_key(initial['source'])
        variants = [email.prepare('other-account', ['abstracts']),
                    email.prepare('fixture-account', ['abstracts', 'service'])]
        altered = copy.deepcopy(self.catalogue)
        altered['categories']['abstracts']['query'] += ' conference'
        variants.append(email.prepare('fixture-account', ['abstracts'], altered))
        altered = copy.deepcopy(self.catalogue)
        altered['version'] = '2'
        variants.append(email.prepare('fixture-account', ['abstracts'], altered))
        for variant in variants:
            self.assertNotEqual(state.source_key(variant['source']), key)

    def test_invalid_selections_and_catalogues_fail(self):
        for categories in ([], ['missing'], ['abstracts', 'abstracts'], ['abstracts', None]):
            with self.assertRaises(ValueError):
                email.prepare('fixture-account', categories)
        with self.assertRaises(ValueError):
            email.prepare('', ['abstracts'])
        for field, value in [('version', ''), ('provider', 'unknown'), ('schema_version', 2)]:
            altered = copy.deepcopy(self.catalogue)
            altered[field] = value
            with self.assertRaises(ValueError):
                email.prepare('fixture-account', ['abstracts'], altered)

    def test_cli_prints_plan_without_writing_files(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/email_queries.py'),
                                     '--identity', 'fixture-account', '--categories', 'service'],
                                    cwd=folder, capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(result.stdout)['subqueries'], ['service'])
            self.assertEqual(list(Path(folder).iterdir()), [])


class EmailCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.fixture = state_tests.PrivateStateTests('runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def request(self, categories):
        request = self.fixture.request()
        plan = email.prepare('fixture-account', categories)
        request.update(source=plan['source'], subqueries=plan['subqueries'])
        return request

    def test_new_catalogue_scope_does_not_inherit_old_narrow_cutoff(self):
        old = self.fixture.begin()
        state.finish_checkpoint(self.fixture.state, old['id'], completion=self.fixture.completion(old))
        run = state.begin_checkpoint(self.fixture.state, self.request(['abstracts', 'service']),
                                     source_approved=True, acknowledge_new_scope=True,
                                     scope_change_reference='Synthetic catalogue adoption approval')['run']
        self.assertNotEqual(old['source_key'], run['source_key'])
        self.assertEqual(dt.datetime.fromisoformat(run['window_start']),
                         dt.datetime.fromisoformat(run['window_end']) - dt.timedelta(days=30))
        old_source = self.fixture.document()['sources'][old['source_key']]
        self.assertEqual(old_source['last_successful_cutoff'], old['window_end'])

    def test_missing_category_page_blocks_completion(self):
        run = self.fixture.begin(self.request(['abstracts', 'service']))
        completion = self.fixture.completion(run)
        completion['pagination'] = completion['pagination'][:1]
        before = self.fixture.checkpoints.read_bytes()
        with self.assertRaises(ValueError):
            state.finish_checkpoint(self.fixture.state, run['id'], completion=completion)
        self.assertEqual(self.fixture.checkpoints.read_bytes(), before)

    def test_unexhausted_page_and_failed_attempt_retain_cutoff(self):
        request = self.request(['abstracts', 'service'])
        first = self.fixture.begin(request)
        state.finish_checkpoint(self.fixture.state, first['id'], completion=self.fixture.completion(first))
        request['end'] = (dt.datetime.fromisoformat(request['end']) + dt.timedelta(hours=1)).isoformat()
        later = self.fixture.begin(request)
        completion = self.fixture.completion(later)
        completion['pagination'][-1]['exhausted'] = False
        with self.assertRaises(ValueError):
            state.finish_checkpoint(self.fixture.state, later['id'], completion=completion)
        state.finish_checkpoint(self.fixture.state, later['id'],
                                failure={'outcome': 'partial', 'reason': 'Synthetic second-page failure'})
        self.assertEqual(self.fixture.document()['sources'][first['source_key']]['last_successful_cutoff'],
                         first['window_end'])

    def test_complete_zero_result_catalogue_advances_only_its_source(self):
        old = self.fixture.begin()
        run = self.fixture.begin(self.request(['abstracts', 'service', 'media']))
        state.finish_checkpoint(self.fixture.state, run['id'], completion=self.fixture.completion(run))
        sources = self.fixture.document()['sources']
        self.assertEqual(sources[run['source_key']]['last_successful_cutoff'], run['window_end'])
        self.assertIsNone(sources[old['source_key']].get('last_successful_cutoff'))


if __name__ == '__main__':
    unittest.main()
