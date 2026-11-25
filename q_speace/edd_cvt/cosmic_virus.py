"""EDD-CVT: Cosmic Viruses (CV) stochastic optimizer.

Implements the CV-driven weight dynamics from the EDD-CVT paper (eq.3-4):
    dW/dt = alpha * CV(t) - beta * H(W)
    CV(t) = eta(t) * grad S_info,  eta(t) ~ N(0, sigma)

CV acts as a stochastic-resonance perturbation that drives continuous
self-optimization. It is a *functional* biological analogy (kept as a
mathematical rule by the BCEL gate), not a literal virus.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np


@dataclass
class CVConfig:
    alpha: float = 0.1
    beta: float = 0.05
    sigma: float = 0.01
    seed: int | None = None

    def __post_init__(self) -> None:
        if not math.isfinite(self.alpha):
            raise ValueError("alpha must be finite")
        if not math.isfinite(self.beta):
            raise ValueError("beta must be finite")
        if not math.isfinite(self.sigma) or self.sigma < 0.0:
            raise ValueError("sigma must be finite and >= 0")


class CosmicVirusOptimizer:
    """Stochastic optimizer driven by Cosmic Virus perturbations."""

    def __init__(self, config: CVConfig | None = None) -> None:
        self.config = config or CVConfig()
        self._rng = np.random.default_rng(self.config.seed)

    def step(
        self,
        weights: np.ndarray,
        gradient_s_info: np.ndarray,
        dt: float = 1.0,
    ) -> np.ndarray:
        """One CV update of the weight matrix W."""
        if not math.isfinite(dt) or dt < 0.0:
            raise ValueError("dt must be finite and >= 0")
        w = np.asarray(weights, dtype=float)
        grad = np.asarray(gradient_s_info, dtype=float)
        if w.shape != grad.shape:
            raise ValueError(f"weights shape {w.shape} must match gradient shape {grad.shape}")
        if not np.all(np.isfinite(w)) or not np.all(np.isfinite(grad)):
            raise ValueError("weights and gradient_s_info must contain only finite values")
        eta = self._rng.normal(0.0, self.config.sigma, size=w.shape)
        cv = eta * grad
        dw = self.config.alpha * cv - self.config.beta * w
        return np.asarray(w + dt * dw, dtype=float)

    def optimize(
        self,
        weights: np.ndarray,
        gradient_fn: Callable[[np.ndarray], np.ndarray],
        steps: int = 50,
        dt: float = 1.0,
    ) -> np.ndarray:
        if steps < 0:
            raise ValueError("steps must be >= 0")
        w = np.asarray(weights, dtype=float).copy()
        if not np.all(np.isfinite(w)):
            raise ValueError("weights must contain only finite values")
        for _ in range(steps):
            w = self.step(w, gradient_fn(w), dt=dt)
        return w
