"""HTTP serving; the trusted local model is loaded once during lifespan."""
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
from typing import Annotated, Literal
import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator
from common import ROOT, HISTORICAL_NOTE, encode_draft
from heroes import HEROES
from early_features import NOTE as EARLY_NOTE, payload_to_frame


class Draft(BaseModel):
    model_config = ConfigDict(extra='forbid', json_schema_extra={'example': {
        'team_a': [1, 2, 3, 4, 5], 'team_b': [6, 7, 8, 9, 10], 'game_mode': 2, 'game_type': 2,
    }})
    team_a: list[StrictInt] = Field(min_length=5, max_length=5)
    team_b: list[StrictInt] = Field(min_length=5, max_length=5)
    game_mode: StrictInt = 2
    game_type: StrictInt = 2

    @model_validator(mode='after')
    def unique_heroes(self):
        if len(set(self.team_a + self.team_b)) != 10:
            raise ValueError('Все 10 героев должны быть разными')
        return self


class Prediction(BaseModel):
    team_a_probability: float
    team_b_probability: float
    predicted_winner: str
    model_name: str
    model_version: str
    note: str


class EarlyTeam(BaseModel):
    model_config = ConfigDict(extra='forbid')
    heroes: list[StrictInt] = Field(min_length=5, max_length=5)
    gold: Annotated[StrictInt, Field(ge=0, le=2000000)]
    xp: Annotated[StrictInt, Field(ge=0, le=2000000)]
    lh: Annotated[StrictInt, Field(ge=0, le=10000)]
    kills: Annotated[StrictInt, Field(ge=0, le=500)]
    deaths: Annotated[StrictInt, Field(ge=0, le=500)]
    level: Annotated[StrictInt, Field(ge=0, le=150)]
    items: Annotated[StrictInt, Field(ge=0, le=2000)]


class EarlyRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    snapshot_seconds: Literal[300] = 300
    radiant: EarlyTeam
    dire: EarlyTeam

    @model_validator(mode='after')
    def unique_heroes(self):
        if len(set(self.radiant.heroes + self.dire.heroes)) != 10:
            raise ValueError('Все 10 героев должны быть разными')
        return self


def load_from_registry(uri, metrics_name):
    """Load models:/Name@alias or models:/Name/<version> plus the report logged in the same run."""
    import mlflow
    import mlflow.sklearn
    mlflow.set_tracking_uri(os.getenv('MLFLOW_TRACKING_URI', f'sqlite:///{(ROOT / "tracking/mlflow.db").as_posix()}'))
    client = mlflow.MlflowClient()
    ref = uri.removeprefix('models:/')
    if '@' in ref:
        name, alias = ref.split('@', 1)
        version = client.get_model_version_by_alias(name, alias)
    else:
        name, number = ref.split('/', 1)
        version = client.get_model_version(name, number)
    model = mlflow.sklearn.load_model(f'models:/{name}/{version.version}')
    report = mlflow.artifacts.download_artifacts(run_id=version.run_id, artifact_path=metrics_name)
    metadata = json.loads(Path(report).read_text(encoding='utf-8'))
    metadata.update(registry_name=name, registry_version=version.version, model_source=uri)
    return {'model': model, 'metadata': metadata}


def load_bundle(uri, path, metrics_name):
    if uri:
        return load_from_registry(uri, metrics_name)
    if not path.exists():
        return None
    bundle = joblib.load(path)
    bundle['metadata'].setdefault('model_source', str(path.name))
    return bundle


