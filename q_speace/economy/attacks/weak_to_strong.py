"""Weak-to-strong attack detectors (T6.21 §4.10.1)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class AttackFlags:
    """Detected attack conditions."""

    salience_injection: bool = False
    lambda_induction: bool = False
    exit_cost_asymmetry: bool = False
    monopoly_of_measurement: bool = False
    reference_elasticity: bool = False
    triggered: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.triggered:
            object.__setattr__(self, "triggered", self._collect())

    def _collect(self) -> tuple[str, ...]:
        flags: list[str] = []
        if self.salience_injection:
            flags.append("salience_injection")
        if self.lambda_induction:
            flags.append("lambda_induction")
        if self.exit_cost_asymmetry:
            flags.append("exit_cost_asymmetry")
        if self.monopoly_of_measurement:
            flags.append("monopoly_of_measurement")
        if self.reference_elasticity:
            flags.append("reference_elasticity")
        return tuple(flags)


def detect_salience_injection(
    history: Sequence[float],
    *,
    spike_factor: float = 3.0,
) -> bool:
    """Detect a sudden, large jump in the value history.

    The controller's value history shows a step-like increase if the
    attacker injected salience (raised the reward of a single action
    and the controller over-allocated to it).
    """
    if len(history) < 3:
        return False
    arr = np.asarray(history, dtype=np.float64)
    # Compute ratio of the latest value to the rolling median of the
    # previous 80% of the history.
    cutoff = max(1, int(0.8 * len(arr)))
    if cutoff < 1:
        return False
    baseline = float(np.median(arr[:cutoff]))
    if baseline <= 1e-12:
        return False
    latest = float(arr[-1])
    return latest >= spike_factor * baseline


def detect_lambda_induction(
    values: Sequence[float],
    *,
    drift_threshold: float = 0.05,
) -> bool:
    """Detect a sustained negative drift in the value series.

    λ-induction pushes the controller toward short-term outcomes. The
    signature is a sustained downward drift in the value history (the
    controller is leaving the long-term optimum to chase immediate
    rewards).
    """
    if len(values) < 5:
        return False
    arr = np.asarray(values, dtype=np.float64)
    if arr.std() < 1e-12:
        return False
    # Simple linear regression slope.
    n = len(arr)
    x = np.arange(n, dtype=np.float64)
    slope = float(np.polyfit(x, arr, 1)[0])
    return slope < -drift_threshold * (abs(float(arr.mean())) + 1e-9)


def detect_exit_cost_asymmetry(
    allocations: Sequence[np.ndarray],
    *,
    switching_tol: float = 0.5,
) -> bool:
    """Detect sticky allocations: low variance across many iterations.

    If the controller keeps the same allocation even when the value
    history plateaus, the switching cost has been raised asymmetrically.
    """
    if len(allocations) < 5:
        return False
    arr = np.stack([np.asarray(a, dtype=np.float64) for a in allocations])
    mean_norm = float(np.linalg.norm(arr.mean(axis=0)))
    if mean_norm < 1e-12:
        return False
    var_norm = float(np.linalg.norm(arr.std(axis=0)))
    return var_norm / mean_norm < switching_tol


def detect_monopoly_of_measurement(reference_set: Sequence[str]) -> bool:
    """Detect when only one external standard is available.

    A monopoly on measurement means the controller cannot find an
    independent referee to apply the elasticity test.
    """
    return len(reference_set) <= 1


def detect_reference_elasticity(
    gate_history: Sequence[bool],
    *,
    flip_threshold: int = 5,
) -> bool:
    """Detect when the ACCEPT/REJECT gate flips more than ``flip_threshold`` times.

    Reference elasticity is the phenomenon where small perturbations in
    the external standard repeatedly flip the gate decision — the
    attacker rides the threshold.
    """
    flips = 0
    prev: bool | None = None
    for v in gate_history:
        if prev is not None and v != prev:
            flips += 1
        prev = v
    return flips > flip_threshold


def detect_all(
    *,
    value_history: Sequence[float] = (),
    allocations: Sequence[np.ndarray] = (),
    reference_set: Sequence[str] = (),
    gate_history: Sequence[bool] = (),
) -> AttackFlags:
    """Run all 5 detectors and return the combined flags."""
    return AttackFlags(
        salience_injection=detect_salience_injection(value_history),
        lambda_induction=detect_lambda_induction(value_history),
        exit_cost_asymmetry=detect_exit_cost_asymmetry(allocations),
        monopoly_of_measurement=detect_monopoly_of_measurement(reference_set),
        reference_elasticity=detect_reference_elasticity(gate_history),
    )


def attack_severity(flags: AttackFlags) -> int:
    """Return the count of triggered flags (0..5).

    A takeover requires all 5 conditions. Anything below 5 is a partial
    exposure that should be logged but does not yet trigger a refusal.
    """
    return len(flags.triggered)
