"""Frequency-based plasticity coefficients (T202 P-plasticity).

A spike-history EMA produces per-unit plasticity coefficients in [0, 1].
The biological STDP mechanism is *accidental* (BCEL gate); only the
exponential moving-average decay rule survives in silicon:

    ema_i(t) = decay * ema_i(t-1) + (1 - decay) * rate_i(t)
    plasticity_i = exp(-lambda * dt) * rate_i      (static form)

Coefficients can scale entanglement fidelity (T202 P3), modulate spike
energy or bridge weights — without any online backpropagation.
"""

from __future__ import annotations

import math

import numpy as np


class SpikePlasticity:
    """Exponential moving average of per-unit spike activity."""

    def __init__(self, num_units: int = 1, decay: float = 0.9, seed: int | None = None) -> None:
        if num_units < 1:
            raise ValueError("num_units must be >= 1")
        if not 0.0 < decay < 1.0:
            raise ValueError("decay must be in (0, 1)")
        self.num_units = num_units
        self.decay = decay
        self._seed = seed
        self._ema = np.zeros(num_units, dtype=float)

    def _rates(self, spikes: np.ndarray) -> np.ndarray:
        s = np.asarray(spikes, dtype=float)
        rate = np.abs(s) if s.ndim == 1 else np.abs(s).sum(axis=-1)
        if rate.size != self.num_units:
            raise ValueError(f"spike activity must yield {self.num_units} units, got {rate.size}")
        rate_typed: np.ndarray = rate
        return rate_typed

    def update(self, spikes: np.ndarray) -> np.ndarray:
        """Update the EMA from a spike array; returns the new raw EMA."""
        rate: np.ndarray = self._rates(spikes)
        self._ema = self.decay * self._ema + (1.0 - self.decay) * rate
        out: np.ndarray = self._ema.copy()
        return out

    def coefficients(self) -> np.ndarray:
        """Plasticity coefficients in [0, 1], normalized across units."""
        m = float(np.max(self._ema))
        if m <= 0.0:
            return np.zeros_like(self._ema)
        return self._ema / m

    @staticmethod
    def decayed_rate(rate: float, dt: float, lam: float = 0.1) -> float:
        """Static plasticity rule: exp(-lambda * dt) * rate."""
        return math.exp(-lam * dt) * rate
