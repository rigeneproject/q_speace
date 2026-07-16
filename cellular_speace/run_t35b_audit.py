import asyncio
import json
from typing import Any, Dict, List, Optional

from speace_core.cellular_brain.analysis.deep_region_audit import (
    DeepRegionAuditor,
    DeepRegionAuditProfile,
)
from speace_core.cellular_brain.regions.brainstem_controller import BrainstemFunctionalController
from speace_core.cellular_brain.regions.deep_region_routing_calibrator import (
    DeepRegionRoutingCalibrator,
    DeepRegionRoutingProfile,
)


def make_profiles() -> List[DeepRegionAuditProfile]:
    """Build T35B profiles comparing brainstem configurations."""
    base = {
        "deep_regions_enabled": True,
        "inter_region_plasticity_enabled": True,
        "region_signal_routing_enabled": True,
        "region_stability_controller_enabled": True,
        "deep_region_routing_calibrator_enabled": True,
        "trigger_mode": "hybrid",
    }
    return [
        DeepRegionAuditProfile(
            profile_id="b0",
            name="baseline_t34b_medium_no_brainstem",
            brainstem_controller_enabled=False,
            t34_profile_id="p3",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="b1",
            name="brainstem_enabled_default",
            brainstem_controller_enabled=True,
            t34_profile_id="p3",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="b2",
            name="brainstem_watchful_sensitive",
            brainstem_controller_enabled=True,
            brainstem_instability_threshold_watchful=0.10,
            brainstem_phi_threshold_watchful=0.22,
            t34_profile_id="p3",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="b3",
            name="brainstem_corrective_sensitive",
            brainstem_controller_enabled=True,
            brainstem_instability_threshold_corrective=0.20,
            brainstem_phi_threshold_corrective=0.18,
            t34_profile_id="p3",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="b4",
            name="brainstem_protective_fast",
            brainstem_controller_enabled=True,
            brainstem_instability_threshold_protective=0.35,
            brainstem_phi_threshold_protective=0.12,
            t34_profile_id="p3",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="b5",
            name="brainstem_energy_priority",
            brainstem_controller_enabled=True,
            brainstem_energy_threshold_emergency=0.25,
            t34_profile_id="p3",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="b6",
            name="brainstem_phi_priority",
            brainstem_controller_enabled=True,
            brainstem_phi_threshold_stable=0.30,
            brainstem_phi_threshold_watchful=0.25,
            brainstem_phi_threshold_corrective=0.20,
            brainstem_phi_threshold_protective=0.15,
            t34_profile_id="p3",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="b7",
            name="brainstem_balanced_homeostasis",
            brainstem_controller_enabled=True,
            brainstem_instability_threshold_watchful=0.12,
            brainstem_instability_threshold_corrective=0.25,
            brainstem_instability_threshold_protective=0.40,
            brainstem_instability_threshold_emergency=0.65,
            brainstem_energy_threshold_emergency=0.20,
            t34_profile_id="p3",
            **base,
        ),
        DeepRegionAuditProfile(
            profile_id="b8",
            name="brainstem_emergency_guard",
            brainstem_controller_enabled=True,
            brainstem_instability_threshold_emergency=0.50,
            brainstem_energy_threshold_emergency=0.30,
            t34_profile_id="p3",
            **base,
        ),
    ]


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
    if enabled:
        orch.model_post_init(None)  # Re-init to pick up brainstem controller
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


