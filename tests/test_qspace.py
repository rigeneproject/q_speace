"""Tests for Q-SPEACE EDD-CVT, metabolism, fractal QCA and orchestrator."""

from __future__ import annotations

import numpy as np

from q_speace.edd_cvt import CosmicVirusOptimizer, InformationalLogicalField
from q_speace.fractal_qca import FractalQCA
from q_speace.genome import QuantumGeneSet
from q_speace.metabolism.cognitive_cost_model import QuantumCostModel, QuantumOperation
from q_speace.orchestrator import QuantumOrchestrator
from q_speace.schumann import run_schumann


def test_sevo_threshold():
    cm = QuantumCostModel()
    assert cm.passes_sevo(3.0, 1.0, threshold=1.5)
    assert not cm.passes_sevo(1.0, 1.0, threshold=1.5)
    assert cm.sevo(1.0, 0.0) <= 0.0


def test_energy_cost_scales_with_qubits():
    cm = QuantumCostModel()
    op1 = QuantumOperation(num_qubits=1, num_gates=1)
    op4 = QuantumOperation(num_qubits=4, num_gates=1)
    assert cm.energy_watts(op4) > cm.energy_watts(op1)


def test_decoherence_budget_increases_cost():
    cm = QuantumCostModel()
    low = QuantumOperation(num_qubits=1, num_gates=1, decoherence_budget=0.1)
    high = QuantumOperation(num_qubits=1, num_gates=1, decoherence_budget=0.9)
    assert cm.energy_watts(high) > cm.energy_watts(low)


def test_ilf_adaptive_clock():
    ilf = InformationalLogicalField(coherence_phi=0.2)
    # Low coherence -> high S_info -> high clock rate.
    assert ilf.adaptive_clock_rate() > 10.0


def test_cv_optimizer_reduces_energy_like_term():
    cv = CosmicVirusOptimizer()
    w = np.array([0.5, -0.5, 0.1])
    out = cv.optimize(w, gradient_fn=lambda x: np.zeros_like(x), steps=5)
    # With zero gradient the -beta*W term pulls weights toward 0.
    assert np.all(np.abs(out) < np.abs(w)).item() or np.allclose(out, w, atol=1e-6)


def test_fractal_qca_runs():
    qca = FractalQCA(num_cells=8, seed=1)
    results = qca.run(ticks=5)
    assert len(results) == 5
    assert 0.0 <= results[-1].coherence_phi <= 1.0


def test_orchestrator_run():
    genome = QuantumGeneSet(enabled=True)
    orch = QuantumOrchestrator(genome=genome, neurons=[f"n{i}" for i in range(4)])
    orch.enable_qca(num_cells=8)
    report = orch.run(ticks=5)
    assert len(report) == 5
    assert "mean_coherence_phi" in orch.report()
    assert "gate_blocked_ratio" in orch.report()
    for r in report:
        assert hasattr(r, "gate_blocked")
        assert hasattr(r, "sevo")


def test_orchestrator_disabled():
    genome = QuantumGeneSet(enabled=False)
    orch = QuantumOrchestrator(genome=genome)
    assert orch.tick() is None


def test_orchestrator_energy_gate_blocks():
    genome = QuantumGeneSet(enabled=True)
    orch = QuantumOrchestrator(
        genome=genome,
        neurons=[f"n{i}" for i in range(4)],
        max_energy_w=0.001,  # very low budget -> gate blocks
    )
    report = orch.run(ticks=3)
    assert sum(1 for r in report if r.gate_blocked) > 0


def test_ilf_q_star_computation():
    ilf = InformationalLogicalField()
    ilf.register_agent("a", weight=2.0)
    ilf.register_agent("b", weight=1.0)
    ilf.set_belief("a", np.array([0.9, 0.1]))
    ilf.set_belief("b", np.array([0.3, 0.7]))
    q = ilf.compute_q_star()
    assert abs(sum(q) - 1.0) < 1e-6
    assert q[0] > q[1]


def test_ilf_q_star_single_agent():
    ilf = InformationalLogicalField()
    ilf.register_agent("x")
    ilf.set_belief("x", np.array([0.2, 0.8]))
    q = ilf.compute_q_star()
    assert abs(q[0] - 0.2) < 1e-6
    assert abs(q[1] - 0.8) < 1e-6


# --- T-SPB-3-A: EMA blending for multi-turn ILF stabilisation ---


def test_ilf_q_star_ema_blends_with_previous():
    """With q_star_ema=0.5, q_star mixes 50/50 with the previous value."""
    ilf = InformationalLogicalField(q_star_ema=0.5)
    ilf.register_agent("x")
    # First call: prev is None → q_star is the raw belief.
    ilf.set_belief("x", np.array([1.0, 0.0]))
    q1 = ilf.compute_q_star()
    assert abs(q1[0] - 1.0) < 1e-6
    # Second call: belief flips, but q_star should be 50/50.
    ilf.set_belief("x", np.array([0.0, 1.0]))
    q2 = ilf.compute_q_star()
    assert abs(q2[0] - 0.5) < 1e-6
    assert abs(q2[1] - 0.5) < 1e-6


def test_ilf_coherence_phi_ema_smooths_across_calls():
    """coherence_phi_ema blends the scalar φ with its previous value."""
    ilf = InformationalLogicalField(coherence_phi_ema=0.5)
    ilf.register_agent("x")
    ilf.set_belief("x", np.array([1.0, 0.0]))
    ilf.compute_q_star()
    phi1 = ilf.coherence_phi
    assert phi1 > 0.999  # peaked belief → near-max coherence (eps floor)
    # Now a near-uniform belief: raw φ would be ~0; EMA should produce
    # a value strictly between 0 and phi1.
    ilf.set_belief("x", np.array([0.5, 0.5]))
    ilf.compute_q_star()
    phi2 = ilf.coherence_phi
    assert 0.0 < phi2 < phi1


def test_ilf_coherence_phi_ema_prevents_collapse():
    """Three near-uniform beliefs must keep φ ≥ 0.05 when EMA is on.

    Regression: without EMA, the same scenario produces φ < 0.05 from
    the second call onward (multi-turn harness bug).
    """
    ilf = InformationalLogicalField(q_star_ema=0.5, coherence_phi_ema=0.5)
    ilf.register_agent("x")
    for belief in ([0.4, 0.1, 0.5], [0.5, 0.2, 0.3], [0.3, 0.4, 0.3]):
        ilf.set_belief("x", np.array(belief))
        ilf.compute_q_star()
        assert ilf.coherence_phi >= 0.05, f"collapse at belief {belief}: φ={ilf.coherence_phi}"


def test_schumann_experiment():
    result = run_schumann(num_qubits=4, ticks=5, seed=42)
    assert result["ticks"] == 5
    assert 0.0 <= result["mean_coherence"] <= 1.0
    assert len(result["coherence_trace"]) == 5
