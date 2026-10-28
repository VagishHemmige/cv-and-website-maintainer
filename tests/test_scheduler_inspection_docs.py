"""Instruction contract checks, not a test of live host latency or scheduler truth."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SchedulerInspectionDocsTests(unittest.TestCase):
    def setUp(self):
        self.doc = (ROOT / 'references/scheduling.md').read_text(encoding='utf-8')
        self.routine = self.doc.split('## Routine read-only scheduler inspection\n', 1)[1].split('\n## ', 1)[0]

    def test_routine_prefers_fresh_identity_checked_file_not_recent_cached_verification(self):
        for phrase in ('CURRENT local task configuration', 'validate the job identity and actual destination',
                       'content hash', 'recent prior verification is not a substitute for a fresh read',
                       'avoid a redundant automation_update mode=view call'):
            self.assertIn(phrase, self.routine)

    def test_fallback_covers_corruption_conflicts_and_host_only_fields(self):
        for phrase in ('missing, unreadable or malformed', 'identity/destination is wrong or ambiguous',
                       'observations conflict', 'host-only fields', 'explicit user request for a live host check'):
            self.assertIn(phrase, self.routine)

    def test_does_not_replace_post_mutation_verification_or_authorize_task_edits(self):
        for phrase in ('does not replace post-mutation verification', 'Never edit task files directly',
                       'require the existing authorization for changes'):
            self.assertIn(phrase, self.routine)
        self.assertIn('6. Read back the saved job and verify ID, prompt, cadence', self.doc)

    def test_preserves_unknown_timing_and_independent_local_work(self):
        for phrase in ('Do not infer a timezone, next run, DST result',
                       'Keep those items unverified', 'continue independently permitted local checks'):
            self.assertIn(phrase, self.routine)

    def test_elapsed_time_is_not_tool_compute_and_no_speedup_guarantee(self):
        for phrase in ('elapsed time may include host waiting, queuing or approval handling',
                       'Keep both when available', 'do not attribute all elapsed time to tool computation',
                       'not scheduler latency guarantees'):
            self.assertIn(phrase, self.routine)

    def test_discovery_entry_point_routes_routine_and_mutation_checks_separately(self):
        skill = (ROOT / 'skills/discover-academic-updates/SKILL.md').read_text(encoding='utf-8')
        self.assertIn("scheduling.md's fresh local task-file check", skill)
        self.assertIn('Keep native host read-back after task creation/updates', skill)
        self.assertIn('never substitute an older cached observation', skill)


if __name__ == '__main__':
    unittest.main()
