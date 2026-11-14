"""T218-T08 tests — certified causal incremental value (CAU-01).

Acceptance (spec §6): opposite-sign trajectory errors are detected as a
certificate-coverage failure when epsilon_model is mis-declared as a
per-trajectory bound; a bound on the *incremental* target restores
coverage; effects beyond the horizon are reported unresolved and never
folded into a positive lower bound.
"""

from __future__ import annotations

import pytest

from q_speace.economy.vtec import (
    CausalEstimate,
    certified_lower_bound,
    covered_by_certificate,
    post_horizon_verdict,
)


def _est(
    *,
    v_hat: float,
    epsilon_model: float,
    post_unknown: bool = False,
    horizon: int = 10,
) -> CausalEstimate:
    return CausalEstimate(
        action="a1",
        baseline="pi0",
        omega="cells:all",
        horizon=horizon,
        v_hat=v_hat,
        epsilon_model=epsilon_model,
        epsilon_spatial=0.0,
        epsilon_temporal=0.0,
        epsilon_stat=0.0,
        confidence_delta=0.95,
        post_horizon_effect_unknown=post_unknown,
    )


def test_certificate_is_v_hat_minus_epsilon_total() -> None:
    est = _est(v_hat=1.0, epsilon_model=0.4)
    est = CausalEstimate(
        action="a1",
        baseline="pi0",
        omega="cells:all",
        horizon=10,
        v_hat=1.0,
        epsilon_model=0.2,
        epsilon_spatial=0.1,
        epsilon_temporal=0.05,
        epsilon_stat=0.05,
        confidence_delta=0.95,
    )
    assert certified_lower_bound(est) == pytest.approx(1.0 - 0.4)


def test_opposite_trajectory_errors_break_per_trajectory_bound() -> None:
    """R4 counterexample: errors +e on the action trajectory and -e on the
    baseline give a difference error of 2e.

    If epsilon_model is (wrongly) declared as a per-trajectory bound e,
    the certificate over-covers and ground truth falls below it.
    """
    e = 0.1
    # true incremental value: (true_a - e) - (true_b + e) = v_hat - 2e
    v_hat = 0.5  # estimated assuming zero error on both trajectories
    true_value = v_hat - 2 * e
    wrong = _est(v_hat=v_hat, epsilon_model=e)  # per-trajectory mis-declaration
    assert not covered_by_certificate(wrong, true_value)


def test_incremental_bound_restores_coverage() -> None:
    """With epsilon_model declared as the bound on the *difference* (2e),
    the certificate is covered."""
    e = 0.1
    v_hat = 0.5
    true_value = v_hat - 2 * e
    right = _est(v_hat=v_hat, epsilon_model=2 * e)
    assert covered_by_certificate(right, true_value)


def test_monte_carlo_term_adds_to_budget() -> None:
    """A statistical term with explicit confidence level widens the bound."""
    est = CausalEstimate(
        action="a1",
        baseline="pi0",
        omega="cells:all",
        horizon=10,
        v_hat=1.0,
        epsilon_model=0.1,
        epsilon_spatial=0.0,
        epsilon_temporal=0.0,
        epsilon_stat=0.2,
        confidence_delta=0.95,
    )
    assert certified_lower_bound(est) == pytest.approx(0.7)


def test_post_horizon_effect_reported_unresolved() -> None:
    est = _est(v_hat=1.0, epsilon_model=0.1, post_unknown=True)
    assert post_horizon_verdict(est) == "OUTSIDE_HORIZON_UNRESOLVED"


def test_post_horizon_effect_absent() -> None:
    est = _est(v_hat=1.0, epsilon_model=0.1)
    assert post_horizon_verdict(est) == "NONE_REPORTED"


def test_no_convenient_horizon_hides_deferred_harm() -> None:
    """A positive in-horizon bound must not silence a deferred harm: the
    unresolved verdict is attached to the estimate and must be surfaced."""
    est = _est(v_hat=2.0, epsilon_model=0.1, post_unknown=True)
    assert certified_lower_bound(est) > 0.0  # in-horizon: positive
    assert post_horizon_verdict(est) == "OUTSIDE_HORIZON_UNRESOLVED"  # but flagged


def test_estimate_validation() -> None:
    with pytest.raises(ValueError):
        _est(v_hat=1.0, epsilon_model=-0.1)
    with pytest.raises(ValueError):
        CausalEstimate(
            action="a",
            baseline="b",
            omega="o",
            horizon=0,
            v_hat=1.0,
            epsilon_model=0.1,
            epsilon_spatial=0.0,
            epsilon_temporal=0.0,
            epsilon_stat=0.0,
            confidence_delta=0.95,
        )
    with pytest.raises(ValueError):
        CausalEstimate(
            action="a",
            baseline="b",
            omega="o",
            horizon=5,
            v_hat=1.0,
            epsilon_model=0.1,
            epsilon_spatial=0.0,
            epsilon_temporal=0.0,
            epsilon_stat=0.0,
            confidence_delta=1.5,
        )
