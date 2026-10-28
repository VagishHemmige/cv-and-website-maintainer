"""F9 pending deferrals; synthetic questions/decisions, no live state writes."""
import contextlib
import datetime as dt
import io
import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch
import test_proposals as base

helper = base.helper


class DeferralTests(unittest.TestCase):
    setUp = base.ProposalTests.setUp
    fixture = base.ProposalTests.fixture
    save_config = base.ProposalTests.save_config
    cli = base.ProposalTests.cli
    runtime = base.ProposalTests.runtime
    propose = base.ProposalTests.propose
    apply = base.ProposalTests.apply

    def pending(self):
        path=self.base/'question.json'
        path.write_text(json.dumps(dict(kind='reconciliation',facts={'issue':'synthetic'},
            missing_fields=['venue'],questions=['Which venue should be recorded?'],sources=['synthetic fixture'])))
        return self.cli('remember',self.state,path)['id']

    def defer(self, ident, **condition):
        return helper.event_pending(self.state,ident,dict(status='deferred',
            deferral_reference='synthetic user deferral',**condition))

    def date(self, days):
        return (dt.datetime.now(dt.timezone.utc)+dt.timedelta(days=days)).isoformat()

    def listing(self,*args):
        output=io.StringIO()
        with patch.object(sys,'argv',['proposals.py','list',str(self.state),*args]),contextlib.redirect_stdout(output):helper.main()
        return output.getvalue()

    def snapshot(self):
        return {str(p.relative_to(self.state)):p.read_bytes() for p in self.state.rglob('*') if p.is_file()}

    def test_defer_requires_one_unambiguous_condition(self):
        self.fixture();ident=self.pending();before=self.snapshot()
        for condition in ({},{'revisit_on':self.date(2),'revisit_trigger':'fixture-trigger'},
                          {'revisit_trigger':''},{'revisit_on':'2026-10-19'}):
            with self.subTest(condition=condition),self.assertRaises(ValueError):self.defer(ident,**condition)
        self.assertEqual(self.snapshot(),before)

    def test_defer_requires_actual_user_decision_reference(self):
        self.fixture();ident=self.pending()
        with self.assertRaisesRegex(ValueError,'actual user deferral'):
            helper.event_pending(self.state,ident,dict(status='deferred',revisit_trigger='fixture-trigger'))
        self.assertEqual(helper.read_pending(self.state,ident)['status'],'needs_information')

    def test_future_date_suppresses_questions_without_discarding_facts(self):
        self.fixture();ident=self.pending();item=self.defer(ident,revisit_on=self.date(2))
        self.assertEqual(item['status'],'deferred')
        self.assertEqual(item['revisit_status'],'waiting_for_date')
        self.assertEqual(item['questions_to_ask'],[])
        self.assertEqual(item['questions'],['Which venue should be recorded?'])
        self.assertEqual(item['facts'],{'issue':'synthetic'})
        self.assertNotIn('Which venue',self.listing())

    def test_past_date_becomes_eligible_without_reopening_status(self):
        self.fixture();ident=self.pending();item=self.defer(ident,revisit_on=self.date(-1))
        self.assertEqual(item['status'],'deferred')
        self.assertEqual(item['revisit_status'],'eligible')
        self.assertEqual(item['questions_to_ask'],['Which venue should be recorded?'])

    def test_named_trigger_requires_exact_match_not_routine_weekly_run(self):
        self.fixture();ident=self.pending();self.defer(ident,revisit_trigger='user-requested-test')
        self.assertEqual(helper.read_pending(self.state,ident,['weekly-review'])['questions_to_ask'],[])
        self.assertEqual(helper.read_pending(self.state,ident,['user-requested-test'])['revisit_status'],'eligible')
        self.assertNotIn('Which venue',self.listing())
        self.assertIn('Which venue',self.listing('--trigger','user-requested-test','--trigger-reference','synthetic actual user request'))

    def test_trigger_reference_is_required_for_cli_and_offer(self):
        self.fixture();ident=self.pending();self.defer(ident,revisit_trigger='fixture-trigger')
        with self.assertRaisesRegex(ValueError,'actual condition/source reference'):
            self.listing('--trigger','fixture-trigger')
        with self.assertRaisesRegex(ValueError,'actual condition/source reference'):
            helper.offer_revisit(self.state,ident,'cycle','synthetic question',['fixture-trigger'])

    def test_plain_text_context_cannot_match_trigger_by_substring(self):
        self.fixture();ident=self.pending();self.defer(ident,revisit_trigger='fixture-trigger')
        with self.assertRaisesRegex(ValueError,'collection of exact condition names'):
            helper.read_pending(self.state,ident,'unrelated prose mentions fixture-trigger somewhere')

    def test_offer_before_condition_is_refused_without_event(self):
        self.fixture();ident=self.pending();self.defer(ident,revisit_on=self.date(2));before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'not eligible'):
            helper.offer_revisit(self.state,ident,'cycle','synthetic offered question')
        self.assertEqual(self.snapshot(),before)

    def test_offered_revisit_is_not_nudged_again_in_later_cycles(self):
        self.fixture();ident=self.pending();self.defer(ident,revisit_on=self.date(-1))
        item=helper.offer_revisit(self.state,ident,'cycle-1','synthetic offered question')
        self.assertEqual(item['revisit_status'],'already_offered')
        self.assertEqual(item['questions_to_ask'],[])
        self.assertEqual(item['revisit_offered_cycle_id'],'cycle-1')
        before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'already offered'):
            helper.offer_revisit(self.state,ident,'cycle-2','synthetic repeated question')
        self.assertNotIn('Which venue',self.listing())
        self.assertEqual(self.snapshot(),before)

    def test_offer_tracks_trigger_reference_and_does_not_claim_answer(self):
        self.fixture();ident=self.pending();self.defer(ident,revisit_trigger='fixture-trigger')
        item=helper.offer_revisit(self.state,ident,'cycle','synthetic offered question',
                                  ['fixture-trigger'],'synthetic actual request')
        self.assertEqual(item['status'],'deferred')
        self.assertEqual(item['missing_fields'],['venue'])
        events=[json.loads(p.read_text()) for p in (self.state/'events'/ident).glob('*.json')]
        offered=next(e for e in events if e.get('event_type')=='revisit_offered')
        self.assertEqual(offered['matched_trigger_reference'],'synthetic actual request')

    def test_user_can_explicitly_resume_early_but_not_without_reference(self):
        self.fixture();ident=self.pending();self.defer(ident,revisit_on=self.date(10))
        with self.assertRaisesRegex(ValueError,'actual user-response/request reference'):
            helper.event_pending(self.state,ident,dict(status='needs_information'))
        item=helper.event_pending(self.state,ident,dict(status='needs_information',resume_reference='synthetic user resumes now'))
        self.assertEqual(item['status'],'needs_information')
        self.assertEqual(item['questions_to_ask'],['Which venue should be recorded?'])

    def test_user_rescheduling_rearms_once_with_new_deferral_id(self):
        self.fixture();ident=self.pending();first=self.defer(ident,revisit_on=self.date(-1))
        helper.offer_revisit(self.state,ident,'cycle-1','synthetic offered question')
        second=self.defer(ident,revisit_trigger='new-user-request')
        self.assertNotEqual(second['deferral_id'],first['deferral_id'])
        self.assertIsNone(second['revisit_offered_at'])
        self.assertEqual(second['questions_to_ask'],[])
        item=helper.offer_revisit(self.state,ident,'cycle-2','synthetic new offered question',
                                  ['new-user-request'],'synthetic new user request')
        self.assertEqual(item['revisit_status'],'already_offered')

    def test_stale_offer_event_cannot_suppress_a_new_deferral(self):
        self.fixture();ident=self.pending();first=self.defer(ident,revisit_on=self.date(-1))
        second=self.defer(ident,revisit_on=self.date(-1))
        path=self.state/'events'/ident/'zz-stale-offer.json'
        path.write_text(json.dumps(dict(status='deferred',event_type='revisit_offered',deferral_id=first['deferral_id'])))
        item=helper.read_pending(self.state,ident)
        self.assertEqual(item['deferral_id'],second['deferral_id'])
        self.assertEqual(item['revisit_status'],'eligible')
        self.assertIn(path.name,item['ignored_revisit_events'])

    def test_rejected_and_superseded_items_cannot_be_deferred_again(self):
        self.fixture()
        for terminal in ('rejected','superseded'):
            with self.subTest(terminal=terminal):
                ident=self.pending();helper.event_pending(self.state,ident,dict(status=terminal))
                with self.assertRaisesRegex(ValueError,'Terminal item cannot be reopened'):
                    self.defer(ident,revisit_trigger='fixture-trigger')
                self.assertEqual(helper.read_pending(self.state,ident)['questions_to_ask'],[])

    def test_historically_applied_item_cannot_be_deferred(self):
        self.fixture();ident=self.pending();proposal=self.propose()
        helper.event_pending(self.state,ident,dict(status='awaiting_approval',proposal_id=proposal,missing_fields=[],questions=[]))
        self.apply(proposal)
        with self.assertRaisesRegex(ValueError,'Terminal item cannot be reopened'):
            self.defer(ident,revisit_trigger='fixture-trigger')

    def test_stale_linked_proposal_does_not_reopen_deferred_questions(self):
        self.fixture();ident=self.pending();proposal=self.propose()
        helper.event_pending(self.state,ident,dict(status='awaiting_approval',proposal_id=proposal,missing_fields=[],questions=[]))
        self.defer(ident,revisit_trigger='fixture-trigger')
        path=self.data/'talks.yml';path.write_text(path.read_text()+'\n')
        item=helper.read_pending(self.state,ident)
        self.assertEqual(item['status'],'deferred')
        self.assertEqual(item['proposal_status'],'stale')
        self.assertEqual(item['questions_to_ask'],[])

    def test_list_and_read_do_not_rewrite_pending_history(self):
        self.fixture();ident=self.pending();self.defer(ident,revisit_trigger='fixture-trigger');before=self.snapshot()
        self.listing('--trigger','fixture-trigger','--trigger-reference','synthetic request')
        helper.read_pending(self.state,ident,['fixture-trigger'])
        self.assertEqual(self.snapshot(),before)

    def test_two_processes_can_record_only_one_offer(self):
        self.fixture();ident=self.pending();self.defer(ident,revisit_on=self.date(-1))
        command=[sys.executable,'-B',str(helper.Path(helper.__file__)),'offer-revisit',str(self.state),ident,
                 '--cycle-id','cycle','--offer-reference','synthetic actual question']
        one=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        two=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        one.communicate(timeout=20);two.communicate(timeout=20)
        self.assertEqual(sorted([one.returncode,two.returncode]),[0,1])
        events=[json.loads(p.read_text()) for p in (self.state/'events'/ident).glob('*.json')]
        self.assertEqual(sum(e.get('event_type')=='revisit_offered' for e in events),1)

    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT'),'Set TEST_RSCRIPT for real R/yaml integration')
    def test_real_r_deferred_candidate_can_resume_then_save_exact_approved_change(self):
        self.fixture();self.stub.stop();ident=self.pending()
        self.defer(ident,revisit_trigger='fixture-trigger')
        helper.event_pending(self.state,ident,dict(status='needs_information',resume_reference='synthetic user supplied answer',
            facts={'venue':'Example Seminar'},missing_fields=[],questions=[]))
        proposal=self.propose()
        helper.event_pending(self.state,ident,dict(status='awaiting_approval',proposal_id=proposal))
        self.apply(proposal)
        self.assertEqual(helper.read_pending(self.state,ident)['status'],'applied')
