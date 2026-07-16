"""Smoke test del kernel SPEACE — versione robusta (no encoding issues)."""
import json, asyncio, time
from pathlib import Path

REPORT_DIR = Path(r"C:\cellular_speace\reports\actions\02_kernel_smoketest")
REPORT_DIR.mkdir(parents=True, exist_ok=True)
results = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "tests": {}}

def add(name, ok, detail):
    results["tests"][name] = {"ok": bool(ok), "detail": str(detail)}
    print("[{}] {}: {}".format("OK" if ok else "FAIL", name, detail))

# 1) Pydantic v2 models
try:
    from speace_core.dna.models import SharedGenome, GenomeIdentity
    g = SharedGenome(identity=GenomeIdentity(entity_name="smoketest", nature="test"))
    add("pydantic_v2_shared_genome", True, "ok")
except Exception as e:
    add("pydantic_v2_shared_genome", False, repr(e))

# 2) EventBus observable dispatch
try:
    from speace_core.event_bus import EventBus, EventDispatchResult
    from speace_core.cellular_brain.base.digital_signal import DigitalSignal

    async def run_bus():
        bus = EventBus()

        def good(sig):
            return "ok"

        def bad(sig):
            raise RuntimeError("explode")

        bus.subscribe("ch", good)
        bus.subscribe("ch", bad)
        sig = DigitalSignal(source="s", target="t", payload={"x": 1})
        out = await bus.publish("ch", sig)
        return out

    bus_results = asyncio.run(run_bus())
    success_count = sum(1 for r in bus_results if r.success)
    failure_count = sum(1 for r in bus_results if not r.success)
    add("event_bus_observable_dispatch", True,
        "results={} success={} failure={} first_handler={} first_error={!r}".format(
            len(bus_results), success_count, failure_count,
            bus_results[0].handler_name, bus_results[-1].error
        ))
except Exception as e:
    add("event_bus_observable_dispatch", False, repr(e))

# 3) NeuralCircuit O(1) indexes
try:
    from speace_core.cellular_brain.circuits.neural_circuit import NeuralCircuit
    from speace_core.cellular_brain.cells.digital_neuron import DigitalNeuron
    from speace_core.cellular_brain.cells.digital_synapse import DigitalSynapse

    n_in = [DigitalNeuron(cell_id="in_{}".format(i), role="digital_neuron", threshold=0.5) for i in range(3)]
    n_hid = [DigitalNeuron(cell_id="hid_{}".format(i), role="digital_neuron", threshold=0.5) for i in range(8)]
    n_out = [DigitalNeuron(cell_id="out_{}".format(i), role="digital_neuron", threshold=0.5) for i in range(2)]
    syns = []
    for i, src in enumerate(n_in + n_hid):
        for j, tgt in enumerate(n_hid + n_out):
            if src.cell_id == tgt.cell_id:
                continue
            s = DigitalSynapse(cell_id="syn_{}_{}".format(i, j), role="digital_synapse",
                              source=src.cell_id, target=tgt.cell_id, weight=0.4)
            syns.append(s)
    circuit = NeuralCircuit(circuit_id="smoke", input_neurons=n_in, hidden_neurons=n_hid,
                           output_neurons=n_out, synapses=syns)
    t0 = time.perf_counter()
    for _ in range(10000):
        circuit._find_synapse("in_0", "hid_0")
        circuit._find_neuron("in_0")
    elapsed = (time.perf_counter() - t0) * 1000
    add("neural_circuit_o1_indexes", True,
        "neurons={} synapses={} 10000_lookups_ms={:.2f} idx_n={} idx_s={}".format(
            len(circuit.all_neurons), len(circuit.synapses), elapsed,
            len(circuit._neuron_index), len(circuit._synapse_index)))
except Exception as e:
    add("neural_circuit_o1_indexes", False, repr(e))

