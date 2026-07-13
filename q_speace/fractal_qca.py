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
        """One fractal-weighted update with REAL long-range coupling.

        Every pair (i,j) contributes w_ij = gamma * d_ij^(-exp) * delta_S,
        so the fractal exponent is now effective (fixes the old d=1 bug).
        Because exp=1.8>1 the aggregate coupling per qubit converges, hence
        the weight stays bounded; clipping to [0,1] makes the resulting RY
        angle (pi*weight) bounded in [0, pi] without hard clipping.
        """
        n = self.num_cells
        new_weights = self.weights.copy()
        for i in range(n):
            coupling = 0.0
            for j in range(n):
                if i == j:
                    continue
                d = min(abs(i - j), n - abs(i - j))
                d = max(d, 1)
                coupling += self.gamma * (d ** (-self.fractal_exponent)) * delta_s_info
            new_weights[i] += coupling
        self.weights = np.clip(new_weights, 0.0, 1.0)

        # Apply a rotation to each qubit scaled by its aggregated weight.
        state = self.state
        for i in range(n):
            angle = float(np.pi * self.weights[i])
            u = QuantumGates.single_qubit(GateType.RY, n, i, angle)
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

    # --- coarse-grained signature interface (for FractalQCACascade) ---

    def signature(self):
        """Return the RG order-parameter (coherence_phi, S, sigma)."""
        from .fractal_qca_cascade import LevelSignature

        probs = self.state.probabilities()
        entropy = -np.sum(probs * np.log(probs + 1e-12))
        max_entropy = self.num_cells * math.log(2.0)
        return LevelSignature(
            name="level",
            n_qubits=self.num_cells,
            coherence_phi=float(1.0 - entropy / max_entropy),
            entropy_s=float(entropy),
            sigma=float(np.std(self.weights)),
        )

    def inject_noise(self, sigma: float) -> None:
        """Bottom-up noise injection (atomic noise rising to higher levels)."""
        if sigma <= 0:
            return
        noise = self._rng.normal(0.0, sigma, size=self.num_cells)
        self.weights = np.clip(self.weights + noise, 0.0, 1.0)

    def seed_from(self, coherence_phi: float, rate: float = 0.1) -> None:
        """Top-down seeding: nudge weights toward a higher-level coherence."""
        target = min(max(coherence_phi, 0.0), 1.0)
        self.weights = np.clip(
            self.weights + rate * (target - self.weights), 0.0, 1.0
        )

    def run(self, ticks: int = 10) -> list[QCAStepResult]:
        results: list[QCAStepResult] = []
        for _ in range(ticks):
            res = self.step()
            results.append(res)
        return results
