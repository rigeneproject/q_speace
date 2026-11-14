"""T218-T02 tests — two-stage parameter screening (BR-02).

Counterexamples from the peer review: L1 (projection vs budget),
MAT-M1 (P=[0,10], p^k=0, proposal=10, Delta=1) and the declared
outcomes for empty admissible set, migration and non-unique projection.
"""

from __future__ import annotations

import numpy as np
import pytest

from q_speace.bridge.screening import (
    ScreeningOutcome,
    lexicographic_select,
    project_onto_intersection,
    screen_candidate,
    weighted_norm,
)


def test_counterexample_projection_alone_does_not_apply_budget() -> None:
    """P=[0,10], p^k=0, proposal=10, Delta=1 -> candidate must be 1, never 10."""
    res = screen_candidate(
        np.array([10.0]),
        np.array([0.0]),
        lower=np.array([0.0]),
        upper=np.array([10.0]),
        scale=np.array([1.0]),
        budget=1.0,
    )
    assert res.outcome is ScreeningOutcome.ACCEPTED
    assert res.candidate is not None
    assert float(res.candidate[0]) == pytest.approx(1.0)


def test_multidim_candidate_respects_budget_norm() -> None:
    """p^k=0, Delta=1, proposal=(1,1): box reach alone would give norm sqrt(2)."""
    res = screen_candidate(
        np.array([1.0, 1.0]),
        np.array([0.0, 0.0]),
        lower=np.array([-10.0, -10.0]),
        upper=np.array([10.0, 10.0]),
        scale=np.array([1.0, 1.0]),
        budget=1.0,
    )
    assert res.candidate is not None
    assert weighted_norm(res.candidate - np.zeros(2), np.ones(2)) <= 1.0 + 1e-12


def test_empty_admissible_set_is_rejected_with_reason() -> None:
    """p^k outside P by more than Delta makes F empty -> declared rejection."""
    res = screen_candidate(
        np.array([5.0]),
        np.array([50.0]),  # p^k far outside P
        lower=np.array([0.0]),
        upper=np.array([10.0]),
        scale=np.array([1.0]),
        budget=1.0,
    )
    assert res.outcome is ScreeningOutcome.REJECTED_EMPTY_SET
    assert res.candidate is None
    assert "empty" in res.reason


def test_budget_zero_pins_to_last_approved() -> None:
    res = screen_candidate(
        np.array([7.0]),
        np.array([2.0]),
        lower=np.array([0.0]),
        upper=np.array([10.0]),
        scale=np.array([1.0]),
        budget=0.0,
    )
    assert res.outcome is ScreeningOutcome.ACCEPTED
    assert res.candidate is not None
    assert float(res.candidate[0]) == pytest.approx(2.0)


def test_policy_migration_rejects_when_p_last_left_new_set() -> None:
    res = screen_candidate(
        np.array([3.0]),
        np.array([9.0]),
        lower=np.array([0.0]),
        upper=np.array([10.0]),
        scale=np.array([1.0]),
        budget=1.0,
        new_lower=np.array([0.0]),
        new_upper=np.array([5.0]),
    )
    assert res.outcome is ScreeningOutcome.REJECTED_MIGRATION
    assert res.candidate is None
    assert "fallback" in res.reason


def test_policy_unchanged_accepts_normally() -> None:
    res = screen_candidate(
        np.array([3.0]),
        np.array([2.0]),
        lower=np.array([0.0]),
        upper=np.array([10.0]),
        scale=np.array([1.0]),
        budget=1.0,
        new_lower=np.array([0.0]),
        new_upper=np.array([5.0]),
    )
    assert res.outcome is ScreeningOutcome.ACCEPTED
    assert res.candidate is not None
    assert float(res.candidate[0]) == pytest.approx(3.0)


def test_project_onto_intersection_raises_on_empty() -> None:
    with pytest.raises(ValueError):
        project_onto_intersection(
            np.array([5.0]),
            np.array([50.0]),
            lower=np.array([0.0]),
            upper=np.array([10.0]),
            scale=np.array([1.0]),
            budget=1.0,
        )


def test_weighted_norm_rejects_nonpositive_scale() -> None:
    with pytest.raises(ValueError):
        weighted_norm(np.array([1.0]), np.array([0.0]))


def test_lexicographic_select_is_deterministic() -> None:
    a = np.array([0.0, 5.0])
    b = np.array([0.0, 2.0])
    c = np.array([1.0, 0.0])
    picked = lexicographic_select([c, a, b, b])
    assert np.array_equal(picked, b)
    with pytest.raises(ValueError):
        lexicographic_select([])
