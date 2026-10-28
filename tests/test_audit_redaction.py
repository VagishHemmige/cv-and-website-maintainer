"""Synthetic private sender tokens only; never a real conversation export."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('audit_redaction_test', ROOT/'scripts/audit_redaction.py')
redact = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(redact)
SECRET = 'SYNTHETIC_UNRELATED_SENDER_7429'


class AuditRedactionTests(unittest.TestCase):
    def fixture(self):
        calls = [dict(id='call1', name='exec', timestamp='2026-10-19', source_line=7,
                      arguments='re.search(r"'+SECRET+'", sender)', unexpected=SECRET)]
        events = [
            dict(type='CommandExecution', id='command1', command=SECRET, cwd='/private/run',
                 aggregated_output={'nested': [SECRET]}, status='completed', exit_code=0,
                 started_at_ms=1, completed_at_ms=4, duration={'secs': 0, 'nanos': 3}),
            dict(type='McpToolCall', id='search1', tool='gmail.search_emails', server='gmail',
                 arguments=json.dumps({'query':'subject:abstract accepted','max_results':100}),
                 result={'payload':SECRET}),
            dict(type='FileChange', id='change1', changes={'diff':SECRET}, stdout=SECRET,
                 stderr=SECRET, status='completed'),
            dict(type='Extension', id='web1', query=SECRET, action={'nested':SECRET}, results=SECRET),
            dict(type='NewUnknownEvent', id='unknown1', hidden_body=SECRET)]
        timing = dict(structured_question_calls=2, observed_escalation_request_wrappers=3,
            limitations=[SECRET], unknown_payload=SECRET,
            turns=[dict(turn_id='t1', duration_ms=17, error=SECRET)],
            completed_item_wall_times=[dict(event_id='command1', type='CommandExecution',
                                           wall_ms=3, tool=None, command=SECRET)])
        reviewed = {'search1':{'query':'subject:abstract accepted','max_results':100}}
        return calls, events, timing, reviewed

    def sanitized(self):
        calls, events, timing, reviewed = self.fixture()
        return (redact.redact_calls(calls), redact.redact_events(events, reviewed),
                redact.redact_timing(timing), reviewed)

    def test_duplicate_and_nested_raw_fields_are_omitted_with_counts_ids_and_timing_retained(self):
        calls, events, timing, reviewed = self.sanitized()
        exported = json.dumps([calls, events, timing])
        self.assertNotIn(SECRET, exported)
        self.assertEqual([event['id'] for event in events],
                         ['command1', 'search1', 'change1', 'web1', 'unknown1'])
        self.assertEqual(events[0]['exit_code'], 0)
        self.assertEqual(events[0]['completed_at_ms']-events[0]['started_at_ms'], 3)
        self.assertEqual(timing['structured_question_calls'], 2)
        self.assertEqual(timing['observed_escalation_request_wrappers'], 3)
        self.assertEqual(timing['turns'][0]['duration_ms'], 17)
        self.assertEqual(timing['completed_item_wall_times'][0]['wall_ms'], 3)
        self.assertEqual(events[1]['reviewed_query_arguments'], reviewed['search1'])
        self.assertEqual(redact.scan_surfaces(calls, events, timing, reviewed), [])

    def test_redaction_does_not_modify_the_original_snapshot(self):
        calls, events, timing, reviewed = self.fixture()
        before = copy.deepcopy((calls, events, timing, reviewed))
        redact.redact_calls(calls); redact.redact_events(events, reviewed); redact.redact_timing(timing)
        self.assertEqual((calls, events, timing, reviewed), before)

    def test_marker_retains_hash_not_raw_literal(self):
        marker = redact.omitted('fixture', 'test omission')
        self.assertTrue(redact.is_marker(marker))
        self.assertEqual(marker['canonical_sha256'], hashlib.sha256(b'"fixture"').hexdigest())
        self.assertEqual(marker['canonical_bytes'], 9)
        self.assertNotIn('fixture', json.dumps(marker))

    def test_unreviewed_connector_arguments_and_payloads_are_never_preserved_by_default(self):
        calls, events, timing, _ = self.fixture()
        event = events[1]; event['arguments'] = {'sender_filter':SECRET}
        clean = redact.redact_events([event])[0]
        self.assertNotIn('reviewed_query_arguments', clean)
        self.assertTrue(redact.is_marker(clean['arguments']))
        self.assertNotIn(SECRET, json.dumps(clean))

    def test_reviewed_query_must_match_exact_event_fields_and_cannot_restore_filter_arguments(self):
        _, events, _, reviewed = self.fixture()
        for invalid in ({'search1':dict(reviewed['search1'], sender_filter=SECRET)},
                        {'search1':{'query':'different','max_results':100}},
                        {'missing':reviewed['search1']}):
            with self.subTest(invalid_keys=list(invalid)), self.assertRaises(ValueError):
                redact.redact_events(events, invalid)
        events[1]['tool'] = 'gmail.batch_read_email'
        with self.assertRaises(ValueError):
            redact.redact_events(events, reviewed)

    def test_scan_rejects_reintroduced_raw_body_and_reports_labels_without_values(self):
        calls, events, timing, reviewed = self.sanitized()
        calls[0]['arguments'] = SECRET
        events[0]['aggregated_output'] = {'nested':SECRET}
        events[2]['changes'] = SECRET
        timing['completed_item_wall_times'][0]['command'] = SECRET
        timing['turns'][0]['error'] = SECRET
        findings = redact.scan_surfaces(calls, events, timing, reviewed)
        for expected in ('tool_calls[0].raw_or_unknown_body', 'timeline[0].aggregated_output',
                         'timeline[2].changes', 'timing[0].command_or_unknown_body',
                         'turns[0].raw_error'):
            self.assertIn(expected, findings)
        self.assertNotIn(SECRET, json.dumps(findings))

    def test_scan_rejects_unknown_fields_and_unreviewed_query_payload(self):
        calls, events, timing, reviewed = self.sanitized()
        events[-1]['new_raw_field'] = SECRET
        events[1]['reviewed_query_arguments']['query'] = SECRET
        timing['unknown'] = SECRET
        findings = redact.scan_surfaces(calls, events, timing, reviewed)
        self.assertIn('timeline[4].unknown_body', findings)
        self.assertIn('timeline[1].unreviewed_query', findings)
        self.assertIn('timing.unknown_body', findings)

    def test_sender_filter_scan_detects_regex_with_sender_or_from_field_without_echoing_it(self):
        for text in ('re.search(r"'+SECRET+'", sender)',
                     "re.compile('"+SECRET+"'); message['from']",
                     're.fullmatch("'+SECRET+'", from_addr)'):
            self.assertTrue(redact.sender_filter_code(text))
        self.assertFalse(redact.sender_filter_code("from pathlib import Path"))
        self.assertFalse(redact.sender_filter_code("record = {'title':'Academic activity'}"))

    def test_guidance_requires_copy_only_export_and_honest_limits(self):
        doc = (ROOT/'references/audit-exports.md').read_text(encoding='utf-8')
        for phrase in ('original snapshots', 'never hidden reasoning', 'not de-identification',
                       'all duplicated surfaces', 'reviewed query', 'Do not send',
                       'original ZIP', 'new export hashes'):
            self.assertIn(phrase, doc)
