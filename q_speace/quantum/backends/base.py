"""Quantum backend abstraction for Q-SPEACE (task T5 / Quantum Inspire).

A backend executes a :class:`BrainQuantumCircuit` and returns measurement
outcomes. The numpy backend is the default and always available; the
Quantum Inspire backend is lazy-loaded and requires an account token
(human action) plus the QI SDK. This keeps cloud access optional and
gated, never a hard dependency.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class QuantumBackend(ABC):
    """Executes named-role circuits and returns measurements."""

    name: str = "abstract"

    @abstractmethod
    def run(
        self, circuit, shots: int = 1024
    ) -> list[tuple[str, str]]:
        """Run the circuit and return [(role, bit), ...] for all qubits."""
        raise NotImplementedError


class NumpyBackend(QuantumBackend):
    """Reference backend using the local numpy QuantumBrainSimulator."""

    name = "numpy"

    def __init__(self, seed: int = None) -> None:
        from ..quantum_brain_simulator import QuantumBrainSimulator

        self._sim = QuantumBrainSimulator(seed=seed)

    def run(self, circuit, shots: int = 1024) -> list[tuple[str, str]]:
        # shots is ignored by the deterministic numpy simulator.
        return self._sim.run(circuit)
