"""Fractal Quantum Cellular Automata (QCA) for Q-SPEACE (task T14).

Implements a recursive, scale-free update of a qubit lattice whose local
rules are fractal (dimension-weighted), reusing the fractal-weighting idea
from the EDD-CVT paper (eq.5: w_ij(t+1) = w_ij + gamma * d^-1.8 * dS).

Goal: macroscopic stability emerges from local rules, measured via
coherence_phi. The "fractality" is *functional* (a scaling rule) and is
kept by the BCEL gate; the biological fractal *shape* is accidental.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .quantum import GateType, QuantumGates, QuantumState


@dataclass
class QCAStepResult:
    tick: int
    coherence_phi: float
    mean_weight: float


class FractalQCA:
    """Fractal-weighted quantum cellular automaton on a 1D qubit ring."""

    def __init__(
        self,
        num_cells: int = 8,
        gamma: float = 0.05,
        fractal_exponent: float = 1.8,
        seed: int = None,
    ) -> None:
        if num_cells < 2:
            raise ValueError("num_cells must be >= 2")
        self.num_cells = num_cells
        self.gamma = gamma
        self.fractal_exponent = fractal_exponent
        self._rng = np.random.default_rng(seed)
        # Initialize weights between neighboring cells.
        self.weights = self._rng.uniform(0.4, 0.6, size=num_cells)
        self.state = QuantumState.equal_superposition(num_cells, seed=seed)

    def _distance_weight(self, a: int, b: int) -> float:
        d = abs(a - b)
        d = min(d, self.num_cells - d)  # ring topology
        d = max(d, 1)
        return d ** (-self.fractal_exponent)

    def step(self, delta_s_info: float = 0.1) -> QCAStepResult:
        """Apply one fractal-weighted update and re-cohere the lattice."""
        new_weights = self.weights.copy()
        for i in range(self.num_cells):
            j = (i + 1) % self.num_cells
            dw = self.gamma * self._distance_weight(i, j) * delta_s_info
            new_weights[i] += dw
        self.weights = np.clip(new_weights, 0.0, 1.0)

        # Apply a rotation to each qubit scaled by its neighborhood weight.
        state = self.state
        for i in range(self.num_cells):
            angle = float(np.pi * self.weights[i])
            u = QuantumGates.single_qubit(GateType.RY, self.num_cells, i, angle)
            state.apply_unitary(u)

        # Coherence proxy from probability concentration.
        probs = state.probabilities()
        entropy = -np.sum(probs * np.log(probs + 1e-12))
        max_entropy = self.num_cells * math.log(2.0)  # 2**num_cells basis states
        coherence_phi = float(1.0 - entropy / max_entropy)

        self.state = state
        return QCAStepResult(
            tick=0,
            coherence_phi=coherence_phi,
            mean_weight=float(np.mean(self.weights)),
        )

    def run(self, ticks: int = 10) -> list[QCAStepResult]:
        results: list[QCAStepResult] = []
        for _ in range(ticks):
            res = self.step()
            results.append(res)
        return results
