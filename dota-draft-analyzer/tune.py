"""Reproduce the exploratory search using Train only; never replaces serving model."""
import json
import time
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_limits
from common import ROOT, FEATURES, load_matches
from draft_features import DraftInteractions
from train import metrics, pipeline


def main():
    frame = load_matches(ROOT / 'data/dota2Train.csv')
    X, y = frame[FEATURES], frame.win.eq(1).astype(int)
    groups = pd.util.hash_pandas_object(X, index=False)
    fit, val = next(GroupShuffleSplit(n_splits=1, test_size=.2, random_state=42).split(X, y, groups))
    candidates = {}
    for leaves, depth, reg in [(7, 3, 10.), (15, 5, 20.), (31, 6, 30.)]:
        candidates[f'hist_{leaves}'] = pipeline(HistGradientBoostingClassifier(
            max_iter=400, learning_rate=.05, max_leaf_nodes=leaves, max_depth=depth,
            l2_regularization=reg, early_stopping=True, random_state=42))
    for scale in [1., 10.]:
        for c in ([.001, .01, .1, 1.] if scale == 1 else [.0003, .001, .003, .01]):
            name = f'pairs_scale{scale}_c{c}'
            candidates[name] = Pipeline([('features', DraftInteractions(main_scale=scale)),
                                        ('classifier', LogisticRegression(C=c, max_iter=500, random_state=42))])
    for alpha in [1., 10.]:
        candidates[f'mlp_alpha{alpha}'] = pipeline(MLPClassifier(
            hidden_layer_sizes=(64, 32), alpha=alpha, batch_size=512, max_iter=100,
            early_stopping=True, n_iter_no_change=8, random_state=42))
    scores = []
    with threadpool_limits(limits=4):
        for name, model in candidates.items():
            started = time.time()
            model.fit(X.iloc[fit], y.iloc[fit])
            result = {'model': name, **metrics(y.iloc[val], model.predict_proba(X.iloc[val])[:, 1]), 'seconds': time.time() - started}
            scores.append(result)
            print(json.dumps(result), flush=True)
    (ROOT / 'models/research_search.json').write_text(json.dumps(scores, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
