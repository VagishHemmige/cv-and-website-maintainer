"""Conversation-guidance contracts; these do not simulate the host UI or model adherence."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class QuestionFlowDocsTests(unittest.TestCase):
    def setUp(self):
        self.doc = (ROOT / 'references/questions.md').read_text(encoding='utf-8')

    def test_direct_category_answer_and_missing_details_have_distinct_routes(self):
        for phrase in ('ask what changed', 'same answer',
                       'Do not require a Changes needed selection', 'focused follow-up is still necessary',
                       'proposal preparation, not live records'):
            self.assertIn(phrase, self.doc)

    def test_deferral_options_name_actual_revisit_without_guessed_defaults(self):
        for phrase in ('Only when I ask', 'actual verified date/time or exact agreed trigger',
                       'Do not turn a generic Defer into a guessed date', 'Existing deferred categories stay deferred'):
            self.assertIn(phrase, self.doc)

    def test_latest_correction_supersedes_old_question_without_inventing_dates(self):
        for phrase in ('Reuse explicit values just supplied', 'supersede the obsolete question',
                       'latest factual answer', 'never silently turn approximate wording into January 1'):
            self.assertIn(phrase, self.doc)

    def test_combined_choice_requires_existing_validated_named_proposal(self):
        for phrase in ('only if the exact validated proposal has already been shown',
                       'before/after, provenance, proposal ID', 'explicitly approve that named proposal',
                       'does not approve unseen config bytes', 'do not pre-authorize unspecified future edits'):
            self.assertIn(phrase, self.doc)
        prefs = (ROOT / 'references/preferences.md').read_text(encoding='utf-8')
        self.assertIn('A bare questionnaire answer cannot approve unseen bytes', prefs)
        self.assertIn('combined questionnaire checkpoints', prefs)

    def test_continuation_preserves_pause_and_per_finding_approval(self):
        for phrase in ('already authorized review', 'Honor pauses, one pending question',
                       'required per-finding/per-proposal approvals', 'continuation does not authorize a new kind of work',
                       'Nothing to add for one category'):
            self.assertIn(phrase, self.doc)

    def test_structured_question_and_existing_approval_guards_remain(self):
        for phrase in ('request_user_input_async', 'Ask exactly one question or decision at a time',
                       'Silence', 'a questionnaire answer cannot replace it'):
            self.assertIn(phrase.lower(), self.doc.lower())

    def test_review_and_discovery_entry_points_use_the_shorter_flow(self):
        review = (ROOT / 'references/reviews.md').read_text(encoding='utf-8')
        skill = (ROOT / 'skills/discover-academic-updates/SKILL.md').read_text(encoding='utf-8')
        self.assertIn('invite the actual item/change in the first answer', review)
        self.assertIn('latest supplied corrections', skill)
        self.assertIn('without a redundant Anything else turn', skill)


if __name__ == '__main__':
    unittest.main()
