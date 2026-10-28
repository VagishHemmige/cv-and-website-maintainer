"""Optional output decisions on synthetic private bootstrap state only."""
import json
from pathlib import Path
import unittest
import zipfile
import test_initialize as baseline
h = baseline.h


class CvPdfInitializationTests(unittest.TestCase):
    setUp = baseline.InitializationTests.setUp
    start = baseline.InitializationTests.start
    answer = baseline.InitializationTests.answer
    def test_applicable_question_sequence(self):
        self.start()
        for goals, expected in [('cv','cv_format'),('website','website_cv'),('both','website_cv')]:
            with self.subTest(goals=goals):
                self.answer('outputs',goals)
                self.answer('starting_point','fresh')
                self.assertEqual(h.status(self.state)['next_question']['id'],expected)

    def test_website_only_needs_no_private_format(self):
        self.start(); self.answer('outputs','website'); self.answer('starting_point','fresh')
        self.answer('website_cv','yes')
        result=h.status(self.state)
        self.assertEqual(result['next_question']['id'],'cv_source')
        self.assertEqual(result['cv_output_choices']['private_format'],'not_requested')
        self.assertTrue(result['cv_output_choices']['pdf_generation_requested'])
        self.assertFalse(result['cv_output_choices']['public_use_approved'])

    def test_private_pdf_does_not_request_public_cv(self):
        self.start(); self.answer('outputs','cv'); self.answer('cv_format','docx_pdf')
        choices=h.status(self.state)['cv_output_choices']
        self.assertTrue(choices['pdf_generation_requested'])
        self.assertEqual(choices['website_cv'],'not_requested')
        self.assertFalse(choices['publication_approved'])

    def test_legacy_answers_remain_pending_without_history_rewrite(self):
        self.start(); self.answer('outputs','both'); self.answer('starting_point','fresh')
        before=(self.state/'initialization.json').read_bytes()
        self.assertEqual(h.status(self.state)['next_question']['id'],'website_cv')
        self.assertEqual(h.status(self.state)['cv_output_choices']['private_format'],'pending')
        self.assertEqual(before,(self.state/'initialization.json').read_bytes())

    def test_deferral_survives_resume_and_does_not_enable_pdf(self):
        self.start(); self.answer('outputs','both'); self.answer('starting_point','fresh')
        self.answer('website_cv','defer'); self.answer('cv_format','defer')
        result=h.status(self.state)
        self.assertEqual(result['next_question']['id'],'cv_source')
        self.assertFalse(result['cv_output_choices']['pdf_generation_requested'])
        self.assertEqual(result['cv_output_choices']['website_cv'],'defer')

    def test_changed_goals_ignore_but_preserve_historical_choice(self):
        self.start(); self.answer('outputs','both'); self.answer('website_cv','yes')
        self.answer('cv_format','docx'); self.answer('outputs','cv')
        result=h.status(self.state)
        self.assertEqual(result['state']['answers']['website_cv'],'yes')
        self.assertEqual(result['cv_output_choices']['website_cv'],'not_requested')
        self.assertFalse(result['cv_output_choices']['pdf_generation_requested'])

    def test_invalid_output_choices_preserve_state(self):
        self.start()
        before=(self.state/'initialization.json').read_bytes()
        for key,value in [('website_cv',True),('website_cv','public'),('cv_format','pdf')]:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                self.answer(key,value)
        self.assertEqual(before,(self.state/'initialization.json').read_bytes())

    def test_staging_reports_choice_without_claiming_or_enabling_adapter(self):
        self.start(); self.answer('outputs','both'); self.answer('website_cv','yes')
        self.answer('cv_format','docx_pdf')
        result=h.stage_starter(self.state,'SYNTHETIC stage request')
        self.assertTrue(result['cv_output_choices']['pdf_generation_requested'])
        self.assertIn('Word-only',result['cv_output_choices']['implementation'])
        self.assertFalse(result['project_created'])
        root=Path(result['project_source_root'])
        with zipfile.ZipFile(Path(h.__file__).parents[1]/'assets/starter.zip') as z:
            self.assertEqual((root/'R/cv.R').read_bytes(),z.read('starter/R/cv.R'))
        self.assertFalse((root/'cv.qmd').exists())
        self.assertFalse(self.project.exists())


if __name__=='__main__': unittest.main()
