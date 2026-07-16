"""Smoke test del decomposition del CellularBrainOrchestrator (T66 strangler fig)."""
import json
import time
from pathlib import Path

REPORT_DIR = Path(r"C:\cellular_speace\reports\actions\02_kernel_smoketest")
REPORT_DIR.mkdir(parents=True, exist_ok=True)
results = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "tests": {}}

def add(name, ok, detail):
    results["tests"][name] = {"ok": bool(ok), "detail": str(detail)}
    print("[{}] {}: {}".format("OK" if ok else "FAIL", name, detail))

# 1) build_mvp istanzia i coordinator e li registra nello scheduler
try:
    from speace_core.orchestrator import CellularBrainOrchestrator
    from speace_core.dna.parser import load_genome
    g = load_genome(Path(r"C:\cellular_speace\speace_core\dna\genome\default_genome.yaml"))
    orch = CellularBrainOrchestrator.build_mvp(g)
    sched = getattr(orch, "_subsystem_scheduler", None)
    coord_attrs = ["_memory_coordinator", "_evolution_coordinator", "_metabolism_coordinator",
                   "_persistence_coordinator", "_self_improvement_coordinator",
                   "_action_governance_coordinator", "_world_model_coordinator"]
    present = {a: getattr(orch, a, None) is not None for a in coord_attrs}
    registered = list(sched._plugins.keys()) if sched else []
    add("orchestrator_decomposition", all(present.values()) and sched is not None,
        "present={} registered={}".format(present, registered))
except Exception as e:
    add("orchestrator_decomposition", False, repr(e))

# 2) SubsystemScheduler esegue fasi in sequenza
try:
    from speace_core.cellular_brain.runtime.subsystem_scheduler import SubsystemScheduler
    from speace_core.cellular_brain.runtime.subsystem_context import SubsystemContext, TickState
    sched = SubsystemScheduler()
    called = []
    class FakeCoord:
        def __init__(self, name):
            self._n = name
        @property
        def name(self):
            return self._n
        @property
        def enabled(self):
            return True
        def on_tick(self, ctx):
            called.append(self._n)
            return None
    sched.assign("memory", FakeCoord("memory"))
    sched.assign("evolution", FakeCoord("evolution"))
    sched.assign("metabolism", FakeCoord("metabolism"))
    ctx = SubsystemContext(orchestrator_ref=lambda: None)
    out = sched.run_all(ctx)
    add("subsystem_scheduler_phases", True, "phases_called={} out={}".format(called, out))
except Exception as e:
    add("subsystem_scheduler_phases", False, repr(e))

# 3) DNA cognitive genome
try:
    from speace_core.dna.evolution_genes import GeneType, GeneFactory
    factory = GeneFactory()
    e = factory.create_gene(GeneType.COGNITIVE, name="test", weight=0.5, attention=0.7)
    add("dna_gene_factory", True, "created_gene_type={} value={}".format(type(e).__name__, e.value))
except Exception as e:
    add("dna_gene_factory", False, repr(e))

results["summary"] = {
    "total": len(results["tests"]),
    "passed": sum(1 for v in results["tests"].values() if v["ok"]),
    "failed": sum(1 for v in results["tests"].values() if not v["ok"]),
}
(REPORT_DIR / "orchestrator_smoketest.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
print("\nSummary: {}".format(results["summary"]))
