"""Training must preserve source labels, connected groups and the serving URL head."""
import unittest
from unittest.mock import patch

from english_sms_training import make_training_rows, historical_nonregression


def row(case, group, label=0):
    return dict(case_id=case, raw_text='Message '+case, label=label, partition='train',
                original_partition='train', do_not_train=False, repair_group=group,
                language='en', label_provenance='source', expert_verified=False)


class EnglishTrainingTests(unittest.TestCase):
    def test_connected_old_and_new_training_groups_stay_in_one_cv_group(self):
        base = [row('old1','old'), row('old2','old',1), dict(row('vi','vi'),language='vi')]
        additions = [dict(row('new1','ignored',1), group='source-new'),
                     dict(row('new2','ignored',1), group='source-new')]
        with patch('english_sms_training.similarity_edges', return_value=[(0,3,.95)]):
            result = make_training_rows(base, additions, lambda text: [])
        groups={r['case_id']:r['repair_group'] for r in result}
        self.assertEqual(groups['old1'],groups['old2'])
        self.assertEqual(groups['old1'],groups['new1'])
        self.assertEqual(groups['new1'],groups['new2'])
        self.assertEqual(result[2]['language'],'vi')
        self.assertTrue(all(r['label']==source['label'] for r,source in zip(result,base+additions)))

    def test_unknown_or_reserved_rows_never_enter_fitting(self):
        for change in [dict(label=None),dict(label=True),dict(partition='test'),
                       dict(original_partition='validation'),dict(do_not_train=True)]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                make_training_rows([row('old','g')],[dict(row('new','g',1),**change)],lambda text:[])
        with self.assertRaises(ValueError):
            make_training_rows([row('same','g')],[row('same','g',1)],lambda text:[])

    def test_false_alarm_and_missed_positive_regressions_block_acceptance(self):
        before={'cohort':dict(confusion_matrix_tn_fp_fn_tp=[10,1,2,7])}
        equal={'cohort':dict(confusion_matrix_tn_fp_fn_tp=[10,1,2,7])}
        self.assertTrue(historical_nonregression(before,equal))
        for matrix in [[9,2,2,7],[10,1,3,6]]:
            self.assertFalse(historical_nonregression(before,{'cohort':dict(confusion_matrix_tn_fp_fn_tp=matrix)}))


if __name__=='__main__':
    unittest.main()
