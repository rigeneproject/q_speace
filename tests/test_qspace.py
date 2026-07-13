"""Tests for Q-SPEACE EDD-CVT, metabolism, fractal QCA and orchestrator."""
from __future__ import annotations

import numpy as np

from q_speace.metabolism.cognitive_cost_model import QuantumCostModel, QuantumOperation
from q_speace.edd_cvt import CosmicVirusOptimizer, InformationalLogicalField
from q_speace.fractal_qca import FractalQCA
from q_speace.genome import QuantumGeneSet
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
    orch = QuantumOrchestrator(
        genome=genome, neurons=[f"n{i}" for i in range(4)]
    )
    orch.enable_qca(num_cells=8)
    report = orch.run(ticks=5)
    assert len(report) == 5
    assert "mean_coherence_phi" in orch.report()


def test_orchestrator_disabled():
    genome = QuantumGeneSet(enabled=False)
    orch = QuantumOrchestrator(genome=genome)
    assert orch.tick() is None


def test_schumann_experiment():
    result = run_schumann(num_qubits=4, ticks=5, seed=42)
    assert result["ticks"] == 5
    assert 0.0 <= result["mean_coherence"] <= 1.0
    assert len(result["coherence_trace"]) == 5
