"""Tests for the Self-Improvement Cortex (SIA) — T32 to T46."""
from __future__ import annotations

import numpy as np

from q_speace.self_improvement_cortex import (
    AdaptiveLevel,
    AdaptiveLevelRegistry,
    DigitalDNAAgent,
    EpigeneticEngine,
    EpigeneticMarker,
    EvolutionCouncil,
    EvolutionaryMemory,
    HarnessUpdate,
    ILFAgent,
    ILFRegulator,
    MemoryAgent,
    MemoryEntry,
    MutationAgent,
    MutationRegistry,
    NeurogenesisPipeline,
    NeuroscienceAgent,
    OrganismObserver,
    QAOASelector,
    QuantumEvolutionEngine,
    QuantumKernelClassifier,
    QuantumOracle,
    RLAgent,
    RollbackManager,
    SafetyAgent,
    SelfImprovementCortex,
    SoftwareArchitect,
    WeightUpdate,
)


def test_organism_observer_snapshot():
    obs = OrganismObserver()
    p = obs.snapshot(coherence_phi=0.8, mean_energy_w=1.5, sci=0.9)
    assert abs(p.coherence_phi - 0.8) < 1e-9
    assert abs(p.mean_energy_w - 1.5) < 1e-9
    assert abs(p.sci - 0.9) < 1e-9
    assert obs.latest() is p
    assert len(obs.trend("coherence_phi")) == 1


def test_organism_observer_delta():
    obs = OrganismObserver()
    p1 = obs.snapshot(coherence_phi=0.5)
    p2 = obs.snapshot(coherence_phi=0.8)
    d = p2.delta(p1)
    assert abs(d["coherence_phi"] - 0.3) < 1e-9


def test_evolution_council_gathers_proposals():
    council = EvolutionCouncil()
    ctx = {"coherence_phi": 0.2, "plasticity_index": 0.2, "prediction_error": 0.3,
           "goal_completion": 0.3, "memory_compression": 0.2, "resilience": 0.3,
           "novelty": 0.1, "ilf_coherence": 0.4}
    proposals = council.gather_proposals(ctx)
    assert len(proposals) >= 1


def test_evolution_council_decide():
    council = EvolutionCouncil()
    proposals = council.gather_proposals({"coherence_phi": 0.2, "plasticity_index": 0.2})
    selected = council.decide(proposals, {})
    assert len(selected) <= 3


def test_adaptive_level_escalation():
    reg = AdaptiveLevelRegistry()
    assert reg.current_level == AdaptiveLevel.PROMPT
    assert reg.escalate() == AdaptiveLevel.WORKFLOW
    assert reg.level_name() == "Workflow"
    assert reg.update_type() == "harness"


def test_adaptive_level_full_cycle():
    reg = AdaptiveLevelRegistry()
    levels = []
    while True:
        levels.append(reg.current_level)
        if reg.escalate() is None:
            break
    assert len(levels) == 10
    assert levels[0] == AdaptiveLevel.PROMPT
    assert levels[-1] == AdaptiveLevel.NEW_NETWORK


def test_dna_registry_record():
    reg = MutationRegistry()
    rec = reg.record("test mutation", 1, "prompt_strategy",
                     {"acc": 0.5}, {"acc": 0.8})
    assert rec.mutation_id is not None
    assert rec.level == 1
    assert reg.count() == 1


def test_dna_registry_successful():
    reg = MutationRegistry()
    reg.record("good", 1, "x", {"m": 0.5}, {"m": 0.9})
    reg.record("bad", 2, "y", {"m": 0.5}, {"m": 0.1})
    successful = reg.successful(min_delta=0.0)
    assert len(successful) == 1


def test_epigenetic_promotion():
    epi = EpigeneticEngine(min_promotions=3, stability_threshold=0.7)
    epi.register("m1")
    epi.promote("m1")
    epi.promote("m1")
    state = epi.state_of("m1")
    assert state is not None
    assert not state.consolidated
    epi.promote("m1")
    assert state.consolidated


def test_epigenetic_rollback():
    epi = EpigeneticEngine()
    epi.register("m1")
    epi.suppress("m1")
    epi.suppress("m1")
    assert epi.should_rollback("m1")


def test_evolutionary_memory_store_and_retrieve():
    mem = EvolutionaryMemory()
    mem.store(MemoryEntry("m1", "ctx1", "test", 1, "x",
                          {"a": 0.5}, {"a": 0.9}, outcome=0.4))
    mem.store(MemoryEntry("m2", "ctx1", "test", 1, "y",
                          {"a": 0.5}, {"a": 0.3}, outcome=-0.2))
    similar = mem.find_similar("ctx1")
    assert len(similar) == 2
    assert mem.has_failed_before("ctx1", "y")
    assert not mem.has_failed_before("ctx1", "z")


def test_ilf_regulator_approves_good_mutation():
    ilf = ILFRegulator(min_threshold=0.3)
    verdict = ilf.assess(performance_impact=0.8, coherence_impact=0.5,
                         resilience_impact=0.7, energy_impact=0.2)
    assert verdict.approved


def test_ilf_regulator_rejects_bad_mutation():
    ilf = ILFRegulator(min_threshold=0.5)
    verdict = ilf.assess(performance_impact=0.1, coherence_impact=-0.5,
                         resilience_impact=-0.3, energy_impact=0.9)
    assert not verdict.approved


