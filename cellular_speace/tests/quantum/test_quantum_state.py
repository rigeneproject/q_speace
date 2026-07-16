"""Tests for the QuantumState primitive."""
import math
import numpy as np
import pytest

from speace_core.cellular_brain.quantum.quantum_state import (
    MeasurementResult,
    QuantumState,
)


class TestQuantumState:
    def test_init_default(self):
        qs = QuantumState(num_qubits=2)
        assert qs.num_qubits == 2
        assert qs.amplitudes.shape == (4,)
        # default is |00>
        assert np.isclose(qs.amplitudes[0], 1.0)
        assert np.isclose(np.sum(np.abs(qs.amplitudes) ** 2), 1.0)

    def test_init_with_state(self):
        qs = QuantumState(num_qubits=3, initial_state=5)
        assert np.isclose(qs.amplitudes[5], 1.0)

    def test_init_invalid_state(self):
        with pytest.raises(ValueError):
            QuantumState(num_qubits=2, initial_state=4)

    def test_init_invalid_qubits(self):
        with pytest.raises(ValueError):
            QuantumState(num_qubits=0)
        with pytest.raises(ValueError):
            QuantumState(num_qubits=17)

    def test_from_amplitudes_normalizes(self):
        qs = QuantumState.from_amplitudes([1.0 + 0j, 1.0 + 0j])
        assert qs.num_qubits == 1
        assert np.isclose(np.sum(np.abs(qs.amplitudes) ** 2), 1.0)
        # each should be 1/sqrt(2)
        assert np.isclose(qs.amplitudes[0], 1.0 / math.sqrt(2.0))

    def test_from_amplitudes_invalid(self):
        with pytest.raises(ValueError):
            QuantumState.from_amplitudes([1, 2, 3])  # not a power of 2

    def test_from_amplitudes_zero(self):
        with pytest.raises(ValueError):
            QuantumState.from_amplitudes([0, 0, 0, 0])

    def test_tensor_product(self):
        a = QuantumState(num_qubits=1, initial_state=0)
        b = QuantumState(num_qubits=1, initial_state=1)
        c = QuantumState.tensor_product(a, b)
        assert c.num_qubits == 2
        # |0> x |1> = |01>
        assert np.isclose(c.amplitudes[1], 1.0)

    def test_equal_superposition(self):
        qs = QuantumState.equal_superposition(num_qubits=3)
        # All 8 amplitudes should be 1/sqrt(8)
        expected = 1.0 / math.sqrt(8.0)
        for amp in qs.amplitudes:
            assert np.isclose(abs(amp), expected)

    def test_normalize(self):
        qs = QuantumState.from_amplitudes([2.0 + 0j, 0j, 0j, 0j])
        # already normalized
        qs.amplitudes *= 3
        qs.normalize()
        assert np.isclose(np.sum(np.abs(qs.amplitudes) ** 2), 1.0)

    def test_apply_unitary_rejects_non_unitary(self):
        qs = QuantumState(num_qubits=1)
        bad = np.array([[2.0, 0], [0, 0.5]])
        with pytest.raises(ValueError):
            qs.apply_unitary(bad)

    def test_apply_unitary_rejects_wrong_shape(self):
        qs = QuantumState(num_qubits=2)  # shape (4,)
        wrong = np.eye(2)
        with pytest.raises(ValueError):
            qs.apply_unitary(wrong)

    def test_measure_full(self):
        qs = QuantumState.equal_superposition(num_qubits=2)
        result = qs.measure()
        assert isinstance(result, MeasurementResult)
        assert len(result.bitstring) == 2
        assert result.probability > 0
        # collapsed state should be a basis state
        assert np.isclose(np.sum(np.abs(result.collapsed_state.amplitudes) ** 2), 1.0)

    def test_measure_single_qubit(self):
        qs = QuantumState.equal_superposition(num_qubits=2)
        result = qs.measure(qubit_index=0)
        assert result.bitstring in ("0", "1")

    def test_measure_invalid_qubit(self):
        qs = QuantumState(num_qubits=2)
        with pytest.raises(ValueError):
            qs.measure(qubit_index=2)

    def test_measure_many(self):
        qs = QuantumState.equal_superposition(num_qubits=3)
        results = qs.measure_many([0, 1, 2])
        assert len(results) == 3
        for r in results:
            assert r.bitstring in ("0", "1")

    def test_probabilities(self):
        qs = QuantumState(num_qubits=2, initial_state=0)
        probs = qs.probabilities()
        assert np.isclose(probs[0], 1.0)
        assert np.isclose(probs.sum(), 1.0)

    def test_fidelity_with_self(self):
        qs = QuantumState(num_qubits=2)
        f = qs.fidelity_with(qs)
        assert np.isclose(f, 1.0)

    def test_fidelity_with_orthogonal(self):
        a = QuantumState(num_qubits=1, initial_state=0)
        b = QuantumState(num_qubits=1, initial_state=1)
        f = a.fidelity_with(b)
        assert np.isclose(f, 0.0)

    def test_fidelity_shape_mismatch(self):
        a = QuantumState(num_qubits=1)
        b = QuantumState(num_qubits=2)
        with pytest.raises(ValueError):
            a.fidelity_with(b)

    def test_to_density_matrix(self):
        qs = QuantumState(num_qubits=1, initial_state=0)
        rho = qs.to_density_matrix()
        # rho = |0><0|
        assert np.isclose(rho[0, 0], 1.0)
        assert np.isclose(rho[1, 1], 0.0)

    def test_copy_independence(self):
        qs = QuantumState(num_qubits=1)
        c = qs.copy()
        c.amplitudes[0] = 0.0
        c.amplitudes[1] = 1.0
        # original unchanged
        assert np.isclose(qs.amplitudes[0], 1.0)
