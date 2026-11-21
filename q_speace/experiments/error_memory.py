"""T228 opt-in synthetic backend, real cortex tick, frozen error-memory bench.

Run: python -m q_speace.experiments.error_memory --output NEW_DIRECTORY
No network, ordinary configuration changes, real quantum backend or actuation.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import math
import platform
import random
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from q_speace.spiking.encoder import SpikeEncodingResult
from q_speace.spiking.plasticity import SpikePlasticity
from q_speace.spiking_brain.cortex import SpikingBrainCortex
from q_speace.spiking_brain.types import ThinkResult

from .error_memory_verifier import RULE_VERSION, Witness, replay, verify


@dataclass(frozen=True)
class BenchConfig:
    experience_seed: int = 22801
    proposal_seed: int = 22802
    perturbation_seed: int = 22803
    episodes_per_family: int = 24
    experience_count: int = 8
    raw_budget: int = 2
    horizon: int = 32
    pulse_transition: int = 12
    band_tv: float = 0.01
    consecutive: int = 3
    default_decay: float = 0.9
    snapshot: tuple[float, float] = (1.0, 1.0)
    belief: tuple[float, float] = (0.9, 0.1)
    rule_version: str = RULE_VERSION
    retrieval: str = "first-frozen-witness-geometric-repair-v1"


@dataclass(frozen=True)
class ErrorEntry:
    entry_id: str
    rule_version: str
    decay: float
    witness: Witness
    replayed: dict[str, float | bool]
    corrected: float
    corrected_verdict: str


DEFAULT_CONFIG = BenchConfig()


def repair(decay: float, witness: Witness) -> float:
    """Use a concrete error to halve update gain; never query the verifier."""
    for _ in range(60):
        result = decay * witness.state + (1 - decay) * witness.rate
        if abs(result - witness.state) <= 0.25:
            return decay
        decay = 1 - (1 - decay) / 2
    return decay


def experience(config: BenchConfig = DEFAULT_CONFIG) -> tuple[ErrorEntry, ...]:
    rng = random.Random(config.experience_seed)
    entries: list[ErrorEntry] = []
    for index in range(config.experience_count):
        decay = rng.uniform(0.25, 0.7)
        verdict = verify(decay)
        assert verdict.status == "INVALIDA" and verdict.witness is not None
        observed = replay(decay, verdict.witness)
        if not observed["violated"] or observed["model_gap"] > 8 * np.finfo(float).eps:
            raise RuntimeError("Counterexample does not reproduce in runtime")
        corrected = repair(decay, verdict.witness)
        corrected_verdict = verify(corrected)
        assert corrected_verdict.status == "VALIDA"
        entries.append(
            ErrorEntry(
                f"experience-{index}",
                RULE_VERSION,
                decay,
                verdict.witness,
                observed,
                corrected,
                corrected_verdict.status,
            )
        )
    return tuple(entries)


def search(seed: int, memory: tuple[ErrorEntry, ...], budget: int) -> dict[str, Any]:
    rng = random.Random(seed)
    feedback: Witness | None = None
    traces: list[dict[str, Any]] = []
    started = time.perf_counter()
    selected: float | None = None
    raw = 0.9
    for index in range(budget):
        # A second raw proposal is a feedback repair; it is still counted.
        raw = rng.uniform(0.25, 0.99) if feedback is None else repair(raw, feedback)
        retrieved = memory[0] if memory else None
        sent = repair(raw, retrieved.witness) if retrieved else raw
        verify_started = time.perf_counter()
        verdict = verify(sent)
        verify_s = time.perf_counter() - verify_started
        reproduced = replay(sent, verdict.witness) if verdict.witness else None
        traces.append(
            {
                "index": index,
                "raw": raw,
                "sent": sent,
                "retrieved": retrieved.entry_id if retrieved else None,
                "retrieved_witness": asdict(retrieved.witness) if retrieved else None,
                "verdict": asdict(verdict),
                "replay": reproduced,
                "verify_s": verify_s,
            }
        )
        if verdict.status == "VALIDA":
            selected = sent
            break
        feedback = verdict.witness
    return {
        "selected": selected,
        "first_valid": bool(traces and traces[0]["verdict"]["status"] == "VALIDA"),
        "raw_count": len(traces),
        "verifier_calls": len(traces),
        "search_s": time.perf_counter() - started,
        "exhausted": selected is None,
        "traces": traces,
    }


class SyntheticBackend:
    """Experimental current-input adapter; production plasticity implementation."""

    backend_name = "t228-synthetic-no-language-model"

    def __init__(self, decay: float, config: BenchConfig) -> None:
        self.kernel = SpikePlasticity(2, decay=decay)
        self.kernel._ema = np.asarray(config.snapshot, dtype=np.float64).copy()
        self.rates = np.ones(2)
        self.belief = np.asarray(config.belief)

    def think(
        self,
        prompt: str,
        coherence_phi: float = 1.0,
        n_tokens: int = 32,
        history: Any = None,
    ) -> ThinkResult:
        self.kernel.update(self.rates)
        spikes = SpikeEncodingResult(
            self.rates.copy(),
            np.ones(2),
            int(np.count_nonzero(self.rates)),
            float(np.mean(self.rates == 0)),
            float(np.mean(self.rates)),
        )
        return ThinkResult(
            text="synthetic bounded activity",
            confidence=1.0,
            belief=self.belief.copy(),
            spikes=spikes,
            plasticity=self.kernel.coefficients(),
        )


def reference_q(rates: np.ndarray, config: BenchConfig) -> np.ndarray:
    """Existing apply consumer at stationary coefficients, no rollout fitting."""
    backend = SyntheticBackend(config.default_decay, config)
    backend.kernel._ema = rates.copy()
    cortex = SpikingBrainCortex(backend=backend)
    backend.rates = rates.copy()
    backend.kernel._ema = rates.copy()
    result = backend.think("reference")
    cortex.apply_to_ilf(result)
    return cortex.ilf.q_star.copy()


async def rollout(decay: float, family: str, seed: int, config: BenchConfig) -> dict[str, Any]:
    rng = random.Random(seed)
    level = 0.0 if family == "experience" else rng.uniform(0.0, 0.18)
    rates = np.array([1.0, level]) if rng.random() < 0.5 else np.array([level, 1.0])
    backend = SyntheticBackend(decay, config)
    cortex = SpikingBrainCortex(backend=backend)
    transition = config.pulse_transition if family == "pulse" else 0
    ticks: list[dict[str, Any]] = []
    streak = 0
    recovery: int | None = None
    for tick in range(config.horizon):
        current = np.ones(2) if family == "pulse" and tick >= transition else rates
        backend.rates = current.copy()
        report = await cortex.tick("T228 synthetic perturbation", n_tokens=0)
        target = reference_q(current, config)
        tv = float(np.abs(cortex.ilf.q_star - target).sum() / 2)
        ticks.append(
            {
                "tick": tick,
                "input": current.tolist(),
                "ema": backend.kernel._ema.tolist(),
                "q_star": cortex.ilf.q_star.tolist(),
                "target": target.tolist(),
                "tv": tv,
                "approved": report.approved,
                "reason": report.reason,
            }
        )
        if tick >= transition:
            streak = streak + 1 if tv <= config.band_tv else 0
            if recovery is None and streak >= config.consecutive:
                recovery = tick - transition + 1
    available = config.horizon - transition
    return {
        "recovered": recovery is not None,
        "recovery_ticks": recovery,
        "censored_ticks": recovery if recovery is not None else available + 1,
        "final_tv": ticks[-1]["tv"],
        "ticks": ticks,
    }


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical(value) + b"\n")


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = (
        "first_valid",
        "raw_count",
        "verifier_calls",
        "search_s",
        "exhausted",
        "recovered",
        "censored_ticks",
        "final_tv",
        "rollout_s",
    )
    result: dict[str, Any] = {}
    for family in ("all", "step", "pulse", "new_candidates"):
        subset = [
            r
            for r in rows
            if r["condition"] in ("A", "B")
            and (
                family == "all"
                or r["family"] == family
                or (family == "new_candidates" and r["new_candidate"])
            )
        ]
        pairs: dict[str, dict[str, Any]] = {}
        for row in subset:
            pairs.setdefault(row["episode"], {})[row["condition"]] = row
        paired = [p for p in pairs.values() if "A" in p and "B" in p]
        stats: dict[str, Any] = {"n_independent_pairs": len(paired)}
        for metric in metrics:
            av = [float(p["A"][metric]) for p in paired]
            bv = [float(p["B"][metric]) for p in paired]
            stats[metric] = {
                "A": float(np.mean(av)) if av else None,
                "B": float(np.mean(bv)) if bv else None,
                "B_minus_A": float(np.mean(np.subtract(bv, av))) if av else None,
            }
        stats["worse_recovery_episodes"] = [
            p["A"]["episode"] for p in paired if p["B"]["censored_ticks"] > p["A"]["censored_ticks"]
        ]
        result[family] = stats
    return result


async def run(output: Path, config: BenchConfig = DEFAULT_CONFIG) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[2]

    def git(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=root, text=True).strip()

    memory = experience(config)
    write_json(
        output / "experience_rollouts.json",
        [
            {
                "entry_id": entry.entry_id,
                **await rollout(
                    entry.corrected, "experience", config.experience_seed + index, config
                ),
            }
            for index, entry in enumerate(memory)
        ],
    )
    frozen = [asdict(e) for e in memory]
    config_data = asdict(config) | {
        "split": {"experience": "step-extremes", "evaluation": ["step", "pulse"]},
        "domain": "2 units, state and abs(input) in [0,1]",
        "metric": "TV(ILF q_star, stationary current-input q_star)",
        "raw_proposal_range": [0.25, 0.99],
        "step_limit": 0.25,
    }
    write_json(output / "config.json", config_data)
    write_json(output / "frozen_memory.json", frozen)
    sources = [
        Path(__file__),
        Path(__file__).with_name("error_memory_verifier.py"),
        root / "q_speace/spiking/plasticity.py",
        root / "q_speace/spiking_brain/cortex.py",
        root / "q_speace/edd_cvt/ilf.py",
        root / "q_speace/spiking_brain/types.py",
        root / "docs/T228_ERROR_MEMORY_PLASTICITY_SPEC.md",
    ]
    manifest = {
        "commit": git("rev-parse", "HEAD"),
        "dirty_status": git("status", "--porcelain=v1"),
        "python": sys.version,
        "platform": platform.platform(),
        "packages": {n: importlib.metadata.version(n) for n in ("numpy", "pydantic", "pytest")},
        "config_sha256": digest(config_data),
        "memory_sha256": digest(frozen),
        "sources_sha256": {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources
        },
        "evaluation_started": False,
        "energy": "not measured",
        "gpu_cuda_model": "not used",
        "data": "generated synthetic, no reserved task data",
    }
    # These bytes are persisted before any evaluation rollout/search.
    write_json(output / "preregistration.json", manifest)
    boundary = [0.875, 0.5, 0.75, math.nextafter(0.75, 0), math.nextafter(0.75, 1)]
    write_json(
        output / "verification_checks.json",
        [
            {
                "decay": d,
                "verdict": asdict(verify(d)),
                "replay": replay(d, v.witness) if (v := verify(d)).witness else None,
            }
            for d in boundary
        ],
    )
    rows: list[dict[str, Any]] = []
    experience_candidates = {e.decay for e in memory} | {e.corrected for e in memory}
    with (output / "episodes.jsonl").open("w", encoding="utf-8") as stream:
        for family_index, family in enumerate(("step", "pulse")):
            for index in range(config.episodes_per_family):
                proposal_seed = config.proposal_seed + family_index * 1000 + index
                perturb_seed = config.perturbation_seed + family_index * 1000 + index
                for condition in ("A", "B", "default", "near_frozen"):
                    if condition in ("A", "B"):
                        found = search(
                            proposal_seed, memory if condition == "B" else (), config.raw_budget
                        )
                        decay = (
                            found["selected"]
                            if found["selected"] is not None
                            else config.default_decay
                        )
                    else:
                        decay = (
                            config.default_decay
                            if condition == "default"
                            else math.nextafter(1.0, 0.0)
                        )
                        found = {
                            "traces": [],
                            "selected": decay,
                            "first_valid": True,
                            "raw_count": 0,
                            "verifier_calls": 0,
                            "search_s": 0.0,
                            "exhausted": False,
                        }
                    started = time.perf_counter()
                    outcome = await rollout(decay, family, perturb_seed, config)
                    row = {
                        "episode": f"{family}-{index}",
                        "family": family,
                        "condition": condition,
                        "proposal_seed": proposal_seed,
                        "perturbation_seed": perturb_seed,
                        "snapshot": list(config.snapshot),
                        "decay": decay,
                        "rollout_s": time.perf_counter() - started,
                        "new_candidate": all(
                            t["raw"] not in experience_candidates
                            and t["sent"] not in experience_candidates
                            for t in found["traces"]
                        ),
                        **found,
                        **outcome,
                    }
                    stream.write(json.dumps(row, allow_nan=False) + "\n")
                    rows.append(row)
    if digest([asdict(e) for e in memory]) != manifest["memory_sha256"]:
        raise RuntimeError("Evaluation mutated memory")
    summary = aggregate(rows)
    summary["controls"] = {
        name: {
            family: {
                "n": len(
                    group := [r for r in rows if r["condition"] == name and r["family"] == family]
                ),
                "recovered_rate": float(np.mean([r["recovered"] for r in group])),
                "censored_ticks": float(np.mean([r["censored_ticks"] for r in group])),
            }
            for family in ("step", "pulse")
        }
        for name in ("default", "near_frozen")
    }
    write_json(output / "summary.json", summary)
    write_json(
        output / "completion.json",
        {
            "config_sha256": digest(config_data),
            "memory_sha256": digest(frozen),
            "episode_rows": len(rows),
            "completed": True,
            "results_sha256": hashlib.sha256((output / "episodes.jsonl").read_bytes()).hexdigest(),
        },
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = asyncio.run(run(args.output))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
