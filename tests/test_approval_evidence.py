"""F8 audit tests with synthetic replies; these never authorize real records."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import test_proposals as records
import test_attachments as attachments
import test_private_state as preferences
from approval_fixture import approval_file

audit = records.helper.approvals


class EvidenceSchemaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TEST_TMP_ROOT')); self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name).resolve()
        self.expected = dict(kind='yaml', id='a'*32, sha256='1'*64, destination=str(self.state/'project/data/teaching.yml'))
        self.input = approval_file(self.state, **dict(kind='yaml',ident='a'*32,sha256='1'*64,destination=self.expected['destination']))
        self.value = json.loads(self.input.read_text(encoding='utf-8'))

    def raw(self):
        return json.dumps(self.value).encode('utf-8')

    def test_unknown_message_time_is_explicit_and_not_fabricated(self):
        parsed = audit.parse(self.raw(), self.expected)
        self.assertIsNone(parsed['approved_at'])
        self.assertEqual(parsed['timestamp_source'], 'message_time_unavailable')
        self.assertEqual(parsed['response'], 'SYNTHETIC FIXTURE APPROVAL ONLY')

    def test_known_message_time_preserves_source(self):
        self.value.update(approved_at='2026-10-17T11:00:00+00:00',timestamp_source='host_message_timestamp')
        self.assertEqual(audit.parse(self.raw(),self.expected)['approved_at'],'2026-10-17T11:00:00+00:00')

    def test_missing_response_or_references_are_not_approval(self):
        for field in ('response','channel','message_reference','proposal_reference','recorded_at'):
            with self.subTest(field=field):
                original = self.value[field]; self.value[field] = ''
                with self.assertRaises(ValueError): audit.parse(self.raw(), self.expected)
                self.value[field] = original

    def test_nonapproval_decision_is_refused(self):
        self.value['decision'] = 'declined'
        with self.assertRaisesRegex(ValueError,'approved decision'):audit.parse(self.raw(),self.expected)

    def test_wrong_item_bytes_or_destination_are_refused(self):
        for field,wrong in (('id','b'*32),('sha256','2'*64),('destination',str(self.state/'other.yml'))):
            with self.subTest(field=field):
                original = self.value['approvals'][0][field]; self.value['approvals'][0][field] = wrong
                with self.assertRaisesRegex(ValueError,'does not match'):audit.parse(self.raw(),self.expected)
                self.value['approvals'][0][field] = original

    def test_duplicate_items_do_not_create_ambiguous_approval(self):
        self.value['approvals'].append(dict(self.value['approvals'][0]))
        with self.assertRaisesRegex(ValueError,'contradictory'):audit.parse(self.raw(),self.expected)

    def test_timestamps_cannot_be_invented_from_capture_time(self):
        self.value['timestamp_source'] = 'host_message_timestamp'
        with self.assertRaisesRegex(ValueError,'Unknown approval time'):audit.parse(self.raw(),self.expected)
        self.value.update(approved_at='2026-10-17T13:00:00+00:00')
        with self.assertRaisesRegex(ValueError,'later than evidence'):audit.parse(self.raw(),self.expected)
        self.value.update(approved_at='2026-10-17T11:00:00')
        with self.assertRaisesRegex(ValueError,'explicit timezones'):audit.parse(self.raw(),self.expected)

    def test_external_path_is_not_copied_into_audit(self):
        with self.assertRaisesRegex(ValueError,'inside the private state'):
            audit.read(self.state, self.state.parent/'external.json',self.expected)

    def test_oversized_or_duplicate_json_is_refused(self):
        with self.assertRaisesRegex(ValueError,'64 KiB'):audit.parse(b' '*65537,self.expected)
        with self.assertRaisesRegex(ValueError,'Duplicate approval'):
            audit.parse(b'{"schema_version":1,"schema_version":1}',self.expected)

    def test_copy_is_immutable_and_hash_verified(self):
        folder = self.state/'audit';folder.mkdir()
        raw = self.raw();reference = audit.persist(folder,raw,self.expected)
        self.assertEqual(reference['sha256'],hashlib.sha256(raw).hexdigest())
        self.value['response'] = 'Different synthetic response'
        with self.assertRaisesRegex(ValueError,'never overwrite'):
            audit.persist(folder,self.raw(),self.expected)
        self.assertEqual((folder/'approval-evidence.json').read_bytes(),raw)
        (folder/'approval-evidence.json').write_bytes(raw+b'\n')
        with self.assertRaisesRegex(ValueError,'hash changed'):audit.verify(folder,reference,self.expected)


class RecordApprovalTests(unittest.TestCase):
    setUp = records.ProposalTests.setUp
    fixture = records.ProposalTests.fixture
    save_config = records.ProposalTests.save_config
    cli = records.ProposalTests.cli
    runtime = records.ProposalTests.runtime
    propose = records.ProposalTests.propose
    apply = records.ProposalTests.apply
    receipt = records.ProposalTests.receipt
    interrupted = records.ProposalTests.interrupted
    mutate_after_live_validation = records.ProposalTests.mutate_after_live_validation

    def test_evidence_required_before_yaml_write(self):
        self.fixture();ident=self.propose();before=(self.data/'teaching.yml').read_bytes()
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            self.cli('apply',self.state,ident,'--approval',ident,*self.runtime())
        with self.assertRaisesRegex(ValueError,'Missing or oversized'):
            self.cli('apply',self.state,ident,'--approval',ident,'--approval-evidence',self.state/'missing.json',*self.runtime())
        self.assertEqual((self.data/'teaching.yml').read_bytes(),before)
        self.assertFalse(self.receipt(ident).exists())

    def test_yaml_receipt_links_exact_response_copy_and_survives_input_change(self):
        self.fixture();ident=self.propose();self.apply(ident)
        folder=self.receipt(ident).parent;receipt=json.loads(self.receipt(ident).read_text())
        raw=(folder/receipt['approval_evidence']['path']).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),receipt['approval_evidence']['sha256'])
        self.assertEqual(json.loads(raw)['response'],'SYNTHETIC FIXTURE APPROVAL ONLY')
        (self.state/('fixture-approval-yaml-'+ident+'.json')).write_text('changed input')
        self.assertEqual(self.cli('status',self.state,ident)['approval_evidence_status'],'recorded')

    def test_mismatched_approval_does_not_write_yaml(self):
        self.fixture();ident=self.propose();before=(self.data/'teaching.yml').read_bytes()
        evidence=approval_file(self.state,'yaml',ident,'0'*64,self.data/'teaching.yml')
        with self.assertRaisesRegex(ValueError,'does not match'):
            self.cli('apply',self.state,ident,'--approval',ident,'--approval-evidence',evidence,*self.runtime())
        self.assertEqual((self.data/'teaching.yml').read_bytes(),before)
        self.assertFalse(self.receipt(ident).exists())

    def test_recovery_refuses_changed_approval_copy_without_rewriting_yaml(self):
        self.fixture();ident=self.propose();self.interrupted(ident)
        folder=self.receipt(ident).parent;path=folder/'approval-evidence.json';path.write_bytes(path.read_bytes()+b'\n')
        before=(self.data/'teaching.yml').read_bytes()
        with self.assertRaisesRegex(ValueError,'hash changed'):
            self.cli('verify',self.state,ident,*self.runtime())
        self.assertEqual((self.data/'teaching.yml').read_bytes(),before)
        self.assertFalse(self.receipt(ident).exists())
        self.assertEqual(self.cli('status',self.state,ident)['approval_evidence_status'],'missing_or_changed')

    def test_legacy_receipt_reports_absence_without_rewriting_history(self):
        self.fixture();ident=self.propose();self.apply(ident)
        value=json.loads(self.receipt(ident).read_text());del value['approval_evidence']
        self.receipt(ident).write_text(json.dumps(value));before=self.receipt(ident).read_bytes()
        result=self.cli('verify',self.state,ident,*self.runtime())
        self.assertEqual(result['approval_evidence_status'],'not_recorded')
        self.assertEqual(self.receipt(ident).read_bytes(),before)

    def test_legacy_interrupted_save_does_not_invent_approval_on_recovery(self):
        self.fixture();ident=self.propose();self.interrupted(ident)
        folder=self.receipt(ident).parent
        for path in (folder/'attempts').glob('*.json'):
            value=json.loads(path.read_text());del value['approval_evidence'];path.write_text(json.dumps(value))
        before=(self.data/'teaching.yml').read_bytes()
        with self.assertRaisesRegex(ValueError,'Missing linked approval'):
            self.cli('verify',self.state,ident,*self.runtime())
        self.assertFalse(self.receipt(ident).exists())
        self.assertEqual((self.data/'teaching.yml').read_bytes(),before)

    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT'),'Set TEST_RSCRIPT for real R/yaml integration')
    def test_real_r_evidence_is_linked_after_successful_validation(self):
        self.fixture();self.stub.stop();ident=self.propose();self.apply(ident)
        result=self.cli('status',self.state,ident)
        self.assertTrue(result['historical_save_verified'])
        self.assertEqual(result['approval_evidence_status'],'recorded')


class AttachmentApprovalTests(unittest.TestCase):
    setUp = attachments.AttachmentTests.setUp
    cli = attachments.AttachmentTests.cli
    stage_pdf = attachments.AttachmentTests.stage_pdf
    save = attachments.AttachmentTests.save

    def test_pdf_approval_must_explicitly_include_public_use(self):
        item=self.stage_pdf()
        path=approval_file(self.state,'attachment',item['id'],item['pdf_sha256'],self.target)
        value=json.loads(path.read_text());value['approvals'][0]['public_use_approved']=False;path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'explicitly cover public use'):
            self.cli('save',self.state,item['id'],'--approval',item['id'],'--approval-evidence',path,'--privacy-reviewed','--public-approved')
        self.assertFalse(self.target.exists())

    def test_pdf_save_requires_evidence_file(self):
        item=self.stage_pdf()
        with self.assertRaisesRegex(ValueError,'Missing or oversized'):
            self.cli('save',self.state,item['id'],'--approval',item['id'],'--approval-evidence',self.state/'missing.json','--privacy-reviewed','--public-approved')
        self.assertFalse(self.target.exists())

    def test_pdf_receipt_audit_detects_changed_copy_but_preserves_saved_bytes(self):
        item=self.stage_pdf();self.save(item,'--privacy-reviewed','--public-approved')
        folder=Path(item['staged_pdf']).parent;receipt=(folder/'saved.json').read_bytes();saved=self.target.read_bytes()
        path=folder/'approval-evidence.json';path.write_bytes(path.read_bytes()+b'\n')
        result=self.cli('status',self.state,item['id'])
        self.assertEqual(result['status'],'saved_bytes_verified')
        self.assertEqual(result['approval_evidence_status'],'missing_or_changed')
        self.assertEqual((folder/'saved.json').read_bytes(),receipt)
        self.assertEqual(self.target.read_bytes(),saved)

    def test_interrupted_pdf_save_keeps_prewrite_evidence_link(self):
        item=self.stage_pdf();real=attachments.helper.write_json
        def interrupt(path,value):
            if path.name=='saved.json':raise OSError('Synthetic post-copy interruption')
            return real(path,value)
        with patch.object(attachments.helper,'write_json',side_effect=interrupt),self.assertRaises(OSError):
            self.save(item,'--privacy-reviewed','--public-approved')
        folder=Path(item['staged_pdf']).parent
        self.assertFalse((folder/'saved.json').exists())
        self.assertEqual(self.cli('status',self.state,item['id'])['approval_evidence_status'],'recorded')
        self.assertFalse(self.cli('status',self.state,item['id'])['save_receipt_present'])
        self.assertEqual(self.target.read_bytes(),Path(item['staged_pdf']).read_bytes())

    def test_legacy_pdf_receipt_reports_missing_evidence_without_backfill(self):
        item=self.stage_pdf();self.save(item,'--privacy-reviewed','--public-approved')
        folder=Path(item['staged_pdf']).parent;path=folder/'saved.json'
        value=json.loads(path.read_text());del value['approval_evidence'];path.write_text(json.dumps(value))
        before=path.read_bytes()
        self.assertEqual(self.cli('status',self.state,item['id'])['approval_evidence_status'],'not_recorded')
        self.assertEqual(path.read_bytes(),before)


class PreferenceApprovalTests(unittest.TestCase):
    setUp = preferences.PrivateStateTests.setUp
    propose = preferences.PrivateStateTests.propose
    apply = preferences.PrivateStateTests.apply

    def test_preference_save_requires_actual_evidence_input(self):
        proposal=self.propose();before=self.config_path.read_bytes()
        with self.assertRaisesRegex(ValueError,'Approval evidence file required'):
            preferences.helper.apply_profile(self.state,proposal['id'],proposal['id'],'Synthetic reference only')
        self.assertEqual(self.config_path.read_bytes(),before)

    def test_preference_receipt_links_hash_of_quoted_response(self):
        proposal=self.propose();result=self.apply(proposal)
        folder=self.state/'state-history'/result['operation_id']
        receipt=json.loads((folder/'committed.json').read_text())
        raw=(folder/'approval-evidence.json').read_bytes()
        self.assertEqual(receipt['approval_evidence']['sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(preferences.helper.operation_status(self.state,result['operation_id'])[2]['approval_evidence_status'],'recorded')

    def test_preference_recovery_refuses_modified_approval(self):
        proposal=self.propose();real=preferences.helper.exclusive
        def interrupt(path,raw):
            if path.name=='committed.json':raise OSError('Synthetic postwrite interruption')
            return real(path,raw)
        with patch.object(preferences.helper,'exclusive',side_effect=interrupt),self.assertRaises(ValueError):self.apply(proposal)
        folder=next((self.state/'state-history').iterdir());path=folder/'approval-evidence.json'
        path.write_bytes(path.read_bytes()+b'\n');before=self.config_path.read_bytes()
        with self.assertRaisesRegex(ValueError,'hash changed'):preferences.helper.verify_operation(self.state,folder.name)
        self.assertFalse((folder/'committed.json').exists())
        self.assertEqual(self.config_path.read_bytes(),before)

    def test_legacy_preference_receipt_remains_unchanged_and_honestly_labelled(self):
        proposal=self.propose();result=self.apply(proposal)
        folder=self.state/'state-history'/result['operation_id']
        for name in ('intent.json','committed.json'):
            path=folder/name;value=json.loads(path.read_text());del value['approval_evidence'];path.write_text(json.dumps(value))
        before={p.name:p.read_bytes() for p in folder.iterdir()}
        result=preferences.helper.verify_operation(self.state,folder.name)
        self.assertEqual(result['approval_evidence_status'],'not_recorded')
        self.assertEqual({p.name:p.read_bytes() for p in folder.iterdir()},before)

    def test_legacy_unverified_preference_commit_does_not_gain_fabricated_evidence(self):
        proposal=self.propose();real=preferences.helper.exclusive
        def interrupt(path,raw):
            if path.name=='committed.json':raise OSError('Synthetic postwrite interruption')
            return real(path,raw)
        with patch.object(preferences.helper,'exclusive',side_effect=interrupt),self.assertRaises(ValueError):self.apply(proposal)
        folder=next((self.state/'state-history').iterdir());path=folder/'intent.json'
        value=json.loads(path.read_text());del value['approval_evidence'];path.write_text(json.dumps(value))
        before=self.config_path.read_bytes()
        with self.assertRaisesRegex(ValueError,'Missing linked approval'):
            preferences.helper.verify_operation(self.state,folder.name)
        self.assertFalse((folder/'committed.json').exists())
        self.assertEqual(self.config_path.read_bytes(),before)
