"""Run SPEACE brain connected to an external task environment.

This launcher demonstrates a working SPEACE brain with an external task:
  - sequence prediction (default)
  - grid-world navigation
  - associative recall (paired-associate memory)

Usage:
    python run_speace_with_environment.py [prediction|grid|associative]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict

from speace_core.environment.environment_adapter import EnvironmentAdapter
from speace_core.environment.cognitive_prediction_environment import SequenceMode


def main(env_kind: str = "prediction") -> Dict[str, Any]:
    t0 = time.perf_counter()
    adapter = EnvironmentAdapter(
        enable_cor=True,
        enable_simulator_backend=True,
        simulator_backend_name="native",
        simulator_backend_interval=10,
        enable_functional_activation=True,
    )
    build_time = time.perf_counter() - t0
    print(f"[1/3] SPEACE brain built in {build_time:.2f}s")

    t1 = time.perf_counter()
    if env_kind == "prediction":
        # Run a few episodes, rotating sequence modes.
        summaries = []
        for i, mode in enumerate(list(SequenceMode)[:4]):
            print(f"[2/3] Running prediction episode {i+1}/4 (mode={mode.value})...")
            summary = adapter.run_prediction_episode(mode=mode, steps=80)
            summaries.append(summary)
            print(
                f"   steps={summary['steps']}"
                f" mean_reward={summary['mean_reward']:.3f}"
                f" learning_trend={summary['learning_trend']:+.3f}"
                f" cor_collapses={summary['cor_collapses']}"
            )
    elif env_kind == "grid":
        summaries = []
        for dim, size in [(1, 10), (1, 15), (2, 8)]:
            print(f"[2/3] Running grid episode (dim={dim}, size={size})...")
            summary = adapter.run_grid_episode(dimensions=dim, size=size)
            summaries.append(summary)
            print(
                f"   steps={summary['steps']}"
                f" total_reward={summary['total_reward']:.3f}"
                f" reached={summary['reached_target']}"
                f" final_distance={summary['final_distance']:.2f}"
            )
    elif env_kind == "associative":
        print("[2/3] Running associative recall episode...")
        summary = adapter.run_associative_recall_episode(
            num_pairs=4,
            study_repetitions=3,
            test_length=20,
        )
        summaries = [summary]
        print(
            f"   study_steps={summary['study_steps']}"
            f" test_steps={summary['test_steps']}"
            f" mean_study_reward={summary['mean_study_reward']:.3f}"
            f" mean_test_reward={summary['mean_test_reward']:.3f}"
            f" learning_gain={summary['learning_gain']:+.3f}"
            f" cor_collapses={summary['cor_collapses']}"
        )
    else:
        raise ValueError(f"Unknown env_kind: {env_kind}; use 'prediction', 'grid', or 'associative'")

    run_time = time.perf_counter() - t1
    print(f"[3/3] Task completed in {run_time:.2f}s")

    report = adapter.report()
    final = {
        "env_kind": env_kind,
        "build_time_seconds": build_time,
        "run_time_seconds": run_time,
        "episodes": summaries,
        "final_status": report,
    }

    report_dir = Path(r"C:\\cellular_speace\\reports\\environment")
    report_dir.mkdir(parents=True, exist_ok=True)
    out_path = report_dir / f"run_{env_kind}_{int(time.time())}.json"
    out_path.write_text(json.dumps(final, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report written to {out_path}")
    return final


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 else "prediction"
    result = main(kind)
    print("\nFinal orchestrator status:")
    for k, v in result["final_status"].items():
        print(f"  {k}: {v}")
