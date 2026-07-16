"""Tests for the QuantumGates factory."""
import math
import numpy as np
import pytest

from speace_core.cellular_brain.quantum.quantum_gates import GateType, QuantumGates
from speace_core.cellular_brain.quantum.quantum_state import QuantumState


def _is_unitary(u, tol=1e-6):
    diff = u.conj().T @ u - np.eye(u.shape[0], dtype=np.complex128)
    return np.max(np.abs(diff)) < tol


class TestQuantumGates:
    def test_hadamard_is_unitary(self):
        u = QuantumGates.single_qubit(GateType.H, num_qubits=1, target=0)
        assert _is_unitary(u)

    def test_pauli_gates_are_unitary(self):
        for g in (GateType.X, GateType.Y, GateType.Z, GateType.S, GateType.T):
            u = QuantumGates.single_qubit(g, num_qubits=2, target=1)
            assert _is_unitary(u), f"{g} not unitary"

    def test_rotation_gates_are_unitary(self):
        for g in (GateType.RX, GateType.RY, GateType.RZ):
            u = QuantumGates.single_qubit(g, num_qubits=3, target=2, angle=math.pi / 4)
            assert _is_unitary(u), f"{g} not unitary"

    def test_hadamard_squared_is_identity(self):
        H = QuantumGates.single_qubit(GateType.H, num_qubits=1, target=0)
        H2 = H @ H
        assert np.allclose(H2, np.eye(2, dtype=np.complex128), atol=1e-6)

    def test_pauli_x_flips(self):
        qs = QuantumState(num_qubits=1, initial_state=0)
        X = QuantumGates.single_qubit(GateType.X, num_qubits=1, target=0)
        qs.apply_unitary(X)
        assert np.isclose(qs.amplitudes[1], 1.0)

    def test_hadamard_creates_superposition(self):
        qs = QuantumState(num_qubits=1, initial_state=0)
        H = QuantumGates.single_qubit(GateType.H, num_qubits=1, target=0)
        qs.apply_unitary(H)
        assert np.isclose(abs(qs.amplitudes[0]), 1.0 / math.sqrt(2.0))
        assert np.isclose(abs(qs.amplitudes[1]), 1.0 / math.sqrt(2.0))

    def test_cnot_unitary(self):
        u = QuantumGates.two_qubit(GateType.CNOT, num_qubits=2, control=0, target=1)
        assert _is_unitary(u)

    def test_cnot_bell_state(self):
        qs = QuantumState(num_qubits=2, initial_state=0)
        H = QuantumGates.single_qubit(GateType.H, num_qubits=2, target=0)
        cnot = QuantumGates.two_qubit(GateType.CNOT, num_qubits=2, control=0, target=1)
        qs.apply_unitary(H)
        qs.apply_unitary(cnot)
        # |Phi+> = (|00> + |11>) / sqrt(2)
        assert np.isclose(abs(qs.amplitudes[0]), 1.0 / math.sqrt(2.0))
        assert np.isclose(abs(qs.amplitudes[3]), 1.0 / math.sqrt(2.0))
        assert np.isclose(abs(qs.amplitudes[1]), 0.0, atol=1e-9)
        assert np.isclose(abs(qs.amplitudes[2]), 0.0, atol=1e-9)

    def test_swap_unitary(self):
        u = QuantumGates.two_qubit(GateType.SWAP, num_qubits=2, control=0, target=1)
        assert _is_unitary(u)

    def test_swap_exchanges(self):
        # |10> -> SWAP -> |01>
        qs = QuantumState(num_qubits=2, initial_state=2)  # |10>
        SWAP = QuantumGates.two_qubit(GateType.SWAP, num_qubits=2, control=0, target=1)
        qs.apply_unitary(SWAP)
        assert np.isclose(abs(qs.amplitudes[2]), 0.0, atol=1e-9)
        assert np.isclose(abs(qs.amplitudes[1]), 1.0)

    def test_invalid_target(self):
        with pytest.raises(ValueError):
            QuantumGates.single_qubit(GateType.H, num_qubits=2, target=2)

    def test_invalid_control_target_equal(self):
        with pytest.raises(ValueError):
            QuantumGates.two_qubit(GateType.CNOT, num_qubits=2, control=0, target=0)

    def test_invalid_control_out_of_range(self):
        with pytest.raises(ValueError):
            QuantumGates.two_qubit(GateType.CNOT, num_qubits=2, control=5, target=0)

    def test_unknown_two_qubit_gate(self):
        with pytest.raises(ValueError):
            QuantumGates.two_qubit(GateType.H, num_qubits=2, control=0, target=1)

    def test_tensor_position_target(self):
        # H on qubit 1 of a 3-qubit system
        H = QuantumGates.single_qubit(GateType.H, num_qubits=3, target=1)
        assert H.shape == (8, 8)
        # Apply to |000> -> should have |000> and |010> each with 1/sqrt(2)
        qs = QuantumState(num_qubits=3, initial_state=0)
        qs.apply_unitary(H)
        assert np.isclose(abs(qs.amplitudes[0]), 1.0 / math.sqrt(2.0))
        assert np.isclose(abs(qs.amplitudes[2]), 1.0 / math.sqrt(2.0))
