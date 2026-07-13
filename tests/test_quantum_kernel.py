"""Tests for the Q-SPEACE quantum kernel."""
from __future__ import annotations

import numpy as np
import pytest

from q_speace.quantum import (
    EntanglementRegistry,
    GateType,
    QuantumBrainSimulator,
    QuantumGates,
    QuantumNeuralBridge,
    QuantumState,
)


def test_state_normalization():
    s = QuantumState.equal_superposition(3)
    assert abs(np.sum(np.abs(s.amplitudes) ** 2) - 1.0) < 1e-9


def test_basis_state():
    s = QuantumState(num_qubits=3, initial_state=5)
    assert s.amplitudes[5] == 1.0 + 0j


def test_from_amplitudes():
    s = QuantumState.from_amplitudes([1, 1, 0, 0])
    assert s.num_qubits == 2
    assert abs(np.sum(np.abs(s.amplitudes) ** 2) - 1.0) < 1e-9


def test_hadamard_is_unitary_and_self_inverse():
    U = QuantumGates.single_qubit(GateType.H, 2, 0)
    assert np.max(np.abs(U.conj().T @ U - np.eye(4, dtype=complex))) < 1e-6
    s = QuantumState(num_qubits=1)
    s.apply_unitary(QuantumGates.single_qubit(GateType.H, 1, 0))
    s.apply_unitary(QuantumGates.single_qubit(GateType.H, 1, 0))
    assert abs(s.amplitudes[0] - 1.0) < 1e-9


def test_cnot_creates_bell_state():
    s = QuantumState(num_qubits=2)
    s.apply_unitary(QuantumGates.single_qubit(GateType.H, 2, 0))
    s.apply_unitary(QuantumGates.two_qubit(GateType.CNOT, 2, 0, 1))
    probs = s.probabilities()
    # Bell state: only |00> and |11> have probability.
    assert abs(probs[0] - 0.5) < 1e-9
    assert abs(probs[3] - 0.5) < 1e-9


def test_measure_collapses():
    s = QuantumState.equal_superposition(2)
    mr = s.measure()
    assert len(mr.bitstring) == 2
    assert abs(np.sum(np.abs(s.amplitudes) ** 2) - 1.0) < 1e-9


def test_entanglement_registry_components():
    reg = EntanglementRegistry()
    reg.entangle("a", "b")
    reg.entangle("b", "c")
    comps = reg.connected_components()
    assert len(comps) == 1
    assert reg.degree("b") == 2


def test_quantum_neural_bridge():
    bridge = QuantumNeuralBridge(num_qubits_per_neuron=1)
    bridge.register("n0")
    bridge.register("n1")
    bridge.entangle_neurons("n0", "n1")
    summary = bridge.summary()
    assert summary["num_neurons"] == 2
    assert summary["num_entanglements"] == 1
    assert summary["connected_components"] == 1


def test_brain_simulator_bell():
    sim = QuantumBrainSimulator()
    circ = __import__("q_speace.quantum", fromlist=["BrainQuantumCircuit"]).BrainQuantumCircuit("bell")
    circ.add_qubit("a")
    circ.add_qubit("b")
    circ.add_gate(GateType.H, target="a")
    circ.add_gate(GateType.CNOT, control="a", target="b")
    sim.run(circ)
    state = sim.state(circ)
    probs = state.probabilities()
    assert abs(probs[0] - 0.5) < 1e-9 and abs(probs[3] - 0.5) < 1e-9
