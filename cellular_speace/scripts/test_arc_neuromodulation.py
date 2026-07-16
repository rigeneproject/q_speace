"""ARC-AGI neuromodulation benchmark — misura l'effetto causale.
Run: python scripts/test_arc_neuromodulation.py --tasks 50
"""
import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

from speace_core.cellular_brain.cognition.few_shot_program_induction_engine import (
    FewShotProgramInductionEngine,
)
from speace_core.benchmark.arc_agi_adapter import ARCAGIAdapter
from speace_core.cellular_brain.cognition.program_schema_library import ProgramSchemaLibrary
from speace_core.cellular_brain.cognition.spatial_symbolic_reasoning_layer import (
    SpatialSymbolicReasoningLayer,
)


def run_benchmark(label, engine, data_dir, schema_dir, limit, ctx=None):
    """Run ARC-AGI benchmark with optional modulator context."""
    adapter = ARCAGIAdapter(engine=engine, data_dir=data_dir)
    adapter.schema_library = ProgramSchemaLibrary(data_dir=schema_dir)
    start = time.time()
    result = adapter.run_benchmark(limit=limit, modulator_context=ctx)
    elapsed = time.time() - start
    result["label"] = label
    result["elapsed_sec"] = round(elapsed, 1)
    return result, adapter


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=int, default=50, help="Number of ARC tasks to evaluate")
    parser.add_argument("--data-dir", default="data/arc_agi", help="Path to ARC JSON files")
    parser.add_argument("--output-dir", default="reports/arc_agi_neuro", help="Output directory")
    parser.add_argument("--clean", action="store_true", help="Clean schema dirs before run")
    args = parser.parse_args()

    base_schema = os.path.join(args.output_dir, "schema_baseline")
    explore_schema = os.path.join(args.output_dir, "schema_explore")
    focus_schema = os.path.join(args.output_dir, "schema_focus")
    urgent_schema = os.path.join(args.output_dir, "schema_urgent")

    for d in [base_schema, explore_schema, focus_schema, urgent_schema]:
        if args.clean and os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)
    os.makedirs(args.output_dir, exist_ok=True)

    limit = args.tasks
    print(f"ARC-AGI Neuromodulation Benchmark — {limit} tasks")
    print("=" * 60)

    contexts = [
        ("BASELINE (no modulation)", None),
        ("HIGH 5HT (exploratory, depth+1)",
         {"acetylcholine": 0.5, "noradrenaline": 0.3, "serotonin": 0.9,
          "gaba_level": 0.5, "global_coherence": 0.5, "metastability": 0.0, "dmn_ratio": 1.0}),
        ("HIGH ACh (focused, depth-1)",
         {"acetylcholine": 0.9, "noradrenaline": 0.3, "serotonin": 0.5,
          "gaba_level": 0.5, "global_coherence": 0.5, "metastability": 0.0, "dmn_ratio": 1.0}),
        ("HIGH NE (urgent, depth-1, top_k=1)",
         {"acetylcholine": 0.5, "noradrenaline": 0.9, "serotonin": 0.5,
          "gaba_level": 0.5, "global_coherence": 0.5, "metastability": 0.0, "dmn_ratio": 1.0}),
    ]

    results = []
    all_reports = {}

    for label, ctx in contexts:
        schema_tag = label.split(" ")[0].lower()
        schema_dir = os.path.join(args.output_dir, f"schema_{schema_tag}")

        spatial = SpatialSymbolicReasoningLayer()
        engine = FewShotProgramInductionEngine(
            spatial_layer=spatial,
            max_candidates=100,
            max_program_depth=3,
        )

        report, adapter = run_benchmark(
            label=label,
            engine=engine,
            data_dir=args.data_dir,
            schema_dir=schema_dir,
            limit=limit,
            ctx=ctx,
        )
        results.append(report)

        print(f"\n  {label}")
        print(f"    Correct: {report['correct']}/{report['attempted']} = {report['top1_accuracy']:.2%}")
        print(f"    Time: {report['elapsed_sec']}s")

        # Collect per-task candidate stats
        cand_counts = [t["results"][0]["candidates_explored"] for t in report["per_task"]]
        print(f"    Candidates: avg={sum(cand_counts)/len(cand_counts):.1f}  "
              f"max={max(cand_counts)}  min={min(cand_counts)}")

        fail = report.get("failure_memory", {})
        no_cand = fail.get("failure_patterns", {}).get("no_candidates", 0)
        print(f"    Failures: no_candidates={no_cand}")

        all_reports[label] = report

    # Comparison table
    print("\n" + "=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)
    print(f"{'Condition':<30s} {'Correct':>8s} {'Accuracy':>10s} {'AvgCand':>8s} {'Time(s)':>8s}")
    print("-" * 70)
    for r in results:
        cands = [t["results"][0]["candidates_explored"] for t in r["per_task"]]
        avg_cand = sum(cands) / len(cands) if cands else 0
        print(f"{r['label']:<30s} {r['correct']:>3d}/{r['attempted']:<3d} "
              f"{r['top1_accuracy']:>9.2%} {avg_cand:>7.1f} {r['elapsed_sec']:>7.1f}")

    # Per-task comparison (first 10 tasks)
    print("\n" + "=" * 60)
    print("PER-TASK COMPARISON (first 10)")
    print(f"{'Task':<12s} {'Baseline':>10s} {'5HT':>7s} {'ACh':>7s} {'NE':>7s}")
    print("-" * 50)
    baseline_report = results[0]
    for i, b_task in enumerate(baseline_report["per_task"][:10]):
        tid = b_task["task_id"]
        b_c = "✓" if b_task["correct"] else "·"
        vals = [b_c]
        for r in results[1:]:
            o_task = r["per_task"][i]
            o_c = "✓" if o_task["correct"] else "·"
            vals.append(o_c)
            if o_task["correct"] != b_task["correct"]:
                diff = "+" if o_task["correct"] else "-"
                vals[-1] += diff
        print(f"  {tid:<12s} {vals[0]:>10s} {vals[1]:>7s} {vals[2]:>7s} {vals[3]:>7s}")

    # Save full reports
    report_path = os.path.join(args.output_dir, "neuromodulation_report.json")
    with open(report_path, "w") as f:
        serializable = {}
        for label, report in all_reports.items():
            r_copy = dict(report)
            r_copy.pop("per_task", None)  # too large
            serializable[label] = r_copy
        json.dump(serializable, f, indent=2)
    print(f"\nReport salvato: {report_path}")


if __name__ == "__main__":
    main()
