#!/usr/bin/env python
"""ARC-AGI Loop — runs ARC-AGI benchmark every 30 minutes and reports cognitive level as % of AGI."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from speace_core.cellular_brain.cognition.few_shot_program_induction_engine import (
    FewShotProgramInductionEngine,
)
from speace_core.cellular_brain.cognition.spatial_symbolic_reasoning_layer import (
    SpatialSymbolicReasoningLayer,
)
from speace_core.cellular_brain.cognition.meta_learning_program_composer import (
    MetaLearningProgramComposer,
)
from speace_core.cellular_brain.cognition.neural_symbolic_primitive_learner import (
    NSPLEngine,
)
from speace_core.cellular_brain.cognition.llm_augmented_program_synthesis import (
    LLMAugmentedProgramSynthesis,
)
from speace_core.cellular_brain.cognition.program_models import (
    _PRIMITIVE_REGISTRY,
)
from speace_core.cellular_brain.language.linguistic_cortical_bridge import (
    LinguisticCorticalBridge,
)
from speace_core.benchmark.arc_agi_adapter import ARCAGIAdapter
from speace_core.dna.parser import load_genome
from speace_core.orchestrator import CellularBrainOrchestrator


HUMAN_ARC_ACCURACY = 0.85


def _build_synthetic_nspl_tasks(registry):
    import random
    tasks = []
    simple = [n for n in registry if n in (
        "identity", "rotate_90", "flip_horizontal", "flip_vertical",
        "fill_holes", "outline", "invert_colors", "remove_noise",
    )]
    for name in simple:
        fn = registry.get(name)
        if fn is None:
            continue
        for _ in range(5):
            grid = [[random.randint(0, 3) for _ in range(3)] for _ in range(3)]
            try:
                out = fn(grid, {})
            except Exception:
                continue
            if out is None:
                continue
            tasks.append({"train": [{"input": grid, "output": out}]})
    return tasks


def build_engine():
    spatial = SpatialSymbolicReasoningLayer()
    nspl = NSPLEngine(_PRIMITIVE_REGISTRY)
    synth_tasks = _build_synthetic_nspl_tasks(_PRIMITIVE_REGISTRY)
    nspl_data = nspl.build_training_data(synth_tasks, max_pairs=50)
    nspl.train(nspl_data, epochs=3, lr=0.05)

    mlpc = MetaLearningProgramComposer()
    bridge = LinguisticCorticalBridge(mock_mode=True)
    llm_aps = LLMAugmentedProgramSynthesis(
        bridge=bridge, primitive_registry=_PRIMITIVE_REGISTRY,
        meta_composer=mlpc, evaluation_mode=True,
    )

    engine = FewShotProgramInductionEngine(
        spatial_layer=spatial,
        nspl_engine=nspl,
        meta_learning_composer=mlpc,
        llm_aps=llm_aps,
        max_program_depth=3,
        max_candidates=150,
    )
    return engine


async def run_arc_benchmark(genome_path: Path, data_dir: Path, limit: int | None) -> dict:
    genome = load_genome(genome_path)
    engine = build_engine()
    orchestrator = CellularBrainOrchestrator.build_mvp(genome)
    orchestrator.arc_agi_benchmark_enabled = True
    orchestrator.evaluation_mode = True
    orchestrator._arc_agi_adapter = ARCAGIAdapter(
        engine=engine,
        data_dir=str(data_dir),
        evaluation_mode=True,
    )

    report = await orchestrator.run_arc_agi_benchmark(split="training", limit=limit)
    return report


def calculate_agi_percentage(arc_accuracy: float) -> float:
    """Calculate cognitive level as percentage of human-level AGI on ARC."""
    return min(100.0, (arc_accuracy / HUMAN_ARC_ACCURACY) * 100.0)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ARC-AGI benchmark loop every 30 minutes")
    parser.add_argument("--interval", type=int, default=1800, help="Interval in seconds (default: 1800 = 30 min)")
    parser.add_argument("--limit", type=int, default=50, help="Max tasks per run (default: 50)")
    parser.add_argument("--genome", default=None, help="Path to genome YAML")
    parser.add_argument("--data-dir", default="data/arc_agi", help="Path to ARC JSON files")
    parser.add_argument("--output-dir", default="reports/arc_agi_loop", help="Report output directory")
    parser.add_argument("--max-runs", type=int, default=None, help="Max number of runs (default: infinite)")
    args = parser.parse_args()

    genome_path = Path(args.genome) if args.genome else Path(__file__).resolve().parent.parent / "speace_core" / "dna" / "genome" / "default_genome.yaml"
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Starting ARC-AGI loop: interval={args.interval}s, limit={args.limit}")
    print(f"Genome: {genome_path}")
    print(f"Data: {data_dir}")
    print(f"Output: {output_dir}")
    print(f"Human ARC baseline: {HUMAN_ARC_ACCURACY:.0%}")
    print("-" * 60)

    run_count = 0
    while args.max_runs is None or run_count < args.max_runs:
        run_count += 1
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        print(f"\n[{ts}] Run #{run_count} starting...")

        try:
            report = asyncio.run(run_arc_benchmark(genome_path, data_dir, args.limit))
        except Exception as exc:
            print(f"[{ts}] ERROR: {exc}")
            if args.max_runs is None:
                print(f"Waiting {args.interval}s before retry...")
                time.sleep(args.interval)
                continue
            return 1

        arc_accuracy = report.get("top1_accuracy", 0.0)
        agi_percentage = calculate_agi_percentage(arc_accuracy)
        correct = report.get("correct", 0)
        attempted = report.get("attempted", 0)

        print(f"[{ts}] ARC Accuracy: {arc_accuracy:.2%} ({correct}/{attempted})")
        print(f"[{ts}] Cognitive Level (vs AGI): {agi_percentage:.1f}%")

        # Save detailed report
        json_path = output_dir / f"arc_agi_loop_{ts}.json"
        json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        # Save summary
        summary = {
            "run": run_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "arc_accuracy": arc_accuracy,
            "agi_percentage": agi_percentage,
            "correct": correct,
            "attempted": attempted,
            "total_tasks": report.get("total_tasks", 0),
        }
        summary_path = output_dir / f"summary_{ts}.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        # Append to cumulative log
        log_path = output_dir / "arc_agi_loop_log.jsonl"
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(summary) + "\n")

        if args.max_runs is None or run_count < args.max_runs:
            print(f"[{ts}] Waiting {args.interval}s ({args.interval//60} min) until next run...")
            time.sleep(args.interval)

    print(f"\nCompleted {run_count} runs. Logs saved to {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())