import pytest

from speace_core.cellular_brain.memory.semantic.cell_assembly import (
    AssemblyActivationTrace,
    CellAssembly,
    SemanticMemoryMetrics,
    SemanticRecallResult,
)
from speace_core.cellular_brain.memory.semantic.cell_assembly_engine import (
    CellAssemblyEngine,
)
from speace_core.cellular_brain.memory.semantic.semantic_memory_store import (
    SemanticMemoryStore,
)
from speace_core.cellular_brain.memory.semantic.semantic_recall_engine import (
    SemanticRecallEngine,
)
from speace_core.cellular_brain.memory.morphology_events import MorphologyEventType
from speace_core.cellular_brain.circuits.neural_circuit import NeuralCircuit
from speace_core.cellular_brain.cells.digital_neuron import DigitalNeuron
from speace_core.orchestrator import CellularBrainOrchestrator
from speace_core.dna.models import SharedGenome


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _make_store():
    return SemanticMemoryStore()


def _make_engine(store=None):
    return CellAssemblyEngine(store=store or _make_store())


def _make_orchestrator():
    genome = SharedGenome(genome_id="test", version="1")
    orch = CellularBrainOrchestrator.build_mvp(genome)
    return orch


def _make_circuit_with_active_neurons():
    n1 = DigitalNeuron(cell_id="n1", role="digital_neuron", energy=0.8, activation=0.6, consecutive_fires=0, apoptosis_risk=0.0)
    n2 = DigitalNeuron(cell_id="n2", role="digital_neuron", energy=0.8, activation=0.7, consecutive_fires=0, apoptosis_risk=0.0)
    n3 = DigitalNeuron(cell_id="n3", role="digital_neuron", energy=0.8, activation=0.5, consecutive_fires=0, apoptosis_risk=0.0)
    circuit = NeuralCircuit(circuit_id="t", input_neurons=[n1], hidden_neurons=[n2, n3], output_neurons=[])
    return circuit


# ------------------------------------------------------------------ #
# 1. Model creation
# ------------------------------------------------------------------ #

def test_cell_assembly_model():
    a = CellAssembly(assembly_id="a1", neuron_ids=["n1", "n2"], strength=0.5)
    assert a.assembly_id == "a1"
    assert a.strength == 0.5


def test_assembly_activation_trace_model():
    t = AssemblyActivationTrace(tick_id=1, active_neuron_ids=["n1"], mean_activation=0.5)
    assert t.tick_id == 1


def test_semantic_recall_result_model():
    r = SemanticRecallResult(best_match_id="a1", similarity_score=0.8, recall_success=True)
    assert r.recall_success is True


def test_semantic_memory_metrics_model():
    m = SemanticMemoryMetrics(assembly_count=3, mean_assembly_strength=0.4)
    assert m.assembly_count == 3


# ------------------------------------------------------------------ #
# 3. SemanticMemoryStore save/load
# ------------------------------------------------------------------ #

def test_store_save_and_get():
    store = _make_store()
    a = CellAssembly(assembly_id="a1", neuron_ids=["n1"])
    store.save(a)
    assert store.get_by_id("a1") is not None
    assert store.count() == 1


def test_store_list_active():
    store = _make_store()
    store.save(CellAssembly(assembly_id="a1", active=True))
    store.save(CellAssembly(assembly_id="a2", active=False))
    assert len(store.list_active()) == 1


def test_store_list_consolidated():
    store = _make_store()
    store.save(CellAssembly(assembly_id="a1", consolidated=True))
    store.save(CellAssembly(assembly_id="a2", consolidated=False))
    assert len(store.list_consolidated()) == 1


def test_store_best_by_strength():
    store = _make_store()
    store.save(CellAssembly(assembly_id="a1", strength=0.9))
    store.save(CellAssembly(assembly_id="a2", strength=0.3))
    best = store.get_best_by_strength(n=1)
    assert best[0].assembly_id == "a1"


def test_store_persistence(tmp_path):
    path = tmp_path / "assemblies.jsonl"
    store = SemanticMemoryStore(storage_path=str(path))
    store.save(CellAssembly(assembly_id="a1", neuron_ids=["n1"]))
    store.flush()
    store2 = SemanticMemoryStore(storage_path=str(path))
    assert store2.get_by_id("a1") is not None


