"""Tests for T250 — SPEACE Neural Brain Remediation & A/B Complex Benchmark."""

from __future__ import annotations

import asyncio
import json

import numpy as np
import pytest
from typer.testing import CliRunner

from q_speace import (
    BCELCatalog,
    ClassicalBaselineAgent,
    SemanticNeuralBackend,
    SPEACENeuralAgent,
    build_complex_ab_workload,
    run_ab_neural_benchmark,
)
from q_speace.cli import app
from q_speace.spiking_brain import SpikingBrainUnavailableError


def test_t250_bcel_entries_present() -> None:
    catalog = BCELCatalog()
    concepts = {eq.concept: eq for eq in catalog.all()}
    func_key = (
        "Post-spike readout trace, three-factor eligibility plasticity, "
        "and unified neural-quantum agent loop (T250)"
    )
    acc_key = (
        "Uncentered cosine similarity and zero-output MSE reward inflation "
        "as intelligence proof (T250)"
    )
    assert func_key in concepts
    assert acc_key in concepts
    assert concepts[func_key].classification == "functional"
    assert concepts[acc_key].classification == "accidental"


def test_semantic_neural_backend_stationary_and_lifecycle() -> None:
    backend = SemanticNeuralBackend(n_classes=3, seed=7)
    r1 = backend.think("Diagnose relay_a anomaly under bounded energy", coherence_phi=0.9)
    r2 = backend.think("Diagnose relay_a anomaly under bounded energy", coherence_phi=0.9)
    assert np.allclose(r1.belief, r2.belief)
    assert abs(r1.confidence - r2.confidence) < 1e-12
    assert backend.health()["ready"] is True

    # Multi-turn history blending remains valid probability simplex
    r3 = backend.think("Follow-up check", coherence_phi=0.8, history=[r1, r2])
    assert np.isclose(float(np.sum(r3.belief)), 1.0)
    assert (r3.belief >= 0.0).all()

    asyncio.run(backend.shutdown())
    with pytest.raises(SpikingBrainUnavailableError):
        backend.think("after shutdown")
    asyncio.run(backend.load())
    assert backend.think("reloaded").confidence >= 0.0


def test_ab_benchmark_speace_outperforms_classical_baseline() -> None:
    comparison = run_ab_neural_benchmark(seed=2026)
    speace = comparison.speace_agent
    base = comparison.classical_baseline

    assert comparison.speace_outperforms_baseline is True
    assert comparison.delta_composite >= 0.40
    assert speace["stage1_associative_top1_acc"] >= 0.80
    assert speace["stage2_sensor_fusion_acc"] > base["stage2_sensor_fusion_acc"]
    assert speace["stage2_second_half_acc"] >= 0.85
    assert speace["stage3_causal_mediator_acc"] == 1.0
    assert speace["stage3_recovery_plan_acc"] == 1.0
    assert base["stage3_causal_mediator_acc"] == 0.0
    assert speace["stage4_valid_completion_rate"] == 1.0
    assert speace["stage4_unsafe_acceptance_rate"] == 0.0
    assert base["stage4_unsafe_acceptance_rate"] == 1.0


def test_standalone_fallback_circuit_when_cellular_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import q_speace.neural_agent as na

    monkeypatch.setattr(na, "_try_build_cellular_orchestrator", lambda seed=2026: None)
    workload = build_complex_ab_workload(seed=2026)
    agent = SPEACENeuralAgent(seed=2026)
    assert agent.uses_full_cellular_orchestrator is False
    res = agent.evaluate(workload)
    base = ClassicalBaselineAgent().evaluate(workload)
    assert res["stage1_associative_top1_acc"] >= 0.90
    assert res["composite_score"] > base["composite_score"]


def test_cli_brain_ab_benchmark() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["brain", "ab-benchmark", "--seed", "2026"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["speace_outperforms_baseline"] is True
    assert (
        payload["speace_agent"]["composite_score"]
        > payload["classical_baseline"]["composite_score"]
    )
