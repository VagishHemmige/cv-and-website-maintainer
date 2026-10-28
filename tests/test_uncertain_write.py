"""Crash boundary on synthetic records; never infer historical execution from bytes."""
import json,os,unittest
from pathlib import Path
from unittest.mock import patch
import test_recovery_attribution as base

h=base.h
class InterruptedProcess(BaseException):pass

class UncertainWriteTests(unittest.TestCase):
    setUp=base.RecoveryAttributionTests.setUp
    fixture=base.RecoveryAttributionTests.fixture
    save_config=base.RecoveryAttributionTests.save_config
    cli=base.RecoveryAttributionTests.cli
    runtime=base.RecoveryAttributionTests.runtime
    propose=base.RecoveryAttributionTests.propose
    apply=base.RecoveryAttributionTests.apply
    receipt=base.RecoveryAttributionTests.receipt
    snapshot=base.RecoveryAttributionTests.snapshot

    @unittest.skipUnless(os.environ.get('TEST_RSCRIPT'),'Set TEST_RSCRIPT for the real-R crash-boundary test')
    def test_real_r_replacement_before_durable_marker_stays_unconfirmed_and_read_only(self):
        self.stub.stop();self.fixture();ident=self.propose();folder,item=h.read_proposal(self.state,ident)
        real=h.atomic_write
        def interrupt(path,raw):
            if Path(path).parent==folder/'attempts':raise InterruptedProcess('SYNTHETIC process loss before marker persistence')
            return real(path,raw)
        with patch.object(h,'atomic_write',side_effect=interrupt),self.assertRaises(InterruptedProcess):self.apply(ident)
        self.assertEqual(h.digest(self.data/item['file']),item['candidate_sha256'])
        self.assertEqual(h.digest(folder/'backup'/item['file']),item['before'][item['file']])
        attempt=json.loads(next((folder/'attempts').glob('*.json')).read_text(encoding='utf-8'))
        self.assertFalse(attempt['target_write_confirmed']);self.assertEqual(attempt['status'],'applying')
        history=self.snapshot(folder);source=self.snapshot(self.data)
        details=self.cli('status',self.state,ident)
        self.assertEqual(details['status'],'saved_unverified');self.assertEqual(details['write_attribution'],'unconfirmed')
        self.assertFalse(details['historical_save_verified'])
        with self.assertRaisesRegex(ValueError,'No confirmed target write'):self.cli('verify',self.state,ident,*self.runtime())
        self.assertFalse(self.receipt(ident).exists())
        self.assertEqual(self.snapshot(folder),history);self.assertEqual(self.snapshot(self.data),source)

    def test_manual_guidance_preserves_uncertainty_and_requires_actual_current_state_review(self):
        text=(Path(__file__).resolve().parents[1]/'references/verification.md').read_text(encoding='utf-8')
        for phrase in ('specifically authorized proposal/state access','leave the source bytes unchanged','current-state acceptance, not a historical save receipt','do not manufacture a no-op proposal','not a reconciliation helper'):
            self.assertIn(phrase,text)
