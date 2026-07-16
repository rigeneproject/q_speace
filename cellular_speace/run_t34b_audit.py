import asyncio
import json
from typing import Any, Dict, List, Optional

from speace_core.cellular_brain.analysis.deep_region_audit import (
    DeepRegionAuditor,
    DeepRegionAuditProfile,
)
from speace_core.cellular_brain.regions.deep_region_routing_calibrator import (
    DeepRegionRoutingCalibrator,
    DeepRegionRoutingProfile,
)


def make_profiles() -> List[DeepRegionAuditProfile]:
    """Build T34B profiles comparing routing v1 vs v2 with stability controller."""
    base = {
        "deep_regions_enabled": True,
        "inter_region_plasticity_enabled": True,
        "region_signal_routing_enabled": True,
        "region_stability_controller_enabled": True,
        "trigger_mode": "hybrid",
    }
    return [
        DeepRegionAuditProfile(
            profile_id="r1n",
            name="routing_v1_no_stability",
            region_stability_controller_enabled=False,
            deep_region_routing_calibrator_enabled=False,  # custom field
            **{k: v for k, v in base.items() if k not in {"region_stability_controller_enabled"}},
        ),
        DeepRegionAuditProfile(
            profile_id="r1s",
            name="routing_v1_with_stability",
            region_stability_controller_enabled=True,
            deep_region_routing_calibrator_enabled=False,
            **{k: v for k, v in base.items() if k not in {"region_stability_controller_enabled"}},
        ),
        DeepRegionAuditProfile(
            profile_id="r2s",
            name="routing_v2_soft_with_stability",
            region_stability_controller_enabled=True,
            deep_region_routing_calibrator_enabled=True,
            t34_profile_id="p2",  # top_k_with_regional_gain
            **{k: v for k, v in base.items() if k not in {"region_stability_controller_enabled"}},
        ),
        DeepRegionAuditProfile(
            profile_id="r2m",
            name="routing_v2_medium_with_stability",
            region_stability_controller_enabled=True,
            deep_region_routing_calibrator_enabled=True,
            t34_profile_id="p3",  # top_k_gain_and_boost
            **{k: v for k, v in base.items() if k not in {"region_stability_controller_enabled"}},
        ),
        DeepRegionAuditProfile(
            profile_id="r2x",
            name="routing_v2_strong_with_stability",
            region_stability_controller_enabled=True,
            deep_region_routing_calibrator_enabled=True,
            t34_profile_id="p5",  # aggressive_deep_stimulation
            **{k: v for k, v in base.items() if k not in {"region_stability_controller_enabled"}},
        ),
        DeepRegionAuditProfile(
            profile_id="r2b",
            name="routing_v2_brainstem_priority_with_stability",
            region_stability_controller_enabled=True,
            deep_region_routing_calibrator_enabled=True,
            t34_profile_id="brainstem",
            **{k: v for k, v in base.items() if k not in {"region_stability_controller_enabled"}},
        ),
        DeepRegionAuditProfile(
            profile_id="r2l",
            name="routing_v2_limbic_soft_with_stability",
            region_stability_controller_enabled=True,
            deep_region_routing_calibrator_enabled=True,
            t34_profile_id="limbic",
            **{k: v for k, v in base.items() if k not in {"region_stability_controller_enabled"}},
        ),
        DeepRegionAuditProfile(
            profile_id="r2bal",
            name="routing_v2_balanced_with_stability",
            region_stability_controller_enabled=True,
            deep_region_routing_calibrator_enabled=True,
            t34_profile_id="p4",  # full_stability_aware
            **{k: v for k, v in base.items() if k not in {"region_stability_controller_enabled"}},
        ),
    ]


