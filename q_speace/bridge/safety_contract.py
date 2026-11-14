"""Bridge-v0 observation-latency-aware safety contract (T218-T04, SAF-01).

Resolves review item SYS-C1: invariance claims are formulated on the
physical state, but the supervisor decides from uncertain, delayed
observations. The contract therefore validates a candidate action on
an explicit *reachable tube*:

1. inflate the estimate ``x̂`` by the declared observation error
   ``epsilon_obs``;
2. propagate the interval through ``age`` control steps of the declared
   hold input (data age until actuation);
3. apply the candidate action and propagate ``horizon_steps`` more;
4. require every reachable state to lie inside ``X_safe``.

If the observation age exceeds the declared maximum, or a critical
input is missing, the verdict is ``UNKNOWN`` and the caller must enter
the declared conservative mode — never "asserted safety".

The plant is supplied as an *interval extension* of the discrete-time
step function ``f``; this keeps the propagation conservative without
assuming monotonicity of ``f``. All operations are numpy-only.

BCEL: interval propagation is a *functional* numerical rule (a
conservative over-approximation of reachable states). No claim about
certainty of the physical world is implied — the verdict UNKNOWN is
first-class, mirroring the measurement-integrity clause of §9.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

import numpy as np


class VerdictKind(StrEnum):
    SAFE = "SAFE"
    UNSAFE = "UNSAFE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class SafetyVerdict:
    kind: VerdictKind
    reason: str
    reachable_lo: np.ndarray | None = None
    reachable_hi: np.ndarray | None = None


IntervalStep = Callable[[np.ndarray, np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray]]
"""Interval extension of f: (x_lo, x_hi, u) -> (x_next_lo, x_next_hi)."""


def _check_interval(x_lo: np.ndarray, x_hi: np.ndarray, name: str) -> None:
    if x_lo.shape != x_hi.shape:
        raise ValueError(f"{name}: interval bounds must share shape")
    if np.any(x_lo > x_hi):
        raise ValueError(f"{name}: interval is empty (lo > hi)")


class SafetyContract:
    """Validates candidate actions on the observation-delay reachable tube."""

    def __init__(
        self,
        x_safe_lower: np.ndarray,
        x_safe_upper: np.ndarray,
        *,
        epsilon_obs: np.ndarray,
        max_age_steps: int,
        hold_input: np.ndarray,
        horizon_steps: int = 1,
    ) -> None:
        if np.any(x_safe_lower > x_safe_upper):
            raise ValueError("X_safe bounds are inconsistent")
        if np.any(epsilon_obs < 0.0):
            raise ValueError("epsilon_obs must be non-negative")
        if max_age_steps < 0 or horizon_steps < 1:
            raise ValueError("max_age_steps >= 0 and horizon_steps >= 1 required")
        self._lower = np.asarray(x_safe_lower, dtype=np.float64)
        self._upper = np.asarray(x_safe_upper, dtype=np.float64)
        self._eps = np.asarray(epsilon_obs, dtype=np.float64)
        self._max_age = max_age_steps
        self._hold = np.asarray(hold_input, dtype=np.float64)
        self._horizon = horizon_steps

    @property
    def max_age_steps(self) -> int:
        return self._max_age

    def check_action(
        self,
        x_hat: np.ndarray,
        *,
        age_steps: int,
        action: np.ndarray | None,
        step: IntervalStep,
    ) -> SafetyVerdict:
        """Validate ``action`` against the reachable tube.

        Returns ``UNKNOWN`` when data is stale or the action is missing:
        the caller must then enter the declared conservative mode.
        """
        x_hat = np.asarray(x_hat, dtype=np.float64)
        if action is None:
            return SafetyVerdict(VerdictKind.UNKNOWN, "missing critical action input")
        if age_steps < 0:
            raise ValueError("age_steps must be non-negative")
        if age_steps > self._max_age:
            return SafetyVerdict(
                VerdictKind.UNKNOWN,
                f"observation age {age_steps} > max age {self._max_age}: "
                "conservative mode required",
            )
        action = np.asarray(action, dtype=np.float64)
        # 1. inflate the estimate by the declared observation error
        x_lo = x_hat - self._eps
        x_hi = x_hat + self._eps
        _check_interval(x_lo, x_hi, "inflated estimate")

        def inflate(lo: np.ndarray, hi: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
            # Declared per-step uncertainty growth: bounded plant noise and
            # discretisation error widen the tube by epsilon_obs each step.
            return lo - self._eps, hi + self._eps

        # 2. propagate through the data-age window under the hold input,
        #    inflating by epsilon_obs each step (uncertainty about the state
        #    grows while the decision is based on stale data)
        for _ in range(age_steps):
            x_lo, x_hi = step(x_lo, x_hi, self._hold)
            x_lo, x_hi = inflate(x_lo, x_hi)
            _check_interval(x_lo, x_hi, "age propagation")
        # 3. apply the candidate action for the declared horizon: the
        #    validated action is applied deterministically on the tube,
        #    so no observation-error inflation occurs here
        for _ in range(self._horizon):
            x_lo, x_hi = step(x_lo, x_hi, action)
            _check_interval(x_lo, x_hi, "action propagation")
        # 4. containment test
        if np.any(x_lo < self._lower) or np.any(x_hi > self._upper):
            return SafetyVerdict(
                VerdictKind.UNSAFE,
                "reachable tube leaves X_safe under declared uncertainty",
                x_lo,
                x_hi,
            )
        return SafetyVerdict(
            VerdictKind.SAFE,
            "reachable tube contained in X_safe",
            x_lo,
            x_hi,
        )
