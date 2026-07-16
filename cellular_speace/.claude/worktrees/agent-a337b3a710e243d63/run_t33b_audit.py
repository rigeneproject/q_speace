import asyncio
import json
from typing import Dict, Any, List

from speace_core.cellular_brain.analysis.deep_region_audit import (
    DeepRegionAuditor,
    DeepRegionAuditProfile,
)


def make_profiles() -> List[DeepRegionAuditProfile]:
    """Build T33B profiles comparing stability on/off for key deep-region configs."""
    return [
        DeepRegionAuditProfile(
            profile_id="n1",
            name="deep_regions_routing_only_no_stability",
            deep_regions_enabled=True,
            inter_region_plasticity_enabled=False,
            region_signal_routing_enabled=True,
            region_stability_controller_enabled=False,
        ),
        DeepRegionAuditProfile(
            profile_id="s1",
            name="deep_regions_routing_only_stability_soft",
            deep_regions_enabled=True,
            inter_region_plasticity_enabled=False,
            region_signal_routing_enabled=True,
            region_stability_controller_enabled=True,
        ),
        DeepRegionAuditProfile(
            profile_id="s2",
            name="deep_regions_routing_only_stability_medium",
            deep_regions_enabled=True,
            inter_region_plasticity_enabled=False,
            region_signal_routing_enabled=True,
            region_stability_controller_enabled=True,
            trigger_mode="hybrid",
        ),
        DeepRegionAuditProfile(
            profile_id="s3",
            name="deep_regions_routing_only_stability_strict",
            deep_regions_enabled=True,
            inter_region_plasticity_enabled=False,
            region_signal_routing_enabled=True,
            region_stability_controller_enabled=True,
            trigger_mode="hybrid",
            ltp_rate=0.02,
            ltd_rate=0.01,
        ),
        DeepRegionAuditProfile(
            profile_id="n2",
            name="deep_regions_full_utility_no_stability",
            deep_regions_enabled=True,
            inter_region_plasticity_enabled=True,
            region_signal_routing_enabled=True,
            region_stability_controller_enabled=False,
            trigger_mode="hybrid",
            tuner_profile_id="t9",
        ),
        DeepRegionAuditProfile(
            profile_id="s4",
            name="deep_regions_full_utility_stability_soft",
            deep_regions_enabled=True,
            inter_region_plasticity_enabled=True,
            region_signal_routing_enabled=True,
            region_stability_controller_enabled=True,
            trigger_mode="hybrid",
            tuner_profile_id="t9",
        ),
        DeepRegionAuditProfile(
            profile_id="s5",
            name="deep_regions_full_utility_stability_medium",
            deep_regions_enabled=True,
            inter_region_plasticity_enabled=True,
            region_signal_routing_enabled=True,
            region_stability_controller_enabled=True,
            trigger_mode="hybrid",
            tuner_profile_id="t9",
        ),
        DeepRegionAuditProfile(
            profile_id="s6",
            name="deep_regions_full_utility_stability_strict",
            deep_regions_enabled=True,
            inter_region_plasticity_enabled=True,
            region_signal_routing_enabled=True,
            region_stability_controller_enabled=True,
            trigger_mode="hybrid",
            ltp_rate=0.02,
            ltd_rate=0.01,
            tuner_profile_id="t9",
        ),
        DeepRegionAuditProfile(
            profile_id="s7",
            name="deep_regions_brainstem_priority_stability",
            deep_regions_enabled=True,
            inter_region_plasticity_enabled=True,
            region_signal_routing_enabled=True,
            region_stability_controller_enabled=True,
            trigger_mode="hybrid",
            energy_modulation_strength=2.0,
        ),
        DeepRegionAuditProfile(
            profile_id="s8",
            name="deep_regions_balanced_stability",
            deep_regions_enabled=True,
            inter_region_plasticity_enabled=True,
            region_signal_routing_enabled=True,
            region_stability_controller_enabled=True,
            trigger_mode="hybrid",
            ltp_rate=0.03,
            ltd_rate=0.02,
            energy_cost_per_update=0.0008,
            energy_modulation_strength=1.2,
        ),
    ]


