import asyncio
import json
from typing import Any, Dict, List, Optional

from speace_core.cellular_brain.analysis.deep_region_audit import (
    DeepRegionAuditor,
    DeepRegionAuditProfile,
    DeepRegionAuditResult,
)
from speace_core.cellular_brain.benchmark.neurofunctional_benchmark import NeuroFunctionalBenchmark
from speace_core.cellular_brain.regions.brainstem_gain_controller import (
    AdaptiveBrainstemGainController,
    GAIN_PROFILE_PRESETS,
)


def make_profiles() -> List[DeepRegionAuditProfile]:
    """Build T38B profiles with differentiated gain presets."""
    base = {
        "deep_regions_enabled": True,
        "inter_region_plasticity_enabled": True,
        "region_signal_routing_enabled": True,
        "region_stability_controller_enabled": True,
        "deep_region_routing_calibrator_enabled": True,
        "brainstem_controller_enabled": True,
        "trigger_mode": "hybrid",
        "t34_profile_id": "p3",
    }
    return [
        DeepRegionAuditProfile(
            profile_id="g0",
            name="baseline_t36_no_gain_controller",
            brainstem_gain_controller_enabled=False,
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="g1",
            name="gain_balanced",
            brainstem_gain_controller_enabled=True,
            brainstem_gain_profile="balanced",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="g2",
            name="gain_cognitive_preserving",
            brainstem_gain_controller_enabled=True,
            brainstem_gain_profile="cognitive_preserving",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="g3",
            name="gain_phi_preserving",
            brainstem_gain_controller_enabled=True,
            brainstem_gain_profile="phi_preserving",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="g4",
            name="gain_low_suppression",
            brainstem_gain_controller_enabled=True,
            brainstem_gain_profile="low_suppression",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="g5",
            name="gain_exploratory",
            brainstem_gain_controller_enabled=True,
            brainstem_gain_profile="exploratory",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="g6",
            name="gain_energy_preserving",
            brainstem_gain_controller_enabled=True,
            brainstem_gain_profile="energy_preserving",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="g7",
            name="gain_emergency_minimal",
            brainstem_gain_controller_enabled=True,
            brainstem_gain_profile="emergency_minimal",
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
    # T38: apply gain profile preset
    gain_profile = extra.get("brainstem_gain_profile", None)
    if gain_enabled and gain_profile and orch._brainstem_gain_controller is not None:
        orch._brainstem_gain_controller.apply_preset(gain_profile)


def compute_t38b_verdict(results: List[Any], baseline: Any) -> str:
    g0 = next((r for r in results if r.profile.profile_id == "g0"), None)
    if g0 is None:
        return "INSUFFICIENT_EVIDENCE"

    g0_net_gain = g0.deep_region_net_gain
    g0_cognitive = g0.cognitive_score
    g0_phi = g0.phi
    g0_energy = g0.energy_efficiency
    g0_suppression = g0.benchmark_metrics.get("suppression_cost", 0.0) if isinstance(g0.benchmark_metrics, dict) else 0.0

    gain_results = [r for r in results if getattr(r.profile, "brainstem_gain_controller_enabled", False)]
    if not gain_results:
        return "INSUFFICIENT_EVIDENCE"

    best = max(gain_results, key=lambda r: r.deep_region_net_gain)
    net_gain_vs_g0 = best.deep_region_net_gain - g0_net_gain
    cog_delta = best.cognitive_score - g0_cognitive
    phi_delta = best.phi - g0_phi
    en_delta = best.energy_efficiency - g0_energy
    bm = best.benchmark_metrics
    reward_v2 = bm.get("brainstem_gain_reward_v2", 0.0) if isinstance(bm, dict) else 0.0
    gain_adjustments = bm.get("gain_adjustments_count", 0) if isinstance(bm, dict) else 0
    over_sup = bm.get("over_suppression_detected", False) if isinstance(bm, dict) else False
    divergence = bm.get("gain_profile_divergence", 0.0) if isinstance(bm, dict) else 0.0
    suppression = bm.get("suppression_cost", 0.0) if isinstance(bm, dict) else 0.0
    suppression_reduced = suppression < g0_suppression

    # Compute cross-profile divergence
    vectors = []
    for r in gain_results:
        if isinstance(r.benchmark_metrics, dict):
            vectors.append({
                "routing_gain": r.benchmark_metrics.get("routing_gain", 1.0),
                "plasticity_gain": r.benchmark_metrics.get("plasticity_gain", 1.0),
                "decay_gain": r.benchmark_metrics.get("decay_gain", 1.0),
                "emergency_gain": r.benchmark_metrics.get("emergency_gain", 1.0),
                "cognitive_preservation_gain": r.benchmark_metrics.get("cognitive_preservation_gain", 1.0),
                "global_brainstem_gain": r.benchmark_metrics.get("global_brainstem_gain", 1.0),
            })
    cross_divergence = AdaptiveBrainstemGainController.compute_gain_profile_divergence(vectors) if len(vectors) >= 2 else 0.0

    # Regression checks
    if cog_delta < -0.05:
        return "GAIN_COGNITIVE_REGRESSION"
    if en_delta < -0.05:
        return "GAIN_ENERGY_REGRESSION"
    if phi_delta < -0.05:
        return "GAIN_PHI_REGRESSION"

    # Strong validation
    if net_gain_vs_g0 >= 0.02 and (reward_v2 >= 0 or suppression_reduced) and cross_divergence > 0.03:
        return "GAIN_VALIDATED"

    # Partial gain
    if net_gain_vs_g0 >= 0.005 and cross_divergence > 0.03:
        return "GAIN_PARTIAL_RECOVERY"

    if net_gain_vs_g0 >= 0.005:
        return "GAIN_PARTIAL_RECOVERY_NO_DIVERSITY"

    # Neutral
    if abs(net_gain_vs_g0) <= 0.005:
        return "GAIN_NEUTRAL"

    # Over suppression
    if over_sup:
        return "GAIN_OVER_SUPPRESSION_REMAINING"

    return "GAIN_NO_EFFECT"


def _recommendation_for_verdict(verdict: str) -> str:
    mapping = {
        "GAIN_VALIDATED": "T39 Autonomic Plasticity Layer",
        "GAIN_PARTIAL_RECOVERY": "T39 Gain Sensitivity Tuning v2",
        "GAIN_PARTIAL_RECOVERY_NO_DIVERSITY": "T39 Diversity Pressure Redesign",
        "GAIN_NEUTRAL": "T39 Gain Input Coupling Redesign",
        "GAIN_OVER_SUPPRESSION_REMAINING": "T39 Adaptive Gain Relaxation",
        "GAIN_COGNITIVE_REGRESSION": "T39 Cognitive/Autonomic Balance Tuning v2",
        "GAIN_ENERGY_REGRESSION": "T39 Metabolic Arbitration Layer v2",
        "GAIN_PHI_REGRESSION": "T39 Phi-Oriented Stability Controller v2",
        "GAIN_NO_EFFECT": "T39 Gain Signal Coupling Fix",
        "INSUFFICIENT_EVIDENCE": "T39 Benchmark Perturbation Redesign",
    }
    return mapping.get(verdict, "T39 Next Step Undefined")


async def main():
    profiles = make_profiles()
    auditor = DeepRegionAuditor(n_adaptive_cycles=5, report_dir="reports/brainstem_gain_tuning")

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
    g0_suppression = g0.benchmark_metrics.get("suppression_cost", 0.0) if g0 and isinstance(g0.benchmark_metrics, dict) else 0.0

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

    verdict = compute_t38b_verdict(results, g0)

    gain_results = [r for r in results if getattr(r.profile, "brainstem_gain_controller_enabled", False)]
    best_gain = max(gain_results, key=lambda r: r.deep_region_net_gain) if gain_results else None
    worst_gain = min(gain_results, key=lambda r: r.deep_region_net_gain) if gain_results else None

    # Compute cross-profile divergence
    vectors = []
    for r in gain_results:
        if isinstance(r.benchmark_metrics, dict):
            vectors.append({
                "routing_gain": r.benchmark_metrics.get("routing_gain", 1.0),
                "plasticity_gain": r.benchmark_metrics.get("plasticity_gain", 1.0),
                "decay_gain": r.benchmark_metrics.get("decay_gain", 1.0),
                "emergency_gain": r.benchmark_metrics.get("emergency_gain", 1.0),
                "cognitive_preservation_gain": r.benchmark_metrics.get("cognitive_preservation_gain", 1.0),
                "global_brainstem_gain": r.benchmark_metrics.get("global_brainstem_gain", 1.0),
            })
    cross_divergence = AdaptiveBrainstemGainController.compute_gain_profile_divergence(vectors) if len(vectors) >= 2 else 0.0

    output = {
        "audit_id": f"t38b_{auditor._seed}",
        "verdict": verdict,
        "baseline_t36": {
            "name": g0.profile.name if g0 else None,
            "cognitive_score": g0_cognitive,
            "phi": g0_phi,
            "energy_efficiency": g0_energy,
            "net_gain": g0_net_gain,
            "suppression_cost": g0_suppression,
        },
        "profiles": [
            {
                "name": r.profile.name,
                "gain_enabled": getattr(r.profile, "brainstem_gain_controller_enabled", False),
                "gain_profile": getattr(r.profile, "brainstem_gain_profile", None),
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
                "brainstem_gain_reward_v2": r.benchmark_metrics.get("brainstem_gain_reward_v2", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "global_brainstem_gain": r.benchmark_metrics.get("global_brainstem_gain", 1.0) if isinstance(r.benchmark_metrics, dict) else 1.0,
                "routing_gain": r.benchmark_metrics.get("routing_gain", 1.0) if isinstance(r.benchmark_metrics, dict) else 1.0,
                "plasticity_gain": r.benchmark_metrics.get("plasticity_gain", 1.0) if isinstance(r.benchmark_metrics, dict) else 1.0,
                "decay_gain": r.benchmark_metrics.get("decay_gain", 1.0) if isinstance(r.benchmark_metrics, dict) else 1.0,
                "energy_recovery_gain": r.benchmark_metrics.get("energy_recovery_gain", 1.0) if isinstance(r.benchmark_metrics, dict) else 1.0,
                "emergency_gain": r.benchmark_metrics.get("emergency_gain", 1.0) if isinstance(r.benchmark_metrics, dict) else 1.0,
                "cognitive_preservation_gain": r.benchmark_metrics.get("cognitive_preservation_gain", 1.0) if isinstance(r.benchmark_metrics, dict) else 1.0,
                "gain_adjustments_count": r.benchmark_metrics.get("gain_adjustments_count", 0) if isinstance(r.benchmark_metrics, dict) else 0,
                "adaptive_gain_learning_rate": r.benchmark_metrics.get("adaptive_gain_learning_rate", 0.05) if isinstance(r.benchmark_metrics, dict) else 0.05,
                "gain_profile_divergence": r.benchmark_metrics.get("gain_profile_divergence", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "gain_convergence_detected": r.benchmark_metrics.get("gain_convergence_detected", False) if isinstance(r.benchmark_metrics, dict) else False,
                "diversity_pressure_applied": r.benchmark_metrics.get("diversity_pressure_applied", False) if isinstance(r.benchmark_metrics, dict) else False,
                "suppression_cost": r.benchmark_metrics.get("suppression_cost", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "suppression_cost_reduction": r.benchmark_metrics.get("suppression_cost_reduction", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
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
        "cross_profile_divergence": cross_divergence,
        "recommendation_t39": _recommendation_for_verdict(verdict),
    }

    import datetime
    from pathlib import Path
    report_dir = Path("reports/brainstem_gain_tuning")
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = report_dir / f"t38b_gain_sensitivity_audit_{ts}.json"
    json_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    md_lines = [
        "# T38B — Gain Sensitivity Audit",
        "",
        f"**Audit ID:** {output['audit_id']}",
        f"**Verdict:** {verdict}",
        f"**Best Gain Profile:** {output['best_gain_profile'] or 'N/A'}",
        f"**Worst Gain Profile:** {output['worst_gain_profile'] or 'N/A'}",
        f"**Cross-Profile Divergence:** {cross_divergence:.4f}",
        f"**T39 Recommendation:** {output['recommendation_t39']}",
        "",
        "## Baseline T36 (brainstem enabled, no gain controller)",
        f"- Cognitive score: {g0_cognitive:.4f}",
        f"- Coherence Phi: {g0_phi:.4f}",
        f"- Energy efficiency: {g0_energy:.4f}",
        f"- Net gain: {g0_net_gain:.4f}",
        f"- Suppression cost: {g0_suppression:.4f}",
        "",
        "## Profiles",
        "",
        "| Profile | Gain | Preset | Cognitive | Phi | Energy | BS State | BS Decisions | BS Gain | Reward v2 | Adjustments | Suppression | Net Gain | vs T36 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for pr in output["profiles"]:
        md_lines.append(
            f"| {pr['name']} | {pr['gain_enabled']} | {pr['gain_profile']} | {pr['cognitive_score']:.4f} | {pr['phi']:.4f} | "
            f"{pr['energy_efficiency']:.4f} | {pr['brainstem_state']} | {pr['brainstem_decisions_count']} | "
            f"{pr['global_brainstem_gain']:.2f} | {pr['brainstem_gain_reward_v2']:.4f} | {pr['gain_adjustments_count']} | "
            f"{pr['suppression_cost']:.4f} | {pr['net_gain']:.4f} | {pr['net_gain_vs_g0']:+.4f} |"
        )

    md_lines.extend([
        "",
        "---",
        "*Generated by T38B Gain Sensitivity Audit*",
    ])

    md_path = report_dir / f"t38b_gain_sensitivity_audit_{ts}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"MD: {md_path}")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
