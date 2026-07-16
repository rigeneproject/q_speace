"""Quantum layer for SPEACE — concrete computational primitives.

This module provides a lightweight, numpy-based quantum simulator that
augments the existing resonance/ and neuroperiodic/ layers with
*real* (not metaphorical) quantum primitives: complex state vectors,
unitary gates, entanglement, and measurement.

Goals:
  - Stay small (numpy only, no Qiskit/Cirq dependency).
  - Stay integrable: QuantumState can attach to a DigitalNeuron or
    a ResonanceField without changing their existing APIs.
  - Be testable: all gates produce numerically correct unitaries.

Public API:
  - QuantumState: complex state vector with apply_gate / measure
  - QuantumGates: factory of standard gates (H, X, Y, Z, CNOT, Rx, Ry, Rz)
  - EntanglementRegistry: track entangled (DigitalNeuron, DigitalNeuron) pairs
  - QuantumBrainSimulator: orchestrate a small quantum brain circuit
  - QuantumNeuralBridge: bridge between quantum layer and DigitalNeurons
"""

from speace_core.cellular_brain.quantum.quantum_state import (
    QuantumState,
    MeasurementResult,
)
from speace_core.cellular_brain.quantum.quantum_gates import (
    QuantumGates,
    GateType,
)
from speace_core.cellular_brain.quantum.entanglement_registry import (
    EntanglementRegistry,
    EntangledPair,
)
from speace_core.cellular_brain.quantum.quantum_brain_simulator import (
    QuantumBrainSimulator,
    BrainQuantumCircuit,
)
from speace_core.cellular_brain.quantum.quantum_neural_bridge import (
    QuantumNeuralBridge,
    attach_quantum_state,
)

__all__ = [
    "QuantumState",
    "MeasurementResult",
    "QuantumGates",
    "GateType",
    "EntanglementRegistry",
    "EntangledPair",
    "QuantumBrainSimulator",
    "BrainQuantumCircuit",
    "QuantumNeuralBridge",
    "attach_quantum_state",
]
