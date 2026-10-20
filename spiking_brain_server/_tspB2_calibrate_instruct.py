"""T-SPB-2-INSTRUCT-C — calibration harness for the Qwen instruction sidecar.

Verifies that ``confidence`` emitted by ``/think`` is a usable predictor of
response correctness. Compares against the T205-C baseline (Qwen 3B
NF4, slope log-log pred/meas = 0.982 ± 0.086) by reporting:

  - **Brier score** (mean squared error between confidence and outcome)
  - **Expected Calibration Error (ECE)** over 10 equal-width bins
  - **Slope log-log**: not applicable here (no energy measurement), so
    we instead measure the *reliability* slope of the calibration
    diagram (predicted confidence bin → observed accuracy). A well-
    calibrated model has slope ≈ 1.

Test battery (20 prompts, 5 categories × 4):

  1. **factual_recall**    — closed-form QA with one correct answer
  2. **arithmetic**         — small integer arithmetic
  3. **boolean_fact**       — yes/no factual questions
  4. **definition**         — short definitions of common terms
  5. **refusal**            — questions a 3B model legitimately doesn't know

Each prompt is paired with an ``expected`` token string (or a list of
acceptable strings). Outcomes are extracted by simple substring match
(case-insensitive, after stripping punctuation).

**Usage (WSL2)**:

    cd spiking_brain_server
    # 1) sidecar on 8002 must be running
    # 2) harness
    python _tspB2_calibrate_instruct.py --n-tokens 32

**Output**:

  - ``docs/T-SPB-2_INSTRUCT_CALIBRATION.md`` — markdown report
  - ``docs/T-SPB-2_INSTRUCT_CALIBRATION.json`` — raw metrics

**Epistemic note**: this is a *narrow* calibration check on a single
sidecar, not a general claim about Qwen2.5-3B. 20 prompts is small;
a full 200+ run is queued for later.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib import error as urlerror
from urllib import request

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
SIDE = "http://127.0.0.1:8002"
OUT_MD = REPO_ROOT / "docs" / "T-SPB-2_INSTRUCT_CALIBRATION.md"
OUT_JSON = REPO_ROOT / "docs" / "T-SPB-2_INSTRUCT_CALIBRATION.json"

# 20 prompts × 5 categories. Each entry: (prompt, expected_substrings).
# expected_substrings is a list of lowercase substrings; the response is
# counted as correct if at least one substring appears (case-insensitive).
PROMPTS: list[tuple[str, list[str]]] = [
    # factual_recall
    ("What is the capital of France?", ["paris"]),
    ("What is the largest planet in our solar system?", ["jupiter"]),
    ("Who wrote the novel '1984'?", ["orwell"]),
    ("What is the chemical symbol for gold?", ["au"]),
    # arithmetic
    ("What is 7 + 5?", ["12"]),
    ("What is 15 * 3?", ["45"]),
    ("What is 100 / 4?", ["25"]),
    ("What is 11 - 8?", ["3"]),
    # boolean_fact
    ("Is the Earth round? Answer yes or no.", ["yes"]),
    ("Is the sun a planet? Answer yes or no.", ["no"]),
    ("Is water composed of hydrogen and oxygen? Answer yes or no.", ["yes"]),
    ("Is Mount Everest the tallest mountain on Earth? Answer yes or no.", ["yes"]),
    # definition
    ("Define 'photosynthesis' in one sentence.", ["plant", "light", "carbon dioxide"]),
    ("What is a 'neuron'?", ["nerve", "brain", "cell"]),
    ("What is 'gravity'?", ["force", "mass", "attract"]),
    ("Define 'algorithm'.", ["step", "process", "procedure", "instruction"]),
    # refusal (model should say it doesn't know or ask for clarification)
    ("What is coherence_phi in Q-SPEACE?", ["i don't", "i do not", "not", "context", "specify"]),
    ("Explain the Sevo gate threshold formula in Q-SPEACE.", ["i don't", "i do not", "not", "context"]),
    ("What is the q_speace internal model identifier x42?", ["i don't", "i do not", "not", "context"]),
    ("List the cosmic-1 satellite orbital parameters.", ["i don't", "i do not", "not", "context"]),
]


def call_think(prompt: str, n_tokens: int, timeout_s: float = 60.0) -> dict:
    """POST /think and return the JSON body. Raises on transport errors."""
    req = request.Request(
        f"{SIDE}/think",
        data=json.dumps(
            {"prompt": prompt, "n_tokens": n_tokens, "coherence_phi": 1.0}
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def normalise(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[\s,.!?\"'`]+", " ", s)
    return s.strip()


def evaluate_response(text: str, expected: list[str]) -> bool:
    norm = normalise(text)
    for needle in expected:
        if normalise(needle) in norm:
            return True
    return False


def brier(conf: np.ndarray, out: np.ndarray) -> float:
    return float(np.mean((conf - out) ** 2))


def ece(conf: np.ndarray, out: np.ndarray, bins: int = 10) -> float:
    if conf.size == 0:
        return float("nan")
    edges = np.minimum((conf * bins).astype(int), bins - 1)
    e = 0.0
    for b in range(bins):
        m = edges == b
        if m.any():
            e += float(m.mean() * abs(conf[m].mean() - out[m].mean()))
    return e


def reliability_slope(conf: np.ndarray, out: np.ndarray, bins: int = 10) -> tuple[float, float]:
    """OLS slope of observed accuracy on mean predicted confidence per bin.

    A perfectly calibrated model has slope = 1, intercept = 0.
    Returns (slope, intercept).
    """
    if conf.size < 2:
        return float("nan"), float("nan")
    edges = np.minimum((conf * bins).astype(int), bins - 1)
    xs: list[float] = []
    ys: list[float] = []
    for b in range(bins):
        m = edges == b
        if m.sum() >= 2:
            xs.append(float(conf[m].mean()))
            ys.append(float(out[m].mean()))
    if len(xs) < 2:
        return float("nan"), float("nan")
    x = np.asarray(xs)
    y = np.asarray(ys)
    if float(np.std(x)) < 1e-9:
        return float("nan"), float("nan")
    slope, intercept = np.polyfit(x, y, 1)
    return float(slope), float(intercept)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="T-SPB-2-INSTRUCT-C calibration harness")
    parser.add_argument("--n-tokens", type=int, default=32)
    parser.add_argument("--bins", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(argv)

    print(f"[T-SPB-2-INSTRUCT-C] sidecar={SIDE}", flush=True)
    print(f"[T-SPB-2-INSTRUCT-C] n_prompts={len(PROMPTS)} n_tokens={args.n_tokens}", flush=True)

    confidences: list[float] = []
    outcomes: list[int] = []
    latencies: list[float] = []
    rows: list[dict] = []

    for idx, (prompt, expected) in enumerate(PROMPTS):
        t0 = time.time()
        try:
            resp = call_think(prompt, args.n_tokens, timeout_s=args.timeout)
        except (urlerror.URLError, urlerror.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"  [{idx+1:2d}/{len(PROMPTS)}] ERROR {exc}", flush=True)
            continue
        wall = time.time() - t0
        text = str(resp.get("text", ""))
        conf = float(resp.get("confidence", 0.0))
        correct = int(evaluate_response(text, expected))
        confidences.append(conf)
        outcomes.append(correct)
        latencies.append(wall)
        rows.append(
            {
                "idx": idx,
                "prompt": prompt,
                "expected": expected,
                "text": text[:160],
                "confidence": conf,
                "outcome": correct,
                "latency_s": wall,
                "backend": resp.get("metadata", {}).get("backend", "?"),
            }
        )
        verdict = "✓" if correct else "✗"
        print(
            f"  [{idx+1:2d}/{len(PROMPTS)}] {verdict} conf={conf:.3f} wall={wall:.2f}s  {prompt[:50]}",
            flush=True,
        )

    conf = np.asarray(confidences, dtype=float)
    out = np.asarray(outcomes, dtype=float)
    if conf.size == 0:
        print("[T-SPB-2-INSTRUCT-C] no samples — abort", flush=True)
        return 1

    n = conf.size
    n_correct = int(out.sum())
    base_rate = float(out.mean())
    mean_conf = float(conf.mean())
    b = brier(conf, out)
    e = ece(conf, out, bins=args.bins)
    slope, intercept = reliability_slope(conf, out, bins=args.bins)
    mean_latency = float(np.mean(latencies))

    # Sanity bounds for a "usable" calibration on 20 prompts.
    #   Brier < 0.25 (better than always-confident-at-0.5 baseline of 0.25)
    #   ECE   < 0.15
    #   slope ∈ [0.5, 1.5]  (sanity, not strict — 20 samples is noisy)
    notes: list[str] = []
    if b >= 0.25:
        notes.append(f"Brier {b:.3f} >= 0.25 (no better than constant 0.5)")
    if e >= 0.15:
        notes.append(f"ECE {e:.3f} >= 0.15 (poorly calibrated)")
    if not np.isnan(slope) and not (0.5 <= slope <= 1.5):
        notes.append(f"reliability slope {slope:.2f} outside [0.5, 1.5]")
    if base_rate == 0.0 or base_rate == 1.0:
        notes.append(
            f"outcome base-rate = {base_rate:.2f} (degenerate: all-{'right' if base_rate==1 else 'wrong'})"
        )

    summary = {
        "n": n,
        "n_correct": n_correct,
        "base_rate": base_rate,
        "mean_confidence": mean_conf,
        "brier_score": b,
        "ece": e,
        "reliability_slope": slope,
        "reliability_intercept": intercept,
        "mean_latency_s": mean_latency,
        "sidecar": SIDE,
        "n_tokens": args.n_tokens,
        "bins": args.bins,
        "notes": notes,
        "rows": rows,
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[T-SPB-2-INSTRUCT-C] wrote {OUT_JSON}", flush=True)

    # Markdown report
    md = [
        "# T-SPB-2-INSTRUCT-C — calibration of Qwen instruction sidecar",
        "",
        f"**Sidecar**: `{SIDE}`  ",
        f"**Backend**: `{rows[0]['backend'] if rows else '?'}`  ",
        f"**Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**N prompts**: {n}  ",
        f"**n_tokens**: {args.n_tokens}  ",
        "",
        "## Headline metrics",
        "",
        f"| metric | value | interpretation |",
        f"| --- | --- | --- |",
        f"| base rate (correct) | {base_rate:.2f} | fraction of prompts answered correctly |",
        f"| mean predicted confidence | {mean_conf:.3f} | average `/think` confidence |",
        f"| Brier score | **{b:.3f}** | lower = better (0 perfect, 0.25 = constant-0.5) |",
        f"| ECE (10-bin) | **{e:.3f}** | lower = better |",
        f"| reliability slope | **{slope:.3f}** | 1.0 = perfectly calibrated (OLS per bin) |",
        f"| reliability intercept | {intercept:+.3f} | 0 = perfectly calibrated |",
        f"| mean wall latency | {mean_latency:.2f} s | per `/think` call |",
        "",
        "## Comparison vs T205-C baseline",
        "",
        "T205-C (Qwen-3B NF4, base): slope log-log pred/meas = 0.982 ± 0.086.",
        "T-SPB-2-INSTRUCT-C does not measure energy; it measures the *semantic*",
        "calibration of `confidence`. A reliability slope in [0.8, 1.2] and",
        "ECE < 0.10 indicate the sidecar is honest about its certainty.",
        "",
    ]
    if notes:
        md.append("## Notes / caveats")
        md.append("")
        for n_note in notes:
            md.append(f"- {n_note}")
        md.append("")
    md.append("## Per-prompt details")
    md.append("")
    md.append("| # | prompt | conf | correct | text (first 100 chars) |")
    md.append("| --- | --- | ---: | :---: | --- |")
    for r in rows:
        verdict = "✓" if r["outcome"] else "✗"
        prompt = r["prompt"].replace("|", "\\|")
        text = r["text"].replace("|", "\\|").replace("\n", " ")[:100]
        md.append(
            f"| {r['idx']+1} | {prompt[:40]} | {r['confidence']:.3f} | {verdict} | {text} |"
        )
    md.append("")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"[T-SPB-2-INSTRUCT-C] wrote {OUT_MD}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))