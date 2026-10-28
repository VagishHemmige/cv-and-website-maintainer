"""Interview-to-profile transitions use disposable state and SYNTHETIC approvals."""
import json
from pathlib import Path
import unittest
import test_initialize as bootstrap
import test_private_state as profile
from approval_fixture import approval_file

class PendingSetupTests(unittest.TestCase):
    setUp=bootstrap.InitializationTests.setUp
    start=bootstrap.InitializationTests.start
    answer=bootstrap.InitializationTests.answer

    def batch(self):
        value=bootstrap.h.load(self.state)
        return {'project_root':str(self.project),'outputs':value['answers']['outputs'],
                'assistance':value['answers']['assistance']}

    def provenance(self):
        return {'source':'SYNTHETIC initialization.json answers: outputs and assistance',
                'recorded_at':bootstrap.h.now()}

    def interview(self):
        self.start();self.answer('outputs','both');self.answer('assistance','guidance')

    def test_multiple_answers_persist_before_project_without_profile(self):
        self.interview();self.answer('project_path',str(self.project))
        resumed=bootstrap.h.load(self.state)
        self.assertEqual(resumed['answers']['outputs'],'both')
        self.assertEqual(resumed['answers']['assistance'],'guidance')
        self.assertEqual(len(resumed['history']),3)
        self.assertFalse(self.project.exists());self.assertFalse((self.state/'config.json').exists())

    def test_batch_waits_for_actual_project_directory(self):
        self.interview();raw=(self.state/'initialization.json').read_bytes()
        with self.assertRaises((ValueError,OSError)):
            profile.helper.propose_profile(self.state,self.batch(),self.provenance(),create=True)
        self.assertEqual((self.state/'initialization.json').read_bytes(),raw)
        self.assertFalse((self.state/'config.json').exists())

    def test_one_combined_proposal_and_one_approval_preserve_interview(self):
        self.interview();self.project.mkdir();raw=(self.state/'initialization.json').read_bytes()
        proposal=profile.helper.propose_profile(self.state,self.batch(),self.provenance(),create=True)
        self.assertEqual(proposal['after']['outputs'],'both');self.assertEqual(proposal['after']['assistance'],'guidance')
        self.assertFalse((self.state/'config.json').exists())
        with self.assertRaises(ValueError):profile.helper.apply_profile(self.state,proposal['id'],proposal['id'],'SYNTHETIC answer only')
        self.assertFalse((self.state/'config.json').exists())
        candidate=self.state/'profile-proposals'/proposal['id']/'after.json'
        evidence=approval_file(self.state,'profile',proposal['id'],profile.helper.sha(candidate.read_bytes()),self.state/'config.json')
        profile.helper.apply_profile(self.state,proposal['id'],proposal['id'],'SYNTHETIC combined approval',evidence)
        config=json.loads((self.state/'config.json').read_text())
        self.assertEqual(config['outputs'],'both');self.assertEqual(config['assistance'],'guidance')
        self.assertEqual((self.state/'initialization.json').read_bytes(),raw)

    def test_corrected_answer_history_survives_combined_proposal(self):
        self.interview();self.answer('outputs','cv');self.project.mkdir()
        proposal=profile.helper.propose_profile(self.state,self.batch(),self.provenance(),create=True)
        self.assertEqual(proposal['after']['outputs'],'cv')
        history=bootstrap.h.load(self.state)['history']
        self.assertEqual([h['value'] for h in history if h['key']=='outputs'],['both','cv'])
        self.assertFalse((self.state/'config.json').exists())

    def test_deferred_bootstrap_answer_stays_pending(self):
        self.interview();self.answer('cv_source',None);self.project.mkdir()
        profile.helper.propose_profile(self.state,self.batch(),self.provenance(),create=True)
        self.assertIsNone(bootstrap.h.load(self.state)['answers']['cv_source'])
        self.assertFalse((self.state/'config.json').exists())

    def test_docs_remove_per_answer_profile_writes_and_state_procedure_limit(self):
        root=Path(__file__).resolve().parents[1]
        preferences=(root/'references/preferences.md').read_text(encoding='utf-8')
        self.assertNotIn('Save incomplete config.json as soon',preferences)
        for text in ('one merge patch','not a packaged answer-staging helper','actual project directory exists','retain the original answer files','No per-answer profile-apply calls'):
            self.assertIn(text,preferences)
        for name in ('references/setup.md','references/questionnaire.md','references/private-state.md','references/initialization.md','skills/configure-academic-records/SKILL.md'):
            self.assertIn('pending',(root/name).read_text(encoding='utf-8'))
