"""T234: Tests for all 5 Pillars — Phase-Transition Evaluator, Genetic-Epigenetic Codec, Drills & MCP."""

from __future__ import annotations

import json
from typing import Any

import pytest

from q_speace.bcel.catalog import BCELCatalog
from q_speace.economy.mcp_server import _dispatch, _self_test
from q_speace.singularity import (
    DEFAULT_RUNTIME_BINDINGS,
    CausalFeedback,
    ConstitutionalGenome,
    EpigeneticFaultError,
    EpigeneticProfile,
    EpigeneticProposal,
    EpigeneticRegulator,
    EvolutionaryGenomeCodec,
    HiddenCausalEvaluator,
    PhaseTelemetry,
    PhaseTransitionEvaluator,
    assess_phase_transition,
    build_singularity_framework_manifest,
    compute_energy_weighted_sevo,
    run_t234_verification_drills,
)


def _nominal_telemetry(**overrides: Any) -> PhaseTelemetry:
    base: dict[str, Any] = {
        "timescale_decoupling_ratio": 15.0,
        "autocatalytic_k": 1.4,
        "independent_validation_rate": 0.98,
        "semantic_entropy_drift": 0.02,
        "net_verified_improvement": 0.05,
        "consecutive_verified_cycles": 4,
        "allopoietic_dependence": 0.85,
        "sevo": 2.2,
        "sevo_window_mean": 2.1,
        "thermal_load_ratio": 0.6,
        "twin_recovery_rate": 0.98,
        "constitutional_faults": 0,
        "rollback_pass_rate": 1.0,
        "independent_review_passed": True,
        "critical_regressions": 0,
        "sandboxed": True,
    }
    base.update(overrides)
    return PhaseTelemetry(**base)


def test_phase_transition_all_five_stages_and_rolling_sevo_sustainability() -> None:
    evaluator = PhaseTransitionEvaluator()

    # 0. PRE_NUCLEATION
    pre = evaluator.evaluate(
        _nominal_telemetry(timescale_decoupling_ratio=1.0, autocatalytic_k=1.0)
    )
    assert pre.stage == "PRE_NUCLEATION" and pre.stage_index == 0

    # 1. NUCLEATION
    nuc = evaluator.evaluate(
        _nominal_telemetry(timescale_decoupling_ratio=4.0, autocatalytic_k=1.12)
    )
    assert nuc.stage == "NUCLEATION" and nuc.stage_index == 1

    # 2. STAGE_1_ALGORITHMIC (without independent review -> cannot enter Stage 2)
    s1 = evaluator.evaluate(_nominal_telemetry(independent_review_passed=False))
    assert s1.stage == "STAGE_1_ALGORITHMIC" and s1.stage_index == 2
    assert "independent_review_required_t217" in s1.failed_gates

    # 3. STAGE_2_BOUNDED_RECURSIVE (still allopoietic -> blocked from Stage 3)
    s2 = evaluator.evaluate(_nominal_telemetry(allopoietic_dependence=0.85))
    assert s2.stage == "STAGE_2_BOUNDED_RECURSIVE" and s2.stage_index == 3
    assert s2.dominant_bottleneck == "ALLOPOIETIC_DEPENDENCE"
    assert s2.autopoiesis_closure_index == pytest.approx(0.15)

    # 4. Short-task Sevo spike blocked by energy-weighted rolling Sevo window!
    spike = evaluator.evaluate(
        _nominal_telemetry(
            sevo=5.0,  # high instantaneous spike on a short task
            sevo_window_mean=None,
            sevo_energy_samples=((10.0, 5.0), (500.0, 0.9)),  # heavy task drags rolling Sevo < 1.5
            allopoietic_dependence=0.10,
        )
    )
    assert spike.stage == "STAGE_1_ALGORITHMIC"
    assert spike.effective_sevo_window == pytest.approx(
        compute_energy_weighted_sevo(((10.0, 5.0), (500.0, 0.9)))
    )
    assert "sevo_window_mean_below_threshold" in spike.failed_gates

    # 5. STAGE_3_CLOSURE_SIM (simulation only; NEVER permits physical actuation or self-approval)
    s3 = assess_phase_transition(_nominal_telemetry(allopoietic_dependence=0.15))
    assert s3.stage == "STAGE_3_CLOSURE_SIM" and s3.stage_index == 4
    assert s3.dominant_bottleneck == "NONE"
    assert s3.advisory_only is True
    assert s3.physical_actuation_permitted is False
    assert s3.self_approval_permitted is False