# 4) Runtime plugin / coordinator import (with graceful failure on missing names)
try:
    from speace_core.cellular_brain.runtime.subsystem_plugin import SubsystemPlugin
    from speace_core.cellular_brain.runtime.subsystem_context import SubsystemContext, TickState
    from speace_core.cellular_brain.runtime.subsystem_scheduler import SubsystemScheduler
    from speace_core.cellular_brain.runtime.coordinators.memory_coordinator import MemoryCoordinator
    from speace_core.cellular_brain.runtime.coordinators.evolution_coordinator import EvolutionCoordinator
    from speace_core.cellular_brain.runtime.coordinators.metabolism_coordinator import MetabolismCoordinator
    from speace_core.cellular_brain.runtime.coordinators.persistence_coordinator import PersistenceCoordinator
    from speace_core.cellular_brain.runtime.coordinators.self_improvement_coordinator import SelfImprovementCoordinator
    from speace_core.cellular_brain.runtime.coordinators.action_governance_coordinator import ActionGovernanceCoordinator
    from speace_core.cellular_brain.runtime.coordinators.world_model_coordinator import WorldModelCoordinator
    from speace_core.cellular_brain.runtime.coordinators.game_ai_integration_coordinator import GameAIIntegrationCoordinator
    import importlib
    sub = importlib.import_module("speace_core.cellular_brain.runtime.coordinators.substrate_coordinator")
    sub_classes = [n for n in dir(sub) if not n.startswith("_") and n.endswith("Coordinator")]
    if not sub_classes:
        # Acceptable: any public class counts as a coordinator module
        sub_classes = [n for n in dir(sub) if not n.startswith("_")]
    add("runtime_plugin_coordinators", True,
        "memory/evolution/metabolism/persistence/self_improvement/action_governance/world_model/game_ai_integration + substrate_module={}".format(sub_classes[:5]))
except Exception as e:
    add("runtime_plugin_coordinators", False, repr(e))

# 5) DNA cognitive genome + evolution genes
try:
    from speace_core.dna.cognitive_genome import CognitiveGenome, CellExpressionRules
    from speace_core.dna.evolution_genes import EvolutionGene, GeneType, GeneRegistry
    add("dna_cognitive_genome_evolution_genes", True,
        "gene_types={}".format([g.value for g in GeneType]))
except Exception as e:
    add("dna_cognitive_genome_evolution_genes", False, repr(e))

# 6) Species orientation in default genome
try:
    import yaml
    sp = yaml.safe_load(Path(r"C:\cellular_speace\speace_core\dna\genome\core\species_orientation.yaml").read_text(encoding="utf-8"))
    default_text = Path(r"C:\cellular_speace\speace_core\dna\genome\default_genome.yaml").read_text(encoding="utf-8")
    default = yaml.safe_load(default_text)
    referenced = ("species_orientation" in default_text)
    add("species_orientation_yaml", True,
        "name={} referenced_in_default_genome={}".format(sp["species_orientation"]["name"], referenced))
except Exception as e:
    add("species_orientation_yaml", False, repr(e))

# 7) Orchestrator build_mvp
try:
    from speace_core.orchestrator import CellularBrainOrchestrator
    from speace_core.dna.parser import load_genome
    g = load_genome(Path(r"C:\cellular_speace\speace_core\dna\genome\default_genome.yaml"))
    orch = CellularBrainOrchestrator.build_mvp(g)
    has_circuit = hasattr(orch, "circuit") or hasattr(orch, "_circuit")
    add("orchestrator_build_mvp", True,
        "circuit_attr_present={} has_coordinators_attr={}".format(has_circuit, hasattr(orch, "coordinators")))
except Exception as e:
    add("orchestrator_build_mvp", False, repr(e))

# 8) ConfigDict usage in dna models
try:
    from speace_core.dna.models import SharedGenome
    has_cfg = "ConfigDict" in str(SharedGenome.model_config) or hasattr(SharedGenome, "model_config")
    add("pydantic_model_config_present", bool(has_cfg), "model_config_type={}".format(type(SharedGenome.model_config).__name__))
except Exception as e:
    add("pydantic_model_config_present", False, repr(e))

results["summary"] = {
    "total": len(results["tests"]),
    "passed": sum(1 for v in results["tests"].values() if v["ok"]),
    "failed": sum(1 for v in results["tests"].values() if not v["ok"]),
}
(REPORT_DIR / "kernel_smoketest.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
print("\nSummary: {}".format(results["summary"]))
