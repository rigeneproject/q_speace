"""T218-T04 tests — observation-latency-aware safety contract (SAF-01).

Acceptance (spec §4.4): stale data and latency above the threshold
trigger the declared conservative mode (UNKNOWN, never "asserted
safety"); the reachable tube includes observation error and delay;
UNSAFE is detected when the action pushes the tube out of X_safe.
"""

from __future__ import annotations

import numpy as np
import pytest

from q_speace.bridge.safety_contract import SafetyContract, VerdictKind


def _linear_step_factory() -> callable:  # type: ignore[type-arg]
    """Interval extension of x_{t+1} = x_t + u_t (scalar or vector u)."""

    def step(x_lo: np.ndarray, x_hi: np.ndarray, u: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return x_lo + u, x_hi + u

    return step


@pytest.fixture()
def contract() -> SafetyContract:
    return SafetyContract(
        x_safe_lower=np.array([-1.0, -1.0]),
        x_safe_upper=np.array([1.0, 1.0]),
        epsilon_obs=np.array([0.1, 0.1]),
        max_age_steps=3,
        hold_input=np.array([0.0, 0.0]),
    )


def test_safe_action_with_delay_and_error(contract: SafetyContract) -> None:
    x_hat = np.array([0.0, 0.0])
    verdict = contract.check_action(
        x_hat, age_steps=2, action=np.array([0.5, 0.5]), step=_linear_step_factory()
    )
    assert verdict.kind is VerdictKind.SAFE
    assert verdict.reachable_lo is not None and verdict.reachable_hi is not None
    # tube after 2 hold steps is [-0.3, 0.3] (eps grows per step);
    # after the action it is [0.2, 0.8].
    assert verdict.reachable_lo[0] == pytest.approx(0.2)
    assert verdict.reachable_hi[0] == pytest.approx(0.8)


def test_unsafe_action_detected_on_reachable_tube(contract: SafetyContract) -> None:
    x_hat = np.array([0.0, 0.0])
    verdict = contract.check_action(
        x_hat, age_steps=2, action=np.array([0.9, 0.0]), step=_linear_step_factory()
    )
    # tube: [-0.3, 0.3] + 0.9 = [0.6, 1.2] leaves X_safe upper bound 1.0
    assert verdict.kind is VerdictKind.UNSAFE


def test_stale_data_returns_unknown_not_asserted_safety(
    contract: SafetyContract,
) -> None:
    x_hat = np.array([0.0, 0.0])
    verdict = contract.check_action(
        x_hat, age_steps=4, action=np.array([0.0, 0.0]), step=_linear_step_factory()
    )
    assert verdict.kind is VerdictKind.UNKNOWN
    assert "conservative" in verdict.reason


def test_missing_action_returns_unknown(contract: SafetyContract) -> None:
    verdict = contract.check_action(
        np.array([0.0, 0.0]), age_steps=1, action=None, step=_linear_step_factory()
    )
    assert verdict.kind is VerdictKind.UNKNOWN
    assert "missing" in verdict.reason


def test_estimation_error_inflation_widens_tube(contract: SafetyContract) -> None:
    """Zero delay: tube is x̂ ± eps; a center estimate near the edge must fail."""
    x_hat = np.array([0.95, 0.0])
    verdict = contract.check_action(
        x_hat, age_steps=0, action=np.array([0.0, 0.0]), step=_linear_step_factory()
    )
    assert verdict.kind is VerdictKind.UNSAFE  # hi = 1.05 > 1.0


def test_exact_edge_is_safe(contract: SafetyContract) -> None:
    x_hat = np.array([0.9, 0.0])
    verdict = contract.check_action(
        x_hat, age_steps=0, action=np.array([0.0, 0.0]), step=_linear_step_factory()
    )
    assert verdict.kind is VerdictKind.SAFE  # hi = 1.0 exactly


def test_horizon_multi_step_propagation(contract: SafetyContract) -> None:
    c = SafetyContract(
        x_safe_lower=np.array([-2.0]),
        x_safe_upper=np.array([2.0]),
        epsilon_obs=np.array([0.0]),
        max_age_steps=0,
        hold_input=np.array([0.0]),
        horizon_steps=3,
    )
    verdict = c.check_action(
        np.array([0.0]), age_steps=0, action=np.array([0.5]), step=_linear_step_factory()
    )
    assert verdict.kind is VerdictKind.SAFE
    assert verdict.reachable_lo is not None
    assert verdict.reachable_lo[0] == pytest.approx(1.5)


def test_construction_validation() -> None:
    with pytest.raises(ValueError):
        SafetyContract(
            x_safe_lower=np.array([1.0]),
            x_safe_upper=np.array([-1.0]),
            epsilon_obs=np.array([0.0]),
            max_age_steps=1,
            hold_input=np.array([0.0]),
        )
    with pytest.raises(ValueError):
        SafetyContract(
            x_safe_lower=np.array([-1.0]),
            x_safe_upper=np.array([1.0]),
            epsilon_obs=np.array([-0.1]),
            max_age_steps=1,
            hold_input=np.array([0.0]),
        )