def create_app(model_path=None, early_model_path=None, model_uri=None, early_model_uri=None):
    path = Path(model_path or os.getenv('MODEL_PATH', str(ROOT / 'models/model.joblib')))
    early_path = Path(early_model_path or os.getenv('EARLY_MODEL_PATH', str(ROOT / 'models/early_model.joblib')))
    # Optional: serve the version the Registry alias points to, e.g. models:/DotaDraftClassifier@champion.
    uri = model_uri or os.getenv('MODEL_URI')
    early_uri = early_model_uri or os.getenv('EARLY_MODEL_URI')

    @asynccontextmanager
    async def lifespan(app):
        app.state.bundle = load_bundle(uri, path, 'metrics.json')
        app.state.early_bundle = load_bundle(early_uri, early_path, 'early_metrics.json')
        yield
        app.state.bundle = None
        app.state.early_bundle = None

    app = FastAPI(title='Dota Match Analyzer', version='2.0.0', lifespan=lifespan,
                  description='Historical draft predictor (2016) and independent minute-five Radiant/Dire predictor (2015).')

    def bundle():
        if app.state.bundle is None:
            raise HTTPException(503, 'Модель не найдена. Запустите python train.py и перезапустите API.')
        return app.state.bundle

    def early_bundle():
        if app.state.early_bundle is None:
            raise HTTPException(503, 'Модель пятой минуты не найдена. Запустите python train_early.py и перезапустите API.')
        return app.state.early_bundle

    @app.get('/')
    def root():
        source = lambda b: b['metadata'].get('model_source') if b else None
        return {'message': 'ML API is running', 'model_loaded': app.state.bundle is not None, 'early_model_loaded': app.state.early_bundle is not None,
                'model_source': source(app.state.bundle), 'early_model_source': source(app.state.early_bundle)}

    @app.get('/health')
    def health():
        bundle()
        return {'status': 'ready'}

    @app.get('/metadata')
    def metadata():
        meta = bundle()['metadata']
        return {**meta, 'heroes': [{'id': i, 'name': HEROES.get(i, f'Hero {i}')} for i in meta['active_hero_ids']], 'note': HISTORICAL_NOTE}

    @app.get('/early/metadata')
    def early_metadata():
        meta = early_bundle()['metadata']
        return {**meta, 'heroes': [{'id': i, 'name': HEROES.get(i, f'Hero {i}')} for i in meta['active_hero_ids']]}

    @app.get('/early/health')
    def early_health():
        early_bundle()
        return {'status': 'ready', 'snapshot_seconds': 300}

    @app.post('/predict/early')
    def predict_early(snapshot: EarlyRequest):
        loaded = early_bundle()
        meta = loaded['metadata']
        if not set(snapshot.radiant.heroes + snapshot.dire.heroes).issubset(meta['active_hero_ids']):
            raise HTTPException(422, 'Герой отсутствует в датасете первых пяти минут. См. /early/metadata.')
        row = payload_to_frame(snapshot.model_dump())
        probability = float(loaded['model'].predict_proba(row)[0, 1])
        return {'radiant_probability': probability, 'dire_probability': 1 - probability,
                'predicted_winner': 'radiant' if probability >= .5 else 'dire',
                'snapshot_seconds': 300, 'model_name': meta['selected_model'],
                'model_version': str(meta['registry_version']), 'note': EARLY_NOTE}

    @app.post('/predict', response_model=Prediction)
    def predict(draft: Draft):
        loaded = bundle()
        meta = loaded['metadata']
        if not set(draft.team_a + draft.team_b).issubset(meta['active_hero_ids']):
            raise HTTPException(422, 'Герой отсутствует в обучающем датасете. См. /metadata.')
        if draft.game_mode not in meta['game_modes'] or draft.game_type not in meta['game_types']:
            raise HTTPException(422, 'Неизвестный режим или тип игры. См. /metadata.')
        row = encode_draft(draft.team_a, draft.team_b, draft.game_mode, draft.game_type)
        p = float(loaded['model'].predict_proba(row)[0, 1])
        return Prediction(team_a_probability=p, team_b_probability=1-p,
                          predicted_winner='team_a' if p >= .5 else 'team_b',
                          model_name=meta['selected_model'], model_version=str(meta['registry_version']), note=HISTORICAL_NOTE)

    return app


app = create_app()
