"""Quantum genome — configuration for the Q-SPEACE quantum layer.

Extends the ``QuantumGeneSet`` concept from cellular speace with real-backend
parameters (backend name, shots, noise model) as required by task T4.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class QuantumGeneSet:
    """Genome section controlling the quantum substrate.

    Maps neural-periodic blocks to qubit counts and configures an optional
    real backend (Qiskit/Aer) behind the numpy emulator.
    """

    enabled: bool = False
    qubits_per_neuron: int = 1
    default_initial_state: int = 0
    entanglement_fidelity_threshold: float = 0.5
    gate_noise: float = 0.0
    periodic_element_qubit_map: dict[str, int] = field(
        default_factory=lambda: {"s": 1, "p": 2, "d": 2, "f": 1, "g": 1}
    )
    # --- real-backend extensions (task T4) ---
    backend_name: str = "numpy"  # "numpy" | "qiskit" | "qiskit-aer" | "quantum-inspire"
    shots: int = 1024
    noise_model: str = "ideal"  # "ideal" | "surface-code" | "depolarizing"

    def validate(self) -> None:
        if self.qubits_per_neuron < 1:
            raise ValueError("qubits_per_neuron must be >= 1")
        if not (0.0 <= self.entanglement_fidelity_threshold <= 1.0):
            raise ValueError("entanglement_fidelity_threshold must be in [0, 1]")
        if self.noise_model not in ("ideal", "surface-code", "depolarizing"):
            raise ValueError(f"unknown noise_model: {self.noise_model}")
