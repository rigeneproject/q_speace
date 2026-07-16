"""Tests for QuantumNeuralBridge integration with DigitalNeurons."""
import pytest

from speace_core.cellular_brain.cells.digital_neuron import DigitalNeuron
from speace_core.cellular_brain.quantum.quantum_neural_bridge import QuantumNeuralBridge


def test_bridge_registers_neuron_from_cell_id():
    bridge = QuantumNeuralBridge(num_qubits_per_neuron=1)
    n = DigitalNeuron(cell_id="n_1", role="digital_neuron")
    slot = bridge.register(n.cell_id)
    assert slot.cell_id == "n_1"
    assert slot.num_qubits == 1
    assert n.cell_id in bridge.slots


def test_bridge_entangles_two_neurons():
    bridge = QuantumNeuralBridge(num_qubits_per_neuron=1)
    a = DigitalNeuron(cell_id="a", role="digital_neuron")
    b = DigitalNeuron(cell_id="b", role="digital_neuron")
    bridge.register(a.cell_id)
    bridge.register(b.cell_id)
    pair = bridge.entangle_neurons(a.cell_id, b.cell_id, fidelity=0.8, label="test")
    assert pair.entity_a == "a"
    assert pair.entity_b == "b"
    assert bridge.entanglements.count() == 1


def test_quantum_compatibility_returns_score():
    bridge = QuantumNeuralBridge(num_qubits_per_neuron=1)
    a = DigitalNeuron(cell_id="a", role="digital_neuron")
    b = DigitalNeuron(cell_id="b", role="digital_neuron")
    bridge.register(a.cell_id, initial_state=0)
    bridge.register(b.cell_id, initial_state=0)
    score = bridge.quantum_compatibility(a.cell_id, b.cell_id)
    assert 0.0 <= score <= 1.0
