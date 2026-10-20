"""Tests for the pseudo-spiking layer (task T202)."""

from __future__ import annotations

import numpy as np
import pytest

from q_speace.edd_cvt import CosmicVirusOptimizer, CVConfig
from q_speace.metabolism.cognitive_cost_model import QuantumCostModel, QuantumOperation
from q_speace.quantum import QuantumNeuralBridge
from q_speace.spiking import (
    SpikeEncodedLinear,
    SpikePlasticity,
    SpikeQuantumBridge,
    dynamic_spikes,
    entangle_by_correlation,
    sparsity,
    spike_correlation,
    spike_count,
    spike_entropy_gradient,
)


def test_dynamic_spikes_gaussian_sparsifies_and_stays_integer():
    x = np.random.default_rng(1).normal(size=1000)
    enc = dynamic_spikes(x, k=3.0)
    assert 0.0 < enc.sparsity < 1.0
    assert 0 < enc.num_spikes < 1000
    assert np.allclose(enc.spikes, np.round(enc.spikes))


def test_dynamic_spikes_lower_k_means_sparser():
    x = np.random.default_rng(1).normal(size=1000)
    coarse = dynamic_spikes(x, k=0.5)
    fine = dynamic_spikes(x, k=3.0)
    assert coarse.sparsity > fine.sparsity


def test_dynamic_spikes_threshold_is_scale_invariant():
    x = np.random.default_rng(1).normal(size=1000)
    a = dynamic_spikes(x, k=3.0)
    b = dynamic_spikes(3.0 * x, k=3.0)
    assert np.allclose(a.spikes, b.spikes, atol=1.0)  # identical up to boundary rounding


def test_dynamic_spikes_output_is_integer_valued():
    x = np.random.default_rng(2).normal(size=(4, 8))
    enc = dynamic_spikes(x)
    assert np.allclose(enc.spikes, np.round(enc.spikes))
    assert enc.vth.shape == (4, 1)


def test_dynamic_spikes_zero_input_is_silent():
    enc = dynamic_spikes(np.zeros((3, 5)))
    assert enc.num_spikes == 0
    assert enc.sparsity == 1.0
    assert enc.rate == 0.0


def test_dynamic_spikes_rejects_bad_k():
    with pytest.raises(ValueError):
        dynamic_spikes(np.zeros(4), k=0.0)


def test_ilf_modulation_reduces_threshold_and_sparsity():
    x = np.random.default_rng(3).normal(size=500)
    coherent = dynamic_spikes(x, coherence_phi=0.9, beta=1.0)
    noisy = dynamic_spikes(x, coherence_phi=0.1, beta=1.0)
    assert coherent.num_spikes > noisy.num_spikes
    assert coherent.sparsity < noisy.sparsity


def test_spike_energy_cost_prefers_sparse_activity():
    cm = QuantumCostModel()
    baseline = cm.energy_watts(QuantumOperation(num_qubits=4, num_gates=4))
    dense = QuantumOperation(num_qubits=4, num_gates=4, num_spikes=1000)
    sparse = QuantumOperation(num_qubits=4, num_gates=4, num_spikes=10)
    assert cm.energy_watts(dense) > cm.energy_watts(sparse) > baseline
    expected_spike_delta = 10 * QuantumCostModel.W_PER_SPIKE * QuantumCostModel.RICALIBRATION_FACTOR
    assert cm.energy_watts(sparse) == pytest.approx(baseline + expected_spike_delta)


def test_spike_count_and_sparsity_helpers():
    s = np.array([[3, 0, 1], [0, 0, 0]])
    assert spike_count(s) == 2
    assert sparsity(s) == pytest.approx(4 / 6)
    assert sparsity(np.zeros(5)) == 1.0


def test_spike_encoded_linear_forward_and_quantization():
    layer = SpikeEncodedLinear(in_features=8, out_features=4, k=3.0, seed=7)
    x = np.random.default_rng(4).normal(size=(3, 8))
    out = layer.forward(x)
    assert out.shape == (3, 4)
    assert np.all(np.isfinite(out))
    max_scale = float(np.max(np.abs(layer._scales)))
    assert layer.quantization_error() <= max_scale


def test_spike_encoded_linear_shape_mismatch():
    layer = SpikeEncodedLinear(in_features=8, out_features=4, seed=7)
    with pytest.raises(ValueError):
        layer.forward(np.zeros((3, 5)))


