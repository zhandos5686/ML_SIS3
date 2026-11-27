"""A single feature contract for training and serving."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
HERO_COLUMNS = [f'hero_{i}' for i in range(1, 114)]
FEATURES = ['game_mode', 'game_type', *HERO_COLUMNS]
COLUMNS = ['win', 'cluster_id', *FEATURES]
HISTORICAL_NOTE = 'Data from 13 August 2016. The estimate does not reflect the current meta and does not guarantee the outcome.'


def load_matches(path):
    frame = pd.read_csv(path, header=None)
    if frame.shape[1] != len(COLUMNS):
        raise ValueError(f'{path}: expected 117 columns, got {frame.shape[1]}')
    frame.columns = COLUMNS
    if frame.isna().any().any() or not all(pd.api.types.is_numeric_dtype(t) for t in frame.dtypes):
        raise ValueError('Dataset must be numeric without missing values')
    if not np.equal(frame.to_numpy(), np.floor(frame.to_numpy())).all():
        raise ValueError('All values must be integers')
    heroes = frame[HERO_COLUMNS]
    if not frame.win.isin([-1, 1]).all() or not heroes.isin([-1, 0, 1]).all().all():
        raise ValueError('Invalid labels or hero encoding')
    if not ((heroes.eq(1).sum(axis=1) == 5) & (heroes.eq(-1).sum(axis=1) == 5)).all():
        raise ValueError('Every match must contain five heroes on each side')
    return frame.astype('int32')


def encode_draft(team_a, team_b, game_mode, game_type):
    row = dict.fromkeys(FEATURES, 0)
    row.update(game_mode=game_mode, game_type=game_type)
    for sign, team in [(1, team_a), (-1, team_b)]:
        for hero in team:
            row[f'hero_{hero}'] = sign
    return pd.DataFrame([row], columns=FEATURES).astype('int32')