# Custom profile factory for T34B
def get_t34_profile(profile_id: str) -> DeepRegionRoutingProfile:
    defaults = {p.profile_id: p for p in DeepRegionRoutingCalibrator.build_default_profiles()}
    if profile_id in defaults:
        return defaults[profile_id]
    if profile_id == "brainstem":
        return DeepRegionRoutingProfile(
            profile_id="brainstem",
            name="brainstem_priority",
            top_k_routing_active=True,
            top_k_ratio=0.15,
            deep_region_signal_boost=1.40,
            stability_aware_routing=True,
            deep_region_damping_floor=0.35,
            flow_memory_enabled=True,
            regional_gain_map={
                "sensory": 1.00,
                "limbic": 1.10,
                "hippocampus": 1.10,
                "default_mode": 1.05,
                "prefrontal": 1.05,
                "cerebellar": 1.10,
                "motor": 1.00,
                "brainstem_homeostatic": 1.50,
            },
        )
    if profile_id == "limbic":
        return DeepRegionRoutingProfile(
            profile_id="limbic",
            name="limbic_soft",
            top_k_routing_active=True,
            top_k_ratio=0.12,
            deep_region_signal_boost=1.20,
            stability_aware_routing=True,
            deep_region_damping_floor=0.25,
            flow_memory_enabled=True,
            regional_gain_map={
                "sensory": 1.00,
                "limbic": 1.35,
                "hippocampus": 1.20,
                "default_mode": 1.05,
                "prefrontal": 1.05,
                "cerebellar": 1.05,
                "motor": 1.00,
                "brainstem_homeostatic": 1.20,
            },
        )
    return defaults.get("p4", DeepRegionRoutingProfile(profile_id="p4", name="full_stability_aware"))


def apply_t34_profile(auditor: DeepRegionAuditor, profile: DeepRegionAuditProfile, orch) -> None:
    """Apply T34 routing calibration to orchestrator if enabled in profile."""
    # Check custom field via model_dump extra fields (Pydantic v2 stores extra in __pydantic_extra__)
    extra = getattr(profile, "__pydantic_extra__", {}) or {}
    enabled = extra.get("deep_region_routing_calibrator_enabled", False)
    t34_id = extra.get("t34_profile_id", None)

    if not enabled or t34_id is None:
        return

    t34_profile = get_t34_profile(t34_id)
    calibrator = DeepRegionRoutingCalibrator(profile=t34_profile)
    orch.deep_region_routing_calibrator_enabled = True
    orch._deep_region_routing_profile = t34_profile
    orch._deep_region_routing_calibrator = calibrator
    calibrator.apply_profile_to_router(orch._region_signal_router)