def test_plasticity_ema_coefficients_in_unit_range():
    plast = SpikePlasticity(num_units=4, decay=0.7)
    for _ in range(10):
        plast.update(np.array([5.0, 3.0, 1.0, 0.0]))
    coeffs = plast.coefficients()
    assert coeffs.shape == (4,)
    assert np.all((coeffs >= 0.0) & (coeffs <= 1.0))
    assert coeffs[0] == pytest.approx(1.0)


def test_plasticity_decayed_rate_formula():
    assert SpikePlasticity.decayed_rate(3.0, dt=5.0, lam=0.1) == pytest.approx(3.0 * np.exp(-0.5))


def test_spike_correlation_matrix():
    t = np.linspace(0.0, 2 * np.pi, 128)
    activity = np.stack([np.sin(t), np.sin(t), np.cos(t)])
    corr = spike_correlation(activity)
    assert corr.shape == (3, 3)
    assert np.allclose(np.diag(corr), 1.0)
    assert np.all(np.abs(corr) <= 1.0 + 1e-12)
    assert corr[0, 1] > 0.99
    assert abs(corr[0, 2]) < 0.05
    assert not np.any(np.isnan(corr))


def test_entangle_by_correlation_threshold():
    bridge = QuantumNeuralBridge(seed=1)
    t = np.linspace(0.0, 4.0 * np.pi, 128)
    activity = np.stack(
        [np.sin(t), np.sin(t), np.random.default_rng(5).normal(size=128), np.zeros(128)]
    )
    pairs = entangle_by_correlation(bridge, activity, threshold=0.5)
    assert len(pairs) == 1
    assert {pairs[0].entity_a, pairs[0].entity_b} == {"n0", "n1"}
    assert pairs[0].label == "spike-correlation"
    assert pairs[0].fidelity > 0.99
    assert bridge.is_entangled("n0", "n1")


def test_entangle_by_correlation_plasticity_scales_fidelity():
    bridge = QuantumNeuralBridge(seed=1)
    t = np.linspace(0.0, 2.0 * np.pi, 64)
    activity = np.stack([np.sin(t), np.sin(t)])
    plast = SpikePlasticity(num_units=2, decay=0.8)
    plast.update(np.array([10.0, 0.0]))
    plast.update(np.array([10.0, 0.0]))
    pairs = entangle_by_correlation(bridge, activity, threshold=0.5, plasticity=plast)
    assert len(pairs) == 1
    assert pairs[0].fidelity == pytest.approx(1.0 * 0.5)


def test_bridge_to_state_amplitude_encoding():
    bridge = SpikeQuantumBridge(seed=3)
    state = bridge.to_state(np.array([3.0, 1.0, 0.0]))
    assert state.num_qubits == 2
    assert np.isclose(np.sum(np.abs(state.amplitudes) ** 2), 1.0)
    assert np.allclose(np.abs(state.amplitudes[:3]), np.array([3.0, 1.0, 0.0]) / np.sqrt(10.0))


def test_bridge_to_qca_rotations():
    bridge = SpikeQuantumBridge()
    angles = bridge.to_qca_rotations(np.array([4.0, 2.0, 0.0]))
    assert angles == pytest.approx(np.array([np.pi, np.pi / 2, 0.0]))
    assert bridge.to_qca_rotations(np.zeros(3)).tolist() == [0.0, 0.0, 0.0]
    per_cell = bridge.to_qca_rotations(np.array([[1.0, 1.0], [0.0, 0.0], [0.5, 0.5]]), num_cells=3)
    assert per_cell[0] == pytest.approx(np.pi)
    assert per_cell[2] == pytest.approx(np.pi / 2)


def test_spike_entropy_gradient_uniform_is_zero():
    grad = spike_entropy_gradient(np.array([1.0, 1.0, 1.0, 1.0]))
    assert np.allclose(grad, 0.0, atol=1e-6)
    assert np.allclose(spike_entropy_gradient(np.zeros(4)), 0.0)


def test_spike_entropy_gradient_peaked_is_nonzero():
    grad = spike_entropy_gradient(np.array([3.0, 1.0, 1.0, 1.0]))
    assert np.linalg.norm(grad) > 0.0
    quiet = spike_entropy_gradient(np.array([3.0, 1.0, 1.0, 0.0]))
    assert quiet[3] == 0.0  # silent units do not contribute


def test_cosmic_virus_sparse_loop_closes_p5():
    cv = CosmicVirusOptimizer(CVConfig(seed=9))
    w = np.array([2.0, 1.5, 1.0, 0.5, 0.0])
    out = cv.optimize(w, gradient_fn=spike_entropy_gradient, steps=5)
    assert out.shape == w.shape
    assert np.all(np.isfinite(out))