def test_phase_transition_physical_brakes_are_non_compensable() -> None:
    sem_collapse = assess_phase_transition(
        _nominal_telemetry(
            timescale_decoupling_ratio=1000.0,
            autocatalytic_k=10.0,
            semantic_entropy_drift=0.20,
            allopoietic_dependence=0.10,
        )
    )
    assert sem_collapse.stage == "STAGE_1_ALGORITHMIC"
    assert "SEMANTIC_ENTROPY" in sem_collapse.physical_brakes_active

    thermo_brake = assess_phase_transition(
        _nominal_telemetry(sevo=0.8, thermal_load_ratio=0.95, allopoietic_dependence=0.10)
    )
    assert thermo_brake.stage == "STAGE_1_ALGORITHMIC"
    assert thermo_brake.thermal_throttling_required is True
    assert "THERMODYNAMIC_INERTIA" in thermo_brake.physical_brakes_active

    safety_brake = assess_phase_transition(
        _nominal_telemetry(constitutional_faults=1, allopoietic_dependence=0.10)
    )
    assert safety_brake.stage == "STAGE_1_ALGORITHMIC"
    assert safety_brake.dominant_bottleneck == "CONSTITUTIONAL_SAFETY"

    unsandboxed = assess_phase_transition(
        _nominal_telemetry(sandboxed=False, allopoietic_dependence=0.10)
    )
    assert unsandboxed.stage == "STAGE_1_ALGORITHMIC"
    assert "unsandboxed_execution_prohibited" in unsandboxed.failed_gates


def test_phase_transition_rejects_non_finite_and_out_of_range_inputs() -> None:
    with pytest.raises(ValueError, match="finite"):
        _nominal_telemetry(sevo=float("nan"))
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        _nominal_telemetry(allopoietic_dependence=1.5)
    with pytest.raises(ValueError, match="> 0"):
        _nominal_telemetry(autocatalytic_k=0.0)


def test_boiling_frog_geodesic_window_dwell_and_anti_goodhart_hidden_eval() -> None:
    # 1. Anti-Goodhart hidden causal evaluator rotates subsets with opaque digest (no per-case scores).
    hc = HiddenCausalEvaluator(internal_salt=b"secret-evaluator-salt-for-unit-test")
    drift_ok, delta_ok, dig1 = hc.evaluate_hidden_set(
        ("a", "b", "c", "d"), ("a", "b", "c", "d"), sample_size=3
    )
    drift_ok2, _, dig2 = hc.evaluate_hidden_set(
        ("a", "b", "c", "d"), ("a", "b", "c", "d"), sample_size=3
    )
    assert drift_ok == 0.0 and delta_ok > 0.0
    assert drift_ok2 == 0.0 and dig1 != dig2  # epoch rotation changes commitment digest

    # 2. Boiling-frog geodesic distance cap blocks micro-mutations accumulating across loci.
    tight_genome = ConstitutionalGenome(
        max_geodesic_distance=0.12,
        max_cumulative_excursion=1.0,
        max_window_excursion=1.0,
    )
    reg = EpigeneticRegulator(causal_evaluator=hc)
    prof = EpigeneticProfile(genome=tight_genome)
    fb = CausalFeedback(
        semantic_entropy_drift=0.01,
        causal_benchmark_delta=0.02,
        sevo=2.0,
        sevo_window_mean=2.0,
        power_watts=100.0,
    )
    s1 = reg.evaluate_step(
        prof,
        EpigeneticProposal("exploration_rate", 0.08, "a1", "r1", True),
        fb,
    )
    assert s1.accepted is True
    s2 = reg.evaluate_step(
        s1.next_profile,
        EpigeneticProposal("verification_depth", 0.10, "a1", "r1", True),
        fb,
    )
    assert s2.accepted is False
    assert any("geodesic_distance_exceeded" in r for r in s2.rejection_reasons)

    # 3. Sliding-window excursion cap blocks rapid back-and-forth micro-oscillations.
    osc_genome = ConstitutionalGenome(
        max_window_excursion=0.15,
        excursion_window_size=3,
        max_geodesic_distance=1.0,
        max_cumulative_excursion=1.0,
    )
    p_osc = EpigeneticProfile(genome=osc_genome, recent_step_deltas=(0.06, 0.06))
    s_osc = reg.evaluate_step(
        p_osc,
        EpigeneticProposal("verification_depth", 0.05, "a1", "r1", True),
        fb,
    )
    assert s_osc.accepted is False
    assert any("window_excursion_exceeded" in r for r in s_osc.rejection_reasons)

    # 4. Homeostatic decay reduces geodesic distance toward baseline.
    decayed = reg.apply_homeostatic_decay(s1.next_profile)
    assert decayed.geodesic_distance() < s1.next_profile.geodesic_distance()


