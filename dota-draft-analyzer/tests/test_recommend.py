import joblib
import numpy as np
import pytest
from fastapi.testclient import TestClient
from common import ROOT, encode_draft
from main import create_app
from recommend import explain, hero_strength


@pytest.fixture(scope='module')
def client():
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture(scope='module')
def model():
    return joblib.load(ROOT / 'models/model.joblib')['model']


def ask(client, **body):
    return client.post('/recommend', json=body)


def test_recommendations_are_free_ranked_and_deterministic(client):
    body = {'team_a': [1, 2, 3], 'team_b': [6, 7, 8, 9], 'side': 'team_a'}
    first = ask(client, **body).json()
    assert ask(client, **body).json() == first
    recs = first['recommendations']
    assert len(recs) == 5 and not first['exact']
    assert not {r['hero_id'] for r in recs} & {1, 2, 3, 6, 7, 8, 9}
    probs = [r['win_probability'] for r in recs]
    assert probs == sorted(probs, reverse=True) and all(0 < p < 1 for p in probs)
    assert recs[0]['delta'] > 0  # the best pick beats a random pick


def test_empty_draft_and_top_parameter(client):
    result = ask(client, team_a=[], team_b=[], top=3).json()
    assert len(result['recommendations']) == 3
    assert result['candidates'] == 111  # all active heroes


def test_last_pick_is_exact_model_probability(client, model):
    a, b = [1, 2, 3, 4], [6, 7, 8, 9, 10]
    result = ask(client, team_a=a, team_b=b, side='team_a').json()
    assert result['exact'] and result['samples'] == 1
    for rec in result['recommendations']:
        expected = model.predict_proba(encode_draft(a + [rec['hero_id']], b, 2, 2))[0, 1]
        assert rec['win_probability'] == pytest.approx(expected)


def test_team_b_last_pick_is_exact(client, model):
    a, b = [1, 2, 3, 4, 5], [6, 7, 8, 9]
    rec = ask(client, team_a=a, team_b=b, side='team_b').json()['recommendations'][0]
    expected = 1 - model.predict_proba(encode_draft(a, b + [rec['hero_id']], 2, 2))[0, 1]
    assert rec['win_probability'] == pytest.approx(expected)


def test_mirrored_draft_gives_same_ranking(client):
    for_a = ask(client, team_a=[1, 2], team_b=[6, 7, 8], side='team_a').json()['recommendations']
    for_b = ask(client, team_a=[6, 7, 8], team_b=[1, 2], side='team_b').json()['recommendations']
    assert [r['hero_id'] for r in for_a] == [r['hero_id'] for r in for_b]


@pytest.mark.parametrize('side', ['team_a', 'team_b'])
def test_explanation_matches_model_log_odds(model, side):
    """Linear model: swapping our last pick c -> r changes our log-odds by exactly
    strength(c) - strength(r) + pair effects(c) - pair effects(r)."""
    ours, theirs, c, r = [1, 2, 3, 4], [6, 7, 8, 9, 10], 14, 50
    def draft(pick):
        return encode_draft(ours + [pick], theirs, 2, 2) if side == 'team_a' else encode_draft(theirs, ours + [pick], 2, 2)
    sign = 1 if side == 'team_a' else -1
    actual = sign * (model.decision_function(draft(c))[0] - model.decision_function(draft(r))[0])
    def total(h):
        return hero_strength(model, h) + sum(x['effect'] for x in explain(model, ours, theirs, h, side))
    assert actual == pytest.approx(total(c) - total(r))


@pytest.mark.parametrize('body', [
    {'team_a': [1, 2, 3, 4, 5], 'team_b': [], 'side': 'team_a'},   # team already full
    {'team_a': [1, 2], 'team_b': [2], 'side': 'team_a'},             # duplicate hero
    {'team_a': [1, 999], 'team_b': [], 'side': 'team_a'},            # unknown hero
    {'team_a': [1, 108], 'team_b': [], 'side': 'team_a'},            # hero absent from Train
    {'team_a': [], 'team_b': [], 'side': 'radiant'},                 # bad side
    {'team_a': [], 'team_b': [], 'top': 11},                         # too many results
    {'team_a': [1, 2, 3, 4, 5, 6], 'team_b': []},                    # six heroes
    {'team_a': [], 'team_b': [], 'extra': 1},                        # unknown field
])
def test_invalid_requests_rejected(client, body):
    assert ask(client, **body).status_code == 422


def test_recommendations_explain_with_names(client):
    rec = ask(client, team_a=[1, 2, 3], team_b=[6, 7, 8, 9], side='team_a').json()['recommendations'][0]
    assert rec['name'] and isinstance(rec['hero_strength'], float)
    assert all(r['kind'] in {'ally', 'opponent'} and r['name'] for r in rec['reasons'])
    assert np.isfinite([r['effect'] for r in rec['reasons']]).all()
