"""Publication recommendations explain consequences without changing authority."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class PublicationChoiceDocumentationTests(unittest.TestCase):
    def test_modes_explain_recommendation_and_autonomous_consequence(self):
        text=(ROOT/'references/setup-execution.md').read_text(encoding='utf-8')
        for phrase in ('For new users, recommend','hold_for_review','after_verified_preview','without asking you again','you may not see the preview before publication','leave publication pending','honor an explicit preference for autonomy','Reuse an existing confirmed choice'):
            with self.subTest(phrase=phrase):self.assertIn(phrase,text)

    def test_onboarding_routes_to_explicit_publication_choice(self):
        skill=(ROOT/'skills/initialize-academic-records/SKILL.md').read_text(encoding='utf-8')
        self.assertIn('Recommend human preview for new users',skill)
        self.assertIn('can push without another confirmation',skill)
        questionnaire=(ROOT/'references/questionnaire.md').read_text(encoding='utf-8')
        self.assertIn('| Publication gate |',questionnaire)
        self.assertIn('leave an undecided choice pending',questionnaire)
