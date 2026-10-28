"""Row-independent record errors retain content identity and multiplicity."""
import json
import os
import unittest
import test_baseline_errors as base

h=base.helper

def report(rows):
    lines=['AR_VALIDATION_V1']
    for message,context in rows:
        lines.append('AR_ERROR\trecord\t'+message.encode().hex()+'\t'+context)
    lines.append('AR_VALIDATION_END\t'+str(len(rows)))
    lines += ['ERROR: '+m for m in dict(rows)]
    return '\n'.join(lines)+'\n'

class StableErrorTests(unittest.TestCase):
    def test_row_move_retains_same_record_error_and_current_display(self):
        previous=base.report();current=base.report(message='honors[12] date invalid date/precision')
        result=h.compare_validation_errors(previous,current)
        self.assertEqual(result['resolved_errors'],[])
        self.assertEqual(result['remaining_errors'],['honors[12] date invalid date/precision'])
        h.compare_validation_errors(previous,current,exact=True)

    def test_changed_record_context_still_blocks_after_move(self):
        with self.assertRaisesRegex(ValueError,'new or changed errors'):
            h.compare_validation_errors(base.report(),base.report(message='honors[2] date invalid date/precision',context='changed-record'))

    def test_changed_diagnostic_detail_still_blocks(self):
        with self.assertRaisesRegex(ValueError,'new or changed errors'):
            h.compare_validation_errors(base.report(),base.report(message='honors[2] start_date invalid date/precision'))

    def test_same_context_in_different_table_is_new(self):
        with self.assertRaisesRegex(ValueError,'new or changed errors'):
            h.compare_validation_errors(base.report(),base.report(message='talks[2] date invalid date/precision'))

    def test_identical_bad_record_added_cannot_hide_behind_set(self):
        previous=report([('teaching[1] invalid date','record-a')])
        current=report([('teaching[1] invalid date','record-a'),('teaching[2] invalid date','record-a')])
        with self.assertRaisesRegex(ValueError,'new or changed errors'):h.compare_validation_errors(previous,current)

    def test_duplicate_machine_diagnostic_cannot_hide(self):
        row=('honors[1] date invalid date/precision','record-a')
        with self.assertRaisesRegex(ValueError,'new or changed errors'):
            h.compare_validation_errors(report([row]),report([row,row]))

    def test_resolved_occurrence_count_and_exact_gate(self):
        previous=report([('teaching[1] invalid date','a'),('teaching[2] invalid date','a')])
        current=report([('teaching[1] invalid date','a')])
        review=h.compare_validation_errors(previous,current)
        self.assertEqual(len(review['resolved_errors']),1);self.assertEqual(len(review['remaining_errors']),1)
        with self.assertRaisesRegex(ValueError,'renewed review'):h.compare_validation_errors(previous,current,exact=True)

    def test_numeric_content_outside_leading_label_not_normalized(self):
        previous=report([('honors[1] unsupported value records[1]','a')])
        current=report([('honors[2] unsupported value records[2]','a')])
        with self.assertRaisesRegex(ValueError,'new or changed errors'):h.compare_validation_errors(previous,current)

    def test_unknown_table_or_invalid_label_not_normalized(self):
        for old,new in [('unknown[1] date','unknown[2] date'),('honors[0] date','honors[1] date')]:
            with self.subTest(old=old),self.assertRaisesRegex(ValueError,'new or changed errors'):
                h.compare_validation_errors(report([(old,'a')]),report([(new,'a')]))

    def test_file_level_duplicate_id_context_stays_strict(self):
        with self.assertRaisesRegex(ValueError,'new or changed errors'):
            h.compare_validation_errors(base.report(message='honors duplicate ids'),base.report(message='honors duplicate ids',context='changed-file'))


@unittest.skipUnless(os.environ.get('TEST_RSCRIPT'),'Set TEST_RSCRIPT for real R/yaml integration')
class RealStableErrorTests(unittest.TestCase):
    setUp=base.RealBaselineTests.setUp
    fixture=base.RealBaselineTests.fixture
    save_config=base.RealBaselineTests.save_config
    cli=base.RealBaselineTests.cli
    runtime=base.RealBaselineTests.runtime
    apply=base.RealBaselineTests.apply
    receipt=base.RealBaselineTests.receipt
    bad_honor=base.RealBaselineTests.bad_honor

    def candidate(self,name,rows):
        path=self.base/'candidate.yml';path.write_text(json.dumps(rows),encoding='utf-8')
        return self.cli('propose',self.state,self.data,name,path,*self.runtime())

    def test_real_r_newest_first_insertion_keeps_existing_error_and_saves(self):
        path,_=self.bad_honor();old=json.loads(path.read_text())
        good=dict(old[0],id='new-honor',title='New synthetic honor',date='2026')
        proposal=self.candidate('honors.yml',[good,*old])
        self.assertEqual(proposal['error_review']['resolved_errors'],[])
        self.assertEqual(len(proposal['error_review']['remaining_errors']),1)
        self.assertIn('honors[2]',proposal['error_review']['remaining_errors'][0])
        self.assertEqual(self.apply(proposal['id'])['status'],'verified_saved')
        self.assertEqual(json.loads(path.read_text()),[good,*old])

    def test_real_r_reorder_retains_two_unchanged_bad_records(self):
        path,_=self.bad_honor();one=json.loads(path.read_text())[0]
        two=dict(one,id='another',title='Different invalid honor',date='2025-14')
        path.write_text(json.dumps([one,two]),encoding='utf-8')
        proposal=self.candidate('honors.yml',[two,one])
        self.assertEqual(len(proposal['error_review']['remaining_errors']),2)
        self.assertEqual(proposal['error_review']['resolved_errors'],[])

    def test_real_r_insert_plus_changed_bad_value_blocks(self):
        path,_=self.bad_honor();one=json.loads(path.read_text())[0];before=path.read_bytes()
        with self.assertRaisesRegex(ValueError,'new or changed errors'):
            self.candidate('honors.yml',[dict(one,id='new',date='2026'),dict(one,date='2024-14')])
        self.assertEqual(path.read_bytes(),before)

    def test_real_r_duplicate_invalid_record_without_id_blocks(self):
        self.stub.stop();self.fixture();path=self.data/'teaching.yml'
        bad=json.loads(path.read_text())[0];bad['dates']=['2024-14-15']
        path.write_text(json.dumps([bad]),encoding='utf-8');before=path.read_bytes()
        with self.assertRaisesRegex(ValueError,'new or changed errors'):
            self.candidate('teaching.yml',[bad,bad])
        self.assertEqual(path.read_bytes(),before)

    def test_real_r_duplicate_id_file_error_remains_conservative(self):
        path,_=self.bad_honor();one=json.loads(path.read_text())[0]
        two=dict(one,title='Different duplicate-ID honor',date='2025-13')
        path.write_text(json.dumps([one,two]),encoding='utf-8');before=path.read_bytes()
        with self.assertRaisesRegex(ValueError,'new or changed errors'):
            self.candidate('honors.yml',[two,one])
        self.assertEqual(path.read_bytes(),before)
