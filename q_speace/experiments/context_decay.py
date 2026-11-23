"""T229. Develop and freeze the archive, then evaluate in a separate invocation."""

from __future__ import annotations

import argparse
import asyncio
import gzip
import hashlib
import json
import math
import platform
import subprocess
import time
from collections.abc import Iterator
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any

from .context_decay_analysis import summarize
from .context_decay_memory import GRID, Entry, choose, shuffled
from .context_decay_runtime import RUNTIME_PROTOCOL, measure, prepare
from .error_memory_verifier import verify

ROOT = Path(__file__).resolve().parents[2]
FAMILIES = ("rectangle", "triangle")
PERMUTATIONS = tuple(range(22941, 22949))
DEVELOPMENT = 64
EVALUATION = 80
DEV_SEED = 22910000
EVAL_SEED = 22920000


def write(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8"
    )


def read(path: Path) -> Any:
    return json.loads(path.read_bytes())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    paths = [
        *sorted((ROOT / "q_speace/experiments").glob("context_decay*.py")),
        *(
            ROOT / name
            for name in (
                "docs/T229_CONTEXT_DECAY_SPEC.md",
                "q_speace/experiments/error_memory.py",
                "q_speace/experiments/error_memory_verifier.py",
                "q_speace/spiking/plasticity.py",
                "q_speace/spiking_brain/cortex.py",
                "q_speace/spiking_brain/types.py",
                "q_speace/spiking_brain/memory.py",
                "q_speace/edd_cvt/ilf.py",
                "q_speace/metabolism/cognitive_cost_model.py",
            )
        ),
    ]
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}


def episodes(count: int, start_seed: int) -> Iterator[tuple[int, str, int]]:
    for index in range(count):
        yield index, FAMILIES[index % len(FAMILIES)], start_seed + index


def audit_development(archive: tuple[Entry, ...]) -> dict[str, Any]:
    """Compare the global column minimum against two prespecified sensor strata."""
    if not archive:
        raise ValueError("archive must be non-empty")
    groups: dict[str, dict[str, Any]] = {}
    for name, rows in (
        ("all", archive),
        ("low_sd", tuple(e for e in archive if e.context <= 0.08 / 0.25)),
        ("high_sd", tuple(e for e in archive if e.context > 0.08 / 0.25)),
    ):
        if rows:
            means = [math.fsum(e.losses[j] for e in rows) / len(rows) for j in range(len(GRID))]
            groups[name] = {"n": len(rows), "means": means, "winner": GRID[means.index(min(means))]}
    subgroups = [g for k, g in groups.items() if k != "all"]
    global_loss = min(groups["all"]["means"])
    separate_loss = math.fsum(min(g["means"]) * g["n"] for g in subgroups) / len(archive)
    return {
        "groups": groups,
        "grid": GRID,
        "global_excess_loss": global_loss - separate_loss,
        "open_evaluation": len({g["winner"] for g in subgroups}) == 2,
    }


def sealed_inputs(directory: Path) -> dict[str, Any]:
    seal: dict[str, Any] = read(directory / "freeze.json")
    for name, expected in seal["files_sha256"].items():
        if sha(directory / name) != expected:
            raise ValueError(f"Input changed since freeze: {name}")
    if source_hashes() != seal["source_sha256"]:
        raise ValueError("Experiment code or specification changed since freeze")
    return seal


