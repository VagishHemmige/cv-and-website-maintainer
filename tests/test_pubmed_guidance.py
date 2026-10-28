"""Instruction contracts only; no live PubMed request or permission simulation."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PubMedGuidanceTests(unittest.TestCase):
    def setUp(self):
        self.doc = (ROOT/'references/pubmed-discovery.md').read_text(encoding='utf-8')

    def test_known_restricted_call_uses_normal_scoped_access_without_repeat_failure(self):
        for phrase in ('Before the first PubMed call', "host's normal approval/escalation flow",
                       'before attempting', 'known blocked command', 'blanket grant'):
            self.assertIn(phrase, self.doc)

    def test_available_tools_do_not_override_source_or_network_authority(self):
        for phrase in ('working authorized connector or browser', 'does not grant host network',
                       'does not authorize a new source or scope', 'evade an access denial',
                       'Do not edit host security settings', 'arbitrary sites'):
            self.assertIn(phrase, self.doc)

    def test_unexpected_failure_is_not_zero_results_and_independent_checks_continue(self):
        for phrase in ('DNS, proxy or connection failure', 'empty PubMed result',
                       'authorized retry also', 'rather than loop',
                       'independently permitted local checks'):
            self.assertIn(phrase, self.doc)

    def test_connectivity_does_not_complete_search_or_advance_failed_cutoff(self):
        for phrase in ('not a\ncompleted discovery search', 'exact saved query scope',
                       'every intended page/subquery', 'durably save results',
                       'previous\nsuccessful cutoff unchanged', 'scope reconciliation'):
            self.assertIn(phrase, self.doc)

    def test_optional_null_clues_do_not_reopen_setup_or_invent_filters(self):
        for phrase in ('null optional\nfield alone', 'does not require a question',
                       'Do not invent variants', 'unapproved hard filter',
                       'Do not repeatedly demand\nall missing identity fields'):
            self.assertIn(phrase, self.doc)

    def test_real_ambiguity_needs_one_clue_and_preserves_deferrals_and_approval(self):
        for phrase in ('Ask one focused question', 'smallest useful clue',
                       'keep that candidate\npending', 'Honor saved deferrals',
                       'suppress\nrepeated unanswered', 'exact profile-proposal approval',
                       'do not silently populate identity fields'):
            self.assertIn(phrase, self.doc)

    def test_existing_work_match_does_not_establish_same_surname_identity_or_authorize_import(self):
        for phrase in ('PMID/DOI', 'resolve duplicate triage',
                       'not that every author', 'Never accept surname-only',
                       'neither\nimports to Zotero nor edits the bibliography'):
            self.assertIn(phrase, self.doc)

    def test_entry_points_route_to_same_access_identity_guidance(self):
        for name in ('references/discovery.md', 'references/runtime.md',
                     'skills/discover-academic-updates/SKILL.md'):
            self.assertIn('pubmed-discovery.md', (ROOT/name).read_text(encoding='utf-8'), name)
        questionnaire = (ROOT/'references/questionnaire.md').read_text(encoding='utf-8')
        self.assertIn('Optional null clues alone do not block a usable search', questionnaire)


if __name__ == '__main__':
    unittest.main()
