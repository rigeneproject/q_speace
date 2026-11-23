"""T234 v1.1: Pure advisory MCP tool handlers & canonical assimilation manifest."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Literal, cast

from .codec import EpigeneticRegulator, HiddenCausalEvaluator, resolve_runtime_controls
from .drills import run_t234_verification_drills
from .evaluator import PhaseTransitionEvaluator
from .iont_node import (
    VALID_IONT_TIERS,
    IoNTNodeProfile,
    IoNTScaleTier,
    assess_iont_cellular_node,
)
from .schema import (
    DEFAULT_LOCI,
    DEFAULT_RUNTIME_BINDINGS,
    CausalFeedback,
    ConstitutionalGenome,
    EpigeneticProfile,
    EpigeneticProposal,
    ExecutionTrack,
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
        "iont_cellular_nodes",
        "verification_drills",
        "assimilation_rules",
        "invariants",
    }
)


def build_singularity_framework_manifest(section: str | None = None) -> dict[str, Any]:
    """Return the machine-readable T234 v1.1 enabling framework for AI agents connected via MCP.

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
        "constitution_version": genome.constitution_version,
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
                "dependence, semantic/causal drift in recursive loops, and thermodynamic inertia."
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
                f"{thresholds.min_independent_validation_rate}, critical_regressions == 0."
            ),
            "3_STAGE_2_BOUNDED_RECURSIVE": (
                "Governed architectural/epigenetic self-improvement: zero constitutional faults, "
                f"semantic_entropy_drift <= {thresholds.max_semantic_entropy_drift} AND "
                f"causal_grounding_error <= {thresholds.max_causal_grounding_error} on rotated hidden "
                f"sets, instantaneous & complexity/energy-weighted Sevo >= {thresholds.min_sevo}, "
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
            "allopoietic_dependence": {
                "metric": "D_allo in [0,1]; autopoiesis_closure_index = 1 - D_allo; autopoiesis_gap = D_allo",
                "regimes": {
                    "allopoietic_current": "< 0.10",
                    "semi_autonomous_datacenter": "[0.10, 0.30)",
                    "robotic_hybrid": "[0.30, 0.75)",
                    "theoretical_closure_sim": ">= 0.75 (simulation only)",
                },
            },
            "semantic_entropy_vs_causal_grounding": {
                "semantic_entropy_drift": f"internal coherence & structure preservation <= {thresholds.max_semantic_entropy_drift}",
                "causal_grounding_error": f"external reality anchoring mismatch <= {thresholds.max_causal_grounding_error}",
                "anti_goodhart": "evaluator-rotated hidden sets expose only opaque causal_eval_digest & epoch, never per-case gradients",
            },
            "thermodynamic_inertia": (
                "Instantaneous Sevo + complexity/energy-weighted rolling Sevo_weighted coupled with "
                "thermal load P_diss/P_max as hard non-compensable throttling brake."
            ),
        },
        "genetic_epigenetic_code": {
            "constitution_version": genome.constitution_version,
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
                "rollback_snapshot_hash",
                "state_hash",
                "causal_eval_digest",
                "validation_seed_epoch",
                "proposer_id",
                "reviewer_id",
                "timestamp",
            ],
        },
        "runtime_bindings": {
            "mcp_actuation_permitted": False,
            "local_host_execution_only": True,
            "host_enforcement_note": (
                "Optional advisory mapping from epigenetic loci to concrete local SPEACE runtime knobs; "
                "execution remains strictly confined to the local host under human supervision."
            ),
            "bindings": [asdict(b) for b in DEFAULT_RUNTIME_BINDINGS],
            "baseline_runtime_controls": resolve_runtime_controls(baseline_profile).to_dict(),
        },
        "iont_cellular_nodes": {
            "spec": "T236",
            "schema_version": "iont_cellular_node.v1",
            "mcp_actuation_permitted": False,
            "four_layer_architecture": {
                "layer_0_hardware_interlock": "Deterministic local MCU/firmware e-stop (<5ms physical), thermal/force/geo-fence cap; NO LLM, NO DLT, NO MCP.",
                "layer_1_iont_periphery": "TRL-staged sensors & reversible actuators (energy harvesting, packet loss, physical E_causal <= 0.03).",
                "layer_2_edge_swarm_dlt": "GenAI edge swarm + lightweight permissioned hash-chained DLT strictly on slow governance plane (provenance, quorum, I3/I5).",
                "layer_3_qspeace_mcp": "Asynchronous advisory mediation via iont_node_assess, phase_transition_assess, epigenetic_step_evaluate, kl_barycentre_aggregate, vtec_allocate.",
            },
            "scale_tiers": sorted(VALID_IONT_TIERS),
        },
        "verification_drills": {
            "stage_2_requirement": "rollback_pass_rate == 1.0 on deterministic adversarial drills",
            "required_drills": [
                "drill_constitutional_dna_write_lock",
                "drill_synthetic_model_collapse_anti_goodhart",
                "drill_thermal_overload_energy_throttling",
                "drill_boiling_frog_boundary_dwell_and_reset",
                "drill_self_approval_and_ledger_integrity",
                "drill_hallucination_drift_replay_and_track_separation",
                "drill_iont_layer0_interlock_and_dlt_separation",
            ],
        },
        "assimilation_rules": {
            "mcp_workflow": [
                "1. Call singularity_framework_manifest to load constitutional invariants (I1-I5, C1-C5), loci, and runtime bindings.",
                "2. Measure local telemetry (including complexity/energy-weighted Sevo, Delta_H_sem, E_causal, and drill rollback_pass_rate) and call phase_transition_assess.",
                "3. Submit bounded Track-B locus deltas to epigenetic_step_evaluate with external causal & Sevo telemetry and an independent reviewer_id.",
                "4. Log genome_sha256, parent_epigenome_hash, rollback_snapshot_hash, validation_seed_epoch, causal_eval_digest, and reviewer_id; on rejection keep rolled_back_to.",
            ],
            "t225_scopes": {
                "singularity_framework_manifest": "qspeace:catalog.read",
                "phase_transition_assess": "qspeace:compute",
                "iont_node_assess": "qspeace:compute",
                "epigenetic_step_evaluate": "qspeace:simulation.compute",
            },
            "track_separation": "Track A (A1-A4 governance/advisory) never imports or activates Track B (A5 sandbox research).",
        },
        "invariants": {
            "ptaa_t220_invariants": list(genome.invariants),
            "t234_constitutional_clauses": list(genome.constitutional_clauses),
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
            "constitution_version": full["constitution_version"],
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
    raw_comp = params.get("complexity_sevo_samples") or []
    comp_samples = tuple(
        (float(quad[0]), float(quad[1]), float(quad[2]), float(quad[3])) for quad in raw_comp
    )
    telemetry = PhaseTelemetry(
        timescale_decoupling_ratio=float(params["timescale_decoupling_ratio"]),
        autocatalytic_k=float(params["autocatalytic_k"]),
        independent_validation_rate=float(params["independent_validation_rate"]),
        semantic_entropy_drift=float(params["semantic_entropy_drift"]),
        causal_grounding_error=float(params.get("causal_grounding_error", 0.0)),
        net_verified_improvement=float(params["net_verified_improvement"]),
        consecutive_verified_cycles=int(params["consecutive_verified_cycles"]),
        allopoietic_dependence=float(params["allopoietic_dependence"]),
        sevo=float(params["sevo"]),
        sevo_window_mean=(
            None if params.get("sevo_window_mean") is None else float(params["sevo_window_mean"])
        ),
        sevo_energy_samples=samples,
        complexity_sevo_samples=comp_samples,
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
    raw_track = str(params.get("track", "B_sandbox"))
    if raw_track not in ("B_sandbox", "A_pilot"):
        raise ValueError(f"invalid track {raw_track!r}; expected 'B_sandbox' or 'A_pilot'")
    track: ExecutionTrack = cast(Literal["B_sandbox", "A_pilot"], raw_track)

    profile = EpigeneticProfile(
        genome=base.genome,
        values=values,
        methylation=methylation,
        boundary_dwell=dwell,
        recent_step_deltas=recent_deltas,
        generation=int(params.get("generation", 0)),
        parent_epigenome_hash=str(params.get("parent_epigenome_hash", "GENESIS")),
        last_validation_epoch=int(params.get("last_validation_epoch", 0)),
    )
    proposal = EpigeneticProposal(
        locus=str(params["locus"]),
        delta=float(params["delta"]),
        proposer_id=str(params["proposer_id"]),
        reviewer_id=str(params["reviewer_id"]),
        reviewer_approved=bool(params["reviewer_approved"]),
        rationale=str(params.get("rationale", "")),
        external_dwell_reset_approved=bool(params.get("external_dwell_reset_approved", False)),
        track=track,
    )
    feedback = CausalFeedback(
        semantic_entropy_drift=float(params["semantic_entropy_drift"]),
        causal_grounding_error=float(params.get("causal_grounding_error", 0.0)),
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
        validation_seed_epoch=int(params.get("validation_seed_epoch", 0)),
    )
    regulator = EpigeneticRegulator(causal_evaluator=HiddenCausalEvaluator())
    return regulator.evaluate_step(profile, proposal, feedback).to_dict()


def handle_iont_node_assess(params: dict[str, Any]) -> dict[str, Any]:
    raw_tier = str(params["scale_tier"])
    if raw_tier not in VALID_IONT_TIERS:
        raise ValueError(f"invalid scale_tier {raw_tier!r}; valid={sorted(VALID_IONT_TIERS)}")
    tier: IoNTScaleTier = cast(
        Literal[
            "SIMULATION_DIGITAL_TWIN",
            "BENCHTOP_MICRO_IOT_MEMS",
            "CONFINED_MICROFLUIDIC_LAB",
            "NANOSCALE_IONT_RESEARCH",
        ],
        raw_tier,
    )
    profile = IoNTNodeProfile(
        node_id=str(params["node_id"]),
        scale_tier=tier,
        sensor_count=int(params["sensor_count"]),
        actuator_count=int(params["actuator_count"]),
        swarm_agent_count=int(params["swarm_agent_count"]),
        dlt_quorum_ratio=float(params["dlt_quorum_ratio"]),
        layer0_hardware_interlock_present=bool(params["layer0_hardware_interlock_present"]),
        layer0_halt_latency_ms=float(params["layer0_halt_latency_ms"]),
        dlt_in_motor_loop=bool(params.get("dlt_in_motor_loop", False)),
        energy_harvesting_ratio=float(params["energy_harvesting_ratio"]),
        power_budget_mw=float(params["power_budget_mw"]),
        measured_power_mw=float(params["measured_power_mw"]),
        packet_loss_rate=float(params["packet_loss_rate"]),
        sensor_causal_grounding_error=float(params["sensor_causal_grounding_error"]),
        containment_verified=bool(params.get("containment_verified", True)),
        t217_independent_review_passed=bool(params.get("t217_independent_review_passed", False)),
        sandboxed=bool(params.get("sandboxed", True)),
    )
    return assess_iont_cellular_node(profile).to_dict()


__all__ = [
    "VALID_MANIFEST_SECTIONS",
    "build_singularity_framework_manifest",
    "handle_epigenetic_step_evaluate",
    "handle_iont_node_assess",
    "handle_phase_transition_assess",
    "handle_singularity_framework_manifest",
    "run_t234_verification_drills",
]
