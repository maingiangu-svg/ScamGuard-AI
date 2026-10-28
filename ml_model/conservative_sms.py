"""SMS-only supervised confirmation; the raw risk never exceeds its anchor."""
import numpy as np

from predict import probability


def score_logits(scores):
    values=np.clip(np.asarray(scores,dtype=float),1e-12,1-1e-12)
    return np.log(values/(1-values)).reshape(-1,1)


class ConservativeSMS:
    classes_=np.array([0,1])

    def __init__(self,anchor,supporter,language_gate=None,minimum_english_confidence=.99):
        self.anchor=anchor
        self.supporter=supporter
        self.language_gate=language_gate
        self.minimum_english_confidence=minimum_english_confidence

    def predict_proba(self,rows):
        values=list(rows)
        before=probability(self.anchor,values)
        confirmation=probability(self.supporter,values)
        if before.shape!=confirmation.shape or len(before)!=len(values):
            raise ValueError('SMS confirmation output shape mismatch')
        score=np.minimum(before,confirmation)
        language_gate=getattr(self,'language_gate',None)
        if language_gate is not None:
            english=probability(language_gate,values)
            if english.shape!=before.shape:raise ValueError('Language gate output shape mismatch')
            score=np.where(english>=self.minimum_english_confidence,score,before)
        return np.column_stack([1-score,score])


class CalibratedSMS:
    classes_=np.array([0,1])

    def __init__(self,model,calibrator):
        self.model=model
        self.calibrator=calibrator

    def predict_proba(self,rows):
        score=probability(self.calibrator,score_logits(probability(self.model,rows)))
        return np.column_stack([1-score,score])
