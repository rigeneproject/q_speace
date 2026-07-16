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
    """Build T39B profiles with gain controller enabled and differentiated presets."""
    base = {
        "deep_regions_enabled": True,
        "inter_region_plasticity_enabled": True,
        "region_signal_routing_enabled": True,
        "region_stability_controller_enabled": True,
        "deep_region_routing_calibrator_enabled": True,
        "brainstem_controller_enabled": True,
        "brainstem_gain_controller_enabled": True,
        "trigger_mode": "hybrid",
        "t34_profile_id": "p3",
    }
    return [
        DeepRegionAuditProfile(
            profile_id="c0",
            name="baseline_t38_no_coupling_baseline",
            brainstem_gain_profile="balanced",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="c1",
            name="coupling_balanced",
            brainstem_gain_profile="balanced",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="c2",
            name="coupling_cognitive_preserving",
            brainstem_gain_profile="cognitive_preserving",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="c3",
            name="coupling_low_suppression",
            brainstem_gain_profile="low_suppression",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="c4",
            name="coupling_phi_preserving",
            brainstem_gain_profile="phi_preserving",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="c5",
            name="coupling_exploratory",
            brainstem_gain_profile="exploratory",
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
    gain_profile = extra.get("brainstem_gain_profile", None)
    if gain_enabled and gain_profile and orch._brainstem_gain_controller is not None:
        orch._brainstem_gain_controller.apply_preset(gain_profile)


def compute_t39b_verdict(results: List[Any], baseline: Any) -> str:
    c0 = next((r for r in results if r.profile.profile_id == "c0"), None)
    if c0 is None:
        return "INSUFFICIENT_EVIDENCE"

    c0_net_gain = c0.deep_region_net_gain
    c0_cognitive = c0.cognitive_score
    c0_phi = c0.phi
    c0_energy = c0.energy_efficiency
    c0_suppression = c0.benchmark_metrics.get("suppression_cost", 0.0) if isinstance(c0.benchmark_metrics, dict) else 0.0

    coupling_results = [r for r in results if getattr(r.profile, "brainstem_gain_controller_enabled", False)]
    if not coupling_results:
        return "INSUFFICIENT_EVIDENCE"

    best = max(coupling_results, key=lambda r: r.deep_region_net_gain)
    net_gain_vs_c0 = best.deep_region_net_gain - c0_net_gain
    cog_delta = best.cognitive_score - c0_cognitive
    phi_delta = best.phi - c0_phi
    en_delta = best.energy_efficiency - c0_energy
    bm = best.benchmark_metrics
    coupling_strength = bm.get("gain_input_coupling_strength", 0.0) if isinstance(bm, dict) else 0.0
    escape_count = bm.get("protective_escape_count", 0) if isinstance(bm, dict) else 0
    adjusted_vitality = bm.get("adjusted_cognitive_vitality_score", 0.0) if isinstance(bm, dict) else 0.0
    adjusted_risk = bm.get("adjusted_autonomic_risk_score", 0.0) if isinstance(bm, dict) else 0.0
    transitions = bm.get("brainstem_state_transition_count", 0) if isinstance(bm, dict) else 0

    # Regression checks
    if cog_delta < -0.05:
        return "COUPLING_COGNITIVE_REGRESSION"
    if en_delta < -0.05:
        return "COUPLING_ENERGY_REGRESSION"
    if phi_delta < -0.05:
        return "COUPLING_PHI_REGRESSION"

    # Effective coupling
    if net_gain_vs_c0 >= 0.02 and coupling_strength > 0 and transitions > 0:
        return "COUPLING_EFFECTIVE"

    # Partial
    if net_gain_vs_c0 >= 0.005 and coupling_strength > 0:
        return "COUPLING_PARTIAL"

    # Neutral
    if abs(net_gain_vs_c0) <= 0.005 and coupling_strength > 0:
        return "COUPLING_NEUTRAL"

    if escape_count > 0:
        return "COUPLING_WEAK"

    return "COUPLING_NO_EFFECT"


def _recommendation_for_verdict(verdict: str) -> str:
    mapping = {
        "COUPLING_EFFECTIVE": "T40 — Autonomic Plasticity Layer",
        "COUPLING_PARTIAL": "T40 — Adaptive Gain Relaxation",
        "COUPLING_NEUTRAL": "T39B v2 — Deeper Coupling Redesign",
        "COUPLING_WEAK": "T39B v2 — Threshold Tuning",
        "COUPLING_COGNITIVE_REGRESSION": "T39 Fix — Cognitive Preservation v2",
        "COUPLING_ENERGY_REGRESSION": "T39 Fix — Metabolic Arbitration v2",
        "COUPLING_PHI_REGRESSION": "T39 Fix — Phi-Oriented Stability v2",
        "COUPLING_NO_EFFECT": "T39 Fix — Coupling Signal Amplification",
        "INSUFFICIENT_EVIDENCE": "T39 Fix — Benchmark Perturbation Redesign",
    }
    return mapping.get(verdict, "T39 Next Step Undefined")


async def main():
    profiles = make_profiles()
    auditor = DeepRegionAuditor(n_adaptive_cycles=5, report_dir="reports/brainstem_gain_coupling")

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

    # Compute deltas vs c0 baseline
    c0 = next((r for r in results if r.profile.profile_id == "c0"), None)
    c0_net_gain = c0.deep_region_net_gain if c0 else 0.0
    c0_cognitive = c0.cognitive_score if c0 else 0.0
    c0_phi = c0.phi if c0 else 0.0
    c0_energy = c0.energy_efficiency if c0 else 0.0
    c0_suppression = c0.benchmark_metrics.get("suppression_cost", 0.0) if c0 and isinstance(c0.benchmark_metrics, dict) else 0.0

    for r in results:
        r.cognitive_score_delta = r.cognitive_score - c0_cognitive
        r.phi_delta = r.phi - c0_phi
        r.energy_efficiency_delta = r.energy_efficiency - c0_energy
        r.functional_improvement_delta = r.functional_improvement - c0.functional_improvement if c0 else 0.0
        r.pathway_utility_delta = r.mean_pathway_utility - c0.mean_pathway_utility if c0 else 0.0
        r.deep_region_net_gain = DeepRegionAuditor.compute_deep_region_net_gain(r, c0)
        r.benchmark_metrics["net_gain_vs_c0"] = r.deep_region_net_gain - c0_net_gain
        r.benchmark_metrics["cognitive_score_delta_vs_c0"] = r.cognitive_score_delta
        r.benchmark_metrics["coherence_phi_delta_vs_c0"] = r.phi_delta
        r.benchmark_metrics["energy_efficiency_delta_vs_c0"] = r.energy_efficiency_delta

    verdict = compute_t39b_verdict(results, c0)

    coupling_results = [r for r in results if getattr(r.profile, "brainstem_gain_controller_enabled", False)]
    best_coupling = max(coupling_results, key=lambda r: r.deep_region_net_gain) if coupling_results else None
    worst_coupling = min(coupling_results, key=lambda r: r.deep_region_net_gain) if coupling_results else None

    output = {
        "audit_id": f"t39b_{auditor._seed}",
        "verdict": verdict,
        "baseline_t38": {
            "name": c0.profile.name if c0 else None,
            "cognitive_score": c0_cognitive,
            "phi": c0_phi,
            "energy_efficiency": c0_energy,
            "net_gain": c0_net_gain,
            "suppression_cost": c0_suppression,
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
                "gain_input_coupling_strength": r.benchmark_metrics.get("gain_input_coupling_strength", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "adjusted_cognitive_vitality_score": r.benchmark_metrics.get("adjusted_cognitive_vitality_score", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "adjusted_autonomic_risk_score": r.benchmark_metrics.get("adjusted_autonomic_risk_score", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "adjusted_balance_pressure": r.benchmark_metrics.get("adjusted_balance_pressure", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "protective_escape_count": r.benchmark_metrics.get("protective_escape_count", 0) if isinstance(r.benchmark_metrics, dict) else 0,
                "protective_state_ratio": r.benchmark_metrics.get("protective_state_ratio", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "corrective_state_ratio": r.benchmark_metrics.get("corrective_state_ratio", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "emergency_state_ratio": r.benchmark_metrics.get("emergency_state_ratio", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "coupling_delta_mean": r.benchmark_metrics.get("coupling_delta_mean", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "suppression_cost_after_coupling": r.benchmark_metrics.get("suppression_cost_after_coupling", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "brainstem_state_transition_count": r.benchmark_metrics.get("brainstem_state_transition_count", 0) if isinstance(r.benchmark_metrics, dict) else 0,
                "net_gain": r.deep_region_net_gain,
                "net_gain_vs_c0": r.benchmark_metrics.get("net_gain_vs_c0", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "cognitive_score_delta_vs_c0": r.benchmark_metrics.get("cognitive_score_delta_vs_c0", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "coherence_phi_delta_vs_c0": r.benchmark_metrics.get("coherence_phi_delta_vs_c0", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "energy_efficiency_delta_vs_c0": r.benchmark_metrics.get("energy_efficiency_delta_vs_c0", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "passed": r.passed,
            }
            for r in results
        ],
        "best_coupling_profile": best_coupling.profile.name if best_coupling else None,
        "worst_coupling_profile": worst_coupling.profile.name if worst_coupling else None,
        "recommendation_t40": _recommendation_for_verdict(verdict),
    }

    import datetime
    from pathlib import Path
    report_dir = Path("reports/brainstem_gain_coupling")
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = report_dir / f"t39b_gain_input_coupling_audit_{ts}.json"
    json_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    md_lines = [
        "# T39B — Gain Input Coupling Audit",
        "",
        f"**Audit ID:** {output['audit_id']}",
        f"**Verdict:** {verdict}",
        f"**Best Coupling Profile:** {output['best_coupling_profile'] or 'N/A'}",
        f"**Worst Coupling Profile:** {output['worst_coupling_profile'] or 'N/A'}",
        f"**T40 Recommendation:** {output['recommendation_t40']}",
        "",
        "## Baseline T38 (gain enabled, balanced)",
        f"- Cognitive score: {c0_cognitive:.4f}",
        f"- Coherence Phi: {c0_phi:.4f}",
        f"- Energy efficiency: {c0_energy:.4f}",
        f"- Net gain: {c0_net_gain:.4f}",
        f"- Suppression cost: {c0_suppression:.4f}",
        "",
        "## Profiles",
        "",
        "| Profile | Gain | Preset | Cognitive | Phi | Energy | Coupling | Adj Vitality | Adj Risk | Escape | Transitions | Suppression | Net Gain | vs T38 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for pr in output["profiles"]:
        md_lines.append(
            f"| {pr['name']} | {pr['gain_enabled']} | {pr['gain_profile']} | {pr['cognitive_score']:.4f} | {pr['phi']:.4f} | "
            f"{pr['energy_efficiency']:.4f} | {pr['gain_input_coupling_strength']:.4f} | "
            f"{pr['adjusted_cognitive_vitality_score']:.4f} | {pr['adjusted_autonomic_risk_score']:.4f} | "
            f"{pr['protective_escape_count']} | {pr['brainstem_state_transition_count']} | "
            f"{pr['suppression_cost_after_coupling']:.4f} | {pr['net_gain']:.4f} | {pr['net_gain_vs_c0']:+.4f} |"
        )

    md_lines.extend([
        "",
        "---",
        "*Generated by T39B Gain Input Coupling Audit*",
    ])

    md_path = report_dir / f"t39b_gain_input_coupling_audit_{ts}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"MD: {md_path}")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
