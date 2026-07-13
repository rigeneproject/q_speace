"""EDD-CVT: Cosmic Viruses (CV) stochastic optimizer.

Implements the CV-driven weight dynamics from the EDD-CVT paper (eq.3-4):
    dW/dt = alpha * CV(t) - beta * H(W)
    CV(t) = eta(t) * grad S_info,  eta(t) ~ N(0, sigma)

CV acts as a stochastic-resonance perturbation that drives continuous
self-optimization. It is a *functional* biological analogy (kept as a
mathematical rule by the BCEL gate), not a literal virus.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np


@dataclass
class CVConfig:
    alpha: float = 0.1
    beta: float = 0.05
    sigma: float = 0.01
    seed: int | None = None


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
        w = np.asarray(weights, dtype=float)
        grad = np.asarray(gradient_s_info, dtype=float)
        eta = self._rng.normal(0.0, self.config.sigma, size=w.shape)
        cv = eta * grad
        dw = self.config.alpha * cv - self.config.beta * w
        return w + dt * dw

    def optimize(
        self,
        weights: np.ndarray,
        gradient_fn: Callable[[np.ndarray], np.ndarray],
        steps: int = 50,
        dt: float = 1.0,
    ) -> np.ndarray:
        w = np.asarray(weights, dtype=float).copy()
        for _ in range(steps):
            w = self.step(w, gradient_fn(w), dt=dt)
        return w
