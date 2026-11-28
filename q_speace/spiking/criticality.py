"""Branching-ratio criticality homeostasis for pseudo-spiking (T248).

Synthesized via BCEL from ``speace_ds/neuromodulation/criticality.py``:
cortical neuronal avalanche and seizure narratives are *accidental* and
removed; only the closed-loop empirical branching-ratio gain controller
regulating ``dynamic_spikes`` threshold divisor ``k`` survives in silicon.

In ``dynamic_spikes(x, k=...)``, ``vth = mean(|x|) / k``:
- Larger ``k`` lowers ``vth`` -> increases spike sensitivity (counters sub-criticality).
- Smaller ``k`` raises ``vth`` -> increases inhibition (counters super-criticality).
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Literal

CriticalityRegime = Literal["sub_critical", "critical", "super_critical"]


@dataclass(frozen=True)
class CriticalityState:
    """Immutable telemetry snapshot of one criticality control step."""

    branching_ratio: float
    regime: CriticalityRegime
    updated_k: float
    delta_k: float
    sample_count: int


class CriticalityController:
    """Closed-loop branching-ratio regulator for ``dynamic_spikes`` divisor ``k``."""

    def __init__(
        self,
        target_sigma: float = 1.0,
        kp: float = 0.25,
        k_min: float = 0.5,
        k_max: float = 10.0,
        low_band: float = 0.85,
        high_band: float = 1.15,
        window: int = 16,
    ) -> None:
        for name, val in (
            ("target_sigma", target_sigma),
            ("kp", kp),
            ("k_min", k_min),
            ("k_max", k_max),
            ("low_band", low_band),
            ("high_band", high_band),
        ):
            if not math.isfinite(val):
                raise ValueError(f"{name} must be finite (got {val!r})")
        if target_sigma <= 0.0:
            raise ValueError("target_sigma must be > 0")
        if kp < 0.0:
            raise ValueError("kp must be >= 0")
        if k_min <= 0.0 or k_max < k_min:
            raise ValueError("0 < k_min <= k_max is required")
        if low_band <= 0.0 or high_band < low_band:
            raise ValueError("0 < low_band <= high_band is required")
        if window < 2:
            raise ValueError("window must be >= 2")

        self.target_sigma = float(target_sigma)
        self.kp = float(kp)
        self.k_min = float(k_min)
        self.k_max = float(k_max)
        self.low_band = float(low_band)
        self.high_band = float(high_band)
        self._counts: deque[int] = deque(maxlen=window)

    def reset(self) -> None:
        """Clear recorded spike-count window."""
        self._counts.clear()

    def empirical_branching_ratio(self) -> float:
        """Return the rolling Laplace-smoothed branching ratio as a ratio of sums.

        ``sigma = sum_t (S_t + 1) / sum_t (S_{t-1} + 1)`` over the window.

        T265 fix: the previous mean-of-ratios form ``E[(S_t + 1)/(S_{t-1} + 1)]`` is biased
        above 1 for any stationary noisy activity (Jensen), e.g. ~1.19 for Poisson(4), which
        drove ``k`` to ``k_min`` under perfectly stationary input. The ratio of sums is 1 for
        stationary activity and equals the growth factor for geometric growth or decay.
        """
        if len(self._counts) < 2:
            return self.target_sigma
        items = list(self._counts)
        num = sum(c + 1.0 for c in items[1:])
        den = sum(c + 1.0 for c in items[:-1])
        return float(num / den)

    def classify_regime(self, sigma: float) -> CriticalityRegime:
        if sigma < self.low_band:
            return "sub_critical"
        if sigma > self.high_band:
            return "super_critical"
        return "critical"

    def step(self, num_spikes: int, current_k: float) -> CriticalityState:
        """Record ``num_spikes`` and compute bounded closed-loop update for ``current_k``."""
        if isinstance(num_spikes, bool) or num_spikes < 0:
            raise ValueError(f"num_spikes must be an int >= 0 (got {num_spikes!r})")
        if not math.isfinite(current_k) or current_k <= 0.0:
            raise ValueError(f"current_k must be finite and > 0 (got {current_k!r})")

        self._counts.append(int(num_spikes))
        sigma = self.empirical_branching_ratio()
        regime = self.classify_regime(sigma)

        if len(self._counts) < 2:
            clamped_k = min(max(float(current_k), self.k_min), self.k_max)
            return CriticalityState(
                branching_ratio=sigma,
                regime=regime,
                updated_k=clamped_k,
                delta_k=clamped_k - float(current_k),
                sample_count=len(self._counts),
            )

        # Negative feedback: sub-critical (sigma < target) -> error > 0 -> raise k -> lower vth.
        # Also handle silent collapse (all recent counts == 0 -> sigma == 1.0 despite silence):
        if all(c == 0 for c in self._counts):
            regime = "sub_critical"
            raw_delta = self.kp * 0.5
        else:
            raw_delta = self.kp * (self.target_sigma - sigma)

        updated_k = min(max(float(current_k) + raw_delta, self.k_min), self.k_max)
        return CriticalityState(
            branching_ratio=sigma,
            regime=regime,
            updated_k=updated_k,
            delta_k=updated_k - float(current_k),
            sample_count=len(self._counts),
        )
