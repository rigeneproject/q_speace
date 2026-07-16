import asyncio
import json
from typing import Any, Dict, List, Optional

from speace_core.cellular_brain.analysis.deep_region_audit import (
    DeepRegionAuditor,
    DeepRegionAuditProfile,
    DeepRegionAuditResult,
)
from speace_core.cellular_brain.benchmark.neurofunctional_benchmark import NeuroFunctionalBenchmark


def make_profiles() -> List[DeepRegionAuditProfile]:
    """Build T37B profiles comparing brainstem with adaptive gain controller."""
    base = {
        "deep_regions_enabled": True,
        "inter_region_plasticity_enabled": True,
        "region_signal_routing_enabled": True,
        "region_stability_controller_enabled": True,
        "deep_region_routing_calibrator_enabled": True,
        "brainstem_controller_enabled": True,
        "trigger_mode": "hybrid",
    }
    return [
        DeepRegionAuditProfile(
            profile_id="g0",
            name="baseline_t36_no_gain_controller",
            brainstem_gain_controller_enabled=False,
            t34_profile_id="p3",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="g1",
            name="brainstem_gain_default",
            brainstem_gain_controller_enabled=True,
            t34_profile_id="p3",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="g2",
            name="brainstem_gain_fast_learning",
            brainstem_gain_controller_enabled=True,
            brainstem_gain_learning_rate=0.10,
            t34_profile_id="p3",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="g3",
            name="brainstem_gain_conservative",
            brainstem_gain_controller_enabled=True,
            brainstem_gain_learning_rate=0.02,
            t34_profile_id="p3",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="g4",
            name="brainstem_gain_emergency_relaxed",
            brainstem_gain_controller_enabled=True,
            brainstem_emergency_gain=0.80,
            t34_profile_id="p3",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="g5",
            name="brainstem_gain_cognitive_priority",
            brainstem_gain_controller_enabled=True,
            brainstem_cognitive_preservation_gain=1.30,
            t34_profile_id="p3",
            **base,
        ),
    ]


from speace_core.cellular_brain.regions.deep_region_routing_calibrator import (
    DeepRegionRoutingCalibrator,
    DeepRegionRoutingProfile,
)


def get_t34_profile(profile_id: str) -> DeepRegionRoutingProfile:
    defaults = {p.profile_id: p for p in DeepRegionRoutingCalibrator.build_default_profiles()}
    if profile_id in defaults:
        return defaults[profile_id]
    return defaults.get("p4", DeepRegionRoutingProfile(profile_id="p4", name="full_stability_aware"))


def apply_t34_profile(auditor: DeepRegionAuditor, profile: DeepRegionAuditProfile, orch) -> None:
    """Apply T34 routing calibration to orchestrator if enabled in profile."""
    extra = getattr(profile, "__pydantic_extra__", {}) or {}
    enabled = extra.get("deep_region_routing_calibrator_enabled", False)
    t34_id = extra.get("t34_profile_id", None)

    if not enabled and t34_id is None:
        return

    t34_profile = get_t34_profile(t34_id or "p3")
    calibrator = DeepRegionRoutingCalibrator(profile=t34_profile)
    orch.deep_region_routing_calibrator_enabled = True
    orch._deep_region_routing_profile = t34_profile
    orch._deep_region_routing_calibrator = calibrator
    calibrator.apply_profile_to_router(orch._region_signal_router)


