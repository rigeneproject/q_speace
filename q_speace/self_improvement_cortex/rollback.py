"""RollbackManager — automatic rollback on metric degradation (T39).

Extended in T218 (SAF-02, review item SYS-C2): :class:`RollbackGuard`
distinguishes *software restore* from *controller transition* and
*plant recovery*. Reloading a previously approved parameter file is
not "safe" by itself: after physical accumulation (stock depletion,
integral windup, neighbour-state drift) the old configuration may no
longer be applicable to the current state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np

from .dna_registry import DNAMutationRecord, MutationRegistry
from .epigenetics import EpigeneticEngine


@dataclass
class RollbackPlan:
    mutation_id: str
    reason: str
    degraded_metrics: dict[str, float]
    threshold_deltas: dict[str, float]
    safe: bool = False

    @property
    def is_actionable(self) -> bool:
        return self.safe and bool(self.degraded_metrics)


class RollbackManager:
    """Monitors metrics and triggers rollback when degradation is detected."""

    def __init__(
        self,
        mutation_registry: MutationRegistry,
        epigenetic_engine: EpigeneticEngine,
        thresholds: dict[str, float] | None = None,
    ) -> None:
        self._registry = mutation_registry
        self._epigenetics = epigenetic_engine
        self._thresholds = thresholds or {
            "coherence_phi": -0.15,
            "mean_energy_w": 2.0,
            "goal_completion": -0.2,
            "resilience": -0.15,
        }

    def evaluate(
        self, mutation: DNAMutationRecord, current_metrics: dict[str, float]
    ) -> RollbackPlan | None:
        degraded = {}
        for metric, threshold in self._thresholds.items():
            before = mutation.metrics_before.get(metric)
            after = current_metrics.get(metric)
            if before is None or after is None:
                continue
            delta = after - before
            if metric in ("mean_energy_w", "energy_consumption", "prediction_error"):
                if delta > threshold:
                    degraded[metric] = delta
            else:
                if delta < threshold:
                    degraded[metric] = delta

        if not degraded:
            return None

        safe = self._safety_check(mutation)
        return RollbackPlan(
            mutation_id=mutation.mutation_id,
            reason=f"degraded metrics: {degraded}",
            degraded_metrics=degraded,
            threshold_deltas=self._thresholds,
            safe=safe,
        )

    def _safety_check(self, mutation: DNAMutationRecord) -> bool:
        epi_state = self._epigenetics.state_of(mutation.mutation_id)
        if epi_state is None:
            return True
        if epi_state.consolidated:
            return False
        return self._epigenetics.should_rollback(mutation.mutation_id)

    def execute(self, plan: RollbackPlan) -> bool:
        return plan.is_actionable


class TransitionKind(StrEnum):
    """Declared rollback transition outcomes (spec §4.3, review C2).

    The three kinds are deliberately distinct: restoring the software
    configuration does not by itself transition the controller state
    nor recover the physical plant.
    """

    SOFTWARE_RESTORE_ALLOWED = "SOFTWARE_RESTORE_ALLOWED"
    CONTROLLER_TRANSITION_REQUIRED = "CONTROLLER_TRANSITION_REQUIRED"
    PLANT_RECOVERY_REQUIRED = "PLANT_RECOVERY_REQUIRED"
    REFUSED_HYSTERESIS = "REFUSED_HYSTERESIS"


@dataclass(frozen=True)
class TransitionDecision:
    kind: TransitionKind
    reason: str
    reset_integrator: bool


class RollbackGuard:
    """Recoverability guards for a rollback transition (SAF-02).

    A previously approved configuration may only be re-applied when:

    * the current plant state lies inside the declared recoverability
      region (a box around the certified operating envelope);
    * the controller's internal integrators have not accumulated past
      the declared threshold (otherwise a controller transition with
      integrator reset is required *before* the restore);
    * the minimum dwell time between transitions has elapsed
      (hysteresis against chattering).
    """

    def __init__(
        self,
        recovery_region_lower: np.ndarray,
        recovery_region_upper: np.ndarray,
        *,
        integral_reset_threshold: float = 1.0,
        min_dwell_steps: int = 5,
    ) -> None:
        if np.any(recovery_region_lower > recovery_region_upper):
            raise ValueError("recovery region bounds are inconsistent")
        if integral_reset_threshold <= 0.0:
            raise ValueError("integral_reset_threshold must be positive")
        if min_dwell_steps < 0:
            raise ValueError("min_dwell_steps must be non-negative")
        self._lower = np.asarray(recovery_region_lower, dtype=np.float64)
        self._upper = np.asarray(recovery_region_upper, dtype=np.float64)
        self._integral_threshold = integral_reset_threshold
        self._min_dwell = min_dwell_steps

    def assess(
        self,
        plant_state: np.ndarray,
        *,
        integral_accumulated: float,
        steps_since_last_transition: int,
        action_rate: float | None = None,
        slew_rate_limit: float | None = None,
    ) -> TransitionDecision:
        """Classify what a rollback requires under the current conditions.

        Loading the old parameter file is only ``SOFTWARE_RESTORE_ALLOWED``
        when all guards pass; each failing guard prescribes the distinct
        procedure that *is* required — and none of them is "the restore
        itself is safe".

        Bumpless-transfer guard (T218 refinement R4): when the current
        action rate already exceeds the declared inverter slew-rate
        limit, an instantaneous step of V_setpoint / droop_gain back to
        ``p_i^k`` would add a current step on the bus; a controller
        transition with :meth:`bumpless_realignment` of the local
        integrator state is prescribed instead.
        """
        state = np.asarray(plant_state, dtype=np.float64)
        if state.shape != self._lower.shape:
            raise ValueError("plant_state shape does not match the recovery region")
        if steps_since_last_transition < self._min_dwell:
            return TransitionDecision(
                TransitionKind.REFUSED_HYSTERESIS,
                reason=(
                    f"only {steps_since_last_transition} steps since the last "
                    f"transition; dwell requires {self._min_dwell}"
                ),
                reset_integrator=False,
            )
        if np.any(state < self._lower) or np.any(state > self._upper):
            return TransitionDecision(
                TransitionKind.PLANT_RECOVERY_REQUIRED,
                reason=(
                    "plant state is outside the recoverability region: the old "
                    "configuration is not applicable; a plant recovery "
                    "procedure is required"
                ),
                reset_integrator=False,
            )
        if integral_accumulated > self._integral_threshold:
            return TransitionDecision(
                TransitionKind.CONTROLLER_TRANSITION_REQUIRED,
                reason=(
                    "controller integrators have accumulated past the threshold: "
                    "reset and transition the controller before restoring"
                ),
                reset_integrator=True,
            )
        if slew_rate_limit is not None:
            if slew_rate_limit <= 0.0:
                raise ValueError("slew_rate_limit must be positive")
            if action_rate is not None and action_rate > slew_rate_limit:
                return TransitionDecision(
                    TransitionKind.CONTROLLER_TRANSITION_REQUIRED,
                    reason=(
                        "action rate exceeds the inverter slew-rate limit: an "
                        "instantaneous parameter step would inject a current "
                        "step on the bus; realign the integrator with "
                        "bumpless_realignment before restoring"
                    ),
                    reset_integrator=True,
                )
        return TransitionDecision(
            TransitionKind.SOFTWARE_RESTORE_ALLOWED,
            reason="all guards passed: state in region, integrators clean, dwell ok",
            reset_integrator=False,
        )

    @staticmethod
    def bumpless_realignment(
        last_action: float,
        kp_new: float,
        error_new: float,
        previous_action: float,
        slew_rate_limit: float,
    ) -> float:
        """Return the integrator state ``I_new`` for a bumpless transfer.

        The control law ``u = kp_new * error_new + I`` is re-based so
        that the restored controller's first action is continuous with
        the last action of the outgoing controller; the target is then
        clamped to the slew-rate window around ``previous_action`` so
        the control-action derivative stays within the inverter limit.

        Parameters
        ----------
        last_action:
            The last action computed by the outgoing controller.
        kp_new, error_new:
            Proportional gain and error under the *restored* parameters.
        previous_action:
            The action one step earlier (slew-rate reference).
        slew_rate_limit:
            Maximum allowed change of the control action per step.

        Returns
        -------
        float
            The integrator state to load so that
            ``kp_new * error_new + I_new`` is slew-compatible.
        """
        if slew_rate_limit <= 0.0:
            raise ValueError("slew_rate_limit must be positive")
        u_target = last_action
        lo = previous_action - slew_rate_limit
        hi = previous_action + slew_rate_limit
        u_clamped = min(max(u_target, lo), hi)
        return u_clamped - kp_new * error_new
