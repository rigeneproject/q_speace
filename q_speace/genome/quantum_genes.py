"""Quantum genome — configuration for the Q-SPEACE quantum layer.

Extends the ``QuantumGeneSet`` concept from cellular speace with real-backend
parameters (backend name, shots, noise model) as required by task T4.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

VALID_BACKENDS: tuple[str, ...] = ("numpy", "qiskit", "qiskit-aer", "quantum-inspire")
REAL_BACKENDS: frozenset[str] = frozenset({"qiskit", "qiskit-aer", "quantum-inspire"})
VALID_NOISE_MODELS: tuple[str, ...] = ("ideal", "surface-code", "depolarizing")


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
        if not math.isfinite(self.entanglement_fidelity_threshold) or not (
            0.0 <= self.entanglement_fidelity_threshold <= 1.0
        ):
            raise ValueError("entanglement_fidelity_threshold must be finite and in [0, 1]")
        if not math.isfinite(self.gate_noise) or not (0.0 <= self.gate_noise <= 1.0):
            raise ValueError("gate_noise must be finite and in [0, 1]")
        if self.shots < 1:
            raise ValueError("shots must be >= 1")
        if self.backend_name not in VALID_BACKENDS:
            raise ValueError(f"unknown backend_name: {self.backend_name}")
        if self.noise_model not in VALID_NOISE_MODELS:
            raise ValueError(f"unknown noise_model: {self.noise_model}")
        # AGENTS.md §2 & T208 §3.5: no real quantum backend without a configured noise_model.
        if self.backend_name in REAL_BACKENDS and self.noise_model == "ideal":
            raise ValueError(
                f"real quantum backend {self.backend_name!r} requires a non-ideal "
                "noise_model ('surface-code' or 'depolarizing')"
            )