def apply_brainstem_config(profile: DeepRegionAuditProfile, orch) -> None:
    """Apply brainstem configuration from profile extra fields."""
    extra = getattr(profile, "__pydantic_extra__", {}) or {}
    enabled = extra.get("brainstem_controller_enabled", False)
    orch.brainstem_controller_enabled = enabled
    gain_enabled = extra.get("brainstem_gain_controller_enabled", False)
    orch.brainstem_gain_controller_enabled = gain_enabled
    if enabled:
        orch.model_post_init(None)
        if orch._brainstem_controller is not None:
            bsc = orch._brainstem_controller
            if "brainstem_phi_threshold_stable" in extra:
                bsc.phi_threshold_stable = extra["brainstem_phi_threshold_stable"]
            if "brainstem_phi_threshold_watchful" in extra:
                bsc.phi_threshold_watchful = extra["brainstem_phi_threshold_watchful"]
            if "brainstem_phi_threshold_corrective" in extra:
                bsc.phi_threshold_corrective = extra["brainstem_phi_threshold_corrective"]
            if "brainstem_phi_threshold_protective" in extra:
                bsc.phi_threshold_protective = extra["brainstem_phi_threshold_protective"]
            if "brainstem_energy_threshold_emergency" in extra:
                bsc.energy_threshold_emergency = extra["brainstem_energy_threshold_emergency"]
            if "brainstem_instability_threshold_watchful" in extra:
                bsc.instability_threshold_watchful = extra["brainstem_instability_threshold_watchful"]
            if "brainstem_instability_threshold_corrective" in extra:
                bsc.instability_threshold_corrective = extra["brainstem_instability_threshold_corrective"]
            if "brainstem_instability_threshold_protective" in extra:
                bsc.instability_threshold_protective = extra["brainstem_instability_threshold_protective"]
            if "brainstem_instability_threshold_emergency" in extra:
                bsc.instability_threshold_emergency = extra["brainstem_instability_threshold_emergency"]


def compute_t37b_verdict(results: List[Any], baseline: Any) -> str:
    g0 = next((r for r in results if r.profile.profile_id == "g0"), None)
    if g0 is None:
        return "INSUFFICIENT_EVIDENCE"

    g0_net_gain = g0.deep_region_net_gain
    g0_cognitive = g0.cognitive_score
    g0_phi = g0.phi
    g0_energy = g0.energy_efficiency

    gain_results = [r for r in results if getattr(r.profile, "brainstem_gain_controller_enabled", False)]
    if not gain_results:
        return "INSUFFICIENT_EVIDENCE"

    best = max(gain_results, key=lambda r: r.deep_region_net_gain)
    net_gain_vs_g0 = best.deep_region_net_gain - g0_net_gain
    cog_delta = best.cognitive_score - g0_cognitive
    phi_delta = best.phi - g0_phi
    en_delta = best.energy_efficiency - g0_energy
    bm = best.benchmark_metrics
    gain_reward = bm.get("brainstem_gain_reward", 0.0) if isinstance(bm, dict) else 0.0
    gain_adjustments = bm.get("gain_adjustments_count", 0) if isinstance(bm, dict) else 0
    over_sup = bm.get("over_suppression_detected", False) if isinstance(bm, dict) else False

    # Regression checks
    if cog_delta < -0.05:
        return "GAIN_COGNITIVE_REGRESSION"
    if en_delta < -0.05:
        return "GAIN_ENERGY_REGRESSION"
    if phi_delta < -0.05:
        return "GAIN_PHI_REGRESSION"

    # Strong validation
    if net_gain_vs_g0 > 0.02 and gain_reward > 0 and gain_adjustments > 0:
        return "GAIN_CONTROLLER_VALIDATED"

    # Partial gain
    if net_gain_vs_g0 > 0.0:
        return "GAIN_PARTIAL_RECOVERY"

    # Neutral
    if abs(net_gain_vs_g0) <= 0.02:
        return "GAIN_NEUTRAL"

    # Over suppression
    if over_sup:
        return "GAIN_OVER_SUPPRESSION_REMAINING"

    return "GAIN_NO_EFFECT"


