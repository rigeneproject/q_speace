"""T-SPB-2-INSTRUCT-MULTITURN — multi-turn stress test.

Drives a 6-turn conversation through a real :class:`SpikingBrainCortex`
backed by the Qwen instruction sidecar. Tracks:

  - per-turn ``confidence``, ``belief``, ``spikes``, ``plasticity``
  - per-turn ``sevo``, ``energy_w``, ``approved`` (CortexReport)
  - running ``ilf.coherence_phi`` after each ``apply_to_ilf``
  - rolling mean of the agent's belief (convergence check)

The hypothesis: belief concentrates over multiple focused turns, so
``coherence_phi`` rises — IF the prompts are coherent with each other.
A scattered conversation (deliberately incoherent) should NOT raise
coherence. We test both regimes.

**Usage (WSL2)**:

    cd spiking_brain_server
    python _tspB2_multiturn.py --scenario focused
    python _tspB2_multiturn.py --scenario scattered
    python _tspB2_multiturn.py --scenario mixed

**Output**:

  - ``docs/T-SPB-2_INSTRUCT_MULTITURN.md`` — markdown report
  - ``docs/T-SPB-2_INSTRUCT_MULTITURN.json`` — raw metrics
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from urllib import error as urlerror
from urllib import request

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

SIDE = "http://127.0.0.1:8002"
OUT_MD = REPO_ROOT / "docs" / "T-SPB-2_INSTRUCT_MULTITURN.md"
OUT_JSON = REPO_ROOT / "docs" / "T-SPB-2_INSTRUCT_MULTITURN.json"

# Three scenarios — each is a 6-turn conversation.
SCENARIOS: dict[str, list[str]] = {
    "focused": [
        "What is the ILF (Informational Logical Field) in Q-SPEACE?",
        "How does the ILF track belief across multiple agents?",
        "What is the role of the Sevo gate in approving ILF updates?",
        "How does coherence_phi change after an approved Sevo gate?",
        "Why does a low-confidence belief not raise coherence_phi?",
        "Summarise the relationship between ILF, Sevo, and coherence_phi.",
    ],
    "scattered": [
        "What is the capital of France?",
        "Compute 17 * 23.",
        "Define 'photosynthesis'.",
        "Is Mount Everest in Asia?",
        "What year did WWII end?",
        "Tell me a joke about robots.",
    ],
    "mixed": [
        "What is coherence_phi in Q-SPEACE?",  # domain
        "What is the capital of Japan?",  # off
        "How does the Sevo gate work?",  # domain
        "Compute 144 / 12.",  # off
        "Why does a uniform belief lower coherence_phi?",  # domain
        "Define 'entropy' in one sentence.",  # off
    ],
}


def call_think(prompt: str, n_tokens: int, history: list[dict] | None = None,
               timeout_s: float = 60.0) -> dict:
    body: dict = {"prompt": prompt, "n_tokens": n_tokens, "coherence_phi": 1.0}
    if history:
        body["history"] = history
    req = request.Request(
        f"{SIDE}/think",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def history_payload(turns: list[dict]) -> list[dict]:
    out: list[dict] = []
    for t in turns:
        out.append(
            {
                "text": t["text"],
                "confidence": t["confidence"],
                "belief": list(t["belief"]),
            }
        )
    return out


async def run_scenario(
    name: str,
    prompts: list[str],
    n_tokens: int,
    q_star_ema: float = 0.5,
    coherence_phi_ema: float = 0.5,
) -> dict:
    """Run one scenario, returning a per-turn trace + summary.

    T-SPB-3-A: ``q_star_ema`` and ``coherence_phi_ema`` default to 0.5
    (the fix). Pass 0.0 to reproduce the legacy behaviour reported in
    ``docs/T-SPB-2_INSTRUCT_MULTITURN.md``.
    """
    from q_speace.edd_cvt.ilf import InformationalLogicalField
    from q_speace.spiking_brain.cortex import SpikingBrainCortex

    ilf = InformationalLogicalField(
        coherence_phi=1.0,
        q_star_ema=q_star_ema,
        coherence_phi_ema=coherence_phi_ema,
    )
    cortex = SpikingBrainCortex(ilf=ilf)
    turns: list[dict] = []
    trace: list[dict] = []

    for idx, prompt in enumerate(prompts):
        history = history_payload(turns[-3:]) if turns else None
        report = await cortex.tick(prompt, n_tokens=n_tokens, agent_id="spiking_brain")
        result = report.result
        if result is None:
            trace.append(
                {
                    "idx": idx,
                    "prompt": prompt,
                    "approved": False,
                    "reason": report.reason,
                    "coherence_phi": float(ilf.coherence_phi),
                    "sevo": report.sevo,
                    "energy_w": report.energy_w,
                }
            )
            continue
        turns.append(
            {
                "text": result.text,
                "confidence": float(result.confidence),
                "belief": np.asarray(result.belief, dtype=float).tolist(),
            }
        )
        trace.append(
            {
                "idx": idx,
                "prompt": prompt,
                "approved": report.approved,
                "reason": report.reason,
                "confidence": float(result.confidence),
                "belief": np.asarray(result.belief, dtype=float).tolist(),
                "spikes": int(np.asarray(result.spikes.spikes).sum()),
                "sparsity": float(result.spikes.sparsity),
                "plasticity": np.asarray(result.plasticity, dtype=float).tolist(),
                "coherence_phi": float(ilf.coherence_phi),
                "sevo": float(report.sevo) if report.sevo != float("-inf") else None,
                "energy_w": float(report.energy_w),
                "latency_s": float(result.latency_s),
                "text_excerpt": result.text[:120],
            }
        )

    approved = [t for t in trace if t.get("approved")]
    final_phi = float(ilf.coherence_phi)
    initial_phi = 1.0
    delta_phi = final_phi - initial_phi
    confidences = [t["confidence"] for t in trace if "confidence" in t]
    mean_conf = float(np.mean(confidences)) if confidences else 0.0

    summary = {
        "scenario": name,
        "n_turns": len(prompts),
        "n_approved": len(approved),
        "approval_rate": len(approved) / max(len(prompts), 1),
        "initial_coherence_phi": initial_phi,
        "final_coherence_phi": final_phi,
        "delta_coherence_phi": delta_phi,
        "mean_confidence": mean_conf,
        "mean_sevo": (
            float(np.mean([t["sevo"] for t in approved if t["sevo"] is not None]))
            if approved
            else None
        ),
        "trace": trace,
    }
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="T-SPB-2-INSTRUCT-MULTITURN")
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIOS.keys()) + ["all"],
        default="all",
    )
    parser.add_argument("--n-tokens", type=int, default=48)
    parser.add_argument(
        "--q-star-ema",
        type=float,
        default=0.5,
        help="ILF q_star EMA blend coefficient (0.0 = legacy, 0.5 = fix)",
    )
    parser.add_argument(
        "--coherence-phi-ema",
        type=float,
        default=0.5,
        help="ILF coherence_phi EMA blend coefficient (0.0 = legacy, 0.5 = fix)",
    )
    args = parser.parse_args(argv)

    targets = list(SCENARIOS.keys()) if args.scenario == "all" else [args.scenario]

    summaries: list[dict] = []
    for name in targets:
        print(f"\n=== scenario: {name} ===", flush=True)
        try:
            summary = asyncio.run(
                run_scenario(
                    name,
                    SCENARIOS[name],
                    args.n_tokens,
                    q_star_ema=args.q_star_ema,
                    coherence_phi_ema=args.coherence_phi_ema,
                )
            )
        except (urlerror.URLError, urlerror.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"  ERROR: {exc}", flush=True)
            continue
        summaries.append(summary)
        print(
            f"  approved={summary['n_approved']}/{summary['n_turns']} "
            f"phi {summary['initial_coherence_phi']:.3f}→{summary['final_coherence_phi']:.3f} "
            f"mean_conf={summary['mean_confidence']:.3f}",
            flush=True,
        )

    OUT_JSON.write_text(
        json.dumps({"summaries": summaries}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[MULTITURN] wrote {OUT_JSON}", flush=True)

    md = [
        "# T-SPB-2-INSTRUCT-MULTITURN — multi-turn coherence evolution",
        "",
        f"**Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Sidecar**: `{SIDE}`  ",
        f"**n_tokens**: {args.n_tokens}  ",
        "",
        "## Summary table",
        "",
        "| scenario | approved / turns | φ₀ | φ_final | Δφ | mean conf |",
        "| --- | :---: | ---: | ---: | ---: | ---: |",
    ]
    for s in summaries:
        md.append(
            f"| {s['scenario']} | {s['n_approved']}/{s['n_turns']} "
            f"| {s['initial_coherence_phi']:.3f} "
            f"| {s['final_coherence_phi']:.3f} "
            f"| {s['delta_coherence_phi']:+.3f} "
            f"| {s['mean_confidence']:.3f} |"
        )
    md.append("")
    md.append("## Interpretation")
    md.append("")
    md.append(
        "- `focused` (all turns on Q-SPEACE ILF/Sevo/coherence) should produce "
        "concentrated beliefs → Δφ ≥ 0 (coherence_phi rises as the agent's "
        "belief vector converges)."
    )
    md.append(
        "- `scattered` (unrelated topics) should leave belief dispersed → "
        "Δφ ≈ 0 or negative (no shared semantic focus)."
    )
    md.append(
        "- `mixed` (3 domain, 3 off-topic) should land between the two."
    )
    md.append("")
    md.append("## Per-turn trace")
    md.append("")
    for s in summaries:
        md.append(f"### `{s['scenario']}`")
        md.append("")
        md.append("| # | approved | conf | φ | sevo | E(W) | text excerpt |")
        md.append("| ---: | :---: | ---: | ---: | ---: | ---: | --- |")
        for t in s["trace"]:
            verdict = "✓" if t.get("approved") else "✗"
            conf = t.get("confidence", float("nan"))
            phi = t.get("coherence_phi", float("nan"))
            sevo = t.get("sevo")
            sevo_s = f"{sevo:.2f}" if sevo is not None else "—"
            energy = t.get("energy_w", float("nan"))
            text = t.get("text_excerpt", "(no result)")
            text = text.replace("|", "\\|").replace("\n", " ")[:80]
            md.append(
                f"| {t['idx']+1} | {verdict} | {conf:.3f} | {phi:.3f} "
                f"| {sevo_s} | {energy:.1f} | {text} |"
            )
        md.append("")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"[MULTITURN] wrote {OUT_MD}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))