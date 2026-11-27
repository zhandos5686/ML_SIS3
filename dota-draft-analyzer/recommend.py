"""Pick advisor on top of the trained draft model; no retraining.

For every free hero the model scores the draft "as if we pick it". Empty slots are
filled with random free heroes (Monte Carlo) and the probabilities are averaged.
All candidates share the same random fill-ins, so their differences are less noisy.
When the candidate completes the draft, the answer is exact.
"""
import numpy as np
import pandas as pd
from common import FEATURES

N_HEROES = 113


def _pair_id(i, j):
    """Same pair indexing as draft_features.DraftInteractions (0-based hero columns)."""
    low, high = min(i, j), max(i, j)
    return low * (2 * N_HEROES - low - 1) // 2 + high - low - 1


def _rows(teams_a, teams_b, game_mode, game_type):
    matrix = np.zeros((len(teams_a), len(FEATURES)), dtype=np.int32)
    matrix[:, 0], matrix[:, 1] = game_mode, game_type
    offset = FEATURES.index('hero_1')  # 0-based hero index i lives in column offset + i
    for row, (a, b) in enumerate(zip(teams_a, teams_b)):
        matrix[row, [offset + h for h in a]] = 1
        matrix[row, [offset + h for h in b]] = -1
    return pd.DataFrame(matrix, columns=FEATURES)


def hero_strength(model, candidate):
    """The hero's own main effect in log-odds for the team that picks it (same for A and B)."""
    features, classifier = model.named_steps['features'], model.named_steps['classifier']
    if not hasattr(features, 'main_scale') or not hasattr(classifier, 'coef_'):
        return None
    start = sum(len(c) for c in features.context_.categories_)
    return float(features.main_scale * classifier.coef_[0][start + candidate - 1])


def explain(model, ours, theirs, candidate, side):
    """Model reasons for a pick: synergy with picked allies, match-ups against picked enemies.
    Effects are in log-odds for our side; available only for the pairwise logistic model."""
    features, classifier = model.named_steps['features'], model.named_steps['classifier']
    if not hasattr(features, 'main_scale') or not hasattr(classifier, 'coef_'):
        return []
    coef = classifier.coef_[0]
    pairs = N_HEROES * (N_HEROES - 1) // 2
    start = sum(len(c) for c in features.context_.categories_) + N_HEROES
    ally_w, opp_w = coef[start:start + pairs], coef[start + pairs:start + 2 * pairs]
    c = candidate - 1
    reasons = [{'hero_id': h, 'kind': 'ally', 'effect': float(ally_w[_pair_id(c, h - 1)])} for h in ours]
    for h in theirs:
        a, b = (c, h - 1) if side == 'team_a' else (h - 1, c)
        value = 1. if a < b else -1.  # sign convention of DraftInteractions
        effect = value * opp_w[_pair_id(a, b)]
        reasons.append({'hero_id': h, 'kind': 'opponent', 'effect': float(effect if side == 'team_a' else -effect)})
    return sorted(reasons, key=lambda r: -abs(r['effect']))


def recommend(model, team_a, team_b, side, active_ids, game_mode=2, game_type=2, samples=50, top=5, seed=42):
    ours, theirs = (team_a, team_b) if side == 'team_a' else (team_b, team_a)
    if len(ours) >= 5:
        raise ValueError('This team already has five heroes')
    picked = set(team_a) | set(team_b)
    free = [h for h in sorted(active_ids) if h not in picked]
    need_ours, need_theirs = 4 - len(ours), 5 - len(theirs)
    exact = need_ours == 0 and need_theirs == 0
    samples = 1 if exact else samples
    rng = np.random.default_rng(seed)
    orders = [rng.permutation(free) for _ in range(samples)]  # shared across candidates

    rows_a, rows_b = [], []
    for candidate in free:
        for order in orders:
            fill = [int(h) for h in order if h != candidate][:need_ours + need_theirs]
            full_ours = [*ours, candidate, *fill[:need_ours]]
            full_theirs = [*theirs, *fill[need_ours:]]
            a, b = (full_ours, full_theirs) if side == 'team_a' else (full_theirs, full_ours)
            rows_a.append([h - 1 for h in a])
            rows_b.append([h - 1 for h in b])
    p_a = model.predict_proba(_rows(rows_a, rows_b, game_mode, game_type))[:, 1]
    p = (p_a if side == 'team_a' else 1 - p_a).reshape(len(free), samples).mean(axis=1)
    baseline = float(p.mean())  # expected chance if the next pick were random
    best = np.argsort(-p)[:top]
    return {
        'side': side, 'exact': exact, 'samples': samples, 'candidates': len(free),
        'random_pick_probability': baseline,
        'recommendations': [{'hero_id': int(free[i]), 'win_probability': float(p[i]), 'delta': float(p[i] - baseline),
                             'hero_strength': hero_strength(model, int(free[i])),
                             'reasons': explain(model, ours, theirs, int(free[i]), side)[:2]} for i in best],
    }