def compute_t35b_verdict(results: List[Any], baseline: Any) -> str:
    b0 = next((r for r in results if r.profile.profile_id == "b0"), None)
    if b0 is None:
        return "INSUFFICIENT_EVIDENCE"

    b0_net_gain = b0.deep_region_net_gain
    b0_cognitive = b0.cognitive_score
    b0_phi = b0.phi
    b0_energy = b0.energy_efficiency

    brainstem_results = [r for r in results if getattr(r.profile, "brainstem_controller_enabled", False)]
    if not brainstem_results:
        return "INSUFFICIENT_EVIDENCE"

    best = None
    best_gain = -999.0

    for r in brainstem_results:
        net_gain_vs_t34b = r.deep_region_net_gain - b0_net_gain
        if net_gain_vs_t34b > best_gain:
            best_gain = net_gain_vs_t34b
            best = r

    if best is None:
        return "INSUFFICIENT_EVIDENCE"

    net_gain_vs_t34b = best.deep_region_net_gain - b0_net_gain
    cog_delta = best.cognitive_score - b0_cognitive
    phi_delta = best.phi - b0_phi
    en_delta = best.energy_efficiency - b0_energy
    bm = best.benchmark_metrics
    brainstem_decisions = bm.get("brainstem_decisions_count", 0) if isinstance(bm, dict) else 0
    brainstem_homeostatic_gain = bm.get("brainstem_homeostatic_gain", 0.0) if isinstance(bm, dict) else 0.0
    brainstem_phi_recovery = bm.get("brainstem_phi_recovery_contribution", 0.0) if isinstance(bm, dict) else 0.0

    # Regression checks
    if cog_delta < -0.05:
        return "BRAINSTEM_COGNITIVE_REGRESSION"
    if en_delta < -0.05:
        return "BRAINSTEM_ENERGY_REGRESSION"
    if phi_delta < -0.05:
        return "BRAINSTEM_PHI_REGRESSION"

    # Over-suppression
    if brainstem_decisions > 0 and best.functional_improvement < b0.functional_improvement - 0.05:
        return "BRAINSTEM_OVER_SUPPRESSION"

    # No effect
    if brainstem_decisions == 0:
        return "BRAINSTEM_NO_EFFECT"

    # Strong validation
    if net_gain_vs_t34b > 0.05 and brainstem_homeostatic_gain > 0 and brainstem_decisions > 0:
        return "BRAINSTEM_FUNCTIONAL_VALIDATED"

    # Partial gain
    if net_gain_vs_t34b > 0.02:
        return "BRAINSTEM_PARTIAL_GAIN"

    # Neutral
    if abs(net_gain_vs_t34b) <= 0.02:
        return "BRAINSTEM_NEUTRAL"

    return "BRAINSTEM_NO_EFFECT"


def _recommendation_for_verdict(verdict: str) -> str:
    mapping = {
        "BRAINSTEM_FUNCTIONAL_VALIDATED": "T36 Autonomic Homeostasis Layer",
        "BRAINSTEM_PARTIAL_GAIN": "T36 Brainstem Sensitivity Tuning",
        "BRAINSTEM_NEUTRAL": "T36 Brainstem Input Coupling Redesign",
        "BRAINSTEM_OVER_SUPPRESSION": "T36 Adaptive Brainstem Gain Controller",
        "BRAINSTEM_ENERGY_REGRESSION": "T36 Metabolic Arbitration Layer",
        "BRAINSTEM_PHI_REGRESSION": "T36 Phi-Oriented Stability Controller",
        "BRAINSTEM_COGNITIVE_REGRESSION": "T36 Cognitive/Autonomic Balance Tuning",
        "BRAINSTEM_NO_EFFECT": "T36 Brainstem Signal Coupling Fix",
        "INSUFFICIENT_EVIDENCE": "T36 Benchmark Perturbation Redesign",
    }
    return mapping.get(verdict, "T36 Next Step Undefined")


