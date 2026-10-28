"""Synthetic senders/domains only; no personal exclusion defaults."""
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
SPEC = importlib.util.spec_from_file_location('sender_exclusions_target', ROOT / 'scripts/sender_exclusions.py')
module = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(module)


def rule(kind='domain', value='example.test', subdomains=False, ident='fixture-rule', account='fixture-account'):
    return dict(id=ident, account=account, kind=kind, value=value, include_subdomains=subdomains,
                reason='Synthetic explicit selection', confirmation_reference='Synthetic exact profile approval')


def config(rules=None):
    return {'discovery': {'sender_exclusions': [rule()] if rules is None else rules}}


def messages(*senders):
    return [{'id': 'message-' + str(i), 'from':sender} for i,sender in enumerate(senders)]


class SenderExclusionTests(unittest.TestCase):
    def test_no_default_filters_and_academic_domains_retained(self):
        incoming = messages('Professor <person@academic.test>', 'Reviewer <person@journal.test>')
        for prefs in ({'discovery':{}}, {'discovery':{'sender_exclusions':None}}, config([])):
            result = module.evaluate(prefs, 'fixture-account', incoming)
            self.assertEqual(result['counts']['retained'], 2)
            self.assertEqual(result['counts']['excluded'], 0)

    def test_domain_matches_exact_boundary_not_substrings(self):
        incoming = messages('a@example.test', 'a@notexample.test', 'a@example.test.evil.test', 'a@dept.example.test')
        result = module.evaluate(config(), 'fixture-account', incoming)
        self.assertEqual([x['id'] for x in result['excluded']], ['message-0'])
        self.assertEqual(result['counts']['retained'], 3)

    def test_subdomains_require_explicit_opt_in_and_boundary(self):
        result = module.evaluate(config([rule(subdomains=True)]), 'fixture-account',
                                 messages('a@dept.example.test', 'a@notexample.test', 'a@example.test.evil.test'))
        self.assertEqual([x['id'] for x in result['excluded']], ['message-0'])

    def test_display_name_does_not_match_and_domain_case_is_normalized(self):
        result = module.evaluate(config(), 'fixture-account', messages(
            '"example.test University" <a@elsewhere.test>', 'Person <a@EXAMPLE.TEST>'))
        self.assertEqual(result['retained_ids'], ['message-0'])
        self.assertEqual(result['excluded'][0]['id'], 'message-1')

    def test_exact_address_preserves_local_case_and_aliases(self):
        prefs = config([rule('address', 'Person@EXAMPLE.TEST')])
        result = module.evaluate(prefs, 'fixture-account', messages(
            'Name <Person@example.test>', 'person@example.test', 'Person+other@example.test', 'OtherPerson@example.test'))
        self.assertEqual([x['id'] for x in result['excluded']], ['message-0'])
        self.assertEqual(result['counts']['retained'], 3)

    def test_multiple_malformed_group_and_injected_headers_retained_for_review(self):
        incoming = messages('a@example.test, b@elsewhere.test', 'not an address',
                            'Group: a@example.test;', 'a@example.test\r\nBcc: b@elsewhere.test',
                            'a@example.test trailing', None, '"a b"@example.test')
        result = module.evaluate(config(), 'fixture-account', incoming)
        self.assertEqual(result['counts']['excluded'], 0)
        self.assertEqual(result['counts']['retained'], len(incoming))
        self.assertEqual(len(result['sender_review_ids']), len(incoming))

    def test_other_account_rules_do_not_apply(self):
        result = module.evaluate(config([rule(account='another-account')]), 'fixture-account', messages('a@example.test'))
        self.assertEqual(result['counts']['excluded'], 0)
        self.assertEqual(result['rule_counts'], {})

    def test_counts_overlap_without_double_counting_unique_messages(self):
        prefs = config([rule(), rule('address', 'a@example.test', ident='second')])
        result = module.evaluate(prefs, 'fixture-account', messages('a@example.test', 'b@elsewhere.test'))
        self.assertEqual(result['counts'], {'returned':2, 'retained':1, 'excluded':1, 'sender_review':0})
        self.assertEqual(result['rule_counts'], {'fixture-rule':1, 'second':1})
        self.assertEqual(len(result['excluded'][0]['matched_rule_ids']), 2)

    def test_regex_display_name_and_implicit_subdomain_rules_refused(self):
        for bad in (rule(value='*.example.test'), rule(value='example'),
                    rule('address', 'Name <a@example.test>'), rule('address','a@example.test',subdomains=True)):
            with self.assertRaises(ValueError):
                module.evaluate(config([bad]), 'fixture-account', messages('a@example.test'))
        bad = rule(); bad['include_subdomains'] = None
        with self.assertRaises(ValueError):
            module.evaluate(config([bad]), 'fixture-account', [])

    def test_bad_rules_and_duplicate_message_ids_stop(self):
        with self.assertRaisesRegex(ValueError, 'IDs must be unique'):
            module.evaluate(config([rule(),rule()]), 'fixture-account', [])
        with self.assertRaisesRegex(ValueError, 'Duplicate message'):
            module.evaluate(config(), 'fixture-account', [{'id':'same','from':'a@example.test'}]*2)
        with self.assertRaises(ValueError):
            module.evaluate(config(), 'fixture-account', [{'id':'one','from':'a@example.test','body':'not accepted'}])

    def test_output_omits_sender_literals_and_inputs_unchanged(self):
        incoming = messages('Private Display <a@example.test>', 'Other <b@elsewhere.test>')
        prefs = config(); original = copy.deepcopy((prefs,incoming))
        result = module.evaluate(prefs, 'fixture-account', incoming)
        output = json.dumps(result)
        for private in ('Private Display','a@example.test','b@elsewhere.test'):
            self.assertNotIn(private, output)
        self.assertEqual((prefs,incoming), original)

    def test_example_profile_has_no_active_sender_rules(self):
        prefs = json.loads((ROOT / 'references/profile.example.json').read_text(encoding='utf-8'))
        self.assertIsNone(prefs['discovery']['sender_exclusions'])

    def test_cli_is_read_only_and_account_scoped(self):
        fixture = fixtures.PrivateStateTests('runTest'); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        prefs = copy.deepcopy(fixture.config); prefs['discovery']['sender_exclusions'] = [rule()]
        fixture.config_path.write_bytes(module.helper.encoded(prefs))
        source = fixture.state / 'senders.json'; source.write_bytes(module.helper.encoded(messages('a@example.test')))
        before = {str(p):p.read_bytes() for p in fixture.base.rglob('*') if p.is_file()}
        output = io.StringIO()
        with patch.object(sys, 'argv', ['sender_exclusions.py',str(fixture.state),str(source),'--account','fixture-account']), contextlib.redirect_stdout(output):
            module.main()
        self.assertEqual(json.loads(output.getvalue())['counts']['excluded'], 1)
        self.assertEqual({str(p):p.read_bytes() for p in fixture.base.rglob('*') if p.is_file()}, before)


if __name__ == '__main__':
    unittest.main()
