"""Sparse hero synergy and counterpick features, computed without outcomes."""
import numpy as np
from scipy import sparse
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import OneHotEncoder
from sklearn.utils.validation import check_is_fitted
from common import HERO_COLUMNS


class DraftInteractions(BaseEstimator, TransformerMixin):
    """113 main effects + signed ally pairs + antisymmetric opponent pairs.

    Swapping teams negates every hero-derived feature. Context is unchanged.
    No win rates or labels are used to build features.
    """
    def __init__(self, main_scale=1.):
        self.main_scale = main_scale

    def fit(self, X, y=None):
        self.context_ = OneHotEncoder(handle_unknown='ignore', sparse_output=True)
        self.context_.fit(X[['game_mode', 'game_type']])
        return self

    def transform(self, X):
        check_is_fitted(self, 'context_')
        h = X[HERO_COLUMNS].to_numpy(dtype=np.float64)
        n, width = h.shape
        if not ((h == 1).sum(axis=1) == 5).all() or not ((h == -1).sum(axis=1) == 5).all():
            raise ValueError('Interaction features require complete 5v5 drafts')
        a = np.where(h == 1)[1].reshape(n, 5)
        b = np.where(h == -1)[1].reshape(n, 5)
        pair_count = width * (width - 1) // 2

        def pair_id(i, j):
            low, high = np.minimum(i, j), np.maximum(i, j)
            return low * (2 * width - low - 1) // 2 + high - low - 1

        i, j = np.triu_indices(5, k=1)
        ally_cols = np.concatenate([pair_id(a[:, i], a[:, j]), pair_id(b[:, i], b[:, j])], axis=1)
        ally_values = np.broadcast_to(np.r_[np.ones(10), -np.ones(10)], (n, 20))
        allies = sparse.csr_matrix((ally_values.ravel(), (np.repeat(np.arange(n), 20), ally_cols.ravel())), shape=(n, pair_count))
        ai, bi = a[:, :, None], b[:, None, :]
        opponent_cols = pair_id(ai, bi).reshape(n, 25)
        opponent_values = np.where(ai < bi, 1., -1.).reshape(n, 25)
        opponents = sparse.csr_matrix((opponent_values.ravel(), (np.repeat(np.arange(n), 25), opponent_cols.ravel())), shape=(n, pair_count))
        return sparse.hstack([self.context_.transform(X[['game_mode', 'game_type']]) * self.main_scale, sparse.csr_matrix(h * self.main_scale), allies, opponents], format='csr')