# ------------------------------------------------------------------ #
# 4–6. observe_activation & detect_candidate_assembly
# ------------------------------------------------------------------ #

def test_observe_activation_captures_active_neurons():
    orch = _make_orchestrator()
    orch.circuit = _make_circuit_with_active_neurons()
    engine = _make_engine()
    trace = engine.observe_activation(orch)
    assert "n2" in trace.active_neuron_ids
    assert trace.mean_activation > 0.0


def test_detect_candidate_assembly_creates_when_sufficient():
    trace = AssemblyActivationTrace(
        tick_id=1,
        active_neuron_ids=["n1", "n2", "n3"],
        active_region_ids=["r1"],
        activation_vector=[0.5, 0.6, 0.7],
        mean_activation=0.6,
        confidence_score=0.5,
        coherence_phi=0.3,
    )
    engine = _make_engine()
    candidate = engine.detect_candidate_assembly(trace)
    assert candidate is not None
    assert candidate.assembly_id.startswith("asm-")


def test_detect_candidate_assembly_rejects_weak():
    trace = AssemblyActivationTrace(
        tick_id=1,
        active_neuron_ids=["n1"],
        activation_vector=[0.1],
        mean_activation=0.05,
    )
    engine = _make_engine()
    assert engine.detect_candidate_assembly(trace) is None


# ------------------------------------------------------------------ #
# 7. match_existing_assembly prevents duplicates
# ------------------------------------------------------------------ #

def test_match_existing_assembly_finds_similar():
    store = _make_store()
    store.save(CellAssembly(assembly_id="a1", activation_signature=[0.5, 0.6, 0.7], active=True, strength=0.5))
    engine = _make_engine(store)
    trace = AssemblyActivationTrace(tick_id=1, activation_vector=[0.5, 0.6, 0.7])
    matched = engine.match_existing_assembly(trace)
    assert matched is not None
    assert matched.assembly_id == "a1"


def test_match_existing_assembly_returns_none_when_dissimilar():
    store = _make_store()
    store.save(CellAssembly(assembly_id="a1", activation_signature=[1.0, 0.0, 0.0], active=True))
    engine = _make_engine(store)
    trace = AssemblyActivationTrace(tick_id=1, activation_vector=[0.0, 1.0, 0.0])
    assert engine.match_existing_assembly(trace) is None


# ------------------------------------------------------------------ #
# 8. reinforce_assembly
# ------------------------------------------------------------------ #

def test_reinforce_increases_strength_and_recurrence():
    assembly = CellAssembly(assembly_id="a1", strength=0.2, recurrence_count=1)
    trace = AssemblyActivationTrace(tick_id=2, mean_activation=0.5, coherence_phi=0.3, mean_energy=0.8)
    engine = _make_engine()
    engine.reinforce_assembly(assembly, trace)
    assert assembly.strength > 0.2
    assert assembly.recurrence_count == 2


# ------------------------------------------------------------------ #
# 9–10. decay & consolidate
# ------------------------------------------------------------------ #

def test_decay_decreases_unused_strength():
    store = _make_store()
    store.save(CellAssembly(assembly_id="a1", strength=0.10, active=True))
    engine = _make_engine(store)
    engine.decay_assemblies()
    a = store.get_by_id("a1")
    assert a.strength < 0.10


def test_consolidate_marks_stable_recurrent():
    store = _make_store()
    store.save(CellAssembly(assembly_id="a1", recurrence_count=5, stability=0.5, active=True))
    engine = _make_engine(store)
    engine.consolidate_assemblies()
    a = store.get_by_id("a1")
    assert a.consolidated is True


# ------------------------------------------------------------------ #
# 11–12. SemanticRecallEngine
# ------------------------------------------------------------------ #

def test_recall_returns_best_match():
    store = _make_store()
    store.save(CellAssembly(assembly_id="a1", activation_signature=[0.5, 0.6, 0.7], active=True, strength=0.5))
    recall = SemanticRecallEngine(store)
    result = recall.recall([0.5, 0.6, 0.7])
    assert result.recall_success is True
    assert result.best_match_id == "a1"


