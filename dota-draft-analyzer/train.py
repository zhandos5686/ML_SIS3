"""Compare on a validation split, refit winner, evaluate official test once."""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from mlflow.models import infer_signature
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, confusion_matrix, f1_score, log_loss, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from common import ROOT, FEATURES, HERO_COLUMNS, load_matches
from draft_features import DraftInteractions

SEED = 42


def metrics(y, p):
    pred = (p >= .5).astype(int)
    return {name: float(value) for name, value in {
        'accuracy': accuracy_score(y, pred), 'f1': f1_score(y, pred, zero_division=0),
        'precision': precision_score(y, pred, zero_division=0),
        'recall': recall_score(y, pred, zero_division=0), 'roc_auc': roc_auc_score(y, p),
        'log_loss': log_loss(y, p, labels=[0, 1]), 'brier_score': brier_score_loss(y, p),
    }.items()}


def log_evaluation_plots(y, p, labels, prefix=''):
    """ROC curve and confusion matrix of the final holdout as PNG artifacts of the active run."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from sklearn.metrics import ConfusionMatrixDisplay, RocCurveDisplay
    roc = RocCurveDisplay.from_predictions(y, p, name='model')
    roc.ax_.plot([0, 1], [0, 1], linestyle='--', color='grey', label='random (AUC = 0.5)')
    roc.ax_.legend(loc='lower right')
    roc.ax_.set_title('ROC curve, test')
    mlflow.log_figure(roc.figure_, f'plots/{prefix}roc_curve.png')
    plt.close(roc.figure_)
    cm = ConfusionMatrixDisplay.from_predictions(y, (p >= .5).astype(int), display_labels=labels, cmap='Blues', values_format='d')
    cm.ax_.set_title('Confusion matrix, test (threshold 0.5)')
    mlflow.log_figure(cm.figure_, f'plots/{prefix}confusion_matrix.png')
    plt.close(cm.figure_)


def pipeline(model, interactions=False):
    if interactions:
        return Pipeline([('features', DraftInteractions(main_scale=10.)), ('classifier', model)])
    return Pipeline([
        ('features', ColumnTransformer([
            ('context', OneHotEncoder(handle_unknown='ignore', sparse_output=False), ['game_mode', 'game_type']),
            ('draft', 'passthrough', HERO_COLUMNS),
        ])), ('classifier', model),
    ])


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'data')
    parser.add_argument('--forest-trees', type=int, default=160)
    parser.add_argument('--extended', action='store_true', default=True, help='Include pair features (default)')
    parser.add_argument('--basic', action='store_false', dest='extended', help='Reproduce the original individual-hero experiment')
    args = parser.parse_args()
    model_dir = ROOT / 'models'
    model_dir.mkdir(exist_ok=True)
    tracking_dir = ROOT / 'tracking'
    tracking_dir.mkdir(exist_ok=True)
    mlflow.set_tracking_uri(os.getenv('MLFLOW_TRACKING_URI', f'sqlite:///{(tracking_dir / "mlflow.db").as_posix()}'))
    mlflow.set_experiment('Dota Draft Analyzer')
    train_path = args.data_dir / 'dota2Train.csv'
    test_path = args.data_dir / 'dota2Test.csv'
    train = load_matches(train_path)
    # Identical drafts/context stay together even if labels disagree.
    X, y = train[FEATURES], train.win.eq(1).astype(int)
    hashes = pd.util.hash_pandas_object(X, index=False)
    fit_idx, val_idx = next(GroupShuffleSplit(n_splits=1, test_size=.2, random_state=SEED).split(X, y, groups=hashes))
    X_fit, X_val, y_fit, y_val = X.iloc[fit_idx], X.iloc[val_idx], y.iloc[fit_idx], y.iloc[val_idx]
    candidates = {
        'baseline': DummyClassifier(strategy='prior'),
        'logistic_c01': LogisticRegression(C=.1, max_iter=500, random_state=SEED),
        'logistic_c1': LogisticRegression(C=1., max_iter=500, random_state=SEED),
        'random_forest': RandomForestClassifier(n_estimators=args.forest_trees, max_depth=22, min_samples_leaf=5, n_jobs=-1, random_state=SEED),
    }
    if args.extended:
        for c in [.0003, .001, .003, .01]:
            candidates[f'pairwise_c{c}'] = LogisticRegression(C=c, max_iter=500, random_state=SEED)
    scores = []
    for name, estimator in candidates.items():
        with mlflow.start_run(run_name=f'validation_{name}'):
            interactions = name.startswith('pairwise_')
            fitted = pipeline(estimator, interactions=interactions).fit(X_fit, y_fit)
            result = metrics(y_val, fitted.predict_proba(X_val)[:, 1])
            mlflow.log_params({'candidate': name, 'seed': SEED, 'feature_encoding': 'signed_pairs_main_scale_10' if interactions else 'individual_heroes', 'fit_rows': len(fit_idx), 'validation_rows': len(val_idx), **estimator.get_params()})
            mlflow.log_metrics({f'validation_{k}': v for k, v in result.items()})
            scores.append({'model': name, **result})
            print(name, result, flush=True)
    # ROC AUC only on validation selects the champion, never official test.
    winner = max(scores, key=lambda r: r['roc_auc'])['model']
    champion = pipeline(candidates[winner], interactions=winner.startswith('pairwise_')).fit(X, y)
    test = load_matches(test_path)
    X_test, y_test = test[FEATURES], test.win.eq(1).astype(int)
    p = champion.predict_proba(X_test)[:, 1]
    test_metrics = metrics(y_test, p)
    active = [i for i in range(1, 114) if train[f'hero_{i}'].ne(0).any()]
    overlap = pd.util.hash_pandas_object(X_test, index=False).isin(set(hashes))
    report = {
        'selected_model': winner, 'selection_metric': 'validation ROC AUC',
        'feature_encoding': 'signed_pairs_main_scale_10' if winner.startswith('pairwise_') else 'individual_heroes',
        'extended_search': args.extended,
        'train_rows': len(train), 'fit_rows': len(fit_idx), 'validation_rows': len(val_idx), 'test_rows': len(test),
        'validation': scores, 'test_metrics': test_metrics,
        'baseline_test_metrics': metrics(y_test, np.full(len(test), y.mean())),
        'confusion_matrix': confusion_matrix(y_test, p >= .5, labels=[0, 1]).tolist(),
        'test_feature_overlap_rows': int(overlap.sum()),
        'test_nonoverlap_metrics': metrics(y_test[~overlap], p[~overlap]) if (~overlap).any() and y_test[~overlap].nunique() == 2 else None,
        'sha256': {path.name: digest(path) for path in [train_path, test_path]},
        'trained_at': datetime.now(timezone.utc).isoformat(), 'dataset_date': '2016-08-13',
        'active_hero_ids': active, 'game_modes': sorted(train.game_mode.unique().tolist()),
        'game_types': sorted(train.game_type.unique().tolist()), 'feature_columns': FEATURES,
    }
    with mlflow.start_run(run_name=f'final_{winner}') as run:
        report['mlflow_run_id'] = run.info.run_id
        mlflow.log_params({'model': winner, 'train_rows': len(train), 'test_rows': len(test), 'seed': SEED, **candidates[winner].get_params()})
        mlflow.log_metrics({f'test_{k}': v for k, v in test_metrics.items()})
        mlflow.set_tags({'dataset': 'UCI Dota2 Games Results', 'dataset_date': '2016-08-13', 'selection': 'validation only'})
        log_evaluation_plots(y_test, p, labels=['B wins', 'A wins'])
        info = mlflow.sklearn.log_model(champion, artifact_path='model', code_paths=[str(ROOT / 'draft_features.py'), str(ROOT / 'common.py')], signature=infer_signature(X.head(), champion.predict(X.head())), input_example=X.head())
        version = mlflow.register_model(info.model_uri, 'DotaDraftClassifier')
        mlflow.MlflowClient().set_registered_model_alias('DotaDraftClassifier', 'champion', version.version)
        report['registry_name'] = 'DotaDraftClassifier'
        report['registry_version'] = version.version
        joblib.dump({'model': champion, 'metadata': report}, model_dir / 'model.joblib', compress=3)
        (model_dir / 'metrics.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        mlflow.log_artifact(str(model_dir / 'metrics.json'))
        mlflow.log_artifact(str(model_dir / 'model.joblib'))
    print(json.dumps({'winner': winner, 'test': test_metrics, 'version': report['registry_version']}, indent=2))


if __name__ == '__main__':
    main()
