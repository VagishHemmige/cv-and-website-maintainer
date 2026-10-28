"""Reviewed baseline diagnostics and real-R corrective saves on disposable records."""
import json,os
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import test_proposals as fixtures

helper=fixtures.helper


def report(message='honors[1] date invalid date/precision',context='record-a',severity='record'):
    return 'AR_VALIDATION_V1\nAR_ERROR\t'+severity+'\t'+message.encode().hex()+'\t'+context+'\nAR_VALIDATION_END\t1\nERROR: '+message+'\n13 files checked; 1 errors; 0 warnings\n'


class DiagnosticTests(unittest.TestCase):
    def test_same_error_in_unchanged_record_can_remain(self):
        result=helper.compare_validation_errors(report(),report())
        self.assertEqual(len(result['remaining_errors']),1);self.assertEqual(result['resolved_errors'],[])

    def test_resolved_error_is_reported(self):
        result=helper.compare_validation_errors(report(),'AR_VALIDATION_V1\nAR_VALIDATION_END\t0\n13 files checked; 0 errors; 0 warnings\n')
        self.assertEqual(result['remaining_errors'],[]);self.assertEqual(len(result['resolved_errors']),1)

    def test_changed_bad_value_cannot_hide_under_same_message(self):
        with self.assertRaisesRegex(ValueError,'new or changed errors'):
            helper.compare_validation_errors(report(),report(context='different-record-value'))

    def test_new_error_is_blocked(self):
        with self.assertRaisesRegex(ValueError,'new or changed errors'):
            helper.compare_validation_errors('',report())

    def test_fatal_baseline_blocks_even_if_candidate_clears_it(self):
        with self.assertRaisesRegex(ValueError,'parser/structure'):
            helper.compare_validation_errors(report(severity='fatal'),'')

    def test_missing_truncated_malformed_reports_fail_closed(self):
        for text in ('ERROR: unstructured\n',report().replace('AR_VALIDATION_END\t1','AR_VALIDATION_END\t2'),report().replace('AR_VALIDATION_V1\n',''),report().replace('ERROR: honors[1] date invalid date/precision','ERROR: different'),report().replace('\trecord\t','\tunknown\t')):
            with self.subTest(text=text[:60]),self.assertRaises(ValueError):helper.validation_errors(text)

    def test_execution_failure_or_missing_report_is_not_data_error(self):
        for result in (SimpleNamespace(returncode=2,stdout=report(),stderr='runtime failure'),SimpleNamespace(returncode=0,stdout='unexpected success',stderr=''),SimpleNamespace(returncode=1,stdout='',stderr='yaml package unavailable')):
            with self.subTest(code=result.returncode),patch.object(helper.subprocess,'run',return_value=result),self.assertRaisesRegex(ValueError,'Validation failed'):
                fixtures.REAL_VALIDATE(__import__('pathlib').Path('.'),'fixture-r',None)

    def test_changed_reviewed_errors_require_renewed_review_even_if_removed(self):
        with self.assertRaisesRegex(ValueError,'renewed review'):
            helper.compare_validation_errors(report(),'',exact=True)

    def test_machine_context_is_not_shown_in_readable_proposal(self):
        displayed=helper.validation_display(report())
        self.assertIn('ERROR: honors',displayed);self.assertNotIn('AR_ERROR',displayed);self.assertNotIn('record-a',displayed)


class WorkflowErrorTests(unittest.TestCase):
    setUp=fixtures.ProposalTests.setUp
    fixture=fixtures.ProposalTests.fixture
    save_config=fixtures.ProposalTests.save_config
    cli=fixtures.ProposalTests.cli
    runtime=fixtures.ProposalTests.runtime
    propose=fixtures.ProposalTests.propose
    apply=fixtures.ProposalTests.apply
    receipt=fixtures.ProposalTests.receipt

    def test_changed_diagnostics_in_staged_check_prevent_any_write(self):
        self.fixture()
        with patch.object(helper,'validate',return_value=report()):ident=self.propose()
        before=(self.data/'teaching.yml').read_bytes()
        with patch.object(helper,'validate',return_value=report(context='changed')),self.assertRaisesRegex(ValueError,'renewed review'):
            self.apply(ident)
        self.assertEqual((self.data/'teaching.yml').read_bytes(),before)
        self.assertFalse(self.receipt(ident).exists())

    def test_changed_current_bibliography_diagnostics_block_before_write(self):
        self.fixture()
        with patch.object(helper,'validate',return_value=report()):ident=self.propose()
        folder,_=helper.read_proposal(self.state,ident);before=(self.data/'teaching.yml').read_bytes()
        def current(root,*args):return report() if root==folder/'staged' else report(context='changed')
        with patch.object(helper,'validate',side_effect=current),self.assertRaisesRegex(ValueError,'renewed review'):
            self.apply(ident)
        self.assertEqual((self.data/'teaching.yml').read_bytes(),before)
        self.assertFalse(self.receipt(ident).exists())

    def test_postwrite_and_recovery_do_not_certify_changed_errors(self):
        self.fixture()
        with patch.object(helper,'validate',return_value=report()):ident=self.propose()
        def current(root,*args):return report(context='changed') if root==self.data else report()
        with patch.object(helper,'validate',side_effect=current),self.assertRaisesRegex(ValueError,'saved_unverified'):
            self.apply(ident)
        saved=(self.data/'teaching.yml').read_bytes()
        with patch.object(helper,'validate',return_value=report(context='changed')),self.assertRaisesRegex(ValueError,'renewed review'):
            self.cli('verify',self.state,ident,*self.runtime())
        self.assertFalse(self.receipt(ident).exists());self.assertEqual((self.data/'teaching.yml').read_bytes(),saved)
        with patch.object(helper,'validate',return_value=report()):result=self.cli('verify',self.state,ident,*self.runtime())
        self.assertFalse(result['record_rewritten'])