def test_recall_fails_safely_when_empty():
    store = _make_store()
    recall = SemanticRecallEngine(store)
    result = recall.recall([0.5, 0.6])
    assert result.recall_success is False


# ------------------------------------------------------------------ #
# 13. reactivate_assembly
# ------------------------------------------------------------------ #

def test_reactivate_injects_bounded_activation():
    orch = _make_orchestrator()
    orch.circuit = _make_circuit_with_active_neurons()
    store = _make_store()
    store.save(CellAssembly(assembly_id="a1", neuron_ids=["n2"], active=True))
    recall = SemanticRecallEngine(store, max_reactivation_energy=0.20)
    before = orch.circuit.hidden_neurons[0].activation
    recall.reactivate_assembly("a1", orch)
    after = orch.circuit.hidden_neurons[0].activation
    assert after >= before
    assert after <= before + 0.20 + 1e-6


# ------------------------------------------------------------------ #
# 14. MorphologicalMemory events
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_semantic_events_emitted():
    orch = _make_orchestrator()
    orch.semantic_memory_enabled = True
    orch.circuit = _make_circuit_with_active_neurons()
    orch.model_post_init(None)
    orch._cell_assembly_engine.min_mean_activation = 0.05
    orch._cell_assembly_engine.min_neurons = 2
    for _ in range(5):
        for n in orch.circuit.hidden_neurons:
            n.activation = 0.8
        orch.run_semantic_memory_cycle()
    events = orch.memory.events
    assert any(
        e.event_type.value in ("cell_assembly_created", "cell_assembly_reinforced")
        for e in events
    )


# ------------------------------------------------------------------ #
# 15. Benchmark metrics include semantic fields
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_benchmark_exposes_semantic_metrics():
    from speace_core.cellular_brain.benchmark.neurofunctional_benchmark import NeuroFunctionalBenchmark
    orch = _make_orchestrator()
    orch.semantic_memory_enabled = True
    orch.model_post_init(None)
    orch.circuit = _make_circuit_with_active_neurons()
    bench = NeuroFunctionalBenchmark(orch)
    result = await bench.run_case(
        "morphological_memory_trace",
        execution_mode="event_driven_burst",
        stdp_enabled=False,
        inhibition_enabled=False,
        energy_control_enabled=False,
        community_detection_enabled=False,
        confidence_enabled=False,
        inter_region_plasticity_enabled=False,
        region_signal_routing_enabled=False,
        input_pattern=[1.0, 0.0],
        target_output=[1.0, 0.0],
        n_ticks=5,
    )
    m = result.metrics
    assert hasattr(m, "semantic_assembly_count")
    assert hasattr(m, "semantic_memory_score")


# ------------------------------------------------------------------ #
# 16–17. Orchestrator integration
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_orchestrator_semantic_enabled():
    orch = _make_orchestrator()
    orch.semantic_memory_enabled = True
    orch.model_post_init(None)
    await orch.run_ticks(3)
    assert orch._semantic_memory_store is not None


@pytest.mark.asyncio
async def test_orchestrator_no_regression_when_disabled():
    orch = _make_orchestrator()
    orch.semantic_memory_enabled = False
    orch.model_post_init(None)
    await orch.run_ticks(3)
    assert orch._semantic_memory_store is None


# ------------------------------------------------------------------ #
# 18. Full semantic cycle produces assembly
# ------------------------------------------------------------------ #

@pytest.mark.asyncio
async def test_full_cycle_produces_assembly():
    orch = _make_orchestrator()
    orch.semantic_memory_enabled = True
    orch.circuit = _make_circuit_with_active_neurons()
    orch.model_post_init(None)
    orch._cell_assembly_engine.min_mean_activation = 0.05
    orch._cell_assembly_engine.min_neurons = 2
    for _ in range(8):
        for n in orch.circuit.hidden_neurons:
            n.activation = 0.8
        orch.run_semantic_memory_cycle()
    metrics = orch.get_semantic_memory_metrics()
    assert metrics is not None
    assert metrics.assembly_count >= 1
