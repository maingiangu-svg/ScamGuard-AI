import unittest
from english_ham_training import validate_additions, diagnostic_gates


class EnglishHamTrainingTests(unittest.TestCase):
    def test_only_isolated_source_negative_training_records_are_admitted(self):
        row = dict(case_id='new', raw_text='See you at the station tomorrow', label=0,
                   source_label='ham', partition='train', original_partition='train',
                   do_not_train=False, language='en', language_confidence=.99,
                   expert_verified=False, human_verified=False, group='g',
                   group_roles=['train'], label_provenance='uci_source_ham_proxy_not_expert_smishing_verdict')
        validate_additions([], [row])
        for change in [dict(label=1),dict(label=True),dict(original_partition='test'),
                       dict(partition='validation'),dict(group_roles=['train','quarantine']),
                       dict(source_label='spam'),dict(expert_verified=True),dict(language='vi'),
                       dict(do_not_train=True),dict(language_confidence=float('nan'))]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_additions([], [dict(row, **change)])
        for base in [[row],[dict(row,case_id='old')]]:
            with self.assertRaises(ValueError):validate_additions(base,[row])

    def test_any_language_or_threshold_regression_blocks_diagnostics(self):
        def cohort(matrix):
            return {str(t):dict(parent=dict(confusion_matrix_tn_fp_fn_tp=[10,1,2,7]),
                               candidate=dict(confusion_matrix_tn_fp_fn_tp=list(matrix))) for t in [.3,.65,.8]}
        cohorts={'validation_en':cohort([10,1,2,7]),'validation_vi':cohort([10,1,2,7])}
        self.assertTrue(all(diagnostic_gates(cohorts).values()))
        cohorts['validation_vi']['0.8']['candidate']['confusion_matrix_tn_fp_fn_tp']=[9,2,2,7]
        gates=diagnostic_gates(cohorts)
        self.assertTrue(gates['0.65']); self.assertFalse(gates['0.8'])
        cohorts['validation_en']['0.65']['candidate']['confusion_matrix_tn_fp_fn_tp']=[10,1,3,6]
        self.assertFalse(diagnostic_gates(cohorts)['0.65'])


if __name__=='__main__':unittest.main()
