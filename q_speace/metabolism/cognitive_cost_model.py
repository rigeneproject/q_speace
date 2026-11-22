"""Quantum cognitive cost model (task T10/T22/T23).

Implements two specs from the EDD-CVT paper:
  - Energy per qubit:  E_opt ≈ 0.5 W/qubit  (eq.10)
  - Entropic efficiency: Sevo = ΔU / ΔS_info, target > 1.5  (§5.1)

Q-SPEACE operations are priced by qubit count, gate count, entanglement
depth and decoherence budget, so they can be gated by an energy controller.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class QuantumOperation:
    """A quantum computation to be costed."""

    num_qubits: int
    num_gates: int
    entanglement_depth: int = 0
    decoherence_budget: float = 0.0  # expected coherence loss [0,1]
    num_spikes: int = 0  # sparse event count; zero preserves T10 behaviour

    def validate(self) -> None:
        if self.num_qubits < 0:
            raise ValueError(f"num_qubits must be >= 0 (got {self.num_qubits})")
        if self.num_gates < 0:
            raise ValueError(f"num_gates must be >= 0 (got {self.num_gates})")
        if self.entanglement_depth < 0:
            raise ValueError(f"entanglement_depth must be >= 0 (got {self.entanglement_depth})")
        if not math.isfinite(self.decoherence_budget) or self.decoherence_budget < 0.0:
            raise ValueError(
                f"decoherence_budget must be finite and >= 0 (got {self.decoherence_budget})"
            )


class QuantumCostModel:
    """Costs quantum operations in energy and entropic efficiency."""

    # Baseline from EDD-CVT eq.10: ~0.5 W per qubit.
    W_PER_QUBIT: float = 0.5
    # Gate energy is a fraction of a qubit-second; tunable.
    W_PER_GATE: float = 0.001
    # Entanglement maintenance cost scales with depth.
    W_PER_ENTANGLEMENT_DEPTH: float = 0.01
    # Decoherence penalty (extra power to maintain fidelity).
    W_PER_DECOHERENCE_UNIT: float = 0.1
    W_PER_SPIKE: float = 0.001

    # Calibration factor derived from T205-C (64 prompt × Qwen2.5-3B NF4
    # on RTX 3060 6 GB — see docs/T205_status.md). Median ratio
    # pred/meas over 64 valid rows was 0.0323 → 1/0.0323 ≈ 30.94. This
    # factor rescales the absolute magnitude of every term uniformly,
    # preserving the functional form (slope log-log ≈ 1 was confirmed
    # with resid_std = 0.086). To restore the original T10/T22/T23
    # presetting, set RICALIBRATION_FACTOR = 1.0.
    RICALIBRATION_FACTOR: float = 30.94

    def energy_watts(self, op: QuantumOperation) -> float:
        """Instantaneous power draw estimate for the operation.

        Decoherence budget increases the cost: a higher budget means the
        system must expend more energy to maintain the desired fidelity.
        """
        op.validate()
        if not math.isfinite(self.RICALIBRATION_FACTOR) or self.RICALIBRATION_FACTOR <= 0.0:
            raise ValueError(
                f"RICALIBRATION_FACTOR must be finite and > 0 (got {self.RICALIBRATION_FACTOR})"
            )
        base = (
            op.num_qubits * self.W_PER_QUBIT
            + op.num_gates * self.W_PER_GATE
            + op.entanglement_depth * self.W_PER_ENTANGLEMENT_DEPTH
            + op.decoherence_budget * self.W_PER_DECOHERENCE_UNIT
            + max(op.num_spikes, 0) * self.W_PER_SPIKE
        )
        return float(base * self.RICALIBRATION_FACTOR)

    def energy_joules(self, op: QuantumOperation, duration_s: float = 1.0) -> float:
        if not math.isfinite(duration_s) or duration_s < 0.0:
            raise ValueError(f"duration_s must be finite and >= 0 (got {duration_s})")
        return float(self.energy_watts(op) * duration_s)

    @staticmethod
    def sevo(delta_utility: float, delta_entropy_info: float) -> float:
        """Entropic efficiency Sevo = ΔU / ΔS_info (target > 1.5).

        delta_entropy_info must be strictly positive; a collapsing,
        disordering, or non-finite step yields Sevo <= 0 (fail-closed)
        and is rejected by the controller.
        """
        if not (math.isfinite(delta_utility) and math.isfinite(delta_entropy_info)):
            return float("-inf")
        if delta_entropy_info <= 0:
            return float("-inf") if delta_utility > 0 else 0.0
        return float(delta_utility / delta_entropy_info)

    @staticmethod
    def passes_sevo(
        delta_utility: float, delta_entropy_info: float, threshold: float = 1.5
    ) -> bool:
        if not math.isfinite(threshold):
            return False
        return QuantumCostModel.sevo(delta_utility, delta_entropy_info) > threshold
