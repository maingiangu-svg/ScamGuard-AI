"""Estimator definitions shared by training and prediction."""
import hashlib
from pathlib import Path
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler
from preprocess import extract_13_features


def url_matrix(urls):
    return np.asarray([extract_13_features(u) for u in urls], dtype=np.float32)


def dense(matrix):
    return matrix.toarray().astype(np.float32)


def text_model():
    return Pipeline([
        ("tfidf", TfidfVectorizer(max_features=10000, ngram_range=(1, 2), sublinear_tf=True)),
        ("classifier", LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000, random_state=42)),
    ])


def url_model():
    return Pipeline([
        ("features", FeatureUnion([
            ("numeric", Pipeline([("extract", FunctionTransformer(url_matrix)),
                                   ("scale", StandardScaler())])),
            ("characters", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                                           max_features=1000, dtype=np.float32)),
        ])),
        ("dense", FunctionTransformer(dense)),
        ("classifier", HistGradientBoostingClassifier(max_depth=4, max_iter=100, random_state=42)),
    ])


def meta_features(text_scores, url_scores, interaction=True):
    columns = [text_scores, url_scores]
    if interaction:
        columns.append(np.asarray(text_scores) * np.asarray(url_scores))
    return np.column_stack(columns)


def pipeline_fingerprint():
    root = Path(__file__).resolve().parent
    source = b''.join((root / name).read_bytes().replace(b'\r\n', b'\n') for name in ('preprocess.py', 'modeling.py'))
    return hashlib.sha256(source).hexdigest()


def url_scores(model, links):
    unique = list(dict.fromkeys(u for row in links for u in row))
    scores = {}
    for start in range(0, len(unique), 512):
        batch = unique[start:start + 512]
        scores.update(zip(batch, model.predict_proba(batch)[:, 1]))
    return np.asarray([max((scores[u] for u in row), default=0.0) for row in links])
