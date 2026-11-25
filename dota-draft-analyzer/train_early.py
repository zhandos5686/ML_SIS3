"""Chronological draft-vs-minute-five comparison on one labeled dataset."""
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
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_limits
from common import ROOT
from early_features import EarlyFeatures, HERO_FIELDS, INPUT_FIELDS, from_raw, frame_to_payload, NOTE
from train import metrics


def chronological_parts(raw):
    if raw.match_id.duplicated().any():
        raise ValueError('Repeated match IDs are not allowed across partitions')
    ordered = raw.sort_values(['start_time', 'match_id']).reset_index(drop=True)
    n = len(ordered)
    return ordered, int(n * .7), int(n * .85)


def make_model(estimator, stats):
    return Pipeline([('features', EarlyFeatures(include_stats=stats)), ('classifier', estimator)])


def main():
    path = ROOT / 'data/early/features.csv'
    raw = pd.read_csv(path)
    if not raw.radiant_win.isin([0, 1]).all():
        raise ValueError('Invalid radiant_win target')
    raw, fit_end, validation_end = chronological_parts(raw)
    X, y = from_raw(raw), raw.radiant_win.astype(int)
    fit, val, test = slice(0, fit_end), slice(fit_end, validation_end), slice(validation_end, len(raw))
    # Final outcome, duration and building states never enter INPUT_FIELDS.
    specs = {
        'baseline': (DummyClassifier(strategy='prior'), False),
        'draft_logistic_c01': (LogisticRegression(C=.1, max_iter=500, random_state=42), False),
        'draft_logistic_c1': (LogisticRegression(C=1., max_iter=500, random_state=42), False),
        'early_logistic_c001': (LogisticRegression(C=.01, max_iter=500, random_state=42), True),
        'early_logistic_c01': (LogisticRegression(C=.1, max_iter=500, random_state=42), True),
        'early_logistic_c1': (LogisticRegression(C=1., max_iter=500, random_state=42), True),
        'early_boost_15': (HistGradientBoostingClassifier(max_iter=250, learning_rate=.05, max_leaf_nodes=15, l2_regularization=10., early_stopping=False, random_state=42), True),
        'early_boost_31': (HistGradientBoostingClassifier(max_iter=250, learning_rate=.05, max_leaf_nodes=31, l2_regularization=20., early_stopping=False, random_state=42), True),
    }
    (ROOT / 'tracking').mkdir(exist_ok=True)
    mlflow.set_tracking_uri(os.getenv('MLFLOW_TRACKING_URI', f'sqlite:///{(ROOT / "tracking/mlflow.db").as_posix()}'))
    mlflow.set_experiment('Dota Minute Five')
    scores = []
    with threadpool_limits(limits=4):
        for name, (estimator, stats) in specs.items():
            with mlflow.start_run(run_name=f'validation_{name}'):
                model = make_model(estimator, stats).fit(X.iloc[fit], y.iloc[fit])
                result = metrics(y.iloc[val], model.predict_proba(X.iloc[val])[:, 1])
                mlflow.log_params({'candidate': name, 'include_stats': stats, 'split': 'chronological_70_15_15', **estimator.get_params()})
                mlflow.log_metrics({f'validation_{k}': v for k, v in result.items()})
                scores.append({'model': name, **result})
                print(name, result, flush=True)
        early_name = max((r for r in scores if r['model'].startswith('early_')), key=lambda r: r['roc_auc'])['model']
        draft_name = max((r for r in scores if r['model'].startswith('draft_')), key=lambda r: r['roc_auc'])['model']
        champion = make_model(*specs[early_name]).fit(X.iloc[:validation_end], y.iloc[:validation_end])
        draft = make_model(*specs[draft_name]).fit(X.iloc[:validation_end], y.iloc[:validation_end])
        # The same final temporal holdout is evaluated only after both choices are fixed.
        probability = champion.predict_proba(X.iloc[test])[:, 1]
        draft_probability = draft.predict_proba(X.iloc[test])[:, 1]
    report = {
        'selected_model': early_name, 'draft_comparator': draft_name,
        'train_rows': validation_end, 'fit_rows': fit_end, 'validation_rows': validation_end - fit_end, 'test_rows': len(raw) - validation_end,
        'split': '70/15/15 by provided start_time, then match_id; final refit on first 85%',
        'split_dates': {name: pd.to_datetime(int(raw.iloc[idx].start_time), unit='s', utc=True).isoformat() for name, idx in [('fit_start', 0), ('validation_start', fit_end), ('test_start', validation_end), ('test_end', len(raw)-1)]},
        'selection_metric': 'validation ROC AUC', 'validation': scores,
        'test_metrics': metrics(y.iloc[test], probability), 'draft_test_metrics': metrics(y.iloc[test], draft_probability),
        'baseline_test_metrics': metrics(y.iloc[test], np.full(len(raw) - validation_end, y.iloc[:validation_end].mean())),
        'confusion_matrix': confusion_matrix(y.iloc[test], probability >= .5, labels=[0, 1]).tolist(),
        'active_hero_ids': sorted(set(X.iloc[:validation_end][HERO_FIELDS].to_numpy(dtype=int).ravel().tolist())),
        'snapshot_seconds': 300, 'input_columns': INPUT_FIELDS,
        'source': json.loads((ROOT / 'data/early/SOURCE.json').read_text(encoding='utf-8')),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'note': NOTE, 'trained_at': datetime.now(timezone.utc).isoformat(),
        'examples': [frame_to_payload(X.iloc[i]) for i in [0, fit_end // 2, fit_end - 1]],
        'comparison_note': 'Draft and minute-five models use identical matches/labels and identical holdout; not directly comparable to UCI 2016 accuracy.',
    }
    correct = (probability >= .5) == y.iloc[test].to_numpy()
    draft_correct = (draft_probability >= .5) == y.iloc[test].to_numpy()
    from scipy.stats import binomtest
    won, lost = int((correct & ~draft_correct).sum()), int((~correct & draft_correct).sum())
    report['paired_comparison'] = {'new_only_correct': won, 'draft_only_correct': lost,
        'accuracy_difference_pp': 100 * (correct.mean() - draft_correct.mean()),
        'mcnemar_exact_pvalue': binomtest(won, won + lost).pvalue if won + lost else 1.}
    with mlflow.start_run(run_name=f'final_{early_name}') as run:
        report['mlflow_run_id'] = run.info.run_id
        mlflow.log_params({'model': early_name, 'snapshot_seconds': 300, 'split': 'chronological_70_15_15', **specs[early_name][0].get_params()})
        mlflow.log_metrics({f'test_{k}': v for k, v in report['test_metrics'].items()})
        mlflow.log_metrics({f'draft_test_{k}': v for k, v in report['draft_test_metrics'].items()})
        info = mlflow.sklearn.log_model(champion, artifact_path='model', code_paths=[str(ROOT / 'early_features.py')],
            signature=infer_signature(X.head(), champion.predict(X.head())), input_example=X.head())
        version = mlflow.register_model(info.model_uri, 'DotaMinuteFiveClassifier')
        mlflow.MlflowClient().set_registered_model_alias('DotaMinuteFiveClassifier', 'champion', version.version)
        report.update(registry_name='DotaMinuteFiveClassifier', registry_version=version.version)
        joblib.dump({'model': champion, 'metadata': report}, ROOT / 'models/early_model.joblib', compress=3)
        (ROOT / 'models/early_metrics.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        mlflow.log_artifact(str(ROOT / 'models/early_metrics.json'))
        mlflow.log_artifact(str(ROOT / 'data/early/SOURCE.json'))
    print(json.dumps({'winner': early_name, 'test': report['test_metrics'], 'draft_test': report['draft_test_metrics'], 'paired': report['paired_comparison']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
