"""Synthetic exclusion rules only; packaged defaults never encode an owner's choices."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import test_private_state as fixtures

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('discovery_exclusions_target', ROOT / 'scripts/discovery_exclusions.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def rule(types=None, ident='fixture-rule'):
    return dict(id=ident, destination='service.yml',
                activity_types=types or ['recommendation_letter', 'external_promotion_review_letter', 'external_tenure_review_letter'],
                reason='Synthetic explicit scope', confirmation_reference='Synthetic exact profile approval')


def candidate(kind='recommendation_letter', destination='service.yml', ident='candidate-1', certainty='supported'):
    return dict(id=ident, destination=destination, classification='new',
                activity_classification=dict(type=kind, certainty=certainty, reference='Synthetic source evidence'))


class ExclusionTests(unittest.TestCase):
    def config(self, rules=None):
        return {'discovery':{'exclusions': [rule()] if rules is None else rules}}

    def test_three_letter_types_excluded_but_other_reviewing_stays(self):
        kinds = ['recommendation_letter', 'external_promotion_review_letter', 'external_tenure_review_letter',
                 'journal_reviewing', 'abstract_reviewing', 'committee_reviewing']
        values = [candidate(kind, ident='candidate-' + str(i)) for i,kind in enumerate(kinds)]
        result = module.evaluate(self.config(), values)
        self.assertEqual(result['counts'], {'eligible':3, 'excluded':3, 'needs_classification':0})
        self.assertEqual([c['activity_classification']['type'] for c in result['eligible']], kinds[3:])
        self.assertEqual(result['rule_counts'], {'fixture-rule':3})
        self.assertEqual(set(result['excluded'][0]), {'id', 'matched_rule_ids'})

    def test_recommendation_only_rule_does_not_cover_promotion_or_tenure(self):
        values = [candidate('external_promotion_review_letter'), candidate('external_tenure_review_letter', ident='candidate-2')]
        result = module.evaluate(self.config([rule(['recommendation_letter'])]), values)
        self.assertEqual(result['counts']['excluded'], 0)
        self.assertEqual(result['counts']['eligible'], 2)

    def test_destination_scope_is_exact(self):
        result = module.evaluate(self.config(), [candidate(destination='honors.yml')])
        self.assertEqual(result['counts']['eligible'], 1)
        self.assertEqual(result['counts']['excluded'], 0)

    def test_uncertain_or_unclassified_service_is_retained_pending(self):
        values = [candidate(certainty='uncertain'), dict(id='unknown', destination='service.yml')]
        result = module.evaluate(self.config(), values)
        self.assertEqual(result['counts'], {'eligible':0, 'excluded':0, 'needs_classification':2})

    def test_no_rule_is_inferred_when_missing_null_or_empty(self):
        values = [candidate()]
        for config in ({'discovery':{}}, {'discovery':{'exclusions':None}}, self.config([])):
            result = module.evaluate(config, values)
            self.assertEqual(result['eligible'], values)
            self.assertEqual(result['counts']['excluded'], 0)

    def test_overlapping_rules_count_unique_candidates_separately(self):
        result = module.evaluate(self.config([rule(), rule(ident='second-rule')]), [candidate()])
        self.assertEqual(result['counts']['excluded'], 1)
        self.assertEqual(result['rule_counts'], {'fixture-rule':1, 'second-rule':1})
        self.assertEqual(len(result['excluded'][0]['matched_rule_ids']), 2)

    def test_bad_rules_stop_instead_of_silently_excluding(self):
        rules = [rule(), rule()]
        with self.assertRaisesRegex(ValueError, 'unique'):
            module.evaluate(self.config(rules), [candidate()])
        for field,value in [('activity_types',['recommendation_letter','recommendation_letter']),
                            ('confirmation_reference',''), ('activity_types',['.*'])]:
            bad = rule(); bad[field] = value
            with self.assertRaises(ValueError):
                module.evaluate(self.config([bad]), [candidate()])
        bad = rule(); bad['sender_domain'] = 'example.invalid'
        with self.assertRaisesRegex(ValueError, 'Unsupported exclusion fields'):
            module.evaluate(self.config([bad]), [candidate()])

    def test_duplicate_candidates_and_unsupported_classification_stop(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate candidate'):
            module.evaluate(self.config(), [candidate(), candidate()])
        for change in ({'certainty':'guessed'}, {'reference':''}):
            bad = candidate(); bad['activity_classification'].update(change)
            with self.assertRaises(ValueError):
                module.evaluate(self.config(), [bad])

    def test_input_is_not_mutated_and_existing_classification_survives(self):
        config = self.config()
        values = [candidate('journal_reviewing')]
        original = copy.deepcopy((config,values))
        result = module.evaluate(config, values)
        self.assertEqual((config,values), original)
        self.assertEqual(result['eligible'][0]['classification'], 'new')

    def test_no_active_exclusions_in_example_profile(self):
        config = json.loads((ROOT / 'references/profile.example.json').read_text(encoding='utf-8'))
        self.assertIsNone(config['discovery']['exclusions'])

    def test_cli_reads_canonical_rules_and_does_not_write(self):
        fixture = fixtures.PrivateStateTests('runTest'); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        config = copy.deepcopy(fixture.config); config['discovery']['exclusions'] = [rule()]
        fixture.config_path.write_bytes(module.helper.encoded(config))
        source = fixture.state / 'candidates.json'
        source.write_bytes(module.helper.encoded([candidate()]))
        before = {str(p):p.read_bytes() for p in fixture.base.rglob('*') if p.is_file()}
        output = io.StringIO()
        with patch.object(sys, 'argv', ['discovery_exclusions.py', str(fixture.state), str(source)]), contextlib.redirect_stdout(output):
            module.main()
        self.assertEqual(json.loads(output.getvalue())['counts']['excluded'], 1)
        self.assertEqual({str(p):p.read_bytes() for p in fixture.base.rglob('*') if p.is_file()}, before)


if __name__ == '__main__':
    unittest.main()
