"""Training-only selection must reduce alarms without sacrificing a language cohort."""
import unittest
import numpy as np

from english_sms_selection import select_config, training_weights, validate_rows


def trial(c=1, weight=1, en=(100,4,5,20), vi=(20,2,2,10), review_fp=10):
    return dict(config=dict(C=c, weak_weight=weight), review_fp=review_fp,
        cohorts={lang:dict(confusion_matrix_tn_fp_fn_tp=list(matrix))
                 for lang,matrix in [('en',en),('vi',vi)]})


class EnglishSelectionTests(unittest.TestCase):
    def test_losing_recall_or_increasing_false_alarms_cannot_win(self):
        trials={'c1_w1':trial(), 'better':trial(4,.5,en=(101,3,3,22)),
                'misses_more':trial(16,.5,en=(104,0,6,19)),
                'harms_vietnamese':trial(16,1,en=(104,0,0,25),vi=(19,3,0,12))}
        self.assertEqual(select_config(trials),'better')
        self.assertEqual(select_config({'c1_w1':trials['c1_w1'],'bad':trials['misses_more']}),'c1_w1')

    def test_missing_cohort_cannot_hide_regression(self):
        missing=trial(4,.5);missing['cohorts'].pop('vi')
        with self.assertRaises(ValueError):select_config({'c1_w1':trial(),'bad':missing})
        with self.assertRaises(ValueError):select_config({'other':trial()})

    def test_provenance_weights_preserve_human_and_vietnamese_policy(self):
        rows=[dict(language='vi'),dict(language='en',human_verified_by_source=True),
              dict(language='en',label_provenance='source_feed_phishing_with_ai_template_scope_screen'),
              dict(language='en',label_provenance='upstream_ham_or_non_smishing_spam')]
        np.testing.assert_array_equal(training_weights(rows,.5),[3,2,.5,1])

    def test_unknown_heldout_and_duplicate_inputs_fail_before_fitting(self):
        rows=[dict(case_id='x',raw_text='hello there',label=0,partition='train',
                   original_partition='train',do_not_train=False,repair_group='g')]
        for change in [dict(label=None),dict(label=True),dict(partition='test'),
                       dict(original_partition='test'),dict(do_not_train=True)]:
            with self.subTest(change=change),self.assertRaises(ValueError):
                validate_rows([dict(rows[0],**change)])
        with self.assertRaises(ValueError):validate_rows(rows+[dict(rows[0],case_id='y',label=1)])


if __name__=='__main__':unittest.main()
