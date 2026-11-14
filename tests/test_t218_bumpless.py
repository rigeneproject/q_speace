"""T218 refinement R4 — bumpless transfer and slew-rate guard (SAF-02).

Acceptance: an instantaneous parameter step when the action rate already
exceeds the inverter slew-rate limit is refused; the guard prescribes a
controller transition with integrator realignment; ``bumpless_realignment``
keeps the control action continuous and clamps to the slew window.
"""

from __future__ import annotations

import numpy as np
import pytest

from q_speace.self_improvement_cortex.rollback import (
    RollbackGuard,
    TransitionKind,
)


@pytest.fixture()
def guard() -> RollbackGuard:
    return RollbackGuard(
        recovery_region_lower=np.array([-0.5, -0.5]),
        recovery_region_upper=np.array([0.5, 0.5]),
        integral_reset_threshold=1.0,
        min_dwell_steps=5,
    )


def test_clean_state_within_slew_allows_restore(guard: RollbackGuard) -> None:
    decision = guard.assess(
        np.array([0.0, 0.0]),
        integral_accumulated=0.1,
        steps_since_last_transition=10,
        action_rate=0.01,
        slew_rate_limit=0.05,
    )
    assert decision.kind is TransitionKind.SOFTWARE_RESTORE_ALLOWED
    assert not decision.reset_integrator


def test_action_rate_exceeding_slew_requires_bumpless_transition(
    guard: RollbackGuard,
) -> None:
    """A step of V_setpoint/droop_gain back to p^k with a saturated action
    rate would inject a current step on the bus: refused as-is."""
    decision = guard.assess(
        np.array([0.0, 0.0]),
        integral_accumulated=0.1,  # integrators are clean
        steps_since_last_transition=10,
        action_rate=0.30,
        slew_rate_limit=0.05,
    )
    assert decision.kind is TransitionKind.CONTROLLER_TRANSITION_REQUIRED
    assert decision.reset_integrator
    assert "bumpless" in decision.reason
    assert "slew" in decision.reason


def test_integrator_guard_still_takes_precedence_over_slew(guard: RollbackGuard) -> None:
    decision = guard.assess(
        np.array([0.0, 0.0]),
        integral_accumulated=5.0,
        steps_since_last_transition=10,
        action_rate=0.30,
        slew_rate_limit=0.05,
    )
    assert decision.kind is TransitionKind.CONTROLLER_TRANSITION_REQUIRED
    assert "integrators" in decision.reason


def test_slew_guard_not_active_when_limit_omitted(guard: RollbackGuard) -> None:
    decision = guard.assess(
        np.array([0.0, 0.0]),
        integral_accumulated=0.1,
        steps_since_last_transition=10,
    )
    assert decision.kind is TransitionKind.SOFTWARE_RESTORE_ALLOWED


def test_bumpless_realignment_is_continuous_within_slew() -> None:
    last_action = 0.40
    previous_action = 0.38
    kp_new = 2.0
    error_new = 0.05
    slew = 0.05
    i_new = RollbackGuard.bumpless_realignment(
        last_action, kp_new, error_new, previous_action, slew
    )
    restored_action = kp_new * error_new + i_new
    assert restored_action == pytest.approx(last_action)  # perfectly bumpless
    # slew window respected by construction
    assert abs(restored_action - previous_action) <= slew + 1e-12


def test_bumpless_realignment_clamps_to_slew_window() -> None:
    last_action = 0.60
    previous_action = 0.40
    slew = 0.05
    i_new = RollbackGuard.bumpless_realignment(
        last_action,
        kp_new=2.0,
        error_new=0.0,
        previous_action=previous_action,
        slew_rate_limit=slew,
    )
    restored_action = 2.0 * 0.0 + i_new
    assert restored_action == pytest.approx(previous_action + slew)  # clamped


def test_bumpless_realignment_validation() -> None:
    with pytest.raises(ValueError):
        RollbackGuard.bumpless_realignment(0.5, 1.0, 0.0, 0.5, slew_rate_limit=0.0)


def test_all_guards_together_region_clean_slew_ok(guard: RollbackGuard) -> None:
    decision = guard.assess(
        np.array([0.3, -0.3]),
        integral_accumulated=0.9,
        steps_since_last_transition=6,
        action_rate=0.0,
        slew_rate_limit=0.05,
    )
    assert decision.kind is TransitionKind.SOFTWARE_RESTORE_ALLOWED