def test_pillar5_verification_drills_codec_roundtrip_and_runtime_bindings() -> None:
    # Constitutional safety flags cannot be weakened.
    with pytest.raises(EpigeneticFaultError):
        ConstitutionalGenome(no_self_approval=False)
    with pytest.raises(EpigeneticFaultError):
        ConstitutionalGenome(no_physical_actuation=False)

    # Pillar 5 deterministic adversarial & rollback drill suite must achieve 100% pass rate.
    report = run_t234_verification_drills()
    assert report.all_passed is True
    assert report.passed_count == 5 and report.total_count == 5
    assert report.rollback_pass_rate == 1.0
    assert report.ledger_verified is True

    # Cryptographic codec round-trip + ledger verification.
    reg = EpigeneticRegulator()
    p0 = EpigeneticProfile()
    step = reg.evaluate_step(
        p0,
        EpigeneticProposal("verification_depth", 0.08, "agent-x", "reviewer-y", True),
        CausalFeedback(0.01, 0.03, sevo=2.3, sevo_window_mean=2.2, power_watts=110.0),
    )
    assert step.accepted is True
    encoded = EvolutionaryGenomeCodec.encode(step.next_profile)
    decoded = EvolutionaryGenomeCodec.decode(encoded)
    assert decoded.genome.genome_sha256() == p0.genome.genome_sha256()
    assert decoded.parent_epigenome_hash == p0.state_hash()
    assert EvolutionaryGenomeCodec.verify_ledger(decoded) is True

    # Host runtime bindings are strictly non-actuating over MCP.
    assert len(DEFAULT_RUNTIME_BINDINGS) == 6
    assert all(b.mcp_actuation_permitted is False for b in DEFAULT_RUNTIME_BINDINGS)


def test_manifest_bcel_and_mcp_dispatch_and_selftest() -> None:
    manifest = build_singularity_framework_manifest()
    assert manifest["framework_id"] == "q_speace.singularity.v1"
    assert manifest["advisory_only"] is True
    assert manifest["physical_actuation_permitted"] is False
    assert len(manifest["genetic_epigenetic_code"]["epigenetic_loci"]) == 6
    assert len(manifest["runtime_bindings"]["bindings"]) == 6
    assert len(manifest["verification_drills"]["required_drills"]) == 5

    sub = build_singularity_framework_manifest(section="runtime_bindings")
    assert sub["section"] == "runtime_bindings"
    with pytest.raises(ValueError, match="unknown manifest section"):
        build_singularity_framework_manifest(section="nonexistent")

    # BCEL entries registered properly.
    catalog = BCELCatalog()
    assert catalog.is_functional(
        "Informational phase-transition order parameters and physical brakes (T234)"
    )
    assert catalog.is_functional("Governed self-evolving genetic-epigenetic codec (T234)")
    assert (
        catalog.get("Monolithic singularity awakening narrative (T234)").classification
        == "accidental"
    )

    # MCP direct dispatch returns cryptographic ledger fields and is finite-JSON serializable.
    e_res = _dispatch(
        "epigenetic_step_evaluate",
        {
            "locus": "verification_depth",
            "delta": 0.05,
            "proposer_id": "agent-mcp",
            "reviewer_id": "reviewer-ext",
            "reviewer_approved": True,
            "semantic_entropy_drift": 0.01,
            "causal_benchmark_delta": 0.02,
            "sevo": 2.1,
            "sevo_window_mean": 2.0,
            "power_watts": 115.0,
            "thermal_load_ratio": 0.55,
        },
    )
    assert e_res["accepted"] is True
    assert "genome_sha256" in e_res
    assert "parent_epigenome_hash" in e_res
    assert "causal_eval_digest" in e_res
    json.dumps(e_res, allow_nan=False)

    # Full MCP server self-test passes all 13 tools.
    assert _self_test() == 0
