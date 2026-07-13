"""EDD-CVT: Informational Logical Field (ILF).

Mirrors the ILF module of cellular speace. Provides coherence_phi (U(1)
and an informational entropy S_info used by the adaptive clock
r(t) = 10 / sqrt(S_info) from the EDD-CVT paper (eq.9).
"""
from __future__ import annotations

import math

import numpy as np


class InformationalLogicalField:
    """Tracks coherence and informational entropy of the organism."""

    def __init__(self, coherence_phi: float = 1.0) -> None:
        self.coherence_phi = float(coherence_phi)

    def update(self, state_vector: np.ndarray) -> None:
        """Update coherence_phi from a normalized activation/state vector."""
        v = np.asarray(state_vector, dtype=float)
        norm = np.sqrt(np.sum(v ** 2))
        if norm > 0:
            v = v / norm
        # Coherence proxy: concentration of mass in few components.
        probs = v ** 2
        entropy = -np.sum(probs * np.log(probs + 1e-12))
        max_entropy = math.log(max(len(probs), 2))
        self.coherence_phi = float(1.0 - entropy / max_entropy)

    @property
    def s_info(self) -> float:
        """Informational entropy proxy in [0, 1] (1 = maximally uncertain)."""
        return float(1.0 - self.coherence_phi)

    def adaptive_clock_rate(self) -> float:
        """r(t) = 10 / sqrt(S_info) from EDD-CVT eq.9.

        Returns a scheduling rate (higher when information is uncertain).
        """
        s = max(self.s_info, 1e-6)
        return 10.0 / math.sqrt(s)
