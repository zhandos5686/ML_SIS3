import copy
import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from common import ROOT
from early_features import from_raw, payload_to_frame, INPUT_FIELDS
from main import create_app
from train_early import chronological_parts


@pytest.fixture
def early_client():
    with TestClient(create_app()) as client:
        yield client


def example(client):
    return copy.deepcopy(client.get('/early/metadata').json()['examples'][0])


def test_final_outcomes_cannot_change_early_features():
    raw = pd.read_csv(ROOT / 'data/early/features.csv', nrows=3)
    changed = raw.copy()
    for field in ['radiant_win', 'duration', 'tower_status_radiant', 'tower_status_dire', 'barracks_status_radiant', 'barracks_status_dire', 'match_id', 'start_time']:
        changed[field] = 999999
    pd.testing.assert_frame_equal(from_raw(raw), from_raw(changed))
    assert not any('status' in c or 'win' in c or 'duration' in c for c in INPUT_FIELDS)


def test_api_snapshot_uses_same_aggregates_as_training(early_client):
    payload = example(early_client)
    raw = pd.read_csv(ROOT / 'data/early/features.csv').sort_values(['start_time', 'match_id']).head(1)
    expected = from_raw(raw).reset_index(drop=True)
    pd.testing.assert_frame_equal(payload_to_frame(payload), expected)
    result = early_client.post('/predict/early', json=payload)
    assert result.status_code == 200
    result = result.json()
    bundle = joblib.load(ROOT / 'models/early_model.joblib')
    p = bundle['model'].predict_proba(expected)[0, 1]
    assert result['radiant_probability'] == pytest.approx(p)
    assert result['radiant_probability'] + result['dire_probability'] == pytest.approx(1.)
    assert result['snapshot_seconds'] == 300
    assert early_client.get('/early/health').status_code == 200


@pytest.mark.parametrize('kind', ['negative', 'missing', 'float_count', 'duplicate', 'unknown', 'wrong_size', 'late', 'outcome'])
def test_invalid_early_snapshots_rejected(early_client, kind):
    payload = example(early_client)
    if kind == 'negative': payload['radiant']['gold'] = -1
    if kind == 'missing': payload['dire'].pop('xp')
    if kind == 'float_count': payload['radiant']['kills'] = 1.5
    if kind == 'duplicate': payload['radiant']['heroes'][0] = payload['dire']['heroes'][0]
    if kind == 'unknown': payload['radiant']['heroes'][0] = 999
    if kind == 'wrong_size': payload['radiant']['heroes'].pop()
    if kind == 'late': payload['snapshot_seconds'] = 301
    if kind == 'outcome': payload['radiant_win'] = 1
    assert early_client.post('/predict/early', json=payload).status_code == 422


def test_chronological_partition_has_no_match_overlap():
    raw = pd.DataFrame({'match_id': range(20), 'start_time': list(range(20))[::-1]})
    ordered, fit_end, val_end = chronological_parts(raw)
    assert fit_end == 14 and val_end == 17
    assert ordered.iloc[fit_end - 1].start_time <= ordered.iloc[fit_end].start_time
    assert ordered.iloc[val_end - 1].start_time <= ordered.iloc[val_end].start_time
    assert set(ordered.iloc[:fit_end].match_id).isdisjoint(ordered.iloc[val_end:].match_id)
    raw.loc[1, 'match_id'] = 0
    with pytest.raises(ValueError): chronological_parts(raw)


def test_missing_early_model_is_explicit(tmp_path):
    with TestClient(create_app(early_model_path=tmp_path / 'absent.joblib')) as client:
        assert client.get('/early/metadata').status_code == 503
        assert client.get('/early/health').status_code == 503
        assert client.get('/health').status_code == 200
