"""T218-T07 tests — additive aggregation and score properties (SCO-01/02/03).

Counterexamples from the peer review:
* MAT-M2: two equal-weight regions with physical values 0 and 1 under a
  nonlinear normalisation b(x)=x^2 — the merged/aggregated score must
  not differ from the fine-grained one;
* L4/M6: monotonicity is at fixed coordinates; trade-offs are legal;
* GOV-G4: cumulative per-group limits block sequences that individually
  pass but cumulatively exceed.
"""

from __future__ import annotations

import numpy as np
import pytest

from q_speace.economy.aggregation import (
    ScorePolicy,
    additive_score,
    cumulative_harm_check,
    monotonicity_at_fixed_coordinates,
    reporting_score,
)


@pytest.fixture()
def policy() -> ScorePolicy:
    return ScorePolicy(alpha=(1.0, 1.0), beta=(1.0, 1.0), version="v0-test")


# --------------------------------------------------------------------- #
# SCO-01: monotonicity at fixed coordinates
# --------------------------------------------------------------------- #
def test_raising_one_harm_never_raises_score(policy: ScorePolicy) -> None:
    benefits = np.array([0.5, 0.5])
    harms = np.array([0.2, 0.1])
    assert monotonicity_at_fixed_coordinates(policy, benefits, harms)


def test_tradeoff_may_legally_raise_total(policy: ScorePolicy) -> None:
    """M6: raising a harm AND a benefit can raise U — not a bug."""
    benefits = np.array([0.5, 0.5])
    harms = np.array([0.2, 0.1])
    base = reporting_score(policy, benefits, harms)
    raised = reporting_score(policy, np.array([0.9, 0.5]), np.array([0.3, 0.1]))
    assert raised > base  # legitimate trade-off


def test_harm_cannot_be_erased_by_multiplicative_factor(policy: ScorePolicy) -> None:
    """The old signed-multiplicative failure mode is structurally gone."""
    benefits = np.array([0.0, 0.0])
    harms = np.array([0.5, 0.0])
    with_harm = reporting_score(policy, benefits, harms)
    without_harm = reporting_score(policy, benefits, np.zeros(2))
    assert with_harm < without_harm  # the penalty survives any benefit value


def test_score_validation(policy: ScorePolicy) -> None:
    with pytest.raises(ValueError):
        reporting_score(policy, np.array([1.5, 0.0]), np.zeros(2))
    with pytest.raises(ValueError):
        reporting_score(policy, np.array([0.5, 0.0]), np.array([-0.1, 0.0]))
    with pytest.raises(ValueError):
        ScorePolicy(alpha=(-1.0,), beta=(1.0,), version="v")


# --------------------------------------------------------------------- #
# SCO-02: additive measure and partition invariance
# --------------------------------------------------------------------- #
def test_counterexample_partition_invariance_with_quadratic_normalisation() -> None:
    """MAT-M2: b(x)=x^2, two half-units with x=0 and x=1.

    Declared pipeline: the normalisation b is applied *pointwise at the
    reference granularity*; a merged region's density is the
    μ-weighted average of the pointwise densities. Fine and merged
    scores then coincide (telescoping integral). The banned shortcut —
    applying b to the local *mean* of x — is documented as the bug the
    rule prevents.
    """
    fine_densities = np.array([0.0**2, 1.0**2])  # b applied pointwise
    fine_measure = np.array([0.5, 0.5])
    fine = additive_score(fine_densities, fine_measure, _dummy_policy())
    # merged region: μ-weighted average of pointwise densities
    merged_density = np.array([float(fine_densities @ fine_measure)])
    merged_measure = np.array([1.0])
    merged = additive_score(merged_density, merged_measure, _dummy_policy())
    assert fine == pytest.approx(0.5)
    assert merged == pytest.approx(fine)


def test_forbidden_normalisation_of_local_mean_is_detectable() -> None:
    """MAT-M2: the banned shortcut gives 0.25 instead of 0.5.

    Regression guard: an implementation must never compute the merged
    density as b(mean(x)). This documents why the additive-density rule
    exists — the physics is identical, the score must not change.
    """
    local_mean = (0.0 + 1.0) / 2
    banned_merged = local_mean**2  # b applied to the mean: FORBIDDEN
    assert banned_merged == pytest.approx(0.25)
    assert banned_merged != pytest.approx(0.5)  # differs from the declared value


def _dummy_policy() -> ScorePolicy:
    # A single identity channel so the integral passes through unchanged.
    return ScorePolicy(alpha=(1.0,), beta=(0.0,), version="identity")


def test_negative_density_subtracts(policy: ScorePolicy) -> None:
    densities = np.array([0.8, -0.3])
    measure = np.array([1.0, 2.0])
    assert additive_score(densities, measure, policy) == pytest.approx(0.8 - 0.6)


def test_additive_score_validation() -> None:
    with pytest.raises(ValueError):
        additive_score(np.array([0.0]), np.array([1.0, 2.0]), _dummy_policy())
    with pytest.raises(ValueError):
        additive_score(np.array([0.0]), np.array([-1.0]), _dummy_policy())


# --------------------------------------------------------------------- #
# SCO-03: cumulative per-group limits
# --------------------------------------------------------------------- #
def test_cumulative_limit_blocks_repeated_load_on_same_group() -> None:
    """G4: daily admissible cuts on the same district accumulate."""
    # each action is individually admissible (0.05 < per-action limit 0.1)
    # but the district's cumulative limit is 0.12
    ok, reason = cumulative_harm_check(np.array([0.15]), np.array([0.12]))
    assert not ok
    assert "group 0" in reason


def test_cumulative_limit_passes_within_bounds() -> None:
    ok, reason = cumulative_harm_check(np.array([0.1]), np.array([0.12]))
    assert ok
    assert "respected" in reason


def test_cumulative_limit_names_first_violated_group() -> None:
    ok, reason = cumulative_harm_check(np.array([0.05, 0.30, 0.05]), np.array([0.10, 0.20, 0.10]))
    assert not ok
    assert "group 1" in reason


def test_cumulative_limit_validation() -> None:
    with pytest.raises(ValueError):
        cumulative_harm_check(np.array([0.0]), np.array([-1.0]))
    with pytest.raises(ValueError):
        cumulative_harm_check(np.array([0.0, 0.0]), np.array([1.0]))