def _recommendation_for_verdict(verdict: str) -> str:
    mapping = {
        "GAIN_CONTROLLER_VALIDATED": "T38 Autonomic Plasticity Layer",
        "GAIN_PARTIAL_RECOVERY": "T38 Gain Sensitivity Tuning",
        "GAIN_NEUTRAL": "T38 Gain Input Coupling Redesign",
        "GAIN_OVER_SUPPRESSION_REMAINING": "T38 Adaptive Gain Relaxation",
        "GAIN_COGNITIVE_REGRESSION": "T38 Cognitive/Autonomic Balance Tuning v2",
        "GAIN_ENERGY_REGRESSION": "T38 Metabolic Arbitration Layer v2",
        "GAIN_PHI_REGRESSION": "T38 Phi-Oriented Stability Controller v2",
        "GAIN_NO_EFFECT": "T38 Gain Signal Coupling Fix",
        "INSUFFICIENT_EVIDENCE": "T38 Benchmark Perturbation Redesign",
    }
    return mapping.get(verdict, "T38 Next Step Undefined")


async def main():
    profiles = make_profiles()
    auditor = DeepRegionAuditor(n_adaptive_cycles=5, report_dir="reports/brainstem_gain")

    results = []
    for p in profiles:
        orch = auditor.build_orchestrator(deep_regions_enabled=p.deep_regions_enabled)
        auditor.apply_homeostatic_baseline(orch)
        auditor.apply_profile(p, orch)
        apply_t34_profile(auditor, p, orch)
        apply_brainstem_config(p, orch)

        benchmark = NeuroFunctionalBenchmark(orch)
        pattern = [1.0 if i % 2 == 0 else 0.0 for i in range(10)]

        try:
            result = await benchmark.run_case(
                auditor.benchmark_case,
                execution_mode="event_driven_burst",
                stdp_enabled=True,
                inhibition_enabled=True,
                energy_control_enabled=True,
                community_detection_enabled=True,
                confidence_enabled=True,
                inter_region_plasticity_enabled=p.inter_region_plasticity_enabled,
                region_signal_routing_enabled=p.region_signal_routing_enabled,
                input_pattern=pattern,
                target_output=pattern,
                n_ticks=auditor.n_adaptive_cycles,
            )
        except Exception as exc:
            res = DeepRegionAuditResult(
                profile=p,
                benchmark_metrics={},
                passed=False,
                failure_reason=str(exc),
            )
            results.append(res)
            continue

        m = result.metrics
        bm = m.model_dump()
        res = DeepRegionAuditResult(
            profile=p,
            benchmark_metrics=bm,
            cognitive_score=m.speace_cognitive_score,
            phi=m.coherence_phi,
            energy_efficiency=m.energy_efficiency,
            functional_improvement=m.functional_improvement,
            mean_pathway_utility=m.mean_pathway_utility,
            deep_region_signal_flow=m.deep_region_signal_flow,
            region_role_alignment_score=m.region_role_alignment_score,
            region_specialization_diversity=m.region_specialization_diversity,
            limbic_salience_score=m.limbic_salience_score,
            cerebellar_error_correction_score=m.cerebellar_error_correction_score,
            default_mode_consolidation_score=m.default_mode_consolidation_score,
            brainstem_homeostatic_stability_score=m.brainstem_homeostatic_stability_score,
            deep_region_cost=m.routing_energy_cost + m.pathway_energy_cost,
            deep_region_benefit=m.regional_signal_flow_score + m.functional_improvement,
            passed=True,
        )
        res.deep_region_net_gain = DeepRegionAuditor.compute_deep_region_net_gain(res, None)
        results.append(res)

    # Compute deltas vs g0 baseline
    g0 = next((r for r in results if r.profile.profile_id == "g0"), None)
    g0_net_gain = g0.deep_region_net_gain if g0 else 0.0
    g0_cognitive = g0.cognitive_score if g0 else 0.0
    g0_phi = g0.phi if g0 else 0.0
    g0_energy = g0.energy_efficiency if g0 else 0.0

    for r in results:
        r.cognitive_score_delta = r.cognitive_score - g0_cognitive
        r.phi_delta = r.phi - g0_phi
        r.energy_efficiency_delta = r.energy_efficiency - g0_energy
        r.functional_improvement_delta = r.functional_improvement - g0.functional_improvement if g0 else 0.0
        r.pathway_utility_delta = r.mean_pathway_utility - g0.mean_pathway_utility if g0 else 0.0
        r.deep_region_net_gain = DeepRegionAuditor.compute_deep_region_net_gain(r, g0)
        r.benchmark_metrics["net_gain_vs_g0"] = r.deep_region_net_gain - g0_net_gain
        r.benchmark_metrics["cognitive_score_delta_vs_g0"] = r.cognitive_score_delta
        r.benchmark_metrics["coherence_phi_delta_vs_g0"] = r.phi_delta
        r.benchmark_metrics["energy_efficiency_delta_vs_g0"] = r.energy_efficiency_delta

    verdict = compute_t37b_verdict(results, g0)

    gain_results = [r for r in results if getattr(r.profile, "brainstem_gain_controller_enabled", False)]
    best_gain = max(gain_results, key=lambda r: r.deep_region_net_gain) if gain_results else None
    worst_gain = min(gain_results, key=lambda r: r.deep_region_net_gain) if gain_results else None

    output = {
        "audit_id": f"t37b_{auditor._seed}",
        "verdict": verdict,
        "baseline_t36": {
            "name": g0.profile.name if g0 else None,
            "cognitive_score": g0_cognitive,
            "phi": g0_phi,
            "energy_efficiency": g0_energy,
            "net_gain": g0_net_gain,
        },
        "profiles": [
            {
                "name": r.profile.name,
                "gain_enabled": getattr(r.profile, "brainstem_gain_controller_enabled", False),
                "cognitive_score": r.cognitive_score,
                "phi": r.phi,
                "energy_efficiency": r.energy_efficiency,
                "functional_improvement": r.functional_improvement,
                "brainstem_state": r.benchmark_metrics.get("brainstem_state", "n/a") if isinstance(r.benchmark_metrics, dict) else "n/a",
                "brainstem_decisions_count": r.benchmark_metrics.get("brainstem_decisions_count", 0) if isinstance(r.benchmark_metrics, dict) else 0,
                "brainstem_energy_modulation": r.benchmark_metrics.get("brainstem_energy_modulation", 1.0) if isinstance(r.benchmark_metrics, dict) else 1.0,
                "brainstem_routing_modulation": r.benchmark_metrics.get("brainstem_routing_modulation", 1.0) if isinstance(r.benchmark_metrics, dict) else 1.0,
                "brainstem_plasticity_modulation": r.benchmark_metrics.get("brainstem_plasticity_modulation", 1.0) if isinstance(r.benchmark_metrics, dict) else 1.0,
                "brainstem_decay_modulation": r.benchmark_metrics.get("brainstem_decay_modulation", 1.0) if isinstance(r.benchmark_metrics, dict) else 1.0,
                "brainstem_homeostatic_gain": r.benchmark_metrics.get("brainstem_homeostatic_gain", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "brainstem_gain_reward": r.benchmark_metrics.get("brainstem_gain_reward", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "global_brainstem_gain": r.benchmark_metrics.get("global_brainstem_gain", 1.0) if isinstance(r.benchmark_metrics, dict) else 1.0,
                "routing_gain": r.benchmark_metrics.get("routing_gain", 1.0) if isinstance(r.benchmark_metrics, dict) else 1.0,
                "plasticity_gain": r.benchmark_metrics.get("plasticity_gain", 1.0) if isinstance(r.benchmark_metrics, dict) else 1.0,
                "decay_gain": r.benchmark_metrics.get("decay_gain", 1.0) if isinstance(r.benchmark_metrics, dict) else 1.0,
                "energy_recovery_gain": r.benchmark_metrics.get("energy_recovery_gain", 1.0) if isinstance(r.benchmark_metrics, dict) else 1.0,
                "emergency_gain": r.benchmark_metrics.get("emergency_gain", 1.0) if isinstance(r.benchmark_metrics, dict) else 1.0,
                "cognitive_preservation_gain": r.benchmark_metrics.get("cognitive_preservation_gain", 1.0) if isinstance(r.benchmark_metrics, dict) else 1.0,
                "gain_adjustments_count": r.benchmark_metrics.get("gain_adjustments_count", 0) if isinstance(r.benchmark_metrics, dict) else 0,
                "over_suppression_detected": r.benchmark_metrics.get("over_suppression_detected", False) if isinstance(r.benchmark_metrics, dict) else False,
                "useful_stabilization_detected": r.benchmark_metrics.get("useful_stabilization_detected", False) if isinstance(r.benchmark_metrics, dict) else False,
                "true_instability_detected": r.benchmark_metrics.get("true_instability_detected", False) if isinstance(r.benchmark_metrics, dict) else False,
                "gain_stability_score": r.benchmark_metrics.get("gain_stability_score", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "net_gain": r.deep_region_net_gain,
                "net_gain_vs_g0": r.benchmark_metrics.get("net_gain_vs_g0", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "cognitive_score_delta_vs_g0": r.benchmark_metrics.get("cognitive_score_delta_vs_g0", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "coherence_phi_delta_vs_g0": r.benchmark_metrics.get("coherence_phi_delta_vs_g0", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "energy_efficiency_delta_vs_g0": r.benchmark_metrics.get("energy_efficiency_delta_vs_g0", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "passed": r.passed,
            }
            for r in results
        ],
        "best_gain_profile": best_gain.profile.name if best_gain else None,
        "worst_gain_profile": worst_gain.profile.name if worst_gain else None,
        "recommendation_t38": _recommendation_for_verdict(verdict),
    }

    import datetime
    from pathlib import Path
    report_dir = Path("reports/brainstem_gain")
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = report_dir / f"t37b_brainstem_gain_audit_{ts}.json"
    json_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    md_lines = [
        "# T37B — Adaptive Brainstem Gain Audit",
        "",
        f"**Audit ID:** {output['audit_id']}",
        f"**Verdict:** {verdict}",
        f"**Best Gain Profile:** {output['best_gain_profile'] or 'N/A'}",
        f"**Worst Gain Profile:** {output['worst_gain_profile'] or 'N/A'}",
        f"**T38 Recommendation:** {output['recommendation_t38']}",
        "",
        "## Baseline T36 (brainstem enabled, no gain controller)",
        f"- Cognitive score: {g0_cognitive:.4f}",
        f"- Coherence Phi: {g0_phi:.4f}",
        f"- Energy efficiency: {g0_energy:.4f}",
        f"- Net gain: {g0_net_gain:.4f}",
        "",
        "## Profiles",
        "",
        "| Profile | Gain | Cognitive | Phi | Energy | BS State | BS Decisions | BS Gain | Gain Reward | Adjustments | OverSup | Net Gain | vs T36 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for pr in output["profiles"]:
        md_lines.append(
            f"| {pr['name']} | {pr['gain_enabled']} | {pr['cognitive_score']:.4f} | {pr['phi']:.4f} | "
            f"{pr['energy_efficiency']:.4f} | {pr['brainstem_state']} | {pr['brainstem_decisions_count']} | "
            f"{pr['global_brainstem_gain']:.2f} | {pr['brainstem_gain_reward']:.4f} | {pr['gain_adjustments_count']} | "
            f"{pr['over_suppression_detected']} | {pr['net_gain']:.4f} | {pr['net_gain_vs_g0']:+.4f} |"
        )

    md_lines.extend([
        "",
        "---",
        "*Generated by T37B Adaptive Brainstem Gain Audit*",
    ])

    md_path = report_dir / f"t37b_brainstem_gain_audit_{ts}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"MD: {md_path}")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
