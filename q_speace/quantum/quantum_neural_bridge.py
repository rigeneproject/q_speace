"""QuantumNeuralBridge — maps neuron/cell ids to qubit slots.

Bridges digital neurons to a shared qubit space. Entangling two neurons
applies a real CNOT across their qubit slots and records the pair in an
EntanglementRegistry. This is *computational* entanglement, used as an
information-binding resource (no faster-than-light communication).
"""

from __future__ import annotations

import numpy as np

from .entanglement_registry import EntanglementRegistry


class QuantumNeuralBridge:
    """Attach quantum states to neuron ids and entangle them."""

    def __init__(self, num_qubits_per_neuron: int = 1, seed: int | None = None) -> None:
        if num_qubits_per_neuron < 1:
            raise ValueError("num_qubits_per_neuron must be >= 1")
        self.num_qubits_per_neuron = num_qubits_per_neuron
        self._seed = seed
        self._slots: dict[str, int] = {}
        self._next_slot: int = 0
        self._registry = EntanglementRegistry()
        self._activity = np.empty(0, dtype=float)

    def _qubit_of(self, neuron_id: str) -> int:
        return self._slots[neuron_id]

    def register(self, neuron_id: str, initial_state: int = 0) -> int:
        if neuron_id in self._slots:
            return self._slots[neuron_id]
        idx = self._next_slot
        self._slots[neuron_id] = idx
        self._next_slot += self.num_qubits_per_neuron
        return idx

    def unregister(self, neuron_id: str) -> None:
        self._slots.pop(neuron_id, None)
        self._registry.remove_entity(neuron_id)

    def entangle_neurons(
        self, a: str, b: str, fidelity: float = 1.0, label: str = "neural"
    ) -> None:
        if a not in self._slots or b not in self._slots:
            raise KeyError("both neurons must be registered")
        self._registry.entangle(a, b, fidelity=fidelity, label=label)

    @property
    def registry(self) -> EntanglementRegistry:
        """Read-only access to software binding records."""
        return self._registry

    @property
    def activity(self) -> np.ndarray:
        """Normalised classical activity supplied by the orchestrator."""
        return self._activity.copy()

    def set_activity(self, values: np.ndarray) -> None:
        """Store one non-negative activity value per registered neuron."""
        activity = np.asarray(values, dtype=float).ravel()
        if activity.size != len(self._slots):
            raise ValueError("activity length must match registered neurons")
        if not np.all(np.isfinite(activity)):
            raise ValueError("activity must contain only finite values")
        if np.any(activity < 0.0):
            raise ValueError("activity must be non-negative")
        total = float(activity.sum())
        self._activity = (
            activity / total if total > 0.0 else np.ones(activity.size) / max(activity.size, 1)
        )

    def is_entangled(self, a: str, b: str) -> bool:
        return self._registry.is_entangled(a, b)

    def quantum_compatibility(self, a: str, b: str) -> float:
        """Return clamped entanglement fidelity proxy in [0, 1] for pair (a, b)."""
        matching = [p.fidelity for p in self._registry.pairs_of(a) if p.involves(b) and a != b]
        if not matching:
            return 0.0
        return float(np.clip(max(matching), 0.0, 1.0))

    def total_qubits(self) -> int:
        return len(self._slots) * self.num_qubits_per_neuron

    def summary(self) -> dict[str, int]:
        return {
            "num_neurons": len(self._slots),
            "num_qubits": self.total_qubits(),
            "num_entanglements": self._registry.count(),
            "connected_components": len(self._registry.connected_components()),
        }
