"""Allowlisted information available at minute 5, without final-match fields."""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import StandardScaler
from sklearn.utils.validation import check_is_fitted

STATS = ['gold', 'xp', 'lh', 'kills', 'deaths', 'level', 'items']
HERO_FIELDS = [f'{side}{i}_hero' for side in ['r', 'd'] for i in range(1, 6)]
STAT_FIELDS = [f'{side}_{stat}' for side in ['r', 'd'] for stat in STATS]
INPUT_FIELDS = HERO_FIELDS + STAT_FIELDS
NOTE = 'Prediction at 5:00 based on historical matches from 2015. All stats must refer to the first five minutes only.'


def from_raw(raw):
    """Ignore *all* columns except heroes and seven early stats per player."""
    out = raw[HERO_FIELDS].copy()
    for side in ['r', 'd']:
        for stat in STATS:
            out[f'{side}_{stat}'] = raw[[f'{side}{i}_{stat}' for i in range(1, 6)]].sum(axis=1, min_count=5)
    values = out.to_numpy(dtype=float)
    if not np.isfinite(values).all() or (out[STAT_FIELDS] < 0).any().any():
        raise ValueError('Early features must be finite and nonnegative')
    if not np.equal(values, np.floor(values)).all():
        raise ValueError('Hero IDs and aggregated counts must be integers')
    heroes = out[HERO_FIELDS].to_numpy(dtype=int)
    if (heroes < 1).any() or (heroes > 113).any() or any(len(set(row)) != 10 for row in heroes):
        raise ValueError('Expected ten different historical hero IDs')
    return out[INPUT_FIELDS].astype('float64')


def payload_to_frame(payload):
    row = {}
    for side, name in [('r', 'radiant'), ('d', 'dire')]:
        team = payload[name]
        row.update({f'{side}{i}_hero': hero for i, hero in enumerate(team['heroes'], 1)})
        row.update({f'{side}_{stat}': team[stat] for stat in STATS})
    return pd.DataFrame([row], columns=INPUT_FIELDS, dtype='float64')


def frame_to_payload(row):
    return {name: {'heroes': [int(row[f'{side}{i}_hero']) for i in range(1, 6)],
                   **{stat: int(row[f'{side}_{stat}']) for stat in STATS}}
            for side, name in [('r', 'radiant'), ('d', 'dire')]}


class EarlyFeatures(BaseEstimator, TransformerMixin):
    def __init__(self, include_stats=True):
        self.include_stats = include_stats

    def _numeric(self, X):
        totals = X[STAT_FIELDS].to_numpy(dtype=float)
        differences = X[[f'r_{s}' for s in STATS]].to_numpy() - X[[f'd_{s}' for s in STATS]].to_numpy()
        return np.column_stack([totals, differences])

    def fit(self, X, y=None):
        self.scaler_ = StandardScaler().fit(self._numeric(X)) if self.include_stats else None
        self.fitted_ = True
        return self

    def transform(self, X):
        check_is_fitted(self, 'fitted_')
        h = X[HERO_FIELDS].to_numpy(dtype=int)
        draft = np.zeros((len(X), 113), dtype=float)
        np.add.at(draft, (np.repeat(np.arange(len(X)), 10), h.ravel() - 1), np.tile([1.] * 5 + [-1.] * 5, len(X)))
        return np.column_stack([draft, self.scaler_.transform(self._numeric(X))]) if self.include_stats else draft
