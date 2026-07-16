import asyncio
from speace_core.cellular_brain.analysis.semantic_stimulation_designer import SemanticStimulationDesigner


async def main():
    designer = SemanticStimulationDesigner(seed=42)
    profiles = SemanticStimulationDesigner.default_profiles()
    print(f"Running T43C suite with {len(profiles)} profiles...")
    suite = await designer.run_suite(profiles=profiles)

    print("\n" + "=" * 80)
    print("T43C — SEMANTIC BENCHMARK STIMULATION REDESIGN RESULTS")
    print("=" * 80)
    print(f"Audit ID:   {suite.audit_id}")
    print(f"Created At: {suite.created_at}")
    print(f"Verdict:    {suite.verdict}")
    print(f"Best Profile: {suite.best_profile}")
    print(f"Worst Profile: {suite.worst_profile}")
    print("\n" + "-" * 80)
    print(
        f"{'Profile':<42} {'Created':>7} {'Reinf':>6} {'Cons':>5} {'Recall':>7} {'Partial':>8} "
        f"{'Stability':>9} {'Discrim':>8} {'Consolid':>9} {'Effect':>7} {'CogD':>7} {'PhiD':>7}"
    )
    print("-" * 80)
    for r in suite.profile_results:
        m = r.metrics
        print(
            f"{r.profile.profile_name:<42} {m.assembly_created_events:>7} {m.assembly_reinforced_events:>6} "
            f"{m.assembly_consolidated_events:>5} {m.recall_success_rate:>7.3f} {m.partial_cue_success_rate:>8.3f} "
            f"{m.mean_assembly_stability:>9.3f} {m.semantic_discrimination_score:>8.3f} "
            f"{m.semantic_consolidation_score:>9.3f} {m.semantic_stimulation_effectiveness:>7.3f} "
            f"{m.cognitive_delta:>+7.3f} {m.phi_delta:>+7.3f}"
        )
    print("-" * 80)
    print(f"\nJSON Report:  {suite.json_report_path}")
    print(f"MD Report:    {suite.markdown_report_path}")
    print("=" * 80)

    verdict_map = {
        "SEMANTIC_STIMULATION_VALIDATED": "T44 — Associative Learning Between Assemblies",
        "SEMANTIC_ENCODING_ONLY": "T43D — Semantic Consolidation Trigger Redesign",
        "SEMANTIC_CONSOLIDATION_WEAK": "T43D — Assembly Consolidation Threshold Tuning",
        "SEMANTIC_RECALL_WEAK": "T43D — Semantic Recall Sensitivity Tuning",
        "SEMANTIC_DISCRIMINATION_FAILURE": "T43D — Pattern Separation / Assembly Orthogonalization",
        "SEMANTIC_OVERACTIVATION": "T43D — Semantic Reactivation Safety Controller",
        "SEMANTIC_GLOBAL_NO_EFFECT": "T43D — Semantic-Cognitive Coupling Integration",
        "INSUFFICIENT_EVIDENCE": "T43D — Semantic Audit Instrumentation Patch",
    }
    next_task = verdict_map.get(suite.verdict, "T43D — Semantic Audit Instrumentation Patch")
    print(f"\nRecommended Next Task: {next_task}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
