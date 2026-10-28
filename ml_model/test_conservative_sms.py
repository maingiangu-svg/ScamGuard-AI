import unittest
from unittest.mock import patch
import numpy as np

from conservative_sms import ConservativeSMS, CalibratedSMS


class FixedModel:
    def __init__(self, scores):self.scores=np.array(scores)
    def predict_proba(self, rows):return np.column_stack([1-self.scores,self.scores])


class ConservativeSMSTests(unittest.TestCase):
    def test_risk_never_exceeds_anchor_and_does_not_create_any_threshold_alert(self):
        anchor=np.array([0,.2949,.295,.3,.6499,.65,.7949,.795,.8,1])
        supporter=np.array([1,.9,.1,.4,.9,.4,.1,1,.7,.99])
        model=ConservativeSMS(FixedModel(anchor),FixedModel(supporter))
        scores=model.predict_proba(['x']*len(anchor))[:,1]
        np.testing.assert_array_equal(scores,np.minimum(anchor,supporter))
        self.assertTrue((scores<=anchor).all())
        for threshold in [.3,.65,.8]:
            self.assertFalse(((scores>=threshold)&(anchor<threshold)).any())
        self.assertTrue(all(round(s*100)<=round(p*100) for s,p in zip(scores,anchor)))

    def test_invalid_component_values_cannot_be_hidden_by_the_minimum(self):
        for bad in [float('nan'),float('inf'),-.1,1.1]:
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                ConservativeSMS(FixedModel([.1]),FixedModel([bad])).predict_proba(['x'])

    def test_uncertain_language_keeps_anchor_and_confident_english_can_only_lower_it(self):
        model=ConservativeSMS(FixedModel([.9,.9,.9]),FixedModel([.1,.1,.1]),
                              FixedModel([.1,.9899,.99]))
        np.testing.assert_array_equal(model.predict_proba(['vi','uncertain','english'])[:,1],[.9,.9,.1])

    def test_calibrator_uses_bounded_score_logits_and_preserves_binary_contract(self):
        class Sigmoid:
            def predict_proba(self, values):
                self.values=values
                p=1/(1+np.exp(-values[:,0]))
                return np.column_stack([1-p,p])
        sigmoid=Sigmoid()
        model=CalibratedSMS(FixedModel([0,.5,1]),sigmoid)
        scores=model.predict_proba(['a','b','c'])[:,1]
        self.assertTrue(np.isfinite(sigmoid.values).all())
        np.testing.assert_allclose(scores,[0,.5,1],atol=1e-10)

    def test_real_routing_preserves_independent_url_review_when_confirmation_lowers_sms(self):
        import predict_hybrid as live
        anchor=FixedModel([.8]);confirmation=ConservativeSMS(anchor,FixedModel([.01]))
        def bundle(model):
            return dict(sms=dict(model=model,threshold=.65,model_id='sms'),
                url=dict(model=FixedModel([.9]),threshold=.5,model_id='url'),
                training=dict(run_id='control',paired_training_samples=0))
        text='Please look at https://example.com/ tomorrow'
        with patch.object(live,'load_bundle',return_value=bundle(anchor)):
            before=live.classify(text)
        with patch.object(live,'load_bundle',return_value=bundle(confirmation)):
            after=live.classify(text)
        self.assertTrue(before['model_ready'] and after['model_ready'])
        self.assertEqual(before['action'],'BLOCK')
        self.assertEqual(after['action'],'REVIEW')
        self.assertTrue(after['url_review_required'])
        self.assertEqual(after['ml_risk_score'],1)


if __name__=='__main__':unittest.main()
