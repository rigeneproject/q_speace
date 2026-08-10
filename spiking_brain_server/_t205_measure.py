"""T205-C measurement harness — 64 prompt × Qwen2.5-3B-Instruct NF4.

Per-prompt:
  - reset torch.cuda memory stats
  - log n_tokens_in
  - background thread samples power.draw at ~100ms via nvidia-smi
  - POST /think to sidecar with coherence_phi, n_tokens
  - log n_tokens_out, wall_clock, max_memory_allocated, confidence, belief_entropy
  - E_prompt_J = sum((P_i - P_idle) * dt)
  - E_per_token_J = E_prompt_J / n_tokens_out
  - cost_predicted_J = QuantumCostModel.energy_watts(op) * wall_clock_s

Baseline P_idle is sampled once before the 64 prompts (15s).

Output:
  - docs/T205C_measurements.csv  (one row per prompt + header)
  - docs/T205C_plots/<4 plots>.png  (if matplotlib available)

Usage:
    cd spiking_brain_server
    bash _t205_run.sh         # wraps python invocation in WSL2

Designed to run from WSL2 (CUDA + nvidia-smi access). Pure-Python
dependencies only: httpx (for /think), numpy (already in Q-SPEACE).
matplotlib is optional; plots are skipped silently if not installed.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import statistics
import subprocess
import sys
import threading
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import httpx
import numpy as np

# Append Q-SPEACE package root (parent of spiking_brain_server) so we can
# import the cognitive cost model + QuantumOperation directly.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from q_speace.metabolism.cognitive_cost_model import QuantumCostModel, QuantumOperation  # noqa: E402


SIDE = "http://127.0.0.1:8002"
PROMPTS_PATH = REPO_ROOT / "docs" / "T205C_prompts.txt"
CSV_PATH = REPO_ROOT / "docs" / "T205C_measurements.csv"
PLOTS_DIR = REPO_ROOT / "docs" / "T205C_plots"

SAMPLE_PERIOD_S = 0.1      # 100ms — matches protocol in T205_status.md
BASELINE_DURATION_S = 15.0  # protocol says 15s, adjust via flag below
N_PROMPTS = 64


@dataclass
class PowerSample:
    t_s: float
    p_w: float
    mem_mb: float  # nvidia-smi memory.used (GiB → MiB)


class PowerSampler:
    """Background thread sampling nvidia-smi power.draw + memory.used at ~100ms.

    Driver v550 dropped ``-lms``; we shell out per sample. The fork+exec
    overhead is ~10-20 ms, comparable to the requested 100 ms period —
    acceptable for this characterization.

    Because the sidecar runs in a separate process (and possibly WSL2
    distribution), we cannot rely on ``torch.cuda.max_memory_allocated()``
    from the orchestrator side; instead we sample the global GPU memory
    counter that the driver exposes.
    """

    def __init__(self) -> None:
        self._samples: list[PowerSample] = []
        self._stop = threading.Event()
        self._t0: float = 0.0
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self) -> None:
        self._t0 = time.monotonic()
        self._samples = []
        self._stop.clear()
        self._thread.start()

    def stop(self) -> list[PowerSample]:
        self._stop.set()
        self._thread.join(timeout=2.0)
        return list(self._samples)

    def _loop(self) -> None:
        while not self._stop.is_set():
            t = time.monotonic() - self._t0
            try:
                out = subprocess.check_output(
                    ["nvidia-smi",
                     "--query-gpu=power.draw,memory.used",
                     "--format=csv,noheader,nounits"],
                    stderr=subprocess.DEVNULL,
                    timeout=2.0,
                ).decode().strip()
                # CSV "power_w, mem_mib"
                parts = [x.strip() for x in out.split(",")]
                p = float(parts[0])
                mem = float(parts[1])
            except Exception:
                p = float("nan")
                mem = float("nan")
            self._samples.append(PowerSample(t_s=t, p_w=p, mem_mb=mem))
            self._stop.wait(SAMPLE_PERIOD_S)


def measure_idle_power(duration_s: float = BASELINE_DURATION_S) -> float:
    """Sample power for ``duration_s`` with model loaded, no generation."""
    sampler = PowerSampler()
    sampler.start()
    time.sleep(duration_s)
    samples = sampler.stop()
    valid = [s.p_w for s in samples if not math.isnan(s.p_w)]
    if not valid:
        raise RuntimeError("no valid idle power samples")
    return statistics.fmean(valid)


def energy_useful_j(samples: list[PowerSample], p_idle_w: float) -> tuple[float, float, float, list[float]]:
    """Compute useful energy from samples via trapezoidal integration of (P - P_idle).

    Returns (E_J, mean_W, peak_W, delta_W_series).
    """
    if len(samples) < 2:
        return 0.0, 0.0, 0.0, []
    deltas: list[float] = []
    e_j = 0.0
    for a, b in zip(samples, samples[1:]):
        dt = b.t_s - a.t_s
        if dt <= 0:
            continue
        p_avg = 0.5 * (a.p_w + b.p_w)
        d = max(p_avg - p_idle_w, 0.0)
        deltas.append(d)
        e_j += d * dt
    if not deltas:
        return 0.0, 0.0, 0.0, []
    return e_j, statistics.fmean(deltas), max(deltas), deltas


def belief_entropy(belief: list[float]) -> float:
    arr = np.asarray(belief, dtype=float)
    arr = arr / max(arr.sum(), 1e-12)
    arr = np.clip(arr, 1e-12, 1.0)
    return float(-(arr * np.log(arr)).sum())


def load_prompts() -> list[str]:
    if not PROMPTS_PATH.exists():
        # generate a default 64-prompt battery — 4 categories × 16 prompts,
        # covers short factual, longer reasoning, italian + english, math.
        return _default_prompts()
    with PROMPTS_PATH.open(encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()][:N_PROMPTS]


def _default_prompts() -> list[str]:
    cats = {
        "factual_short_it": [
            "Rispondi in italiano: cos'è la costante di Planck?",
            "Rispondi in italiano: chi ha scritto la Divina Commedia?",
            "Rispondi in italiano: qual è la capitale del Giappone?",
            "Rispondi in italiano: cos'è un neurone specchio?",
            "Rispondi in italiano: cosa significa 'entanglement'?",
            "Rispondi in italiano: chi è Alan Turing?",
            "Rispondi in italiano: cos'è il CERN?",
            "Rispondi in italiano: qual è la moneta del Regno Unito?",
            "Rispondi in italiano: cos'è la schiuma quantistica?",
            "Rispondi in italiano: chi ha dipinto la Gioconda?",
            "Rispondi in italiano: cos'è un buco nero?",
            "Rispondi in italiano: chi era Marie Curie?",
            "Rispondi in italiano: cos'è la relatività generale?",
            "Rispondi in italiano: chi ha fondato Apple?",
            "Rispondi in italiano: cos'è il bosone di Higgs?",
            "Rispondi in italiano: chi era Leonardo da Vinci?",
        ],
        "reasoning_short_en": [
            "Answer briefly: if a>b and b>c, what is a>c?",
            "Answer briefly: which is larger, 7/9 or 8/11?",
            "Answer briefly: 5 + 3 * 2 = ?",
            "Answer briefly: what comes next: 2, 4, 8, 16, ?",
            "Answer briefly: how many sides does a hexagon have?",
            "Answer briefly: is the square root of 2 rational?",
            "Answer briefly: what is 12 squared?",
            "Answer briefly: what is the next prime after 7?",
            "Answer briefly: how many degrees in a right angle?",
            "Answer briefly: what is 100 divided by 4?",
            "Answer briefly: which is bigger, a kilometer or a mile?",
            "Answer briefly: how many seconds in an hour?",
            "Answer briefly: what is 0.5 + 0.25?",
            "Answer briefly: is 17 prime?",
            "Answer briefly: how many bits in a byte?",
            "Answer briefly: what is the cube root of 27?",
        ],
        "reasoning_long_it": [
            "Rispondi in italiano in due frasi: perché il ghiaccio galleggia sull'acqua?",
            "Rispondi in italiano in due frasi: cos'è la selezione naturale?",
            "Rispondi in italiano in due frasi: come funziona un vaccino?",
            "Rispondi in italiano in due frasi: perché il cielo è blu?",
            "Rispondi in italiano in due frasi: cos'è l'effetto serra?",
            "Rispondi in italiano in due frasi: come funziona una cellula a combustibile?",
            "Rispondi in italiano in due frasi: cos'è la crittografia asimmetrica?",
            "Rispondi in italiano in due frasi: come funziona un transistor?",
            "Rispondi in italiano in due frasi: cos'è un buco nero supermassiccio?",
            "Rispondi in italiano in due frasi: come si forma un arcobaleno?",
            "Rispondi in italiano in due frasi: cos'è il DNA?",
            "Rispondi in italiano in due frasi: cos'è la meccanica quantistica?",
            "Rispondi in italiano in due frasi: cos'è il deep learning?",
            "Rispondi in italiano in due frasi: come funziona un motore a scoppio?",
            "Rispondi in italiano in due frasi: cos'è il teorema di Pitagora?",
            "Rispondi in italiano in due frasi: come funziona la fotosintesi?",
        ],
        "explain_short_en": [
            "In one sentence: what is a derivative?",
            "In one sentence: what is TCP/IP?",
            "In one sentence: what is JSON?",
            "In one sentence: what is Big-O notation?",
            "In one sentence: what is a hash function?",
            "In one sentence: what is a semaphore?",
            "In one sentence: what is a neural network?",
            "In one sentence: what is a kernel in OS?",
            "In one sentence: what is polymorphism?",
            "In one sentence: what is a REST API?",
            "In one sentence: what is SQL?",
            "In one sentence: what is a linked list?",
            "In one sentence: what is quicksort?",
            "In one sentence: what is a public key?",
            "In one sentence: what is GPU computing?",
            "In one sentence: what is vector embedding?",
        ],
    }
    out: list[str] = []
    for cat in cats.values():
        out.extend(cat)
    return out[:N_PROMPTS]


def think(prompt: str, n_tokens: int, coherence: float, timeout_s: float = 60.0) -> dict:
    with httpx.Client(timeout=timeout_s) as cli:
        r = cli.post(
            f"{SIDE}/think",
            json={
                "prompt": prompt,
                "coherence_phi": coherence,
                "n_tokens": n_tokens,
                "history": None,
            },
        )
        r.raise_for_status()
        return r.json()


def reset_cuda_stats() -> None:
    try:
        import torch  # noqa: F401
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.empty_cache()
    except Exception:
        pass


def max_memory_mb() -> float:
    try:
        import torch
        if torch.cuda.is_available():
            return float(torch.cuda.max_memory_allocated()) / (1024 ** 2)
    except Exception:
        pass
    return float("nan")


@dataclass
class Row:
    fields: dict


def run(p_idle_w: float, coherence: float = 1.0, n_tokens: int = 96) -> list[dict]:
    cost = QuantumCostModel()
    prompts = load_prompts()
    if len(prompts) < N_PROMPTS:
        # pad with first N by cycling — keeps the schedule length deterministic
        prompts = (prompts * (N_PROMPTS // len(prompts) + 1))[:N_PROMPTS]
    rows: list[dict] = []
    print(f"[T205-C] P_idle = {p_idle_w:.2f} W", flush=True)
    print(f"[T205-C] running {len(prompts)} prompts, coherence={coherence}, n_tokens_max={n_tokens}", flush=True)
    for idx, prompt in enumerate(prompts):
        reset_cuda_stats()
        sampler = PowerSampler()
        sampler.start()
        t_start = time.monotonic()
        try:
            resp = think(prompt, n_tokens=n_tokens, coherence=coherence)
            err = ""
        except Exception as exc:
            resp = None
            err = f"{type(exc).__name__}: {exc}"
        wall = time.monotonic() - t_start
        samples = sampler.stop()
        e_j, mean_useful, peak_useful, deltas = energy_useful_j(samples, p_idle_w)
        # GPU memory seen via nvidia-smi (MiB). The sidecar lives in a
        # separate process so we cannot use torch.cuda here.
        valid_mem = [s.mem_mb for s in samples if not math.isnan(s.mem_mb)]
        max_mem = max(valid_mem) if valid_mem else float("nan")
        if resp is None:
            row = {
                "prompt_idx": idx,
                "prompt_text": prompt[:80],
                "n_tokens_in": "",
                "n_tokens_out": 0,
                "wall_clock_s": f"{wall:.4f}",
                "max_memory_allocated_MB": f"{max_mem:.1f}",
                "P_idle_W": f"{p_idle_w:.2f}",
                "P_mean_W_useful": "",
                "P_peak_W_useful": "",
                "E_prompt_J": f"{e_j:.4f}",
                "E_per_token_J": "",
                "cost_predicted_W": "",
                "cost_predicted_J": "",
                "confidence": "",
                "belief_entropy": "",
                "ratio_pred_over_measured": "",
                "text_first_80_chars": "",
                "error": err,
            }
        else:
            n_out = int(resp.get("n_tokens", 0))
            conf = float(resp.get("confidence", 0.0))
            belief = resp.get("belief", [])
            ent = belief_entropy(belief)
            text = str(resp.get("text", ""))
            md = resp.get("metadata", {}) or {}
            try:
                n_in = int(md.get("n_tokens_in", 0))
            except Exception:
                n_in = 0
            op = QuantumOperation(
                num_qubits=4,
                num_gates=max(n_out * 3, 1),
                entanglement_depth=2,
                decoherence_budget=max(1.0 - conf, 0.0),
            )
            pred_w = float(cost.energy_watts(op))
            pred_j = pred_w * wall
            ratio = pred_j / e_j if e_j > 1e-6 else float("nan")
            row = {
                "prompt_idx": idx,
                "prompt_text": prompt[:80],
                "n_tokens_in": n_in,
                "n_tokens_out": n_out,
                "wall_clock_s": f"{wall:.4f}",
                "max_memory_allocated_MB": f"{max_mem:.1f}",
                "P_idle_W": f"{p_idle_w:.2f}",
                "P_mean_W_useful": f"{mean_useful:.2f}",
                "P_peak_W_useful": f"{peak_useful:.2f}",
                "E_prompt_J": f"{e_j:.4f}",
                "E_per_token_J": f"{(e_j / max(n_out, 1)):.6f}",
                "cost_predicted_W": f"{pred_w:.6f}",
                "cost_predicted_J": f"{pred_j:.6f}",
                "confidence": f"{conf:.4f}",
                "belief_entropy": f"{ent:.4f}",
                "ratio_pred_over_measured": f"{ratio:.4f}",
                "text_first_80_chars": text.replace("\n", " ")[:80],
                "error": "",
            }
        rows.append(row)
        if (idx + 1) % 8 == 0:
            print(
                f"  [{idx+1:2d}/{len(prompts)}] "
                f"n_out={row['n_tokens_out']:3d} "
                f"wall={row['wall_clock_s']}s "
                f"E={row['E_prompt_J']}J "
                f"pred/meas={row.get('ratio_pred_over_measured','-')} "
                f"text={row['text_first_80_chars'][:30]!r}",
                flush=True,
            )
    return rows


def write_csv(rows: list[dict]) -> None:
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    keys = list(rows[0].keys()) if rows else []
    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"[T205-C] wrote {len(rows)} rows → {CSV_PATH}", flush=True)


def plot(rows: list[dict]) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        print("[T205-C] matplotlib not available; skipping plots", flush=True)
        return
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    valid = [r for r in rows if r["error"] == "" and float(r["E_prompt_J"]) > 1e-6]
    if not valid:
        print("[T205-C] no valid rows for plotting", flush=True)
        return

    e_meas = np.array([float(r["E_prompt_J"]) for r in valid])
    e_pred = np.array([float(r["cost_predicted_J"]) for r in valid])
    e_per_tok = np.array([float(r["E_per_token_J"]) for r in valid])
    n_out = np.array([float(r["n_tokens_out"]) for r in valid], dtype=float)
    conf = np.array([float(r["confidence"]) for r in valid])
    max_mem = np.array([float(r["max_memory_allocated_MB"]) for r in valid])
    p_useful = np.array([float(r["P_mean_W_useful"]) for r in valid])
    n_in = np.array([float(r.get("n_tokens_in") or 0) for r in valid])

    # Plot 1: cost_predicted vs cost_measured (log-log)
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(e_meas, e_pred, s=20, alpha=0.6)
    lo = float(min(e_meas.min(), e_pred.min())) * 0.5
    hi = float(max(e_meas.max(), e_pred.max())) * 1.5
    ax.plot([lo, hi], [lo, hi], "k--", lw=0.8, label="y = x (slope 1)")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("E_measured (J)"); ax.set_ylabel("E_predicted (J)")
    ax.set_title("T205-C: QuantumCostModel energy prediction vs physical")
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "cost_pred_vs_measured.png", dpi=110)
    plt.close(fig)

    # Plot 2: E_per_token vs n_tokens_out
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(n_out, e_per_tok * 1000, s=20, alpha=0.6)  # in mJ
    ax.set_xlabel("n_tokens_out"); ax.set_ylabel("E_per_token (mJ)")
    ax.set_title("T205-C: useful energy per output token")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "energy_per_token_vs_tokens_out.png", dpi=110)
    plt.close(fig)

    # Plot 3: useful power mean vs (1 - confidence)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(1.0 - conf, p_useful, s=20, alpha=0.6)
    ax.set_xlabel("1 - confidence"); ax.set_ylabel("P_useful mean (W)")
    ax.set_title("T205-C: useful power vs model uncertainty")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "power_vs_inverse_confidence.png", dpi=110)
    plt.close(fig)

    # Plot 4: max_memory vs n_tokens_out
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(n_out, max_mem, s=20, alpha=0.6)
    ax.set_xlabel("n_tokens_out"); ax.set_ylabel("max_memory_allocated (MiB)")
    ax.set_title("T205-C: VRAM peak vs output length")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "max_memory_vs_tokens_out.png", dpi=110)
    plt.close(fig)
    print(f"[T205-C] plots → {PLOTS_DIR}", flush=True)


def summarize(rows: list[dict]) -> dict:
    valid = [r for r in rows if r["error"] == "" and float(r["E_prompt_J"]) > 1e-6]
    if not valid:
        return {"n_valid": 0}
    e_meas = np.array([float(r["E_prompt_J"]) for r in valid])
    e_pred = np.array([float(r["cost_predicted_J"]) for r in valid])
    n_out = np.array([float(r["n_tokens_out"]) for r in valid])
    # log-log regression slope (numpy polyfit)
    log_m = np.log(e_meas); log_p = np.log(e_pred)
    slope, intercept = np.polyfit(log_m, log_p, 1)
    resid = log_p - (slope * log_m + intercept)
    return {
        "n_valid": len(valid),
        "n_total": len(rows),
        "P_idle_W_mean": float(np.mean([float(r["P_idle_W"]) for r in valid])),
        "E_meas_J_mean": float(e_meas.mean()),
        "E_pred_J_mean": float(e_pred.mean()),
        "slope_log_log_pred_vs_meas": float(slope),
        "intercept_log_log": float(intercept),
        "resid_std": float(resid.std()),
        "E_per_token_mJ_mean": float(np.mean([float(r["E_per_token_J"]) for r in valid]) * 1000),
        "max_mem_MB_mean": float(np.mean([float(r["max_memory_allocated_MB"]) for r in valid])),
        "wall_s_mean": float(np.mean([float(r["wall_clock_s"]) for r in valid])),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="T205-C measurement harness")
    ap.add_argument("--coherence", type=float, default=1.0)
    ap.add_argument("--n-tokens", type=int, default=96)
    ap.add_argument("--skip-idle", action="store_true",
                    help="do not remeasure P_idle; use last row's value")
    ap.add_argument("--baseline-duration", type=float, default=BASELINE_DURATION_S)
    args = ap.parse_args(argv)

    print(f"[T205-C] sidecar={SIDE}, prompts={PROMPTS_PATH}", flush=True)
    if args.skip_idle and CSV_PATH.exists():
        with CSV_PATH.open(encoding="utf-8") as f:
            r = next(csv.DictReader(f))
        p_idle = float(r["P_idle_W"])
        print(f"[T205-C] reusing P_idle={p_idle:.2f} W from existing CSV", flush=True)
    else:
        print(f"[T205-C] measuring P_idle for {args.baseline_duration:.0f}s ...", flush=True)
        p_idle = measure_idle_power(duration_s=args.baseline_duration)
        print(f"[T205-C] P_idle = {p_idle:.2f} W", flush=True)

    rows = run(p_idle_w=p_idle, coherence=args.coherence, n_tokens=args.n_tokens)
    write_csv(rows)
    summary = summarize(rows)
    print("[T205-C] summary:", flush=True)
    for k, v in summary.items():
        print(f"  {k}: {v}", flush=True)
    plot(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())