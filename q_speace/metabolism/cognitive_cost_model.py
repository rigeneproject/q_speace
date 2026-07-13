"""Quantum cognitive cost model (task T10/T22/T23).

Implements two specs from the EDD-CVT paper:
  - Energy per qubit:  E_opt ≈ 0.5 W/qubit  (eq.10)
  - Entropic efficiency: Sevo = ΔU / ΔS_info, target > 1.5  (§5.1)

Q-SPEACE operations are priced by qubit count, gate count, entanglement
depth and decoherence budget, so they can be gated by an energy controller.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QuantumOperation:
    """A quantum computation to be costed."""

    num_qubits: int
    num_gates: int
    entanglement_depth: int = 0
    decoherence_budget: float = 0.0  # expected coherence loss [0,1]


class QuantumCostModel:
    """Costs quantum operations in energy and entropic efficiency."""

    # Baseline from EDD-CVT eq.10: ~0.5 W per qubit.
    W_PER_QUBIT: float = 0.5
    # Gate energy is a fraction of a qubit-second; tunable.
    W_PER_GATE: float = 0.001
    # Entanglement maintenance cost scales with depth.
    W_PER_ENTANGLEMENT_DEPTH: float = 0.01

    def energy_watts(self, op: QuantumOperation) -> float:
        """Instantaneous power draw estimate for the operation."""
        return (
            op.num_qubits * self.W_PER_QUBIT
            + op.num_gates * self.W_PER_GATE
            + op.entanglement_depth * self.W_PER_ENTANGLEMENT_DEPTH
        )

    def energy_joules(self, op: QuantumOperation, duration_s: float = 1.0) -> float:
        return self.energy_watts(op) * duration_s

    @staticmethod
    def sevo(delta_utility: float, delta_entropy_info: float) -> float:
        """Entropic efficiency Sevo = ΔU / ΔS_info (target > 1.5).

        delta_entropy_info must be strictly positive; a collapsing or
        disordering step yields Sevo <= 0 and is rejected by the controller.
        """
        if delta_entropy_info <= 0:
            return float("-inf") if delta_utility > 0 else 0.0
        return delta_utility / delta_entropy_info

    @staticmethod
    def passes_sevo(delta_utility: float, delta_entropy_info: float, threshold: float = 1.5) -> bool:
        return QuantumCostModel.sevo(delta_utility, delta_entropy_info) > threshold
