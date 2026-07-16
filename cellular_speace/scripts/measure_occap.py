#!/usr/bin/env python3
"""Measure SPEACE Organismic Cognitive Capacity (OCCap) via the PSN + OCCap observer.

Usage:
    python scripts/measure_occap.py [--ticks N] [--output DIR]

Simulates the physiological signal network for N ticks, computes Ω(t) at
each update interval, and writes a timestamped JSON report under reports/occap/.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from speace_core.cellular_brain.psn import Physiome, PhysiologicalSignalBus
from speace_core.cognitive_observatory.occap import OCCapCalculator, ComplexityVector, OCCapState

REPORTS_ROOT = PROJECT_ROOT / "reports" / "occap"
PHYSIOME_DIR = PROJECT_ROOT / "speace_core" / "dna" / "genome" / "physiology"


# ── Physiological signal profiles ──────────────────────────────
# Each signal has: baseline, amplitude (variance), noise, and optional perturbation phase values.

import random
random.seed(42)
_rng = random.Random(42)

SIGNAL_PROFILES: Dict[str, Dict[str, float]] = {
    "energy":          {"baseline": 0.65, "amp": 0.12, "noise": 0.06},
    "nutrition":       {"baseline": 0.60, "amp": 0.10, "noise": 0.05},
    "fatigue":         {"baseline": 0.20, "amp": 0.08, "noise": 0.05},
    "repair":          {"baseline": 0.30, "amp": 0.05, "noise": 0.04},
    "growth":          {"baseline": 0.25, "amp": 0.04, "noise": 0.04},
    "stress":          {"baseline": 0.30, "amp": 0.10, "noise": 0.07},
    "threat":          {"baseline": 0.10, "amp": 0.05, "noise": 0.04},
    "danger":          {"baseline": 0.05, "amp": 0.03, "noise": 0.03},
    "safety":          {"baseline": 0.80, "amp": 0.08, "noise": 0.05},
    "prediction_error":{"baseline": 0.25, "amp": 0.08, "noise": 0.06},
    "inflammation":    {"baseline": 0.10, "amp": 0.04, "noise": 0.04},
    "damage":          {"baseline": 0.02, "amp": 0.02, "noise": 0.03},
    "plasticity":      {"baseline": 0.40, "amp": 0.06, "noise": 0.05},
    "reward":          {"baseline": 0.30, "amp": 0.10, "noise": 0.06},
    "novelty":         {"baseline": 0.35, "amp": 0.08, "noise": 0.05},
    "opportunity":     {"baseline": 0.25, "amp": 0.06, "noise": 0.05},
    "curiosity":       {"baseline": 0.40, "amp": 0.08, "noise": 0.05},
    "coherence":       {"baseline": 0.65, "amp": 0.06, "noise": 0.05},
    "entropy":         {"baseline": 0.30, "amp": 0.05, "noise": 0.05},
    "synchronization": {"baseline": 0.60, "amp": 0.06, "noise": 0.05},
    "temperature":     {"baseline": 0.45, "amp": 0.05, "noise": 0.04},
    "hydration":       {"baseline": 0.70, "amp": 0.08, "noise": 0.05},
}


def gauss(scale: float = 1.0) -> float:
    """Gaussian noise with given scale."""
    return _rng.gauss(0, scale)


def simulate_signal(sid: str, tick: int, phase: str = "normal") -> float:
    """Return a realistic signal value for a given tick and phase."""
    p = SIGNAL_PROFILES[sid]
    b = p["baseline"]
    a = p["amp"]
    n = p["noise"]

    # Multi-frequency circadian oscillations (stronger)
    circadian = (
        0.5 * math.sin(2 * math.pi * tick / 100.0)
        + 0.3 * math.sin(2 * math.pi * tick / 33.0)
        + 0.2 * math.sin(2 * math.pi * tick / 17.0)
    ) * a

    # Gaussian noise (5% of scale)
    noise = gauss(n)

    if phase == "perturbation":
        if sid == "stress":
            return max(0.0, min(1.0, 0.8 + 0.15 * math.sin(tick * 0.3) + gauss(0.05)))
        if sid == "energy":
            return max(0.0, min(1.0, 0.25 + 0.10 * math.sin(tick * 0.2) + gauss(0.04)))
        if sid == "damage":
            return max(0.0, min(1.0, 0.4 + 0.12 * math.sin(tick * 0.15) + gauss(0.03)))
        if sid == "inflammation":
            return max(0.0, min(1.0, 0.5 + 0.10 * math.sin(tick * 0.2) + gauss(0.04)))
        if sid == "fatigue":
            return max(0.0, min(1.0, 0.65 + 0.10 * math.sin(tick * 0.15) + gauss(0.04)))
        if sid == "safety":
            return max(0.0, min(1.0, 0.30 + 0.12 * math.sin(tick * 0.25) + gauss(0.05)))
        if sid == "coherence":
            return max(0.0, min(1.0, 0.35 + 0.08 * math.sin(tick * 0.1) + gauss(0.04)))
        if sid in ("threat", "danger"):
            return max(0.0, min(1.0, 0.50 + 0.15 * math.sin(tick * 0.3) + gauss(0.05)))
        if sid == "prediction_error":
            return max(0.0, min(1.0, 0.65 + 0.12 * math.sin(tick * 0.2) + gauss(0.05)))
        if sid == "repair":
            return max(0.0, min(1.0, 0.55 + 0.10 * math.sin(tick * 0.12) + gauss(0.04)))
        return max(0.0, min(1.0, 0.55 + circadian + noise))

    if phase == "recovery":
        recovery_factor = max(0.0, 1.0 - (tick - 280) / 220.0)
        if sid == "energy":
            return max(0.0, min(1.0, b + circadian + 0.4 * recovery_factor + noise))
        if sid in ("stress", "fatigue", "inflammation", "damage"):
            return max(0.0, min(1.0, b - 0.3 * recovery_factor + circadian + noise))
        if sid in ("safety", "coherence"):
            return max(0.0, min(1.0, b - 0.2 * recovery_factor + circadian + noise))
        return max(0.0, min(1.0, b + circadian + noise))

    # Normal phase
    return max(0.0, min(1.0, b + circadian + noise))


def run_simulation(
    n_ticks: int = 500,
    perturbation_start: int = 150,
    perturbation_end: int = 280,
) -> OCCapCalculator:
    """Run a full PSN + OCCap simulation and return the calculator with history."""
    print(f"  Loading Physiome from {PHYSIOME_DIR} ...")
    phys = Physiome(str(PHYSIOME_DIR))
    phys.load()
    violations = phys.validate()
    if violations:
        print(f"  Warning — Physiome violations: {violations}")
    print(f"  Physiome v{phys.version}: {len(phys.systems)} systems, {len(phys.organs)} organs, "
          f"{len(phys.tissues_by_id)} tissues, {len(phys.constitutional_signals)} signals, "
          f"{len(phys.molecules)} molecules")

    print("  Creating PSN dual-bus (homeostatic PD: Kp=0.12, Kd=0.04) ...")
    psn = PhysiologicalSignalBus(phys, auto_register_hormones=True,
                                  enable_homeostatic_control=True,
                                  homeostatic_Kp=0.12, homeostatic_Kd=0.04)

    print("  Creating OCCap calculator ...")
    calc = OCCapCalculator(psn)

    print(f"  Running {n_ticks} ticks ...")
    last_report = 0
    for t in range(1, n_ticks + 1):
        psn.tick_begin(t)

        # Determine simulation phase
        if perturbation_start <= t <= perturbation_end:
            phase = "perturbation"
        elif t > perturbation_end:
            recovery_progress = (t - perturbation_end) / (n_ticks - perturbation_end)
            if recovery_progress < 0.3:
                phase = "perturbation"
            elif recovery_progress < 0.6:
                phase = "recovery"
            else:
                phase = "normal"
        else:
            phase = "normal"

        # Publish all constitutional signals
        for sid in phys.constitutional_signals:
            val = simulate_signal(sid, t, phase)
            psn.publish_stream(sid, val, source="simulation")

        # Set estimates for PBM-related metrics
        pred_err = simulate_signal("prediction_error", t, phase)
        psn.set_estimate("prediction_error", pred_err)
        psn.set_estimate("learning_rate", 0.3 + 0.3 * (1.0 - pred_err))
        damage_level = simulate_signal("damage", t, phase)
        psn.set_estimate("damage_level", damage_level)

        # Set meta-signals
        psn.set_meta_signal("receptor_occupancy", 0.4 + 0.2 * math.sin(2 * math.pi * t / 50.0))
        psn.set_meta_signal("reallocation_capacity", 0.5 + 0.2 * math.sin(2 * math.pi * t / 80.0))
        psn.set_meta_signal("avg_recovery_ticks", 8.0 + 10.0 * max(0.0, damage_level - 0.2))

        # Publish periodic event for novelty/learning
        if t % 75 == 0:
            psn.publish_event("novelty", 0.7, source="simulation", category="NOVELTY", duration=5)
        if t % 120 == 0:
            psn.publish_event("reward", 0.8, source="simulation", category="REWARD", duration=8)
        if phase == "perturbation" and t % 30 == 0:
            psn.publish_event("damage", 0.6, source="simulation", category="DAMAGE", duration=6)
            psn.publish_event("inflammation", 0.5, source="simulation", category="ALARM", duration=8)

        # Deduct metabolic costs (makes M dynamic)
        cost = 0.004 * len(phys.constitutional_signals) * (1.0 + damage_level)
        psn.metabolism.global_energy = max(0.0, psn.metabolism.global_energy - cost)
        # Energy recovery when not in perturbation
        if psn.metabolism.global_energy < 5.0:
            recovery = 0.03 if phase != "perturbation" else 0.005
            psn.metabolism.global_energy = min(5.0, psn.metabolism.global_energy + recovery)

        psn.tick_end(t)

        # Compute OCCap (uses cached sub-metrics per configured intervals)
        state = calc.compute(t)

        # Progress report
        if t - last_report >= 100:
            print(f"    tick={t:4d}: OCCap={state.occap:.4f} "
                  f"C_mag={state.C_mag:.4f} I={state.I:.4f} P={state.P:.4f} "
                  f"Phi={state.Phi:.4f} M={state.M:.4f} R={state.R:.4f} "
                  f"OCEff={state.oceff:.6f}")
            last_report = t

    return calc


def generate_report(calc: OCCapCalculator, n_ticks: int) -> Dict[str, Any]:
    """Generate a comprehensive OCCap report."""
    state = calc.current_state
    traj_summary = calc.trajectory.get_trajectory_summary()
    history = calc.history

    if not history:
        return {"error": "No history available"}

    # Compute time-series statistics per dimension
    def stats(values: List[float]) -> Dict[str, float]:
        if not values:
            return {"min": 0, "max": 0, "mean": 0, "std": 0, "final": 0}
        mean = sum(values) / len(values)
        var = sum((v - mean) ** 2 for v in values) / len(values)
        return {
            "min": round(min(values), 4),
            "max": round(max(values), 4),
            "mean": round(mean, 4),
            "std": round(math.sqrt(var), 4),
            "final": round(values[-1], 4),
            "initial": round(values[0], 4),
            "delta": round(values[-1] - values[0], 4),
        }

    occap_series = [s.occap for s in history]
    oceff_series = [s.oceff for s in history]
    i_series = [s.I for s in history]
    p_series = [s.P for s in history]
    phi_series = [s.Phi for s in history]
    m_series = [s.M for s in history]
    r_series = [s.R for s in history]
    cmag_series = [s.C_mag for s in history]

    dim_names = ["occap", "oceff", "C_mag", "I", "P", "Phi", "M", "R"]
    dim_series = [occap_series, oceff_series, cmag_series, i_series, p_series, phi_series, m_series, r_series]

    report = {
        "report_metadata": {
            "timestamp": time.time(),
            "n_ticks": n_ticks,
            "n_history": len(history),
            "script": "measure_occap.py",
            "framework_version": "T178 v1.0",
        },
        "current_state": state.as_dict() if state else {},
        "trajectory": traj_summary,
        "dimension_statistics": {
            dim: stats(ser) for dim, ser in zip(dim_names, dim_series)
        },
        "complexity_decomposition": {
            "C_s": stats([s.C.structural for s in history]),
            "C_f": stats([s.C.functional for s in history]),
            "C_r": stats([s.C.regulatory for s in history]),
            "C_i": stats([s.C.informational for s in history]),
            "C_t": stats([s.C.temporal for s in history]),
        },
    }

    # Add comparative analysis if we have normal vs perturbation phases
    mid = n_ticks // 2
    if len(history) > mid + 50:
        pre = history[:mid]
        post = history[mid:]
        report["phase_comparison"] = {
            "pre_perturbation": {
                "mean_occap": round(sum(s.occap for s in pre) / len(pre), 4),
                "mean_I": round(sum(s.I for s in pre) / len(pre), 4),
                "mean_Phi": round(sum(s.Phi for s in pre) / len(pre), 4),
                "mean_R": round(sum(s.R for s in pre) / len(pre), 4),
            },
            "post_perturbation": {
                "mean_occap": round(sum(s.occap for s in post) / len(post), 4),
                "mean_I": round(sum(s.I for s in post) / len(post), 4),
                "mean_Phi": round(sum(s.Phi for s in post) / len(post), 4),
                "mean_R": round(sum(s.R for s in post) / len(post), 4),
            },
        }

    return report


def print_report_summary(report: Dict[str, Any]) -> None:
    """Print a human-readable summary of the OCCap report."""
    print("\n" + "=" * 70)
    print("  SPEACE — Organismic Cognitive Capacity (OCCap) Report")
    print("=" * 70)

    meta = report.get("report_metadata", {})
    print(f"\n  Ticks simulated: {meta.get('n_ticks', '?')}")
    print(f"  History length:  {meta.get('n_history', '?')}")

    state = report.get("current_state", {})
    if state:
        print(f"\n  == Omega(t) State Field ==")
        print(f"  OCCap    = {state.get('occap', 0):.4f}   (Organismic Cognitive Capacity)")
        print(f"  OCEff    = {state.get('oceff', 0):.6f}   (Organismic Cognitive Efficiency)")
        print(f"  |C|      = {state.get('C_mag', 0):.4f}   (Complexity magnitude)")
        print(f"  I        = {state.get('I', 0):.4f}   (Integration)")
        print(f"  P        = {state.get('P', 0):.4f}   (Plasticity)")
        print(f"  Phi_o    = {state.get('Phi', 0):.4f}   (Organismic Coherence)")
        print(f"  M        = {state.get('M', 0):.4f}   (Metabolic capacity)")
        print(f"  R        = {state.get('R', 0):.4f}   (Resilience)")

        print(f"\n  == Complexity Decomposition ==")
        print(f"  C_s (structural)      = {state.get('C_s', 0):.4f}")
        print(f"  C_f (functional)      = {state.get('C_f', 0):.4f}")
        print(f"  C_r (regulatory)      = {state.get('C_r', 0):.4f}")
        print(f"  C_i (informational)   = {state.get('C_i', 0):.4f}")
        print(f"  C_t (temporal)        = {state.get('C_t', 0):.4f}")

    traj = report.get("trajectory", {})
    if traj:
        print(f"\n  == Psi(t) Evolutionary Trajectory ==")
        print(f"  Speed:          {traj.get('current_speed', 0):.4f}")
        print(f"  Stability:      {traj.get('current_stability', 0):.4f}")
        print(f"  Exploration:    {traj.get('exploration_volume', 0):.4f}")
        print(f"  Current stage:  {traj.get('current_stage', '?')}")
        stages = traj.get("stages", [])
        if stages:
            print(f"  Developmental stages ({len(stages)}):")
            for s in stages:
                print(f"    {s['name']:16s}: ticks {s['start_tick']:4d}-{s['end_tick']:4d}  "
                      f"OCCap={s['mean_occap']:.3f}  stability={s['mean_stability']:.3f}")

    stats = report.get("dimension_statistics", {})
    if stats:
        print(f"\n  == Dimension Statistics ==")
        print(f"  {'Metric':10s} {'Min':8s} {'Max':8s} {'Mean':8s} {'Std':8s} {'Final':8s}")
        print(f"  {'-'*50}")
        for dim, s in stats.items():
            print(f"  {dim:10s} {s['min']:8.4f} {s['max']:8.4f} {s['mean']:8.4f} "
                  f"{s['std']:8.4f} {s['final']:8.4f}")

    phase_comp = report.get("phase_comparison", {})
    if phase_comp:
        print(f"\n  == Phase Comparison (pre vs post perturbation) ==")
        pre = phase_comp.get("pre_perturbation", {})
        post = phase_comp.get("post_perturbation", {})
        for key in pre:
            print(f"    {key}: {pre[key]:.4f} -> {post.get(key, 0):.4f}")

    # Cross-domain comparison
    print(f"\n  == Cross-Domain OCCap Comparison (from T178 sec14) ==")
    print(f"  {'Organism':25s} {'|C|':8s} {'I':8s} {'Phi_o':8s}")
    print(f"  {'-'*51}")
    comparisons = [
        ("C. elegans (302 neurons)", "0.01", "0.1", "0.3"),
        ("Honeybee (~1M neurons)", "0.05", "0.3", "0.5"),
        ("Mouse (~70M neurons)", "0.3", "0.5", "0.6"),
        ("Human (~86B neurons)", "1.0", "0.8", "0.8"),
        ("Elephant (~257B neurons)", "1.5", "0.6", "0.6"),
        ("GPT-4 (1.8T params)", "2.0", "0.2", "0.1"),
        ("SPEACE (this run)", f"{state.get('C_mag', 0):.2f}", f"{state.get('I', 0):.2f}", f"{state.get('Phi', 0):.2f}"),
    ]
    for name, cs, i, phi in comparisons:
        print(f"  {name:25s} {cs:>8s} {i:>8s} {phi:>8s}")

    print(f"\n  Report saved to: {REPORTS_ROOT}")


def save_report(report: Dict[str, Any]) -> Path:
    """Save the OCCap report as JSON."""
    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    path = REPORTS_ROOT / f"occap_{timestamp}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"  Report written to {path}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure SPEACE OCCap")
    parser.add_argument("--ticks", type=int, default=500, help="Number of simulation ticks (default: 500)")
    parser.add_argument("--output", type=str, default=None, help="Output directory (default: reports/occap/)")
    args = parser.parse_args()

    print(f"\n  SPEACE OCCap Measurement")
    print(f"  ========================")
    print(f"  Ticks: {args.ticks}")
    print(f"  Perturbation: ticks 150–280 (stress, damage, inflammation)")

    calc = run_simulation(n_ticks=args.ticks)

    print(f"\n  Generating report ...")
    report = generate_report(calc, args.ticks)

    if args.output:
        global REPORTS_ROOT
        REPORTS_ROOT = Path(args.output)

    save_report(report)
    print_report_summary(report)

    print(f"\n  Done.")


if __name__ == "__main__":
    main()
