"""T218-T06 tests — rollback recoverability guards (SAF-02, review C2).

Acceptance: rollback after physical/integral accumulation is never
labelled "safe restore"; distinct outcomes for plant recovery,
controller transition and hysteresis; the legacy RollbackManager
behaviour is preserved.
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


def test_clean_state_allows_software_restore(guard: RollbackGuard) -> None:
    decision = guard.assess(
        np.array([0.0, 0.0]),
        integral_accumulated=0.1,
        steps_since_last_transition=10,
    )
    assert decision.kind is TransitionKind.SOFTWARE_RESTORE_ALLOWED
    assert not decision.reset_integrator


def test_rollback_after_integral_accumulation_requires_controller_transition(
    guard: RollbackGuard,
) -> None:
    """C2: restoring p^k does not reset the controller integrators."""
    decision = guard.assess(
        np.array([0.0, 0.0]),
        integral_accumulated=2.5,
        steps_since_last_transition=10,
    )
    assert decision.kind is TransitionKind.CONTROLLER_TRANSITION_REQUIRED
    assert decision.reset_integrator
    assert "integrators" in decision.reason


def test_rollback_after_physical_accumulation_requires_plant_recovery(
    guard: RollbackGuard,
) -> None:
    """C2: the old configuration is not applicable outside the region."""
    decision = guard.assess(
        np.array([0.8, 0.0]),  # outside the [-0.5, 0.5] region
        integral_accumulated=0.1,
        steps_since_last_transition=10,
    )
    assert decision.kind is TransitionKind.PLANT_RECOVERY_REQUIRED
    assert not decision.reset_integrator
    assert "plant recovery" in decision.reason


def test_hysteresis_refuses_immediate_reflip(guard: RollbackGuard) -> None:
    decision = guard.assess(
        np.array([0.0, 0.0]),
        integral_accumulated=0.1,
        steps_since_last_transition=2,
    )
    assert decision.kind is TransitionKind.REFUSED_HYSTERESIS


def test_state_shape_mismatch_raises(guard: RollbackGuard) -> None:
    with pytest.raises(ValueError):
        guard.assess(
            np.array([0.0]),
            integral_accumulated=0.0,
            steps_since_last_transition=10,
        )


def test_region_and_threshold_validation() -> None:
    with pytest.raises(ValueError):
        RollbackGuard(
            recovery_region_lower=np.array([1.0]),
            recovery_region_upper=np.array([-1.0]),
        )
    with pytest.raises(ValueError):
        RollbackGuard(
            recovery_region_lower=np.array([-1.0]),
            recovery_region_upper=np.array([1.0]),
            integral_reset_threshold=0.0,
        )


def test_legacy_rollback_manager_unchanged() -> None:
    """The T39 RollbackManager behaviour is preserved (no regression)."""
    from q_speace.self_improvement_cortex.rollback import RollbackManager

    manager = RollbackManager(
        mutation_registry=None,  # type: ignore[arg-type]
        epigenetic_engine=None,  # type: ignore[arg-type]
        thresholds={"coherence_phi": -0.15},
    )
    assert manager._thresholds == {"coherence_phi": -0.15}
