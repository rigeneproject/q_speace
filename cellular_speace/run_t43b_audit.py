import asyncio
from speace_core.cellular_brain.analysis.semantic_memory_audit import SemanticMemoryAuditor


async def main():
    auditor = SemanticMemoryAuditor(seed=42)
    profiles = SemanticMemoryAuditor.default_profiles()
    print(f"Running T43B audit with {len(profiles)} profiles...")
    report = await auditor.run_audit_suite(profiles=profiles)

    print("\n" + "=" * 80)
    print("T43B — SEMANTIC MEMORY FUNCTIONAL AUDIT RESULTS")
    print("=" * 80)
    print(f"Audit ID:   {report.audit_id}")
    print(f"Created At: {report.created_at}")
    print(f"Verdict:    {report.verdict}")
    print(f"Best Profile: {report.best_profile}")
    print(f"Overall Net Gain: {report.semantic_net_gain:.4f}")
    print("\n" + "-" * 80)
    print(f"{'Profile':<42} {'Cog':>6} {'Phi':>6} {'Energy':>7} {'Asm':>5} {'Cons':>5} {'Recall':>7} {'Str':>6} {'Score':>6} {'NetGain':>8}")
    print("-" * 80)
    for r in report.profile_results:
        m = r.metrics
        print(
            f"{r.profile.name:<42} {m.cognitive_score:>6.3f} {m.coherence_phi:>6.3f} "
            f"{m.energy_efficiency:>7.3f} {m.semantic_assembly_count:>5} {m.semantic_consolidated_assembly_count:>5} "
            f"{m.semantic_recall_success_rate:>7.3f} {m.mean_assembly_strength:>6.3f} {m.semantic_memory_score:>6.3f} {m.semantic_net_gain:>+8.4f}"
        )
    print("-" * 80)
    print(f"\nJSON Report:  {report.json_report_path}")
    print(f"MD Report:    {report.markdown_report_path}")
    print("=" * 80)

    # Recommend next task
    verdict = report.verdict
    if verdict == "SEMANTIC_MEMORY_VALIDATED":
        next_task = "T44 — Associative Learning Between Assemblies"
    elif verdict in ("SEMANTIC_MEMORY_PASSIVE", "SEMANTIC_RECALL_WEAK"):
        next_task = "T43C — Semantic Recall Sensitivity Tuning"
    elif verdict == "SEMANTIC_OVERCONSOLIDATION":
        next_task = "T43C — Assembly Consolidation Guard"
    elif verdict == "SEMANTIC_ENERGY_REGRESSION":
        next_task = "T43C — Semantic Memory Energy Governor"
    elif verdict == "SEMANTIC_COGNITIVE_REGRESSION":
        next_task = "T43C — Semantic Memory Cognitive Guard"
    elif verdict == "SEMANTIC_PHI_REGRESSION":
        next_task = "T43C — Semantic Coherence Stabilizer"
    else:
        next_task = "T43C — Semantic Benchmark Stimulation Redesign"
    print(f"\nRecommended Next Task: {next_task}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
