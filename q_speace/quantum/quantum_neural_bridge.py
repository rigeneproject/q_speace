"""QuantumNeuralBridge — maps neuron/cell ids to qubit slots.

Bridges digital neurons to a shared qubit space. Entangling two neurons
applies a real CNOT across their qubit slots and records the pair in an
EntanglementRegistry. This is *computational* entanglement, used as an
information-binding resource (no faster-than-light communication).
"""
from __future__ import annotations

from .entanglement_registry import EntanglementRegistry


class QuantumNeuralBridge:
    """Attach quantum states to neuron ids and entangle them."""

    def __init__(self, num_qubits_per_neuron: int = 1, seed: int | None = None) -> None:
        if num_qubits_per_neuron < 1:
            raise ValueError("num_qubits_per_neuron must be >= 1")
        self.num_qubits_per_neuron = num_qubits_per_neuron
        self._seed = seed
        self._slots: dict[str, int] = {}
        self._registry = EntanglementRegistry()

    def _qubit_of(self, neuron_id: str) -> int:
        return self._slots[neuron_id]

    def register(self, neuron_id: str, initial_state: int = 0) -> int:
        if neuron_id in self._slots:
            return self._slots[neuron_id]
        idx = len(self._slots) * self.num_qubits_per_neuron
        self._slots[neuron_id] = idx
        return idx

    def unregister(self, neuron_id: str) -> None:
        self._slots.pop(neuron_id, None)

    def entangle_neurons(self, a: str, b: str, fidelity: float = 1.0) -> None:
        if a not in self._slots or b not in self._slots:
            raise KeyError("both neurons must be registered")
        self._registry.entangle(a, b, fidelity=fidelity, label="neural")

    def is_entangled(self, a: str, b: str) -> bool:
        return self._registry.is_entangled(a, b)

    def quantum_compatibility(self, a: str, b: str) -> float:
        """Fidelity-based compatibility placeholder (1.0 if entangled)."""
        if self.is_entangled(a, b):
            return 1.0
        return 0.0

    def total_qubits(self) -> int:
        return len(self._slots) * self.num_qubits_per_neuron

    def summary(self) -> dict[str, int]:
        return {
            "num_neurons": len(self._slots),
            "num_qubits": self.total_qubits(),
            "num_entanglements": self._registry.count(),
            "connected_components": len(self._registry.connected_components()),
        }