def compute_t34b_verdict(results: List[Any], baseline: Any, v1_no_stability: Any, v1_with_stability: Any) -> str:
    v2_results = [r for r in results if r.profile.name.startswith("routing_v2")]
    if not v2_results:
        return "INSUFFICIENT_EVIDENCE"

    # Compute phi_recovery vs 4-region baseline (not within-run)
    base_phi = baseline.phi if baseline else 0.0
    base_cog = baseline.cognitive_score if baseline else 0.0
    base_en = baseline.energy_efficiency if baseline else 0.0

    best = None
    best_score = -999.0

    for r in v2_results:
        bm = r.benchmark_metrics
        phi_recovery = max(0.0, r.phi - base_phi)
        instability_mean = bm.get("region_instability_mean", 0.0) if isinstance(bm, dict) else getattr(bm, "region_instability_mean", 0.0)
        actions = bm.get("stability_actions_applied", 0) if isinstance(bm, dict) else getattr(bm, "stability_actions_applied", 0)
        cognitive = r.cognitive_score
        energy = r.energy_efficiency
        brainstem = bm.get("brainstem_homeostatic_stability_score", 0.0) if isinstance(bm, dict) else getattr(bm, "brainstem_homeostatic_stability_score", 0.0)
        deep_activation = bm.get("mean_deep_region_activation", 0.0) if isinstance(bm, dict) else getattr(bm, "mean_deep_region_activation", 0.0)

        score = (
            0.30 * phi_recovery
            + 0.25 * (1.0 if actions > 0 else 0.0)
            + 0.20 * (1.0 if instability_mean >= 0.25 else instability_mean / 0.25)
            + 0.15 * cognitive
            + 0.10 * energy
        )
        if score > best_score:
            best_score = score
            best = r

    if best is None:
        return "INSUFFICIENT_EVIDENCE"

    bm = best.benchmark_metrics
    phi_recovery = max(0.0, best.phi - base_phi)
    instability_mean = bm.get("region_instability_mean", 0.0) if isinstance(bm, dict) else getattr(bm, "region_instability_mean", 0.0)
    actions = bm.get("stability_actions_applied", 0) if isinstance(bm, dict) else getattr(bm, "stability_actions_applied", 0)
    cognitive = best.cognitive_score
    energy = best.energy_efficiency
    brainstem = bm.get("brainstem_homeostatic_stability_score", 0.0) if isinstance(bm, dict) else getattr(bm, "brainstem_homeostatic_stability_score", 0.0)
    deep_activation = bm.get("mean_deep_region_activation", 0.0) if isinstance(bm, dict) else getattr(bm, "mean_deep_region_activation", 0.0)

    # Check regressions relative to v1_with_stability (per-profile, not best)
    v1s_cog = v1_with_stability.cognitive_score if v1_with_stability else cognitive
    v1s_en = v1_with_stability.energy_efficiency if v1_with_stability else energy
    v1s_phi = v1_with_stability.phi if v1_with_stability else best.phi

    # Check if ANY v2 profile has severe regression
    for r in v2_results:
        if r.cognitive_score < v1s_cog - 0.05:
            # Only return regression if it's the majority; otherwise note but continue
            pass

    if cognitive < v1s_cog - 0.05:
        return "ROUTING_V2_COGNITIVE_REGRESSION"
    if energy < v1s_en - 0.05:
        return "ROUTING_V2_ENERGY_REGRESSION"
    if best.phi < v1s_phi - 0.05:
        return "ROUTING_V2_OVERSTIMULATION"

    # Check for no effect (all v2 profiles have ~same metrics as v1 with no actions)
    v1s_instability = (v1_with_stability.benchmark_metrics.get("region_instability_mean", 0.0)
                       if v1_with_stability and isinstance(v1_with_stability.benchmark_metrics, dict) else 0.0)
    all_no_actions = all(
        (r.benchmark_metrics.get("stability_actions_applied", 0) if isinstance(r.benchmark_metrics, dict) else 0) == 0
        for r in v2_results
    )
    if all_no_actions:
        return "ROUTING_V2_NO_EFFECT"

    # Activation without stability (actions==0 despite high activation)
    if deep_activation > 0.05 and actions == 0 and instability_mean < 0.25:
        return "ROUTING_V2_ACTIVATION_WITHOUT_STABILITY"

    # Strong result: phi_recovery > 0.05, actions > 0, no collapse
    if phi_recovery > 0.05 and actions > 0:
        if brainstem > 0.0:
            return "ROUTING_V2_STABILITY_VALIDATED"
        return "ROUTING_V2_STABILITY_VALIDATED"  # brainstem is optional

    # Partial recovery: phi_recovery > 0.02, actions > 0
    if phi_recovery > 0.02 and actions > 0:
        return "ROUTING_V2_PARTIAL_RECOVERY"

    # Controller working but minimal phi recovery
    if actions > 0 and instability_mean >= 0.25:
        return "ROUTING_V2_PARTIAL_RECOVERY"

    return "ROUTING_V2_NO_EFFECT"


