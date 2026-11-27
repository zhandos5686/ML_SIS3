"""API can serve the version that the MLflow Registry alias `champion` points to."""
import joblib
import mlflow
import pytest
from fastapi.testclient import TestClient
from common import ROOT, encode_draft
from main import create_app

DB = ROOT / 'tracking/mlflow.db'
pytestmark = pytest.mark.skipif(not DB.exists(), reason='Run train.py and train_early.py to create the local Registry')


def champion_version(name):
    mlflow.set_tracking_uri(f'sqlite:///{DB.as_posix()}')
    return str(mlflow.MlflowClient().get_model_version_by_alias(name, 'champion').version)


def test_api_serves_registry_champion():
    app = create_app(model_uri='models:/DotaDraftClassifier@champion',
                     early_model_uri='models:/DotaMinuteFiveClassifier@champion')
    with TestClient(app) as client:
        root = client.get('/').json()
        assert root['model_source'] == 'models:/DotaDraftClassifier@champion'
        assert root['early_model_source'] == 'models:/DotaMinuteFiveClassifier@champion'
        meta = client.get('/metadata').json()
        assert str(meta['registry_version']) == champion_version('DotaDraftClassifier')
        result = client.post('/predict', json={'team_a': [1, 2, 3, 4, 5], 'team_b': [6, 7, 8, 9, 10], 'game_mode': 2, 'game_type': 2})
        assert result.status_code == 200
        assert result.json()['model_version'] == champion_version('DotaDraftClassifier')
        early = client.get('/early/metadata').json()
        assert str(early['registry_version']) == champion_version('DotaMinuteFiveClassifier')
        assert client.post('/predict/early', json=early['examples'][0]).status_code == 200


def test_registry_and_exported_file_give_same_prediction():
    """After training, models/model.joblib is the same model as the champion version."""
    with TestClient(create_app(model_uri='models:/DotaDraftClassifier@champion')) as client:
        p = client.post('/predict', json={'team_a': [1, 2, 3, 4, 5], 'team_b': [6, 7, 8, 9, 10], 'game_mode': 2, 'game_type': 2}).json()
    local = joblib.load(ROOT / 'models/model.joblib')
    if str(local['metadata']['registry_version']) != p['model_version']:
        pytest.skip('Exported file and champion differ (alias was moved manually)')
    assert p['team_a_probability'] == pytest.approx(local['model'].predict_proba(encode_draft([1, 2, 3, 4, 5], [6, 7, 8, 9, 10], 2, 2))[0, 1])
