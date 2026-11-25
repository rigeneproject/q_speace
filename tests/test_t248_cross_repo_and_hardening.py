"""T248: Cross-repository BCEL synthesis & core fail-closed hardening tests."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from typer.testing import CliRunner

import q_speace
from q_speace.bcel import BCELCatalog
from q_speace.cli import app
from q_speace.edd_cvt import CosmicVirusOptimizer, CVConfig, InformationalLogicalField
from q_speace.fractal_qca import FractalQCA
from q_speace.genome import QuantumGeneSet
from q_speace.orchestrator import QuantumOrchestrator
from q_speace.quantum import EntanglementRegistry, QuantumNeuralBridge, QuantumState
from q_speace.schumann import run_schumann
from q_speace.self_improvement_cortex import (
    AgentProposal,
    EpistemicProposalAuditor,
    EvolutionaryMemory,
    EvolutionCouncil,
    MemoryEntry,
    SandboxedPatchCycle,
    SelfImprovementCortex,
)
from q_speace.spiking import (
    CausalEdge,
    CriticalityController,
    SpikeEncodingResult,
    SpikePlasticity,
    StructuralCausalDAG,
    spike_temporal_asymmetry,
)
from q_speace.spiking_brain import Memory, SemanticEpisodicMemory, ThinkResult, embed_text_hashed
from q_speace.systemic_resonance import NodeState, ResonanceEngine


def _make_think_result(text: str, confidence: float = 0.8) -> ThinkResult:
    return ThinkResult(
        text=text,
        confidence=confidence,
        belief=np.array([0.7, 0.3]),
        spikes=SpikeEncodingResult(
            spikes=np.array([1.0, 0.0]),
            vth=np.array([0.5]),
            num_spikes=1,
            sparsity=0.5,
            rate=0.5,
        ),
        plasticity=np.array([0.5, 0.5]),
        n_tokens=8,
        latency_s=0.01,
    )


def test_t248_bcel_catalog_and_dunder_all_hygiene() -> None:
    cat = BCELCatalog()
    functional_concepts = [
        "Branching-ratio criticality homeostasis and synaptic scaling (T248)",
        "Precision-weighted ILF belief pooling and variational free-energy surprise (T248)",
        "Directed spike-lag causal discovery and non-destructive do-calculus DAG (T248)",
        "Hybrid SQLite-FTS5 feature-hashed episodic memory and continuous evolutionary recall (T248)",
        "Transactional pre/post sandbox patch verification and epistemic perturbation audit (T248)",
    ]
    for concept in functional_concepts:
        assert cat.is_functional(concept) is True

    accidental = "Heuristic IIT Phi consciousness gates and anatomical lobe personas (T248)"
    assert cat.is_functional(accidental) is False

    # No duplicate entries in q_speace.__all__
    assert len(q_speace.__all__) == len(set(q_speace.__all__))


def test_t248_quantum_state_bridge_and_registry_hardening() -> None:
    # 1. QuantumState.apply_unitary rejects NaN/Inf matrices fail-closed
    s = QuantumState(num_qubits=1)
    with pytest.raises(ValueError, match="finite"):
        s.apply_unitary(np.array([[np.nan, 0.0], [0.0, 1.0]], dtype=np.complex128))
    with pytest.raises(ValueError, match="finite"):
        s.apply_unitary(np.array([[np.inf, 0.0], [0.0, 1.0]], dtype=np.complex128))
    assert np.all(np.isfinite(s.amplitudes))

    # 2. EntanglementRegistry rejects non-finite fidelity and cleans up entity pairs
    reg = EntanglementRegistry()
    with pytest.raises(ValueError, match="finite"):
        reg.entangle("a", "b", fidelity=float("nan"))
    reg.entangle("a", "b", fidelity=0.75)
    reg.entangle("b", "c", fidelity=0.50)
    assert reg.remove_entity("b") == 2
    assert reg.count() == 0

    # 3. QuantumNeuralBridge monotonic slots, unregister cleanup, real fidelity, finite activity
    bridge = QuantumNeuralBridge(num_qubits_per_neuron=2)
    s_a = bridge.register("a")
    s_b = bridge.register("b")
    assert (s_a, s_b) == (0, 2)
    bridge.entangle_neurons("a", "b", fidelity=0.68)
    assert np.isclose(bridge.quantum_compatibility("a", "b"), 0.68)

    bridge.unregister("a")
    assert bridge.is_entangled("a", "b") is False
    s_c = bridge.register("c")
    assert s_c != s_b  # Must never collide with 'b' slot (2)!
    assert s_c == 4

    with pytest.raises(ValueError, match="finite"):
        bridge.set_activity(np.array([0.5, float("nan")]))


def test_t248_fractal_qca_cv_resonance_and_schumann_hardening() -> None:
    # 1. FractalQCA tick increment + bounds + NaN rejection
    with pytest.raises(ValueError, match=r"\[2, 16\]"):
        FractalQCA(num_cells=17)
    with pytest.raises(ValueError, match="finite"):
        FractalQCA(num_cells=4, gamma=float("nan"))

    qca = FractalQCA(num_cells=4, seed=7)
    steps = qca.run(ticks=3)
    assert [r.tick for r in steps] == [0, 1, 2]
    assert all(0.0 <= r.coherence_phi <= 1.0 for r in steps)

    with pytest.raises(ValueError, match="finite"):
        qca.step(delta_s_info=float("nan"))
    with pytest.raises(ValueError, match="finite"):
        qca.inject_noise(float("nan"))
    with pytest.raises(ValueError, match="finite"):
        qca.seed_from(float("nan"))

    # 2. CosmicVirusOptimizer fail-closed validation
    with pytest.raises(ValueError, match="sigma"):
        CVConfig(sigma=-0.1)
    opt = CosmicVirusOptimizer(CVConfig(seed=3))
    with pytest.raises(ValueError, match="match"):
        opt.step(np.ones(3), np.ones(2))
    with pytest.raises(ValueError, match="finite"):
        opt.step(np.array([1.0, np.nan]), np.ones(2))
    with pytest.raises(ValueError, match="dt"):
        opt.step(np.ones(2), np.ones(2), dt=-0.5)

    # 3. ResonanceEngine combinatorial max_nodes cap
    with pytest.raises(ValueError, match="max_nodes"):
        ResonanceEngine(max_nodes=5)
    eng = ResonanceEngine(max_nodes=6)
    for idx in range(6):
        eng.update_node_state(NodeState(f"n{idx}", 0.2, 0.1, 0.1, 0.0))
    # Updating existing node is allowed, 7th distinct node is blocked
    eng.update_node_state(NodeState("n0", 0.3, 0.1, 0.1, 0.0))
    with pytest.raises(ValueError, match="max_nodes limit"):
        eng.update_node_state(NodeState("n6", 0.2, 0.1, 0.1, 0.0))

    # 4. Schumann bounds + CLI n=1 QCA guard
    with pytest.raises(ValueError, match="ticks"):
        run_schumann(num_qubits=2, ticks=0)
    res = run_schumann(num_qubits=3, ticks=3, seed=5)
    assert len(res["coherence_trace"]) == 3  # type: ignore[arg-type]

    runner = CliRunner()
    cli_res = runner.invoke(app, ["quantum", "run", "-n", "1", "-t", "2"])
    assert cli_res.exit_code == 0


def test_t248_criticality_controller_plasticity_and_orchestrator_liveness() -> None:
    ctrl = CriticalityController(target_sigma=1.0, kp=0.4, k_min=0.5, k_max=8.0, window=6)
    # First observation initializes window without jumping
    s0 = ctrl.step(10, current_k=3.0)
    assert s0.sample_count == 1 and s0.updated_k == 3.0

    # Collapsing spikes (10 -> 1 -> 0): sub-critical -> controller increases k (lowers vth)
    s1 = ctrl.step(1, current_k=s0.updated_k)
    s2 = ctrl.step(0, current_k=s1.updated_k)
    assert s2.regime == "sub_critical"
    assert s2.updated_k > 3.0

    # Runaway spikes (0 -> 20 -> 80): super-critical -> controller decreases k (raises vth)
    ctrl_hi = CriticalityController(target_sigma=1.0, kp=0.4, k_min=0.5, k_max=8.0, window=4)
    ctrl_hi.step(2, current_k=4.0)
    hi_state = ctrl_hi.step(30, current_k=4.0)
    assert hi_state.regime == "super_critical"
    assert hi_state.updated_k < 4.0

    # Homeostatic synaptic scaling on SpikePlasticity (both max_scale clamp and exact target)
    plast = SpikePlasticity(num_units=3, decay=0.5)
    plast.update(np.array([0.04, 0.08, 0.06]))  # mean EMA = 0.03 -> 10x max_scale clamp = 0.30
    scaled_clamped = plast.homeostatic_scale(target_mean=0.5, max_scale=10.0)
    assert np.isclose(np.mean(scaled_clamped), 0.30, atol=1e-6)
    scaled_exact = plast.homeostatic_scale(target_mean=0.5, max_scale=10.0)
    assert np.isclose(np.mean(scaled_exact), 0.50, atol=1e-6)
    with pytest.raises(ValueError, match="finite"):
        plast.update(np.array([1.0, float("nan"), 0.0]))

    # Orchestrator criticality integration + bounded history + temporal liveness
    orch = QuantumOrchestrator(
        genome=QuantumGeneSet(enabled=True),
        neurons=["n0", "n1", "n2", "n3"],
        seed=0,
        enable_spikes=True,
        enable_criticality=True,
        max_history=5,
    )
    orch.enable_qca(num_cells=4)
    reports = orch.run(ticks=8)
    assert len(reports) == 8
    assert orch.report()["ticks"] == 5  # Bounded ring buffer maxlen=5
    assert orch.temporal_liveness() is True
    assert all(
        r.criticality_regime in ("sub_critical", "critical", "super_critical") for r in reports
    )


def test_t248_precision_weighted_ilf_and_variational_free_energy() -> None:
    ilf = InformationalLogicalField()
    ilf.register_agent("reliable")
    ilf.register_agent("noisy")
    ilf.set_belief("reliable", np.array([0.9, 0.1]))
    ilf.set_belief("noisy", np.array([0.1, 0.9]))

    # Equal weights initially -> symmetric compromise ~ [0.5, 0.5]
    q_equal = ilf.compute_q_star()
    assert np.allclose(q_equal, np.array([0.5, 0.5]), atol=1e-6)

    # Observe low error for 'reliable' and high error for 'noisy'
    p_rel = ilf.observe_prediction_error("reliable", 0.02, eta=1.0)
    p_noi = ilf.observe_prediction_error("noisy", 1.50, eta=1.0)
    assert p_rel > p_noi

    q_weighted = ilf.compute_q_star()
    assert q_weighted[0] > 0.85  # Precision pooling trusts 'reliable'
    fe = ilf.variational_free_energy(kl_weight=1.0)
    assert fe > 0.0 and np.isfinite(fe)


def test_t248_spike_temporal_asymmetry_and_non_destructive_causal_dag() -> None:
    # Construct deterministic spike chain n0 -> n1 (lag 1) -> n2 (lag 1)
    steps = 24
    activity = np.zeros((3, steps), dtype=float)
    trigger_times = [1, 5, 9, 13, 17, 21]
    for t in trigger_times:
        activity[0, t] = 1.0
        activity[1, t + 1] = 1.0
        activity[2, t + 2] = 1.0

    edges = spike_temporal_asymmetry(
        activity, max_lag=1, min_cooccurrences=3, threshold=0.5, ids=["sensor", "relay", "output"]
    )
    edge_pairs = {(e.source, e.target) for e in edges}
    assert ("sensor", "relay") in edge_pairs
    assert ("relay", "output") in edge_pairs
    assert ("output", "sensor") not in edge_pairs

    dag = StructuralCausalDAG.from_temporal_edges(["sensor", "relay", "output"], edges)
    edges_before = dag.edges

    # Natural prediction vs mutilated do(relay = 0.0): cutting sensor -> relay blocks propagation!
    natural = dag.predict({"sensor": 2.0})
    assert natural["output"] > 0.0

    intervened = dag.intervene({"relay": 0.0}, exogenous={"sensor": 2.0})
    assert intervened["relay"] == 0.0
    assert intervened["output"] == 0.0

    # CRITICAL REGRESSION GUARD: intervene() must NEVER mutate dag.edges in-place!
    assert dag.edges == edges_before
    assert dag.predict({"sensor": 2.0}) == natural

    # Pearl 3-step counterfactual
    cf = dag.counterfactual(observed=natural, do_map={"sensor": 0.0})
    assert np.isclose(cf["output"], 0.0)

    # Cycle detection
    with pytest.raises(ValueError, match="cycle"):
        StructuralCausalDAG(
            nodes=["a", "b"],
            edges=[CausalEdge("a", "b", 0.5), CausalEdge("b", "a", 0.5)],
        )


def test_t248_semantic_episodic_memory_and_continuous_evolutionary_recall(tmp_path: Path) -> None:
    # 1. Deterministic blake2b feature-hashed embeddings
    v1 = embed_text_hashed("quantum coherence stabilization protocol")
    v2 = embed_text_hashed("protocol for stabilizing quantum coherence")
    v3 = embed_text_hashed("microgrid diesel frequency droop")
    assert np.isclose(np.linalg.norm(v1), 1.0)
    assert float(np.dot(v1, v2)) > float(np.dot(v1, v3))

    # 2. SemanticEpisodicMemory satisfies Memory Protocol, hybrid search, deduplication & TTL
    db_path = tmp_path / "episodes.sqlite3"
    mem = SemanticEpisodicMemory(db_path, max_entries=50, ttl_seconds=60.0)
    assert isinstance(mem, Memory)

    async def _exercise() -> None:
        await mem.put(_make_think_result("Quantum Lindblad decoherence damping rate", 0.75))
        await mem.put(_make_think_result("Quantum Lindblad decoherence damping rate", 0.92))
        await mem.put(_make_think_result("Solar sunspot modulation of RY gate", 0.80))

        hits = await mem.get_relevant("decoherence Lindblad damping", k=2)
        assert len(hits) >= 1
        assert "Lindblad" in hits[0].text

        removed = mem.consolidate()
        assert removed == 1
        rec = await mem.recent(k=10)
        assert len(rec) == 2

        archived = mem.archive_expired(now=1e12)
        assert archived == 2
        assert len(await mem.recent(k=10)) == 0

    try:
        asyncio.run(_exercise())
    finally:
        mem.close()

    # 3. EvolutionaryMemory continuous metric cosine + Jaccard recall (fixes float jitter)
    evo = EvolutionaryMemory()
    evo.store(
        MemoryEntry(
            mutation_id="m1",
            context_signature="0.7123401",
            reason="stabilize phi",
            level=3,
            target="ilf",
            metrics_before={"coherence_phi": 0.7123401, "sevo": 1.8},
            metrics_after={"coherence_phi": 0.82, "sevo": 2.1},
            outcome=0.25,
            tags=["ilf", "coherence"],
        )
    )
    evo.store(
        MemoryEntry(
            mutation_id="m2",
            context_signature="0.1",
            reason="radio power",
            level=2,
            target="sdr",
            metrics_before={"snr": 12.0},
            metrics_after={"snr": 14.0},
            outcome=0.10,
            tags=["rf"],
        )
    )
    # Exact string signature misses jittered float 0.7123402, continuous recall finds m1!
    assert evo.find_similar("0.7123402") == []
    similar = evo.find_similar_metrics(
        {"coherence_phi": 0.7123402, "sevo": 1.79}, tags=["coherence"], top_k=1
    )
    assert len(similar) == 1 and similar[0].mutation_id == "m1"


def test_t248_sandboxed_patch_cycle_and_epistemic_proposal_auditor() -> None:
    # 1. SandboxedPatchCycle commits non-regressing improvements & rolls back regressions/exceptions
    cycle = SandboxedPatchCycle(min_delta=0.05, allow_key_regression=False)
    state: dict[str, Any] = {"gain": 1.0, "bias": 0.0}

    def bench(s: Any) -> dict[str, float]:
        return {
            "task_a": float(s["gain"]) * 0.5,
            "task_b": 0.6 - abs(float(s["bias"])),
        }

    # Regression on task_b -> rolled back automatically!
    reg_res = cycle.run(
        state,
        patch_fn=lambda s: s.update(gain=1.4, bias=0.3),
        benchmark_fn=bench,
    )
    assert reg_res.committed is False
    assert reg_res.reason == "rolled_back_fixture_regression"
    assert "task_b" in reg_res.worsened_keys
    assert state == {"gain": 1.0, "bias": 0.0}

    # Exception inside patch -> rolled back automatically!
    def _boom(s: dict[str, Any]) -> None:
        s["gain"] = 999.0
        raise RuntimeError("patch crash")

    err_res = cycle.run(state, patch_fn=_boom, benchmark_fn=bench)
    assert err_res.committed is False
    assert err_res.reason == "patch_exception:RuntimeError"
    assert state == {"gain": 1.0, "bias": 0.0}

    # Genuine Pareto improvement -> committed!
    ok_res = cycle.run(
        state,
        patch_fn=lambda s: s.update(gain=1.3),
        benchmark_fn=bench,
    )
    assert ok_res.committed is True
    assert state["gain"] == 1.3
    assert "task_a" in ok_res.improved_keys and not ok_res.worsened_keys

    # 2. EpistemicProposalAuditor fast-path + perturbation stability
    council = EvolutionCouncil()
    auditor = EpistemicProposalAuditor(num_perturbations=6, noise_sigma=0.02, seed=11)
    assert auditor.score_uncertain(0.5) is True
    assert auditor.score_uncertain(0.01) is False

    # Deeply sub-threshold coherence (0.10 << 0.30) stays stable under sigma=0.02 noise
    ctx = {"coherence_phi": 0.10, "plasticity_index": 0.10, "resilience": 0.8, "dna_stability": 0.9}
    props = council.gather_proposals(ctx)
    assert props
    verdict = auditor.audit(props[0], ctx, council=council, evidence_count=5)
    assert verdict.approved is True
    assert verdict.perturbation_stability >= 0.8

    # Knife-edge proposal forged without council support fails perturbation stability
    forged = AgentProposal(
        agent_name="forged_agent",
        level=9,
        target="nonexistent",
        reason="unverified",
        confidence=0.6,
        expected_impact=0.5,
        risk=0.2,
    )
    bad_verdict = auditor.audit(forged, ctx, council=council, evidence_count=1)
    assert bad_verdict.approved is False
    assert bad_verdict.reason == "rejected_perturbation_instability"

    # Bounded SelfImprovementCortex history
    sia = SelfImprovementCortex(max_history=3)
    for _ in range(6):
        sia.tick(ctx)
    assert sia.report()["ticks"] == 3
