import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from common import FEATURES, ROOT, encode_draft, load_matches
from main import create_app


def test_feature_encoding_matches_csv():
    data = load_matches(ROOT / 'data/dota2Test.csv').iloc[0]
    a = [i for i in range(1, 114) if data[f'hero_{i}'] == 1]
    b = [i for i in range(1, 114) if data[f'hero_{i}'] == -1]
    row = encode_draft(a, b, int(data.game_mode), int(data.game_type))
    np.testing.assert_array_equal(row.iloc[0].to_numpy(), data[FEATURES].to_numpy())


@pytest.fixture
def client():
    with TestClient(create_app()) as c:
        yield c


def payload():
    return {'team_a': [1, 2, 3, 4, 5], 'team_b': [6, 7, 8, 9, 10], 'game_mode': 2, 'game_type': 2}


def test_real_model_http_roundtrip(client):
    assert client.get('/health').status_code == 200
    assert client.get('/docs').status_code == 200
    assert client.get('/openapi.json').status_code == 200
    result = client.post('/predict', json=payload())
    assert result.status_code == 200
    result = result.json()
    assert 0 <= result['team_a_probability'] <= 1
    assert result['team_a_probability'] + result['team_b_probability'] == pytest.approx(1.)
    bundle = joblib.load(ROOT / 'models/model.joblib')
    row = encode_draft([1,2,3,4,5], [6,7,8,9,10], 2, 2)
    assert result['team_a_probability'] == pytest.approx(bundle['model'].predict_proba(row)[0, 1])


@pytest.mark.parametrize('update', [
    {'team_a': [1, 1, 3, 4, 5]}, {'team_b': [1, 7, 8, 9, 10]},
    {'team_a': [1, 2]}, {'team_a': [1, 2, 3, 4, 999]},
    {'team_a': [1, 2, 3, 4, 108]}, {'game_mode': 999},
    {'game_type': 999}, {'team_a': [True, 2, 3, 4, 5]},
    {'game_mode': '2'}, {'extra': 'invalid'},
])
def test_invalid_drafts_rejected(client, update):
    assert client.post('/predict', json={**payload(), **update}).status_code == 422


def test_missing_model_stays_observable(tmp_path):
    with TestClient(create_app(tmp_path / 'absent.joblib')) as c:
        assert c.get('/').status_code == 200
        assert c.get('/').json()['model_loaded'] is False
        assert c.get('/health').status_code == 503
        assert c.post('/predict', json=payload()).status_code == 503


def test_metadata_has_only_observed_heroes(client):
    meta = client.get('/metadata').json()
    assert 24 not in meta['active_hero_ids']
    assert 108 not in meta['active_hero_ids']
    assert len(meta['heroes']) == len(meta['active_hero_ids'])
    assert meta['test_rows'] == 10294
