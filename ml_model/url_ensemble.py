"""A supervised residual gate between two frozen URL classifiers."""
import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.utils.validation import check_is_fitted

CUTOFFS = (.5, .6, .7, .8, .85, .9, .95, .975, .99, 1.01)


def pooled_scores(primary, parent, cutoff):
    return np.where(parent >= cutoff, np.maximum(primary, parent), primary)


def measures(y, p):
    predicted = p >= .5
    tn, fp = int(((y == 0) & ~predicted).sum()), int(((y == 0) & predicted).sum())
    fn, tp = int(((y == 1) & ~predicted).sum()), int(((y == 1) & predicted).sum())
    return dict(confusion_matrix_tn_fp_fn_tp=[tn, fp, fn, tp], accuracy=(tn + tp) / len(y),
                precision=tp / (tp + fp) if tp + fp else 0,
                recall=tp / (tp + fn), f1=2 * tp / (2 * tp + fp + fn))


def valid_scores(values, length):
    values = np.asarray(values, dtype=float)
    if values.shape != (length,) or not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
        raise ValueError('Finite, aligned out-of-sample probabilities required')
    return values


def learn_cutoff(y, primary, parent, benign_seed_scores):
    y = np.asarray(y)
    if y.ndim != 1 or set(y) != {0, 1}:
        raise ValueError('Both explicit source label classes required')
    primary, parent = valid_scores(primary, len(y)), valid_scores(parent, len(y))
    seeds = np.asarray(benign_seed_scores, dtype=float).reshape(-1, 2)
    for column in range(2):
        valid_scores(seeds[:, column], len(seeds))
    old, new = measures(y, parent), measures(y, primary)
    candidates, eligible = [], []
    for cutoff in CUTOFFS:
        score = measures(y, pooled_scores(primary, parent, cutoff))
        seed_scores = pooled_scores(seeds[:, 0], seeds[:, 1], cutoff)
        extra_seed_alerts = int(((seeds[:, 0] < .5) & (seed_scores >= .5)).sum())
        accepted = (score['accuracy'] > .95 and extra_seed_alerts == 0
                    and score['confusion_matrix_tn_fp_fn_tp'][1] <= old['confusion_matrix_tn_fp_fn_tp'][1]
                    and score['confusion_matrix_tn_fp_fn_tp'][3] >= new['confusion_matrix_tn_fp_fn_tp'][3])
        item = dict(cutoff=cutoff, metrics=score, new_benign_seed_alerts=extra_seed_alerts, eligible=accepted)
        candidates.append(item)
        if accepted:
            eligible.append(item)
    selected = (max(eligible, key=lambda item: (item['metrics']['confusion_matrix_tn_fp_fn_tp'][3],
                    item['metrics']['accuracy'], item['cutoff'])) if eligible else candidates[-1])
    return selected['cutoff'], dict(gate_pass=bool(eligible), selected=selected['metrics'],
        cutoff=selected['cutoff'], parent_reference=old, primary_reference=new, candidates=candidates,
        estimates_are_training_selection_not_independent_test=True)


class GatedURLClassifier(ClassifierMixin, BaseEstimator):
    def __init__(self, primary, parent):
        self.primary = primary
        self.parent = parent

    def fit(self, X, y, *, primary_oof=None, parent_oof=None, benign_seed_scores=()):
        if primary_oof is None or parent_oof is None or len(X) != len(y):
            raise ValueError('Aligned externally audited OOF scores are required; no fitted-score fallback')
        for model in (self.primary, self.parent):
            if not np.array_equal(model.classes_, [0, 1]):
                raise ValueError('Frozen heads must use class order 0, 1')
        self.cutoff_, self.training_report_ = learn_cutoff(y, primary_oof, parent_oof, benign_seed_scores)
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, X):
        check_is_fitted(self, 'cutoff_')
        primary = valid_scores(self.primary.predict_proba(X)[:, 1], len(X))
        parent = valid_scores(self.parent.predict_proba(X)[:, 1], len(X))
        p = pooled_scores(primary, parent, self.cutoff_)
        return np.column_stack((1 - p, p))

    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= .5).astype(int)
