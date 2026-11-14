"""T218 refinement R2 — lexicographic tie-break with tolerance band.

Acceptance: solver noise (~1e-15) below the declared ε_tie = 1e-12
cannot override the lexicographic rule among global minima; candidates
strictly outside the band can never win; determinism across runs.
"""

from __future__ import annotations

import numpy as np
import pytest

from q_speace.bridge.screening import (
    lexicographic_select,
    select_projection_tie_break,
)


def test_noise_below_band_cannot_override_lexicographic_rule() -> None:
    """Two global minima whose distances differ by 1e-15 (< ε_tie).

    A strict ``min()`` would pick A (distance 1.0 < 1.0 + 1e-15); the
    band rule collects both and the lexicographic rule picks B.
    """
    proposal = np.zeros(2)
    scale = np.ones(2)
    a = np.array([1.0, 0.0])  # distance exactly 1.0
    b = np.array([0.0, 1.0]) * (1.0 + 1e-15)  # distance 1.0 + ~1e-15
    picked = select_projection_tie_break([a, b], proposal, scale)
    assert np.allclose(picked, np.array([0.0, 1.0]), atol=1e-9)


def test_candidate_outside_band_never_wins() -> None:
    """A lexicographically tiny candidate far from the optimum is excluded."""
    proposal = np.zeros(2)
    scale = np.ones(2)
    near = np.array([0.0, 1.0])  # distance 1.0, lexicographically larger
    far_tiny = np.array([-9.0, 0.0])  # distance 9.0, lexicographically smaller
    picked = select_projection_tie_break([far_tiny, near], proposal, scale)
    assert np.array_equal(picked, near)


def test_strict_min_outside_band_is_still_picked() -> None:
    """When a single candidate is strictly closest by more than the band,
    it wins regardless of the lexicographic order."""
    proposal = np.zeros(2)
    scale = np.ones(2)
    closest = np.array([1.0, 1.0])  # weighted distance ~1.414
    lexicographic_but_far = np.array([0.0, 3.0])  # distance 3.0
    picked = select_projection_tie_break([lexicographic_but_far, closest], proposal, scale)
    assert np.allclose(picked, closest)


def test_band_is_exact_at_epsilon_boundary() -> None:
    """A candidate at distance d_min + epsilon_tie exactly is in band;
    d_min + 10*epsilon_tie is out."""
    proposal = np.zeros(2)
    scale = np.ones(2)
    a = np.array([1.0, 0.0])  # distance 1.0
    b = np.array([0.0, 1.0 + 1e-12])  # distance 1.0 + 1e-12 (exactly in band)
    picked = select_projection_tie_break([a, b], proposal, scale)
    assert np.allclose(picked, np.array([0.0, 1.0]), atol=1e-9)  # lexicographic wins
    c = np.array([0.0, 1.0 + 1e-11])  # 1e-11 above: outside the band
    picked2 = select_projection_tie_break([a, c], proposal, scale)
    assert np.allclose(picked2, a)


def test_weighted_scale_is_respected() -> None:
    proposal = np.zeros(2)
    scale = np.array([1.0, 2.0])
    a = np.array([2.0, 0.0])  # weighted distance 2.0
    b = np.array([0.0, 4.0])  # weighted distance 2.0
    picked = select_projection_tie_break([a, b], proposal, scale)
    assert np.array_equal(picked, b)  # tie → lexicographic picks b


def test_determinism_across_runs() -> None:
    proposal = np.zeros(2)
    scale = np.ones(2)
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0]) * (1.0 + 1e-15)
    r1 = select_projection_tie_break([a, b], proposal, scale)
    r2 = select_projection_tie_break([a, b], proposal, scale)
    assert np.array_equal(r1, r2)


def test_validation() -> None:
    with pytest.raises(ValueError):
        select_projection_tie_break([], np.zeros(2), np.ones(2))
    with pytest.raises(ValueError):
        select_projection_tie_break([np.ones(2)], np.zeros(2), np.ones(2), epsilon_tie=-1.0)
    with pytest.raises(ValueError):
        select_projection_tie_break([np.ones(2)], np.zeros(2), np.array([0.0, 1.0]))


def test_lexicographic_select_unchanged_for_exact_ties() -> None:
    a = np.array([0.0, 5.0])
    b = np.array([0.0, 2.0])
    assert np.array_equal(lexicographic_select([a, b]), b)
