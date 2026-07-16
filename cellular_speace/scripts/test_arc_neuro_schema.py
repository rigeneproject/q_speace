"""ARC-AGI neuromodulation — test con schema library pre-popolato."""
import json
import os
import shutil
import time
from speace_core.cellular_brain.cognition.few_shot_program_induction_engine import (
    FewShotProgramInductionEngine,
)
from speace_core.benchmark.arc_agi_adapter import ARCAGIAdapter
from speace_core.cellular_brain.cognition.program_schema_library import ProgramSchemaLibrary
from speace_core.cellular_brain.cognition.spatial_symbolic_reasoning_layer import (
    SpatialSymbolicReasoningLayer,
)

DATA_DIR = "data/arc_agi"
SCHEMA_DIR = "data/schema_library_neuro"
REPORT_DIR = "reports/arc_agi_neuro"
os.makedirs(REPORT_DIR, exist_ok=True)

# Phase 1: Build shared schema library by running baseline on all 400 tasks
schema_dir = SCHEMA_DIR
if os.path.exists(schema_dir):
    shutil.rmtree(schema_dir)
os.makedirs(schema_dir, exist_ok=True)

print("=" * 60)
print("FASE 1: Build schema library su 400 task (baseline)")
print("=" * 60)
spatial = SpatialSymbolicReasoningLayer()
engine = FewShotProgramInductionEngine(
    spatial_layer=spatial, max_candidates=100, max_program_depth=3,
)
adapter = ARCAGIAdapter(engine=engine, data_dir=DATA_DIR)
adapter.schema_library = ProgramSchemaLibrary(data_dir=schema_dir)

result_base = adapter.run_benchmark(limit=400, modulator_context=None)
print(f"Baseline 400 task: {result_base['correct']}/{result_base['attempted']} = {result_base['top1_accuracy']:.2%}")
schema_count = adapter.schema_library.size() if hasattr(adapter.schema_library, 'size') else 0
if not schema_count:
    # Fallback: check via internal store
    store = getattr(adapter.schema_library, '_store', {})
    schema_count = len(store) if isinstance(store, dict) else 0
print(f"Schemas stored: {schema_count}")

# Phase 2: Run conditions with SAME schema library
conditions = [
    ("BASELINE (no ctx)", None),
    ("HIGH 5HT (explore)", {
        "acetylcholine": 0.5, "noradrenaline": 0.3, "serotonin": 0.9,
        "gaba_level": 0.5, "global_coherence": 0.5, "metastability": 0.0, "dmn_ratio": 1.0,
    }),
    ("HIGH ACh (focus)", {
        "acetylcholine": 0.9, "noradrenaline": 0.3, "serotonin": 0.5,
        "gaba_level": 0.5, "global_coherence": 0.5, "metastability": 0.0, "dmn_ratio": 1.0,
    }),
    ("HIGH NE (urgent)", {
        "acetylcholine": 0.5, "noradrenaline": 0.9, "serotonin": 0.5,
        "gaba_level": 0.5, "global_coherence": 0.5, "metastability": 0.0, "dmn_ratio": 1.0,
    }),
    ("HIGH GABA (inhibited)", {
        "acetylcholine": 0.5, "noradrenaline": 0.3, "serotonin": 0.5,
        "gaba_level": 0.9, "global_coherence": 0.5, "metastability": 0.0, "dmn_ratio": 1.0,
    }),
]

print("\n" + "=" * 60)
print("FASE 2: Stessi 400 task con diversa neuromodulazione")
print("=" * 60)

all_results = {}
for label, ctx in conditions:
    spatial2 = SpatialSymbolicReasoningLayer()
    engine2 = FewShotProgramInductionEngine(
        spatial_layer=spatial2, max_candidates=100, max_program_depth=3,
    )
    adapter2 = ARCAGIAdapter(engine=engine2, data_dir=DATA_DIR)
    adapter2.schema_library = ProgramSchemaLibrary(data_dir=schema_dir)

    start = time.time()
    result = adapter2.run_benchmark(limit=400, modulator_context=ctx)
    elapsed = time.time() - start

    cands = [t["results"][0]["candidates_explored"] for t in result["per_task"]]
    avg_c = sum(cands) / len(cands) if cands else 0
    no_cand = result.get("failure_memory", {}).get("failure_patterns", {}).get("no_candidates", 0)

    print(f"\n  {label}")
    print(f"    Correct: {result['correct']}/{result['attempted']} = {result['top1_accuracy']:.2%}")
    print(f"    Avg candidates: {avg_c:.1f}  No-candidates: {no_cand}")
    print(f"    Time: {elapsed:.1f}s")

    all_results[label] = result

# Comparison
print("\n" + "=" * 60)
print("COMPARISON")
print("=" * 60)
print(f"{'Condition':<30s} {'Correct':>8s} {'Acc%':>7s} {'AvgC':>5s} {'NoCand':>7s} {'Time':>6s}")
print("-" * 70)
for label in [c[0] for c in conditions]:
    r = all_results[label]
    cands = [t["results"][0]["candidates_explored"] for t in r["per_task"]]
    avg_c = sum(cands) / len(cands) if cands else 0
    no_c = r.get("failure_memory", {}).get("failure_patterns", {}).get("no_candidates", 0)
    print(f"{label:<30s} {r['correct']:>3d}/{r['attempted']:<3d} {r['top1_accuracy']:>6.2%} "
          f"{avg_c:>4.1f} {no_c:>6d} {r.get('elapsed', 0):>5.1f}")

# Diff matrix: which tasks changed?
print("\n" + "=" * 60)
print("TASK-LEVEL CHANGES (vs baseline)")
print("=" * 60)
base_task_map = {t["task_id"]: t for t in all_results[conditions[0][0]]["per_task"]}
for label, ctx in conditions[1:]:
    r = all_results[label]
    changes = []
    for t in r["per_task"]:
        base_t = base_task_map[t["task_id"]]
        if t["correct"] != base_t["correct"]:
            direction = "+" if t["correct"] else "-"
            changes.append(f"{t['task_id']}({direction})")
    if changes:
        print(f"  {label}: {len(changes)} changes: {', '.join(changes[:10])}")
    else:
        print(f"  {label}: 0 changes (identical to baseline)")

# Schema library final state
schema_count_final = adapter2.schema_library.size() if hasattr(adapter2.schema_library, 'size') else 0
if not schema_count_final:
    store2 = getattr(adapter2.schema_library, '_store', {})
    schema_count_final = len(store2) if isinstance(store2, dict) else 0
print(f"\nSchema library: {schema_count} before, {schema_count_final} after")
print("\nDone.")
