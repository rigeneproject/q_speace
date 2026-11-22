"""T220 §10 & T221-27: Seed ignition criterion pass/fail, timeout, and rollback requirement."""

from __future__ import annotations

import pytest

from q_speace.seed import (
    ConstitutionalFault,
    IgnitionCriterion,
    IgnitionObservation,
    SeedLifecycle,
    SeedState,
)


def _passing_obs() -> IgnitionObservation:
    return IgnitionObservation(
        accepted_mutations=3,
        min_metric_delta=0.02,
        consolidations=1,
        metabolic_balance_j=5.0,
        constitutional_faults=0,
        rollbacks_exercised=1,
        window_ticks=40,
    )


def test_ignition_passes_when_all_thresholds_met() -> None:
    seed = SeedLifecycle(criterion=IgnitionCriterion(min_accepted_mutations=3, max_window_ticks=50))
    verdict = seed.attempt_ignition(_passing_obs())
    assert verdict.passed is True
    assert verdict.reasons == ()
    assert seed.state == SeedState.IMPROVING


def test_ignition_returns_dormant_on_timeout_or_missing_rollback() -> None:
    seed = SeedLifecycle(criterion=IgnitionCriterion(max_window_ticks=50))

    # Window timeout -> stays DORMANT and logs diagnostic
    timed_out = IgnitionObservation(
        accepted_mutations=5,
        min_metric_delta=0.1,
        consolidations=2,
        metabolic_balance_j=10.0,
        constitutional_faults=0,
        rollbacks_exercised=1,
        window_ticks=51,
    )
    v_timeout = seed.attempt_ignition(timed_out)
    assert v_timeout.passed is False
    assert any("timed out" in r for r in v_timeout.reasons)
    assert seed.state == SeedState.DORMANT

    # Zero rollbacks exercised -> fails ignition
    no_rollback = IgnitionObservation(
        accepted_mutations=5,
        min_metric_delta=0.1,
        consolidations=2,
        metabolic_balance_j=10.0,
        constitutional_faults=0,
        rollbacks_exercised=0,
        window_ticks=20,
    )
    v_rb = seed.attempt_ignition(no_rollback)
    assert v_rb.passed is False
    assert any("rollbacks_exercised" in r for r in v_rb.reasons)
    assert seed.state == SeedState.DORMANT


def test_ignition_fails_on_negative_balance_or_constitutional_fault() -> None:
    seed = SeedLifecycle()
    bad_obs = IgnitionObservation(
        accepted_mutations=1,
        min_metric_delta=-0.05,
        consolidations=0,
        metabolic_balance_j=-2.0,
        constitutional_faults=1,
        rollbacks_exercised=0,
        window_ticks=10,
    )
    verdict = seed.attempt_ignition(bad_obs)
    assert verdict.passed is False
    assert len(verdict.reasons) == 6
    assert seed.state == SeedState.DORMANT

    # Cannot ignite from EXTINGUISHED without governance restart
    seed.extinguish(authority="human:maintainer", reason="halt")
    with pytest.raises(ConstitutionalFault, match="DORMANT"):
        seed.attempt_ignition(_passing_obs())