@unittest.skipUnless(os.environ.get('TEST_RSCRIPT'),'Set TEST_RSCRIPT for real R/yaml integration')
class RealBaselineTests(unittest.TestCase):
    setUp=fixtures.ProposalTests.setUp
    fixture=fixtures.ProposalTests.fixture
    save_config=fixtures.ProposalTests.save_config
    cli=fixtures.ProposalTests.cli
    runtime=fixtures.ProposalTests.runtime
    propose=fixtures.ProposalTests.propose
    apply=fixtures.ProposalTests.apply
    receipt=fixtures.ProposalTests.receipt

    def bad_honor(self):
        self.stub.stop();self.fixture()
        path=self.data/'honors.yml';good=path.read_text();path.write_text(good.replace('2024','2024-13'),encoding='utf-8')
        return path,good

    def correct_honor(self,good):
        candidate=self.base/'corrected.yml';candidate.write_text(good,encoding='utf-8')
        return self.cli('propose',self.state,self.data,'honors.yml',candidate,*self.runtime())

    def test_real_r_invalid_date_can_be_proposed_and_corrected(self):
        path,good=self.bad_honor();proposal=self.correct_honor(good)
        self.assertEqual(len(proposal['error_review']['resolved_errors']),1)
        self.assertEqual(proposal['error_review']['remaining_errors'],[])
        self.assertNotIn('AR_ERROR',proposal['baseline_validation'])
        self.assertEqual(self.apply(proposal['id'])['status'],'verified_saved')
        self.assertEqual(path.read_text(),good)

    def test_real_r_unchanged_unrelated_error_is_explicit_and_retained(self):
        path,_=self.bad_honor();before=path.read_bytes();ident=self.propose()
        _,item=helper.read_proposal(self.state,ident)
        self.assertEqual(len(item['error_review']['remaining_errors']),1)
        self.assertEqual(self.apply(ident)['status'],'verified_saved')
        self.assertEqual(path.read_bytes(),before)
        receipt=json.loads(self.receipt(ident).read_text())
        self.assertIn('ERROR: honors',receipt['validation'])

    def test_real_r_changed_invalid_date_and_new_error_are_blocked(self):
        path,good=self.bad_honor();before=path.read_bytes()
        with self.assertRaisesRegex(ValueError,'new or changed errors'):
            self.correct_honor(good.replace('2024','2024-14'))
        candidate=self.base/'bad-teaching.yml';candidate.write_text((self.data/'teaching.yml').read_text().replace('2024-04-15','2024-14-15'))
        with self.assertRaisesRegex(ValueError,'new or changed errors'):
            self.cli('propose',self.state,self.data,'teaching.yml',candidate,*self.runtime())
        self.assertEqual(path.read_bytes(),before)

    def test_real_r_malformed_yaml_still_blocks_proposals(self):
        self.stub.stop();self.fixture();(self.data/'honors.yml').write_text('broken: [\n')
        with self.assertRaisesRegex(ValueError,'Validation failed'):
            self.propose()

    def test_real_r_remaining_errors_survive_interrupted_verification_recovery(self):
        path,_=self.bad_honor();before=path.read_bytes();ident=self.propose()
        real=helper.validate_current_bibliography
        def interrupt(root,*args,**kwargs):
            if kwargs.get('candidate_root') is None:raise ValueError('Synthetic postwrite interruption')
            return real(root,*args,**kwargs)
        with patch.object(helper,'validate_current_bibliography',side_effect=interrupt),self.assertRaisesRegex(ValueError,'saved_unverified'):
            self.apply(ident)
        target=(self.data/'teaching.yml').read_bytes()
        result=self.cli('verify',self.state,ident,*self.runtime())
        self.assertEqual(result['status'],'verified_saved');self.assertFalse(result['record_rewritten'])
        self.assertEqual((self.data/'teaching.yml').read_bytes(),target);self.assertEqual(path.read_bytes(),before)


if __name__=='__main__':unittest.main()
