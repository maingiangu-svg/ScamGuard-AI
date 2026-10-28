import unittest
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from conservative_sms_training import choose, cohort_metrics, fit_head


class ConservativeSelectionTests(unittest.TestCase):
    def trial(self, fp=2,fn=1,margin=.1):
        metrics={lang:{str(t):dict(confusion_matrix_tn_fp_fn_tp=[20,fp,fn,10])
                       for t in [.3,.65,.8]} for lang in ['en','vi']}
        return dict(cohorts=metrics,positive_margin=margin)

    def test_false_negatives_or_a_missing_language_cannot_hide_behind_fewer_alarms(self):
        baseline=self.trial()['cohorts']
        trials=[self.trial(1,1),self.trial(0,2),self.trial(2,1,.2)]
        self.assertEqual(choose(trials,baseline),0)
        self.assertIsNone(choose([self.trial(0,2)],baseline))
        missing=self.trial();missing['cohorts'].pop('vi')
        with self.assertRaises(ValueError):choose([missing],baseline)

    def test_confirmation_margin_breaks_ties_without_reading_test_scores(self):
        baseline=self.trial()['cohorts']
        self.assertEqual(choose([self.trial(1,1,.1),self.trial(1,1,.2)],baseline),1)

    def test_unsafe_confirmation_margin_cannot_win_by_reducing_alarms(self):
        baseline=self.trial()['cohorts']
        self.assertEqual(choose([self.trial(0,1,.01),self.trial(1,1,.1)],baseline),1)
        self.assertIsNone(choose([self.trial(0,1,.01)],baseline))

    def test_offset_changes_only_confirmation_intercept_after_supervised_fit(self):
        rows=[dict(raw_text=text,label=label,language='en',label_provenance='source') for text,label in [
            ('please meet me for lunch',0),('your parcel requires a payment immediately',1),
            ('see you tomorrow at home',0),('verify your password using the link now',1)]]
        parent=Pipeline([('features',CountVectorizer()),('classifier',LogisticRegression(random_state=42))])
        config=dict(C=1,weak_weight=.1,positive_weight=1,confirmation_shift=0)
        ordinary=fit_head(parent,rows,config)
        shifted=fit_head(parent,rows,{**config,'confirmation_shift':2})
        np.testing.assert_array_equal(ordinary.named_steps['classifier'].coef_,shifted.named_steps['classifier'].coef_)
        np.testing.assert_allclose(shifted.named_steps['classifier'].intercept_,ordinary.named_steps['classifier'].intercept_+2)


if __name__=='__main__':unittest.main()