def compute_t33b_verdict(results: List[Any], baseline: Any) -> str:
    stability_results = [r for r in results if r.profile.region_stability_controller_enabled]
    no_stability = [r for r in results if not r.profile.region_stability_controller_enabled]
    if not stability_results or not no_stability:
        return "INSUFFICIENT_EVIDENCE"

    # Compare each stability result against its no-stability counterpart by name prefix
    max_phi_recovery = 0.0
    any_overdamped = False
    for sr in stability_results:
        prefix = sr.profile.name.replace("_stability_soft", "").replace("_stability_medium", "").replace("_stability_strict", "").replace("_stability", "")
        ns = next((r for r in no_stability if prefix in r.profile.name or r.profile.name in prefix), None)
        if ns is None:
            continue
        # Check cognitive/energy regression relative to no-stability counterpart
        if sr.cognitive_score < ns.cognitive_score - 0.05:
            return "STABILITY_COGNITIVE_REGRESSION"
        if sr.energy_efficiency < ns.energy_efficiency - 0.05:
            return "STABILITY_ENERGY_REGRESSION"
        # Overdamping check
        if sr.profile.region_signal_routing_enabled and sr.benchmark_metrics.get("regional_signal_flow_score", 0.0) == 0.0:
            any_overdamped = True
        # Phi recovery relative to no-stability (approximate via phi_recovery_score if available, else direct phi diff)
        recovery = sr.benchmark_metrics.get("phi_recovery_score", 0.0)
        if recovery == 0.0:
            recovery = max(0.0, sr.phi - ns.phi)
        max_phi_recovery = max(max_phi_recovery, recovery)

    if any_overdamped:
        return "STABILITY_OVERDAMPING"

    if max_phi_recovery > 0.05:
        return "STABILITY_VALIDATED"
    if max_phi_recovery > 0.02:
        return "STABILITY_PARTIAL_RECOVERY"
    return "STABILITY_NO_EFFECT"


async def main():
    profiles = make_profiles()
    auditor = DeepRegionAuditor(n_adaptive_cycles=5)

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
    for p in profiles:
        res = await auditor.run_profile(p)
        results.append(res)

    verdict = compute_t33b_verdict(results, baseline)

    # Build JSON output
    output = {
        "audit_id": f"t33b_{auditor._seed}",
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
                "cognitive_score": r.cognitive_score,
                "phi": r.phi,
                "energy_efficiency": r.energy_efficiency,
                "regional_signal_flow": r.benchmark_metrics.get("regional_signal_flow_score", 0.0),
                "deep_region_signal_flow": r.benchmark_metrics.get("deep_region_signal_flow", 0.0),
                "phi_recovery_score": r.benchmark_metrics.get("phi_recovery_score", 0.0),
                "region_instability_mean": r.benchmark_metrics.get("region_instability_mean", 0.0),
                "unstable_region_count": r.benchmark_metrics.get("unstable_region_count", 0),
                "stability_actions_applied": r.benchmark_metrics.get("stability_actions_applied", 0),
                "routing_blocks_applied": r.benchmark_metrics.get("routing_blocks_applied", 0),
                "cooldowns_started": r.benchmark_metrics.get("cooldowns_started", 0),
                "brainstem_override_count": r.benchmark_metrics.get("brainstem_override_count", 0),
                "mean_region_damping_factor": r.benchmark_metrics.get("mean_region_damping_factor", 1.0),
            }
            for r in results
        ],
    }

    # Write JSON report
    import datetime
    from pathlib import Path
    report_dir = Path("reports/region_stability")
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = report_dir / f"t33b_stability_audit_{ts}.json"
    json_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    # Write Markdown report
    md_lines = [
        "# T33B — Deep Region Audit With Stability Controller",
        "",
        f"**Audit ID:** {output['audit_id']}",
        f"**Verdict:** {verdict}",
        "",
        "## Baseline (4-Region)",
        f"- Cognitive score: {baseline.cognitive_score:.4f}",
        f"- Coherence Phi: {baseline.phi:.4f}",
        f"- Energy efficiency: {baseline.energy_efficiency:.4f}",
        "",
        "## Profiles",
        "",
        "| Profile | Stability | Cognitive | Phi | Energy | Flow | Instability | Actions | Damping |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for p in output["profiles"]:
        md_lines.append(
            f"| {p['name']} | {'Yes' if p['stability_enabled'] else 'No'} | "
            f"{p['cognitive_score']:.4f} | {p['phi']:.4f} | "
            f"{p['energy_efficiency']:.4f} | {p['regional_signal_flow']:.4f} | "
            f"{p['region_instability_mean']:.4f} | {p['stability_actions_applied']} | "
            f"{p['mean_region_damping_factor']:.4f} |"
        )
    md_lines.extend(["", "---", "*Generated by T33B Stability Audit*"])
    md_path = report_dir / f"t33b_stability_audit_{ts}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"MD: {md_path}")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