def test_neurogenesis_pipeline():
    ng = NeurogenesisPipeline(min_occurrences=3)
    for _ in range(3):
        ng.observe_activity("test_pattern", {})
    activities = ng.detect_recurrent_activities()
    assert len(activities) == 1
    spec = ng.propose_module("test_pattern", novelty=0.5)
    assert spec is not None
    assert spec.status.name == "CREATED"
    ng.advance(spec.module_id)
    ng.advance(spec.module_id)
    assert len(ng.active_modules()) == 0
    ng.advance(spec.module_id)
    ng.advance(spec.module_id)
    ng.advance(spec.module_id)
    assert len(ng.active_modules()) >= 1


def test_rollback_manager():
    reg = MutationRegistry()
    epi = EpigeneticEngine()
    rm = RollbackManager(reg, epi)
    rec = reg.record("test", 1, "x", {"coherence_phi": 0.8}, {"coherence_phi": 0.3})
    epi.suppress(rec.mutation_id)
    epi.suppress(rec.mutation_id)
    plan = rm.evaluate(rec, {"coherence_phi": 0.3})
    assert plan is not None
    assert plan.is_actionable


def test_quantum_oracle_grover():
    oracle = QuantumOracle(num_qubits=6, seed=42)
    items = [0.1, 0.2, 0.3, 0.8, 0.9, 0.05, 0.7, 0.4]
    idx, score = oracle.search(items, threshold=0.6)
    assert idx >= 0
    assert score > 0.6


def test_quantum_oracle_no_match():
    oracle = QuantumOracle(num_qubits=4, seed=42)
    items = [0.1, 0.2, 0.3, 0.4]
    idx, score = oracle.search(items, threshold=0.9)
    assert idx == -1
    assert score == 0.0


def test_qaoa_selector():
    qaoa = QAOASelector(num_qubits=4)
    proposals = [
        {"id": "a", "expected_impact": 0.8, "risk": 0.2, "energy_cost": 0.1},
        {"id": "b", "expected_impact": 0.3, "risk": 0.7, "energy_cost": 0.5},
        {"id": "c", "expected_impact": 0.6, "risk": 0.3, "energy_cost": 0.2},
    ]
    selected = qaoa.select(proposals, num_selected=2)
    assert len(selected) <= 2


def test_quantum_kernel_classifier():
    kernel = QuantumKernelClassifier(num_qubits=4, seed=42)
    X = [np.array([0.8, 0.2, 0.7, 0.1], dtype=np.float64),
         np.array([0.2, 0.8, 0.3, 0.5], dtype=np.float64)]
    y = [1.0, -1.0]
    kernel.fit(X, y)
    pred = kernel.predict(np.array([0.7, 0.3, 0.6, 0.2], dtype=np.float64))
    assert isinstance(pred, float)


def test_quantum_evolution_engine():
    qee = QuantumEvolutionEngine()
    qee.oracle = QuantumOracle(num_qubits=4, seed=42)
    strategies = [
        {"id": "a", "expected_impact": 0.8, "risk": 0.2, "confidence": 0.7,
         "energy_cost": 0.1, "novelty": 0.3, "score": 0.8},
        {"id": "b", "expected_impact": 0.3, "risk": 0.7, "confidence": 0.4,
         "energy_cost": 0.5, "novelty": 0.1, "score": 0.3},
    ]
    results = qee.propose_candidates(strategies, {}, top_k=2)
    assert len(results) >= 1


def test_cortex_tick():
    cortex = SelfImprovementCortex()
    report = cortex.tick({"coherence_phi": 0.7, "plasticity_index": 0.5})
    assert report.tick == 1
    assert report.proposals >= 0
    assert report.selected >= 0


def test_cortex_multi_tick():
    cortex = SelfImprovementCortex()
    for i in range(5):
        report = cortex.tick({"coherence_phi": 0.7, "plasticity_index": 0.3 + i * 0.1})
    summary = cortex.report()
    assert summary["ticks"] == 5
    assert summary["total_proposals"] >= 0


def test_harness_update():
    hu = HarnessUpdate(level=AdaptiveLevel.PROMPT, target="test", old_value="a", new_value="b")
    assert "Harness" in hu.description


def test_weight_update():
    wu = WeightUpdate(level=AdaptiveLevel.LORA, method="lora", target_model="policy")
    assert "Weight" in wu.description


def test_dna_agent_proposes():
    agent = DigitalDNAAgent()
    props = agent.propose({"dna_stability": 0.9, "mutation_success_rate": 0.2})
    assert len(props) >= 1


def test_neuroscience_agent_low_coherence():
    agent = NeuroscienceAgent()
    props = agent.propose({"coherence_phi": 0.2, "plasticity_index": 0.5})
    assert any(p.target == "world_model" for p in props)


def test_safety_agent_high_confidence():
    agent = SafetyAgent()
    props = agent.propose({"resilience": 0.2})
    assert any(p.target == "safety_tools" for p in props)
    if props:
        assert agent.confidence_in(props[0]) > 0.9


def test_cli_sia_help():
    import subprocess
    import sys
    result = subprocess.run([sys.executable, "-m", "q_speace.cli", "sia", "--help"],
                           capture_output=True, text=True, cwd=r"C:\Users\rober\Desktop\Q-SPEACE\q_speace")
    assert "Self-Improvement" in result.stdout or "Self-Improvement" in result.stderr


def test_cli_sia_run():
    import subprocess
    import sys
    result = subprocess.run([sys.executable, "-m", "q_speace.cli", "sia", "run", "--ticks", "3"],
                           capture_output=True, text=True, cwd=r"C:\Users\rober\Desktop\Q-SPEACE\q_speace")
    assert result.returncode == 0


def test_cli_qee():
    import subprocess
    import sys
    result = subprocess.run([sys.executable, "-m", "q_speace.cli", "quantum", "qee"],
                           capture_output=True, text=True, cwd=r"C:\Users\rober\Desktop\Q-SPEACE\q_speace")
    assert result.returncode == 0