async def develop(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=False)
    certificates = [asdict(verify(d)) for d in GRID]
    if any(c["status"] != "VALIDA" for c in certificates):
        raise ValueError("Grid contains a decay outside the verified domain")
    config = {
        "grid": GRID,
        "certificates": certificates,
        "families": FAMILIES,
        "n_development": DEVELOPMENT,
        "n_evaluation": EVALUATION,
        "development_seed_base": DEV_SEED,
        "evaluation_seed_base": EVAL_SEED,
        "episode_seeds": "base + index; alternate families in listed order",
        "permutation_seeds": PERMUTATIONS,
        "bootstrap_seed": 22977,
        "bootstrap_reps": 4000,
        "neighbors": 7,
        "distance": "absolute difference of prefix population SD / 0.25",
        "ties": "development row index for neighbors, grid order for coefficients",
        "metric": "sum(TV(q_star, stationary latent reference)) over 48 ticks",
        "primary": ["B_minus_C", "Dmean_minus_C"],
        "runtime": RUNTIME_PROTOCOL,
    }
    write(directory / "config.json", config)
    started = time.perf_counter()
    archive = []
    dev_rows = []
    for index, family, seed in episodes(DEVELOPMENT, DEV_SEED):
        state = await prepare(seed, family)
        outcomes = [await measure(state, d) for d in GRID]
        archive.append(Entry(index, state.context, tuple(r["loss"] for r in outcomes)))
        dev_rows.append(
            {
                "index": index,
                "family": family,
                "seed": seed,
                "description": state.description,
                "snapshot_id": state.snapshot_id,
                "context": state.context,
                "outcomes": [
                    dict(
                        decay=d,
                        **{
                            k: r[k]
                            for k in ("loss", "prefix_loss", "perturbation_loss", "return_loss")
                        },
                    )
                    for d, r in zip(GRID, outcomes, strict=True)
                ],
            }
        )
    write(directory / "archive.json", [asdict(e) for e in archive])
    write(directory / "development.json", dev_rows)
    gate = audit_development(tuple(archive))
    write(directory / "development_gate.json", gate)
    elapsed = time.perf_counter() - started
    files = ("config.json", "archive.json", "development.json", "development_gate.json")

    def git(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).rstrip()

    write(
        directory / "freeze.json",
        {
            "created_utc": datetime.now(UTC).isoformat(),
            "files_sha256": {n: sha(directory / n) for n in files},
            "source_sha256": source_hashes(),
            "commit": git("rev-parse", "HEAD"),
            "dirty_status": git("-c", "core.quotepath=false", "status", "--short"),
            "environment": {
                "python": platform.python_version(),
                "numpy": version("numpy"),
                "system": platform.platform(),
                "backend": "synthetic CPU",
            },
            "offline_build_s": elapsed,
            "offline_rollouts": len(archive) * len(GRID),
            "offline_cortex_ticks": DEVELOPMENT * (8 + len(GRID) * 40),
            "open_evaluation": gate["open_evaluation"],
        },
    )
    print(json.dumps(gate, indent=2))


async def evaluate(directory: Path) -> None:
    seal = sealed_inputs(directory)
    if not seal["open_evaluation"]:
        raise ValueError("Development gate closed")
    archive = tuple(
        Entry(e["index"], e["context"], tuple(e["losses"]))
        for e in read(directory / "archive.json")
    )
    tasks = [(label, None, archive if label != "A" else ()) for label in ("A", "B", "C")]
    perm_start = time.perf_counter()
    arms = [*tasks, *(("D", p, shuffled(archive, p)) for p in PERMUTATIONS)]
    perm_s = time.perf_counter() - perm_start
    out = directory / "evaluation"
    out.mkdir(exist_ok=False)
    write(
        out / "opened.json",
        {"utc": datetime.now(UTC).isoformat(), "freeze_sha256": sha(directory / "freeze.json")},
    )
    rows: list[dict[str, Any]] = []
    with (
        (out / "episodes.jsonl").open("w", encoding="utf-8") as logs,
        gzip.open(out / "trajectories.jsonl.gz", "wt", encoding="utf-8") as trajectories,
    ):
        for idx, family, seed in episodes(EVALUATION, EVAL_SEED):
            state = await prepare(seed, family)
            decisions: list[dict[str, Any]] = []
            # Finish every choice before any post-decision tick is simulated.
            for label, permutation, table in arms:
                started = time.perf_counter_ns()
                selection = choose(label, state.context, table)
                lookup = time.perf_counter_ns() - started
                decisions.append(
                    {
                        **selection,
                        "condition": label,
                        "permutation_seed": permutation,
                        "lookup_ns": lookup,
                    }
                )
            stored: dict[float, list[dict[str, Any]]] = {}
            for decision in decisions:
                d = decision["decay"]
                outcome = await measure(state, d)
                ticks = outcome.pop("ticks")
                key = f"{idx}/{d}"
                # All replicas execute; identical full trajectories share one disk record.
                if d not in stored:
                    trajectories.write(
                        json.dumps({"key": key, "ticks": ticks}, allow_nan=False) + "\n"
                    )
                    stored[d] = ticks
                elif ticks != stored[d]:
                    raise RuntimeError("Paired clone diverged at fixed decay")
                decision.update(outcome, trajectory=key)
            row = {
                "id": idx,
                "family": family,
                "seed": seed,
                "description": state.description,
                "snapshot_id": state.snapshot_id,
                "context": state.context,
                "decisions": decisions,
            }
            logs.write(json.dumps(row, allow_nan=False) + "\n")
            rows.append(row)
    sealed_inputs(directory)
    write(out / "summary.json", summarize(rows))
    write(
        out / "completion.json",
        {
            "episodes": len(rows),
            "decisions": sum(len(r["decisions"]) for r in rows),
            "permutation_setup_s": perm_s,
            "files_sha256": {
                n: sha(out / n) for n in ("episodes.jsonl", "trajectories.jsonl.gz", "summary.json")
            },
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("develop", "evaluate"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run((develop if args.phase == "develop" else evaluate)(args.output))


if __name__ == "__main__":
    main()
