import asyncio
import json
from speace_core.cellular_brain.audit.integrated_neurocellular_audit import IntegratedNeurocellularAudit

async def main():
    audit = IntegratedNeurocellularAudit(seed=42, evolution_db_path="data/evolution_t20_baseline")
    configs = IntegratedNeurocellularAudit.default_configurations()
    # Override n_adaptive_cycles for all configs
    for c in configs:
        c.n_adaptive_cycles = 5
        c.benchmark_case = "morphological_memory_trace"

    report = await audit.run_all(configurations=configs)

    # Print concise summary
    s = report.summary
    print(f"\n{'='*60}")
    print("T20 CANONICAL AUDIT REPORT")
    print(f"{'='*60}")
    print(f"Audit ID: {report.audit_id}")
    print(f"Created:  {report.created_at}")
    print(f"\nVerdict:  {s.verdict.upper()}")
    print(f"Baseline: {s.baseline_name}")
    print(f"Best Config: {s.best_configuration}")
    print(f"Best Cognitive Score: {s.best_cognitive_score}")
    print(f"Best Fitness Score:   {s.best_fitness_score}")
    print("\n--- Deltas (full organism vs baseline) ---")
    print(f"  Cognitive Score Delta:   {s.cognitive_score_delta:+.4f}")
    print(f"  Phi Delta:               {s.phi_delta:+.4f}")
    print(f"  Energy Efficiency Delta: {s.energy_efficiency_delta:+.4f}")
    print(f"  Modularity Delta:        {s.modularity_delta:+.4f}")
    print(f"  Confidence Delta:        {s.confidence_delta:+.4f}")
    print(f"  Stability Delta:         {s.stability_delta:+.4f}")
    print("\n--- Results per configuration ---")
    for r in report.results:
        m = r.benchmark_metrics
        fit_str = f"{r.fitness_score:.4f}" if r.fitness_score is not None else "    —"
        print(
            f"  {r.configuration.name:45s}  "
            f"cog={m.get('speace_cognitive_score', 0.0):.4f}  "
            f"phi={m.get('coherence_phi', 0.0):.4f}  "
            f"energy={m.get('energy_efficiency', 0.0):.4f}  "
            f"mod={m.get('modularity_proxy', 0.0):.4f}  "
            f"conf={m.get('confidence_score', 0.0):.4f}  "
            f"fit={fit_str:>7s}  "
            f"{'PASS' if r.test_passed else 'FAIL'}"
        )
    print("\n--- Report files ---")
    print(f"JSON: {report.json_report_path}")
    print(f"MD:   {report.markdown_report_path}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    asyncio.run(main())