async def main():
    profiles = make_profiles()
    auditor = DeepRegionAuditor(n_adaptive_cycles=5, report_dir="reports/brainstem")

    results = []
    for p in profiles:
        orch = auditor.build_orchestrator(deep_regions_enabled=p.deep_regions_enabled)
        auditor.apply_homeostatic_baseline(orch)
        auditor.apply_profile(p, orch)
        apply_t34_profile(auditor, p, orch)
        apply_brainstem_config(p, orch)

        from speace_core.cellular_brain.benchmark.neurofunctional_benchmark import NeuroFunctionalBenchmark
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
            from speace_core.cellular_brain.analysis.deep_region_audit import DeepRegionAuditResult
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
        from speace_core.cellular_brain.analysis.deep_region_audit import DeepRegionAuditResult
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

    # Compute net_gain_vs_t34b for each brainstem profile
    b0 = next((r for r in results if r.profile.profile_id == "b0"), None)
    b0_net_gain = b0.deep_region_net_gain if b0 else 0.0
    b0_cognitive = b0.cognitive_score if b0 else 0.0
    b0_phi = b0.phi if b0 else 0.0
    b0_energy = b0.energy_efficiency if b0 else 0.0

    # Compute deltas vs baseline and net_gain for all results
    for r in results:
        r.cognitive_score_delta = r.cognitive_score - b0_cognitive
        r.phi_delta = r.phi - b0_phi
        r.energy_efficiency_delta = r.energy_efficiency - b0_energy
        r.functional_improvement_delta = r.functional_improvement - b0.functional_improvement if b0 else 0.0
        r.pathway_utility_delta = r.mean_pathway_utility - b0.mean_pathway_utility if b0 else 0.0
        r.deep_region_net_gain = DeepRegionAuditor.compute_deep_region_net_gain(r, b0)
        r.benchmark_metrics["net_gain_vs_t34b"] = r.deep_region_net_gain - b0_net_gain
        r.benchmark_metrics["cognitive_score_delta_vs_t34b"] = r.cognitive_score_delta
        r.benchmark_metrics["coherence_phi_delta_vs_t34b"] = r.phi_delta
        r.benchmark_metrics["energy_efficiency_delta_vs_t34b"] = r.energy_efficiency_delta

    verdict = compute_t35b_verdict(results, b0)

    brainstem_results = [r for r in results if getattr(r.profile, "brainstem_controller_enabled", False)]
    best_brainstem = max(brainstem_results, key=lambda r: r.deep_region_net_gain) if brainstem_results else None
    worst_brainstem = min(brainstem_results, key=lambda r: r.deep_region_net_gain) if brainstem_results else None

    # Build JSON output
    output = {
        "audit_id": f"t35b_{auditor._seed}",
        "verdict": verdict,
        "baseline_t34b": {
            "name": b0.profile.name if b0 else None,
            "cognitive_score": b0_cognitive,
            "phi": b0_phi,
            "energy_efficiency": b0_energy,
            "net_gain": b0_net_gain,
        },
        "profiles": [
            {
                "name": r.profile.name,
                "brainstem_enabled": getattr(r.profile, "brainstem_controller_enabled", False),
                "cognitive_score": r.cognitive_score,
                "phi": r.phi,
                "energy_efficiency": r.energy_efficiency,
                "functional_improvement": r.functional_improvement,
                "regional_signal_flow": r.benchmark_metrics.get("regional_signal_flow_score", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "deep_region_signal_flow": r.deep_region_signal_flow,
                "mean_deep_region_activation": r.benchmark_metrics.get("mean_deep_region_activation", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "region_instability_mean": r.benchmark_metrics.get("region_instability_mean", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "stability_actions_applied": r.benchmark_metrics.get("stability_actions_applied", 0) if isinstance(r.benchmark_metrics, dict) else 0,
                "routing_blocks_applied": r.benchmark_metrics.get("routing_blocks_applied", 0) if isinstance(r.benchmark_metrics, dict) else 0,
                "cooldowns_started": r.benchmark_metrics.get("cooldowns_started", 0) if isinstance(r.benchmark_metrics, dict) else 0,
                "brainstem_state": r.benchmark_metrics.get("brainstem_state", "n/a") if isinstance(r.benchmark_metrics, dict) else "n/a",
                "brainstem_decisions_count": r.benchmark_metrics.get("brainstem_decisions_count", 0) if isinstance(r.benchmark_metrics, dict) else 0,
                "brainstem_energy_modulation": r.benchmark_metrics.get("brainstem_energy_modulation", 1.0) if isinstance(r.benchmark_metrics, dict) else 1.0,
                "brainstem_routing_modulation": r.benchmark_metrics.get("brainstem_routing_modulation", 1.0) if isinstance(r.benchmark_metrics, dict) else 1.0,
                "brainstem_plasticity_modulation": r.benchmark_metrics.get("brainstem_plasticity_modulation", 1.0) if isinstance(r.benchmark_metrics, dict) else 1.0,
                "brainstem_decay_modulation": r.benchmark_metrics.get("brainstem_decay_modulation", 1.0) if isinstance(r.benchmark_metrics, dict) else 1.0,
                "brainstem_recovery_actions": r.benchmark_metrics.get("brainstem_recovery_actions", 0) if isinstance(r.benchmark_metrics, dict) else 0,
                "brainstem_emergency_count": r.benchmark_metrics.get("brainstem_emergency_count", 0) if isinstance(r.benchmark_metrics, dict) else 0,
                "brainstem_homeostatic_gain": r.benchmark_metrics.get("brainstem_homeostatic_gain", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "brainstem_phi_recovery_contribution": r.benchmark_metrics.get("brainstem_phi_recovery_contribution", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "net_gain": r.deep_region_net_gain,
                "net_gain_vs_t34b": r.benchmark_metrics.get("net_gain_vs_t34b", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "cognitive_score_delta_vs_t34b": r.benchmark_metrics.get("cognitive_score_delta_vs_t34b", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "coherence_phi_delta_vs_t34b": r.benchmark_metrics.get("coherence_phi_delta_vs_t34b", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "energy_efficiency_delta_vs_t34b": r.benchmark_metrics.get("energy_efficiency_delta_vs_t34b", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "passed": r.passed,
            }
            for r in results
        ],
        "best_brainstem_profile": best_brainstem.profile.name if best_brainstem else None,
        "worst_brainstem_profile": worst_brainstem.profile.name if worst_brainstem else None,
        "recommendation_t36": _recommendation_for_verdict(verdict),
    }

    # Write JSON report
    import datetime
    from pathlib import Path
    report_dir = Path("reports/brainstem")
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = report_dir / f"t35b_brainstem_audit_{ts}.json"
    json_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    # Write Markdown report
    md_lines = [
        "# T35B — Brainstem Functional Audit",
        "",
        f"**Audit ID:** {output['audit_id']}",
        f"**Verdict:** {verdict}",
        f"**Best Brainstem Profile:** {output['best_brainstem_profile'] or 'N/A'}",
        f"**Worst Brainstem Profile:** {output['worst_brainstem_profile'] or 'N/A'}",
        f"**T36 Recommendation:** {output['recommendation_t36']}",
        "",
        "## Baseline T34B (routing_v2_medium_with_stability, no brainstem)",
        f"- Cognitive score: {b0_cognitive:.4f}",
        f"- Coherence Phi: {b0_phi:.4f}",
        f"- Energy efficiency: {b0_energy:.4f}",
        f"- Net gain: {b0_net_gain:.4f}",
        "",
        "## Profiles",
        "",
        "| Profile | Brainstem | Cognitive | Phi | Energy | Deep Act | Instability | Actions | BS State | BS Decisions | BS Net Gain | vs T34B |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for p in output["profiles"]:
        md_lines.append(
            f"| {p['name']} | "
            f"{'Yes' if p['brainstem_enabled'] else 'No'} | "
            f"{p['cognitive_score']:.4f} | {p['phi']:.4f} | {p['energy_efficiency']:.4f} | "
            f"{p['mean_deep_region_activation']:.4f} | {p['region_instability_mean']:.4f} | "
            f"{p['stability_actions_applied']} | {p['brainstem_state']} | {p['brainstem_decisions_count']} | "
            f"{p['net_gain']:.4f} | {p['net_gain_vs_t34b']:+.4f} |"
        )

    md_lines.extend([
        "",
        "## Detailed Brainstem Profiles",
        "",
    ])
    for p in output["profiles"]:
        if not p["brainstem_enabled"]:
            continue
        md_lines.extend([
            f"### {p['name']}",
            f"- Cognitive: {p['cognitive_score']:.4f} (delta {p['cognitive_score_delta_vs_t34b']:+.4f})",
            f"- Phi: {p['phi']:.4f} (delta {p['coherence_phi_delta_vs_t34b']:+.4f})",
            f"- Energy: {p['energy_efficiency']:.4f} (delta {p['energy_efficiency_delta_vs_t34b']:+.4f})",
            f"- Deep activation mean: {p['mean_deep_region_activation']:.4f}",
            f"- Instability mean: {p['region_instability_mean']:.4f}",
            f"- Stability actions: {p['stability_actions_applied']}",
            f"- Brainstem state: {p['brainstem_state']}",
            f"- Brainstem decisions: {p['brainstem_decisions_count']}",
            f"- Brainstem energy modulation: {p['brainstem_energy_modulation']:.4f}",
            f"- Brainstem routing modulation: {p['brainstem_routing_modulation']:.4f}",
            f"- Brainstem plasticity modulation: {p['brainstem_plasticity_modulation']:.4f}",
            f"- Brainstem decay modulation: {p['brainstem_decay_modulation']:.4f}",
            f"- Brainstem recovery actions: {p['brainstem_recovery_actions']}",
            f"- Brainstem emergency count: {p['brainstem_emergency_count']}",
            f"- Brainstem homeostatic gain: {p['brainstem_homeostatic_gain']:.4f}",
            f"- Brainstem phi recovery: {p['brainstem_phi_recovery_contribution']:.4f}",
            f"- Net gain: {p['net_gain']:.4f}",
            f"- Net gain vs T34B: {p['net_gain_vs_t34b']:+.4f}",
            "",
        ])

    md_lines.extend([
        "---",
        "*Generated by T35B Brainstem Functional Audit*",
    ])
    md_path = report_dir / f"t35b_brainstem_audit_{ts}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"MD: {md_path}")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