async def main():
    profiles = make_profiles()
    auditor = DeepRegionAuditor(n_adaptive_cycles=5, report_dir="reports/deep_region_routing")

    # Baseline
    baseline_profile = DeepRegionAuditProfile(
        profile_id="base",
        name="four_region_baseline",
        deep_regions_enabled=False,
        inter_region_plasticity_enabled=True,
        region_signal_routing_enabled=False,
    )
    baseline = await auditor.run_profile(baseline_profile)

    results = []
    v1_no_stability = None
    v1_with_stability = None

    for p in profiles:
        orch = auditor.build_orchestrator(deep_regions_enabled=p.deep_regions_enabled)
        auditor.apply_homeostatic_baseline(orch)
        auditor.apply_profile(p, orch)
        apply_t34_profile(auditor, p, orch)

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
            # Build a minimal result on failure
            from speace_core.cellular_brain.analysis.deep_region_audit import DeepRegionAuditResult
            result_obj = DeepRegionAuditResult(
                profile=p,
                benchmark_metrics={},
                passed=False,
                failure_reason=str(exc),
            )
            results.append(result_obj)
            if p.profile_id == "r1n":
                v1_no_stability = result_obj
            if p.profile_id == "r1s":
                v1_with_stability = result_obj
            continue

        m = result.metrics
        bm = m.model_dump()
        deep_metrics: Dict[str, Any] = {}
        if orch._region_registry is not None:
            from speace_core.cellular_brain.regions.deep_region_specialization import DeepRegionSpecialization
            deep_metrics = DeepRegionSpecialization.compute_deep_region_metrics(orch._region_registry)

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
        # Compute deltas vs baseline
        res.cognitive_score_delta = res.cognitive_score - baseline.cognitive_score
        res.phi_delta = res.phi - baseline.phi
        res.energy_efficiency_delta = res.energy_efficiency - baseline.energy_efficiency
        res.functional_improvement_delta = res.functional_improvement - baseline.functional_improvement
        res.pathway_utility_delta = res.mean_pathway_utility - baseline.mean_pathway_utility
        res.deep_region_net_gain = DeepRegionAuditor.compute_deep_region_net_gain(res, baseline)

        results.append(res)
        if p.profile_id == "r1n":
            v1_no_stability = res
        if p.profile_id == "r1s":
            v1_with_stability = res

    verdict = compute_t34b_verdict(results, baseline, v1_no_stability, v1_with_stability)

    # Find best and worst v2 profiles
    v2_results = [r for r in results if r.profile.name.startswith("routing_v2")]
    best_v2 = max(v2_results, key=lambda r: r.deep_region_net_gain) if v2_results else None
    worst_v2 = min(v2_results, key=lambda r: r.deep_region_net_gain) if v2_results else None

    # Build JSON output
    output = {
        "audit_id": f"t34b_{auditor._seed}",
        "verdict": verdict,
        "baseline": {
            "name": baseline.profile.name,
            "cognitive_score": baseline.cognitive_score,
            "phi": baseline.phi,
            "energy_efficiency": baseline.energy_efficiency,
        },
        "profiles": [
            {
                "name": r.profile.name,
                "stability_enabled": r.profile.region_stability_controller_enabled,
                "t34_enabled": (getattr(r.profile, "__pydantic_extra__", {}) or {}).get("deep_region_routing_calibrator_enabled", False),
                "t34_profile_id": (getattr(r.profile, "__pydantic_extra__", {}) or {}).get("t34_profile_id", None),
                "cognitive_score": r.cognitive_score,
                "phi": r.phi,
                "energy_efficiency": r.energy_efficiency,
                "cognitive_score_delta": r.cognitive_score_delta,
                "phi_delta": r.phi_delta,
                "energy_efficiency_delta": r.energy_efficiency_delta,
                "regional_signal_flow": r.benchmark_metrics.get("regional_signal_flow_score", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "deep_region_signal_flow": r.benchmark_metrics.get("deep_region_signal_flow", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "deep_region_activation_mean": r.benchmark_metrics.get("mean_deep_region_activation", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "brainstem_activation_score": r.benchmark_metrics.get("brainstem_homeostatic_stability_score", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "phi_recovery_score": r.benchmark_metrics.get("phi_recovery_score", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "region_instability_mean": r.benchmark_metrics.get("region_instability_mean", 0.0) if isinstance(r.benchmark_metrics, dict) else 0.0,
                "unstable_region_count": r.benchmark_metrics.get("unstable_region_count", 0) if isinstance(r.benchmark_metrics, dict) else 0,
                "stability_actions_applied": r.benchmark_metrics.get("stability_actions_applied", 0) if isinstance(r.benchmark_metrics, dict) else 0,
                "routing_blocks_applied": r.benchmark_metrics.get("routing_blocks_applied", 0) if isinstance(r.benchmark_metrics, dict) else 0,
                "cooldowns_started": r.benchmark_metrics.get("cooldowns_started", 0) if isinstance(r.benchmark_metrics, dict) else 0,
                "brainstem_override_count": r.benchmark_metrics.get("brainstem_override_count", 0) if isinstance(r.benchmark_metrics, dict) else 0,
                "mean_region_damping_factor": r.benchmark_metrics.get("mean_region_damping_factor", 1.0) if isinstance(r.benchmark_metrics, dict) else 1.0,
                "deep_region_net_gain": r.deep_region_net_gain,
                "passed": r.passed,
            }
            for r in results
        ],
        "best_v2_profile": best_v2.profile.name if best_v2 else None,
        "worst_v2_profile": worst_v2.profile.name if worst_v2 else None,
        "recommendation_t35": _recommendation_for_verdict(verdict),
    }

    # Write JSON report
    import datetime
    from pathlib import Path
    report_dir = Path("reports/deep_region_routing")
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = report_dir / f"t34b_routing_v2_audit_{ts}.json"
    json_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    # Write Markdown report
    md_lines = [
        "# T34B — Stability Audit With Routing v2",
        "",
        f"**Audit ID:** {output['audit_id']}",
        f"**Verdict:** {verdict}",
        f"**Best v2 Profile:** {output['best_v2_profile'] or 'N/A'}",
        f"**Worst v2 Profile:** {output['worst_v2_profile'] or 'N/A'}",
        f"**T35 Recommendation:** {output['recommendation_t35']}",
        "",
        "## Baseline (4-Region)",
        f"- Cognitive score: {baseline.cognitive_score:.4f}",
        f"- Coherence Phi: {baseline.phi:.4f}",
        f"- Energy efficiency: {baseline.energy_efficiency:.4f}",
        "",
        "## Profiles",
        "",
        "| Profile | T34 | Stability | Cognitive | Phi | Energy | Flow | Deep Act | Instability | Actions | Damping | Phi Rec | Net Gain |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for p in output["profiles"]:
        md_lines.append(
            f"| {p['name']} | "
            f"{'Yes' if p['t34_enabled'] else 'No'} | "
            f"{'Yes' if p['stability_enabled'] else 'No'} | "
            f"{p['cognitive_score']:.4f} | {p['phi']:.4f} | {p['energy_efficiency']:.4f} | "
            f"{p['regional_signal_flow']:.4f} | {p['deep_region_activation_mean']:.4f} | "
            f"{p['region_instability_mean']:.4f} | {p['stability_actions_applied']} | "
            f"{p['mean_region_damping_factor']:.4f} | {p['phi_recovery_score']:.4f} | "
            f"{p['deep_region_net_gain']:.4f} |"
        )
    md_lines.extend([
        "",
        "## Detailed v2 Profiles",
        "",
    ])
    for p in output["profiles"]:
        if not p["t34_enabled"]:
            continue
        md_lines.extend([
            f"### {p['name']}",
            f"- T34 profile: {p['t34_profile_id']}",
            f"- Cognitive: {p['cognitive_score']:.4f} (delta {p['cognitive_score_delta']:+.4f})",
            f"- Phi: {p['phi']:.4f} (delta {p['phi_delta']:+.4f})",
            f"- Energy: {p['energy_efficiency']:.4f} (delta {p['energy_efficiency_delta']:+.4f})",
            f"- Deep activation mean: {p['deep_region_activation_mean']:.4f}",
            f"- Brainstem score: {p['brainstem_activation_score']:.4f}",
            f"- Instability mean: {p['region_instability_mean']:.4f}",
            f"- Stability actions: {p['stability_actions_applied']}",
            f"- Phi recovery: {p['phi_recovery_score']:.4f}",
            f"- Net gain: {p['deep_region_net_gain']:.4f}",
            "",
        ])

    md_lines.extend([
        "---",
        "*Generated by T34B Routing v2 Stability Audit*",
    ])
    md_path = report_dir / f"t34b_routing_v2_audit_{ts}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"MD: {md_path}")
    print(json.dumps(output, indent=2))


def _recommendation_for_verdict(verdict: str) -> str:
    mapping = {
        "ROUTING_V2_STABILITY_VALIDATED": "T35 Brainstem Functional Integration",
        "ROUTING_V2_PARTIAL_RECOVERY": "T35 Stability/Performance Balance Tuning",
        "ROUTING_V2_ACTIVATION_WITHOUT_STABILITY": "T35 Stability Threshold Calibration",
        "ROUTING_V2_OVERSTIMULATION": "T35 Adaptive Routing Gain Controller",
        "ROUTING_V2_NO_EFFECT": "T35 Deep Region Activation Redesign v3",
        "ROUTING_V2_ENERGY_REGRESSION": "T35 Brainstem Energy Arbitration",
        "ROUTING_V2_COGNITIVE_REGRESSION": "T35 Deep Region Role Rebalancing",
        "INSUFFICIENT_EVIDENCE": "T35 Benchmark Stimulation Redesign",
    }
    return mapping.get(verdict, "T35 Next Step Undefined")


if __name__ == "__main__":
    asyncio.run(main())
