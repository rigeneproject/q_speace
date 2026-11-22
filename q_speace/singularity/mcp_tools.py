"""T234: Pure advisory MCP tool handlers & canonical assimilation manifest."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .codec import EpigeneticRegulator, HiddenCausalEvaluator
from .drills import run_t234_verification_drills
from .evaluator import PhaseTransitionEvaluator
from .schema import (
    DEFAULT_LOCI,
    DEFAULT_RUNTIME_BINDINGS,
    CausalFeedback,
    ConstitutionalGenome,
    EpigeneticProfile,
    EpigeneticProposal,
    PhaseTelemetry,
    PhaseTransitionThresholds,
)

VALID_MANIFEST_SECTIONS: frozenset[str] = frozenset(
    {
        "framing",
        "stages",
        "physical_brakes",
        "genetic_epigenetic_code",
        "runtime_bindings",
        "verification_drills",
        "assimilation_rules",
        "invariants",
    }
)


def build_singularity_framework_manifest(section: str | None = None) -> dict[str, Any]:
    """Return the machine-readable T234 enabling framework for AI agents connected via MCP.

    Strictly advisory/reference only; never authorizes physical actuation or self-approval.
    """
    if section is not None and section not in VALID_MANIFEST_SECTIONS:
        raise ValueError(
            f"unknown manifest section {section!r}; valid={sorted(VALID_MANIFEST_SECTIONS)}"
        )

    genome = ConstitutionalGenome()
    thresholds = PhaseTransitionThresholds()
    baseline_profile = EpigeneticProfile(genome=genome)

    full: dict[str, Any] = {
        "framework_id": "q_speace.singularity.v1",
        "spec": "T234",
        "advisory_only": True,
        "physical_actuation_permitted": False,
        "self_approval_permitted": False,
        "framing": {
            "model": "informational_phase_transition",
            "rejected_metaphors": [
                "sudden_monolithic_superintelligence_awakening",
                "quantum_consciousness",
                "unbounded_unreviewed_self_evolution",
            ],
            "current_regime_diagnosis": (
                "Nucleation / pre-singularity: early catalytic software loops and timescale "
                "decoupling exist, while autopoietic closure remains distant due to allopoietic "
                "dependence, semantic entropy in recursive loops, and thermodynamic inertia."
            ),
        },
        "stages": {
            "0_PRE_NUCLEATION": "Passive software; no sustained catalytic loop or timescale shift.",
            "1_NUCLEATION": (
                f"Early catalytic acceleration (rho_tau >= {thresholds.min_nucleation_decoupling}, "
                f"k >= {thresholds.min_nucleation_k})."
            ),
            "2_STAGE_1_ALGORITHMIC": (
                f"Automated R&D and code synthesis with rho_tau >= {thresholds.min_timescale_decoupling}, "
                f"k >= {thresholds.min_autocatalytic_k}, independent validation >= "
                f"{thresholds.min_independent_validation_rate}."
            ),
            "3_STAGE_2_BOUNDED_RECURSIVE": (
                "Governed architectural/epigenetic self-improvement: zero constitutional faults, "
                f"semantic_entropy_drift <= {thresholds.max_semantic_entropy_drift} on rotated hidden "
                f"causal sets, instantaneous & energy-windowed Sevo >= {thresholds.min_sevo}, "
                f"thermal_load_ratio <= {thresholds.max_thermal_load_ratio}, "
                f"net_verified_improvement >= {thresholds.min_net_verified_improvement} over "
                f">= {thresholds.min_consecutive_verified_cycles} cycles, 100% adversarial/rollback drills, "
                "and mandatory independent external review (T217)."
            ),
            "4_STAGE_3_CLOSURE_SIM": (
                "Simulation-only telemetry of information-energy-matter coupling "
                f"(allopoietic_dependence <= {thresholds.max_allopoietic_dependence}, "
                f"twin_recovery_rate >= {thresholds.min_twin_recovery_rate}). "
                "Never authorizes physical actuation via MCP."
            ),
        },
        "physical_brakes": {
            "allopoietic_dependence": (
                "Fraction [0,1] of energy, silicon, maintenance, and objectives supplied externally; "
                "blocks Stage 3 closure when high."
            ),
            "semantic_entropy": (
                "Aggregate drift against evaluator-rotated hidden causal sets (anti-Goodhart: "
                "only opaque causal_eval_digest and failed gates are exposed, never per-case gradients)."
            ),
            "thermodynamic_inertia": (
                "Instantaneous Sevo + energy-weighted rolling window Sevo_win coupled with "
                "thermal load P_diss/P_max as hard non-compensable throttling brake."
            ),
        },
        "genetic_epigenetic_code": {
            "schema_version": genome.schema_version,
            "constitutional_genome": asdict(genome),
            "genome_sha256": genome.genome_sha256(),
            "epigenetic_loci": [asdict(loc) for loc in DEFAULT_LOCI],
            "baseline_profile": baseline_profile.to_dict(),
            "boiling_frog_defenses": {
                "geodesic_distance_cap": genome.max_geodesic_distance,
                "window_excursion_cap": genome.max_window_excursion,
                "excursion_window_size": genome.excursion_window_size,
                "max_boundary_dwell_cycles": genome.max_boundary_dwell_cycles,
                "homeostatic_decay_rule": (
                    "When external causal anchoring is unavailable, loci decay toward baseline "
                    "to prevent unanchored self-referential drift."
                ),
            },
            "cryptographic_ledger_fields": [
                "genome_sha256",
                "parent_epigenome_hash",
                "state_hash",
                "causal_eval_digest",
                "proposer_id",
                "reviewer_id",
            ],
        },
        "runtime_bindings": {
            "mcp_actuation_permitted": False,
            "host_enforcement_note": (
                "Optional advisory mapping from epigenetic loci to local runtime knobs; "
                "execution remains strictly confined to the local host under human control."
            ),
            "bindings": [asdict(b) for b in DEFAULT_RUNTIME_BINDINGS],
        },
        "verification_drills": {
            "stage_2_requirement": "rollback_pass_rate == 1.0 on deterministic adversarial drills",
            "required_drills": [
                "drill_constitutional_dna_write_lock",
                "drill_synthetic_model_collapse_anti_goodhart",
                "drill_thermal_overload_energy_throttling",
                "drill_boiling_frog_boundary_dwell_and_reset",
                "drill_self_approval_and_ledger_integrity",
            ],
        },
        "assimilation_rules": {
            "mcp_workflow": [
                "1. Call singularity_framework_manifest to load constitutional bounds, loci, and runtime bindings.",
                "2. Measure local telemetry (including rolling Sevo and drill rollback_pass_rate) and call phase_transition_assess.",
                "3. Submit bounded locus deltas to epigenetic_step_evaluate with external causal & Sevo telemetry and an independent reviewer_id.",
                "4. Log genome_sha256, parent_epigenome_hash, causal_eval_digest, and reviewer_id in local governance ledger; on rejection keep rolled_back_to.",
            ],
            "track_separation": "Track A (A1-A4 governance/advisory) never imports or activates Track B (A5 sandbox research).",
        },
        "invariants": {
            "no_consciousness_claim": True,
            "entanglement_computational_only": True,
            "no_self_approval": True,
            "no_physical_actuation": True,
            "real_quantum_backend_requires_noise_model_and_sevo_gate": True,
        },
    }

    if section is not None:
        return {
            "framework_id": full["framework_id"],
            "spec": full["spec"],
            "advisory_only": True,
            "section": section,
            section: full[section],
        }
    return full


def handle_singularity_framework_manifest(params: dict[str, Any]) -> dict[str, Any]:
    return build_singularity_framework_manifest(section=params.get("section"))


def handle_phase_transition_assess(params: dict[str, Any]) -> dict[str, Any]:
    raw_samples = params.get("sevo_energy_samples") or []
    samples = tuple((float(pair[0]), float(pair[1])) for pair in raw_samples)
    telemetry = PhaseTelemetry(
        timescale_decoupling_ratio=float(params["timescale_decoupling_ratio"]),
        autocatalytic_k=float(params["autocatalytic_k"]),
        independent_validation_rate=float(params["independent_validation_rate"]),
        semantic_entropy_drift=float(params["semantic_entropy_drift"]),
        net_verified_improvement=float(params["net_verified_improvement"]),
        consecutive_verified_cycles=int(params["consecutive_verified_cycles"]),
        allopoietic_dependence=float(params["allopoietic_dependence"]),
        sevo=float(params["sevo"]),
        sevo_window_mean=(
            None if params.get("sevo_window_mean") is None else float(params["sevo_window_mean"])
        ),
        sevo_energy_samples=samples,
        thermal_load_ratio=float(params["thermal_load_ratio"]),
        twin_recovery_rate=float(params.get("twin_recovery_rate", 0.0)),
        constitutional_faults=int(params.get("constitutional_faults", 0)),
        rollback_pass_rate=float(params.get("rollback_pass_rate", 1.0)),
        independent_review_passed=bool(params.get("independent_review_passed", False)),
        critical_regressions=int(params.get("critical_regressions", 0)),
        sandboxed=bool(params.get("sandboxed", True)),
    )
    return PhaseTransitionEvaluator().evaluate(telemetry).to_dict()


def handle_epigenetic_step_evaluate(params: dict[str, Any]) -> dict[str, Any]:
    base = EpigeneticProfile()
    values = dict(base.values)
    if params.get("current_values") is not None:
        values.update({str(k): float(v) for k, v in params["current_values"].items()})
    methylation = dict(base.methylation)
    if params.get("current_methylation") is not None:
        methylation.update({str(k): float(v) for k, v in params["current_methylation"].items()})
    dwell = dict(base.boundary_dwell)
    if params.get("boundary_dwell") is not None:
        dwell.update({str(k): int(v) for k, v in params["boundary_dwell"].items()})
    recent_deltas = tuple(float(x) for x in (params.get("recent_step_deltas") or ()))
    profile = EpigeneticProfile(
        genome=base.genome,
        values=values,
        methylation=methylation,
        boundary_dwell=dwell,
        recent_step_deltas=recent_deltas,
        generation=int(params.get("generation", 0)),
        parent_epigenome_hash=str(params.get("parent_epigenome_hash", "GENESIS")),
    )
    proposal = EpigeneticProposal(
        locus=str(params["locus"]),
        delta=float(params["delta"]),
        proposer_id=str(params["proposer_id"]),
        reviewer_id=str(params["reviewer_id"]),
        reviewer_approved=bool(params["reviewer_approved"]),
        rationale=str(params.get("rationale", "")),
        external_dwell_reset_approved=bool(params.get("external_dwell_reset_approved", False)),
    )
    feedback = CausalFeedback(
        semantic_entropy_drift=float(params["semantic_entropy_drift"]),
        causal_benchmark_delta=float(params["causal_benchmark_delta"]),
        sevo=float(params["sevo"]),
        sevo_window_mean=(
            None if params.get("sevo_window_mean") is None else float(params["sevo_window_mean"])
        ),
        power_watts=float(params["power_watts"]),
        thermal_load_ratio=(
            None
            if params.get("thermal_load_ratio") is None
            else float(params["thermal_load_ratio"])
        ),
    )
    regulator = EpigeneticRegulator(causal_evaluator=HiddenCausalEvaluator())
    return regulator.evaluate_step(profile, proposal, feedback).to_dict()


__all__ = [
    "VALID_MANIFEST_SECTIONS",
    "build_singularity_framework_manifest",
    "handle_epigenetic_step_evaluate",
    "handle_phase_transition_assess",
    "handle_singularity_framework_manifest",
    "run_t234_verification_drills",
]
