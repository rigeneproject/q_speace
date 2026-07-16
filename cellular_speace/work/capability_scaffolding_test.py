"""Test failure_memory + object_centric_representation scaffolding."""
import json
from pathlib import Path
import tempfile

REPORT_DIR = Path(r"C:\cellular_speace\reports\actions\05_capability_scaffolding")
REPORT_DIR.mkdir(parents=True, exist_ok=True)
results = {"tests": {}}

def add(name, ok, detail):
    results["tests"][name] = {"ok": bool(ok), "detail": str(detail)}
    print("[{}] {}: {}".format("OK" if ok else "FAIL", name, detail))

# 1) Failure memory
try:
    from speace_core.cellular_brain.memory.gap_scaffolds import FailureMemory, FailureRecord
    fm = FailureMemory()
    fm.record(FailureRecord("fspi", "arc_task_42", "no_candidate", {"task_id": "42"}, 0.7, ["arc"]))
    fm.record(FailureRecord("fspi", "arc_task_43", "timeout", {"task_id": "43"}, 0.5, ["arc"]))
    fm.record(FailureRecord("regulator", "chaos", "severity_saturation", {}, 0.9, ["critical"]))
    add("failure_memory_record_count", len(fm._records) == 3, "records={}".format(len(fm._records)))
    by_sub = fm.by_subsystem("fspi")
    add("failure_memory_by_subsystem", len(by_sub) == 2, "fspi_count={}".format(len(by_sub)))
    crit = fm.by_tag("critical")
    add("failure_memory_by_tag", len(crit) == 1, "critical_count={}".format(len(crit)))
    sims = fm.similar("arc candidate", k=2)
    add("failure_memory_similar", len(sims) == 2 and sims[0][0].subsystem == "fspi",
        "top={} score={:.3f}".format(sims[0][0].task, sims[0][1]))
    stats = fm.stats()
    add("failure_memory_stats", stats["total"] == 3 and "fspi" in stats["by_subsystem"],
        "stats={}".format(stats))
except Exception as e:
    add("failure_memory", False, repr(e))

# 2) Failure memory persistence round-trip
try:
    from speace_core.cellular_brain.memory.gap_scaffolds import FailureMemory, FailureRecord
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "failures.jsonl"
        fm1 = FailureMemory(persist_path=p)
        fm1.record(FailureRecord("fspi", "arc_task_99", "no_candidate", {}, 0.5, ["arc"]))
        fm2 = FailureMemory(persist_path=p)
        add("failure_memory_persistence", len(fm2._records) == 1,
            "reloaded_records={}".format(len(fm2._records)))
except Exception as e:
    add("failure_memory_persistence", False, repr(e))

# 3) Object-centric representation
try:
    from speace_core.cellular_brain.memory.gap_scaffolds import ObjectCentricRepresentation, ObjectSlot
    ocr = ObjectCentricRepresentation()
    sc = ocr.create("scene_001")
    sc.add(ObjectSlot("red", {"color": "red", "size": 1}))
    sc.add(ObjectSlot("square", {"shape": "square"}))
    sc.add(ObjectSlot("small", {"scale": 0.3}))
    sc.relate("red", "is", "color")
    sc.relate("small", "is", "size")
    add("object_centric_create_scene", ocr.get("scene_001") is sc, "scene_id_present")
    add("object_centric_slots", len(ocr.slots("scene_001")) == 3,
        "slots={}".format(len(ocr.slots("scene_001"))))
    composed = sc.compose(["red", "square"])
    add("object_centric_compose", composed is not None and composed.name == "red__square",
        "composed_name={}".format(composed.name if composed else None))
    add("object_centric_relations", len(sc.relations) == 2, "relations={}".format(len(sc.relations)))
    add("object_centric_stats", ocr.stats()["scenes"] == 1,
        "stats={}".format(ocr.stats()))
except Exception as e:
    add("object_centric", False, repr(e))

results["summary"] = {
    "total": len(results["tests"]),
    "passed": sum(1 for v in results["tests"].values() if v["ok"]),
    "failed": sum(1 for v in results["tests"].values() if not v["ok"]),
}
(REPORT_DIR / "capability_scaffolding.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
print("\nSummary: {}".format(results["summary"]))
