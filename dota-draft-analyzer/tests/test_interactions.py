import numpy as np
from common import encode_draft
from draft_features import DraftInteractions


def test_swapping_teams_negates_hero_and_pair_effects():
    a, b = [1, 2, 3, 4, 5], [6, 7, 8, 9, 10]
    x = encode_draft(a, b, 2, 2)
    encoder = DraftInteractions(main_scale=10).fit(x)
    original = encoder.transform(x).toarray()[0]
    swapped = encoder.transform(encode_draft(b, a, 2, 2)).toarray()[0]
    context_width = sum(len(c) for c in encoder.context_.categories_)
    np.testing.assert_array_equal(original[:context_width], swapped[:context_width])
    np.testing.assert_array_equal(original[context_width:], -swapped[context_width:])
    assert encoder.transform(x).nnz == 57  # 2 context + 10 heroes + 20 ally pairs + 25 opponents


def test_pair_meaning_and_player_order_invariance():
    a, b = [1, 2, 3, 4, 5], [6, 7, 8, 9, 10]
    x = encode_draft(a, b, 2, 2)
    encoder = DraftInteractions().fit(x)
    original = encoder.transform(x).toarray()[0]
    np.testing.assert_array_equal(original, encoder.transform(encode_draft(a[::-1], b[::-1], 2, 2)).toarray()[0])
    ally_start = 2 + 113
    opponents_start = ally_start + 113 * 112 // 2
    assert original[ally_start] == 1  # heroes 1 and 2 together on A
    assert original[opponents_start + 4] == 1  # hero 1 on A versus hero 6 on B
    assert original[opponents_start] == 0  # heroes 1 and 2 are not opponents
