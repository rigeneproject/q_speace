"""T-GOV-01 — Pre-execution impact check via the digital twin.

Implements the T210 BCEL rule "Impact simulation / digital twin":
pre-execution check of the resulting state against declared invariants.

Design invariants (from T-GOV-01 spec):
- The twin may only *confirm* or *reject* a proposal; it can never extend
  the admissible set ``A_safe`` (T210-DIFF §2).
- Twin unavailable or prediction failure → ``unverifiable``; in strict mode
  (default) unverifiable blocks the proposal (conservative refusal), never
  bypasses it.
- Every check result is meant to be recorded in the actuator audit trail.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ImpactInvariant:
    """A declared invariant over a predicted physical state dict."""

    invariant_id: str
    description: str
    predicate: Callable[[dict[str, float]], bool]


@dataclass
class ImpactCheckResult:
    outcome: str  # "pass" | "reject" | "unverifiable"
    reason: str = ""
    predicted_state: dict[str, float] = field(default_factory=dict)
    failed_invariants: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "reason": self.reason,
            "predicted_state": dict(self.predicted_state),
            "failed_invariants": list(self.failed_invariants),
        }


def _between(key: str, lo: float, hi: float) -> ImpactInvariant:
    def _pred(state: dict[str, float]) -> bool:
        value = float(state.get(key, 0.0))
        return lo <= value <= hi

    return ImpactInvariant(
        invariant_id=f"{key}_within_{lo}_{hi}",
        description=f"{key} must stay in [{lo}, {hi}] after the action",
        predicate=_pred,
    )


# Default invariants over PhysicalEnvironmentModel.STATE_KEYS.
# Sensor semantics (CyberPhysicalSensorArray): cpu_avg/battery_level are
# percentages, temp_avg is °C, process_count is a count, while mem_used,
# disk_used, net_in, net_out are reported in absolute bytes (not %).
# Byte-scaled plausibility bounds catch absurd predictions (negative or
# overflowed values) without false-rejecting real machines. Deployments can
# tighten or replace these via the ``invariants`` constructor argument.
_GIB = 2.0**30
DEFAULT_IMPACT_INVARIANTS: list[ImpactInvariant] = [
    _between("cpu_avg", 0.0, 100.0),
    _between("mem_used", 0.0, 1024.0 * _GIB),
    _between("disk_used", 0.0, 4096.0 * _GIB),
    _between("net_in", 0.0, 1024.0 * _GIB),
    _between("net_out", 0.0, 1024.0 * _GIB),
    _between("temp_avg", 0.0, 110.0),
    _between("process_count", 0.0, 100000.0),
    _between("battery_level", 0.0, 100.0),
]

# Default mapping proposal-kind → simulated state delta. Conservative by
# design: deltas represent the *expected immediate physical footprint* of
# the action family, not exact effects.
DEFAULT_ACTION_DELTAS: dict[str, dict[str, float]] = {
    "send_signal_to_self": {"cpu_avg": 0.5},
    "log_event": {"disk_used": 0.1},
    "create_checkpoint": {"disk_used": 0.5},
    "execute_command": {"cpu_avg": 10.0, "temp_avg": 2.0},
    "delete_file": {"disk_used": -1.0},
}


class TwinImpactChecker:
    """Evaluate a proposal's predicted impact against declared invariants.

    ``twin`` is any object exposing ``simulate_action(action_delta,
    horizon_ticks) -> {"trace": [...], ...}`` (see ``DigitalTwinModel``).
    """

    def __init__(
        self,
        twin: Any = None,
        invariants: list[ImpactInvariant] | None = None,
        action_deltas: dict[str, dict[str, float]] | None = None,
        horizon_ticks: int = 5,
        strict_unverifiable: bool = True,
    ):
        self._twin = twin
        self._invariants = list(invariants or DEFAULT_IMPACT_INVARIANTS)
        self._action_deltas = dict(action_deltas or DEFAULT_ACTION_DELTAS)
        self._horizon_ticks = int(horizon_ticks)
        self.strict_unverifiable = bool(strict_unverifiable)

    def set_twin(self, twin: Any) -> None:
        self._twin = twin

    def _delta_for(self, action_type: str) -> dict[str, float]:
        return dict(self._action_deltas.get(action_type, {"cpu_avg": 2.0}))

    def check_proposal(self, action_type: str, params: dict[str, Any]) -> ImpactCheckResult:
        """Predict the proposal's resulting state and evaluate invariants."""
        if self._twin is None:
            result = ImpactCheckResult(
                outcome="unverifiable",
                reason="twin_unavailable",
            )
            result.to_dict()  # ensure serializable shape
            return self._apply_strictness(result)

        try:
            simulation = self._twin.simulate_action(
                self._delta_for(action_type), horizon_ticks=self._horizon_ticks
            )
        except Exception as exc:
            return self._apply_strictness(
                ImpactCheckResult(outcome="unverifiable", reason=f"twin_error:{exc}")
            )

        trace = simulation.get("trace") or []
        if not trace:
            return self._apply_strictness(
                ImpactCheckResult(outcome="unverifiable", reason="empty_trace")
            )
        predicted_state = {k: float(v) for k, v in trace[-1]["state"].items()}

        failed: list[str] = []
        for invariant in self._invariants:
            try:
                ok = bool(invariant.predicate(predicted_state))
            except Exception as exc:
                failed.append(f"{invariant.invariant_id}(eval_error:{exc})")
                continue
            if not ok:
                failed.append(invariant.invariant_id)

        if failed:
            return ImpactCheckResult(
                outcome="reject",
                reason="predicted_state_violates_invariants",
                predicted_state=predicted_state,
                failed_invariants=failed,
            )
        return ImpactCheckResult(
            outcome="pass",
            reason="all_invariants_hold",
            predicted_state=predicted_state,
        )

    def _apply_strictness(self, result: ImpactCheckResult) -> ImpactCheckResult:
        """In strict mode ``unverifiable`` is escalated to ``reject``.

        The escalated result keeps outcome ``reject`` with the original
        reason so the audit shows the conservative refusal origin.
        """
        if result.outcome == "unverifiable" and self.strict_unverifiable:
            return ImpactCheckResult(
                outcome="reject",
                reason=f"unverifiable:{result.reason}",
                predicted_state=result.predicted_state,
                failed_invariants=result.failed_invariants,
            )
        return result
