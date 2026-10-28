"""C1/B2: synthetic check-ins interleaved with searches; no owner state access."""
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import test_private_state as fixtures
helper = fixtures.helper

class CheckInTests(unittest.TestCase):
    setUp = fixtures.PrivateStateTests.setUp
    request = fixtures.PrivateStateTests.request
    begin = fixtures.PrivateStateTests.begin
    completion = fixtures.PrivateStateTests.completion
    document = fixtures.PrivateStateTests.document

    def event(self, action='dispatched', revision=0, cycle='cycle-1'):
        return dict(event_id=helper.uuid.uuid4().hex, cycle_id=cycle, expected_revision=revision,
                    action=action, actor='user' if action in ('selected','closed') else 'system',
                    reference='SYNTHETIC actual event evidence', occurred_at=helper.now().isoformat())

    def record(self, **kwargs):
        return helper.record_check_in(self.state, self.event(**kwargs))

    def test_check_in_during_search_preserves_profile_and_completes_cutoff(self):
        before=self.config_path.read_bytes();run=self.begin()
        self.record();self.record(action='closed',revision=1)
        result=helper.finish_checkpoint(self.state,run['id'],completion=self.completion(run))
        self.assertEqual(result['last_successful_cutoff'],run['window_end'])
        self.assertEqual(self.config_path.read_bytes(),before)
        self.assertEqual(helper.check_in_status(self.state)['state']['cycles']['cycle-1']['manual_submission_state'],'closed')

    def test_identical_event_replay_does_not_write_or_duplicate_history(self):
        event=self.event();helper.record_check_in(self.state,event)
        before={str(p):p.read_bytes() for p in self.state.rglob('*') if p.is_file()}
        self.assertEqual(helper.record_check_in(self.state,event)['status'],'already_recorded')
        self.assertEqual(before,{str(p):p.read_bytes() for p in self.state.rglob('*') if p.is_file()})
        event['reference']='Different evidence'
        with self.assertRaisesRegex(ValueError,'different evidence'):helper.record_check_in(self.state,event)

    def test_second_dispatch_and_stale_revision_refused(self):
        self.record()
        with self.assertRaisesRegex(ValueError,'already dispatched'):self.record(revision=1)
        with self.assertRaisesRegex(ValueError,'revision'):self.record(action='closed')
        self.assertEqual(helper.check_in_status(self.state)['state']['cycles']['cycle-1']['revision'],1)

    def test_nothing_to_add_requires_user_and_does_not_close_other_cycle(self):
        self.record();self.record(cycle='cycle-2')
        event=self.event(action='closed',revision=1);event['actor']='system'
        with self.assertRaisesRegex(ValueError,'actual user'):helper.record_check_in(self.state,event)
        self.record(action='closed',revision=1)
        cycles=helper.check_in_status(self.state)['state']['cycles']
        self.assertEqual(cycles['cycle-2']['manual_submission_state'],'open')
        self.assertEqual(cycles['cycle-1']['manual_submission_state'],'closed')

    def test_broader_completion_is_separate_and_requires_due(self):
        self.record()
        with self.assertRaisesRegex(ValueError,'must be due'):self.record(action='broader_completed',revision=1)
        self.record(action='broader_due',revision=1)
        self.record(action='broader_completed',revision=2)
        cycle=helper.check_in_status(self.state)['state']['cycles']['cycle-1']
        self.assertEqual(cycle['broader_review_state'],'completed')
        self.assertEqual(cycle['manual_submission_state'],'open')

    def test_ignored_is_not_closed_and_user_can_respond_later(self):
        self.record();self.record(action='ignored',revision=1)
        event=self.event(action='selected',revision=2);event['categories']=['grants']
        helper.record_check_in(self.state,event)
        self.assertEqual(helper.check_in_status(self.state)['state']['cycles']['cycle-1']['manual_submission_state'],'open')

    def test_runtime_writer_rejects_preferences_bad_evidence_and_future(self):
        for field,value in [('discovery',{'sources':['new']}),('approval_policy','none'),('categories',['grants'])]:
            event=self.event();event[field]=value
            with self.assertRaises(ValueError):helper.record_check_in(self.state,event)
        for field,value in [('reference',''),('expected_revision',True),('occurred_at','2999-01-01T00:00:00+00:00')]:
            event=self.event();event[field]=value
            with self.assertRaises(ValueError):helper.record_check_in(self.state,event)
        self.assertFalse((self.state/'reviews/check-in-state.json').exists())

    def test_legacy_progress_requires_review_not_automatic_migration(self):
        self.config['review']={'check_in':{'last_cycle_id':'old','manual_submission_state':'closed'}}
        self.config_path.write_bytes(helper.encoded(self.config));before=self.config_path.read_bytes()
        self.assertTrue(helper.check_in_status(self.state)['migration_required'])
        with self.assertRaisesRegex(ValueError,'reviewed migration'):self.record()
        self.assertEqual(self.config_path.read_bytes(),before)

    def test_null_legacy_fields_need_no_profile_migration(self):
        self.config['review']={'last_broader_completed_at':None,'check_in':{'last_cycle_id':None,'manual_submission_state':None,'output_freshness':None}}
        self.config_path.write_bytes(helper.encoded(self.config));before=self.config_path.read_bytes()
        self.record()
        self.assertEqual(self.config_path.read_bytes(),before)

    def test_status_is_read_only_and_malformed_state_is_preserved(self):
        before={str(p):p.read_bytes() for p in self.state.rglob('*') if p.is_file()}
        self.assertFalse(helper.check_in_status(self.state)['exists'])
        self.assertEqual(before,{str(p):p.read_bytes() for p in self.state.rglob('*') if p.is_file()})
        path=self.state/'reviews/check-in-state.json';path.parent.mkdir();path.write_text('{"schema_version":1,"cycles":[],"events":{}}')
        raw=path.read_bytes()
        with self.assertRaisesRegex(ValueError,'Malformed'):self.record()
        self.assertEqual(path.read_bytes(),raw)

    def test_failed_replace_keeps_prior_cycle_and_backup(self):
        self.record();path=self.state/'reviews/check-in-state.json';before=path.read_bytes()
        with patch.object(helper.os,'replace',side_effect=OSError('SYNTHETIC failure')):
            with self.assertRaisesRegex(ValueError,'interrupted'):self.record(action='closed',revision=1)
        self.assertEqual(path.read_bytes(),before)
        self.assertTrue(any((p/'before.json').read_bytes()==before for p in (self.state/'state-history').iterdir() if (p/'before.json').exists()))

    def test_receipt_interruption_recovers_without_replaying_event(self):
        event=self.event();real=helper.exclusive
        def fail(path,raw):
            if path.name=='committed.json':raise OSError('SYNTHETIC interruption')
            return real(path,raw)
        with patch.object(helper,'exclusive',side_effect=fail):
            with self.assertRaises(ValueError):helper.record_check_in(self.state,event)
        folder=next((self.state/'state-history').iterdir());path=self.state/'reviews/check-in-state.json';before=path.read_bytes()
        self.assertEqual(helper.operation_status(self.state,folder.name)[2]['status'],'committed_unverified')
        helper.verify_operation(self.state,folder.name)
        self.assertEqual(path.read_bytes(),before)
        self.assertEqual(helper.record_check_in(self.state,event)['status'],'already_recorded')

    def test_changed_scope_permissions_identity_paths_still_block(self):
        for patch_value in ({'discovery':{'sources':[]}}, {'identity':{'full_name':'Different'}},
                            {'review':{'approved_sources':[]}}, {'approved_files':['unexpected']},
                            {'unknown':{'preserve':9}}):
            with self.subTest(change=patch_value):
                run=self.begin();completion=self.completion(run)
                self.config_path.write_bytes(helper.encoded(helper.merge(self.config,patch_value)))
                with self.assertRaisesRegex(ValueError,'Profile changed during search'):
                    helper.finish_checkpoint(self.state,run['id'],completion=completion)
                helper.finish_checkpoint(self.state,run['id'],failure={'outcome':'unauthorized','reason':'SYNTHETIC changed scope'})
                self.config_path.write_bytes(helper.encoded(self.config))

    def test_only_legacy_progress_changes_are_excluded_not_reminder_preferences(self):
        run=self.begin()
        current=copy.deepcopy(self.config);current['review']={'last_broader_completed_at':'2026-10-01',
            'check_in':{'last_cycle_id':'old-cycle','manual_submission_state':'closed','output_freshness':'unknown'}}
        self.config_path.write_bytes(helper.encoded(current))
        helper.finish_checkpoint(self.state,run['id'],completion=self.completion(run))
        self.end=(helper.timestamp(self.end)+helper.dt.timedelta(hours=1)).isoformat()
        run=self.begin();current['review']['check_in']['reminder_mode']='different'
        self.config_path.write_bytes(helper.encoded(current))
        with self.assertRaisesRegex(ValueError,'Profile changed'):helper.finish_checkpoint(self.state,run['id'],completion=self.completion(run))

    def test_scope_change_at_commit_boundary_does_not_advance(self):
        run=self.begin();completion=self.completion(run);real=helper.commit
        def change(*args,**kwargs):
            self.config_path.write_bytes(helper.encoded({**self.config,'new_permission':'changed'}))
            return real(*args,**kwargs)
        with patch.object(helper,'commit',side_effect=change):
            with self.assertRaisesRegex(ValueError,'Profile changed before checkpoint save'):
                helper.finish_checkpoint(self.state,run['id'],completion=completion)
        self.assertNotIn('last_successful_cutoff',self.document()['sources'][run['source_key']])

    def test_interrupted_source_can_be_failed_then_restarted_without_lost_cutoff(self):
        first=self.begin();helper.finish_checkpoint(self.state,first['id'],completion=self.completion(first))
        self.end=(helper.timestamp(self.end)+helper.dt.timedelta(hours=1)).isoformat()
        interrupted=self.begin()
        helper.finish_checkpoint(self.state,interrupted['id'],failure={'outcome':'interrupted','reason':'SYNTHETIC verified previous worker stopped'})
        later=self.begin()
        self.assertEqual(later['previous_successful_cutoff'],first['window_end'])
        self.assertEqual(later['window_start'],interrupted['window_start'])

    def test_legacy_active_run_keeps_full_hash_guard(self):
        run=self.begin();doc=self.document();stored=doc['runs'][run['id']]
        stored.pop('scope_hash_version');stored.pop('search_scope_sha256')
        self.checkpoints.write_bytes(helper.encoded(doc))
        self.config_path.write_text(json.dumps(self.config,separators=(',',':')),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Profile changed'):helper.finish_checkpoint(self.state,run['id'],completion=self.completion(run))

    def test_cli_check_in_record_and_status(self):
        path=self.base/'event.json';path.write_bytes(helper.encoded(self.event()))
        for argv in (['check-in-record',str(self.state),str(path)],['check-in-status',str(self.state)]):
            output=io.StringIO()
            with patch.object(sys,'argv',['private_state.py',*argv]),__import__('contextlib').redirect_stdout(output):helper.main()
            result=json.loads(output.getvalue())
        self.assertEqual(result['state']['cycles']['cycle-1']['revision'],1)

if __name__=='__main__':unittest.main()

