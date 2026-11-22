"""T234 v1.1: Tests for all 5 Pillars — Evaluator, Codec Bridges, Drills, Runtime Controls & MCP."""

from __future__ import annotations

import json
from typing import Any

import pytest

from q_speace.bcel.catalog import BCELCatalog
from q_speace.economy.mcp_server import _dispatch, _self_test
from q_speace.seed.constitution import SeedGenome
from q_speace.self_improvement_cortex.epigenetics import EpigeneticMarker
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
    classify_autopoiesis_regime,
    compute_complexity_weighted_sevo,
    compute_energy_weighted_sevo,
    resolve_runtime_controls,
    run_t234_verification_drills,
)


def _nominal_telemetry(**overrides: Any) -> PhaseTelemetry:
    base: dict[str, Any] = {
        "timescale_decoupling_ratio": 15.0,
        "autocatalytic_k": 1.4,
        "independent_validation_rate": 0.98,
        "semantic_entropy_drift": 0.02,
        "causal_grounding_error": 0.01,
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


def test_phase_transition_stages_separate_ecausal_complexity_sevo_and_regimes() -> None:
    evaluator = PhaseTransitionEvaluator()

    # 0. PRE_NUCLEATION & 1. NUCLEATION
    pre = evaluator.evaluate(
        _nominal_telemetry(timescale_decoupling_ratio=1.0, autocatalytic_k=1.0)
    )
    assert pre.stage == "PRE_NUCLEATION" and pre.stage_index == 0
    nuc = evaluator.evaluate(
        _nominal_telemetry(timescale_decoupling_ratio=4.0, autocatalytic_k=1.12)
    )
    assert nuc.stage == "NUCLEATION" and nuc.stage_index == 1

    # Stage 1 blocked when critical_regressions > 0 (T234 §2 Stage 1 invariant)
    reg_s1 = evaluator.evaluate(_nominal_telemetry(critical_regressions=1))
    assert reg_s1.stage == "NUCLEATION"
    assert reg_s1.stage_gates["stage_1_algorithmic"] is False

    # 2. STAGE_1_ALGORITHMIC (no independent review -> cannot advance to Stage 2)
    s1 = evaluator.evaluate(_nominal_telemetry(independent_review_passed=False))
    assert s1.stage == "STAGE_1_ALGORITHMIC" and s1.stage_index == 2
    assert "independent_review_required_t217" in s1.failed_gates

    # Coherent hallucination drift: Delta_H_sem=0.0 but E_causal=0.08 (>0.03) blocks Stage 2!
    hal = evaluator.evaluate(
        _nominal_telemetry(semantic_entropy_drift=0.0, causal_grounding_error=0.08)
    )
    assert hal.stage == "STAGE_1_ALGORITHMIC"
    assert "CAUSAL_GROUNDING_ERROR" in hal.physical_brakes_active
    assert "causal_grounding_error_exceeded" in hal.failed_gates
    assert hal.reality_grounding_index == pytest.approx(0.92)

    # 3. STAGE_2_BOUNDED_RECURSIVE & Autopoiesis Regime telemetry
    s2 = evaluator.evaluate(_nominal_telemetry(allopoietic_dependence=0.85))
    assert s2.stage == "STAGE_2_BOUNDED_RECURSIVE" and s2.stage_index == 3
    assert s2.autopoiesis_closure_index == pytest.approx(0.15)
    assert s2.autopoiesis_gap == pytest.approx(0.85)
    assert s2.autopoiesis_regime == "semi_autonomous_datacenter"
    assert classify_autopoiesis_regime(0.02) == "allopoietic_current"
    assert classify_autopoiesis_regime(0.45) == "robotic_hybrid"
    assert classify_autopoiesis_regime(0.85) == "theoretical_closure_sim"

    # 4. Complexity-weighted Sevo blocks trivial micro-task farming!
    comp_samples = (
        (0.1, 10.0, 1.0, 1.0),  # tiny trivial task with Sevo=10
        (10.0, 1.0, 2.0, 1.0),  # high-complexity real task with Sevo=0.5
    )
    comp_sevo = compute_complexity_weighted_sevo(comp_samples)
    assert comp_sevo < 1.5
    farmed = evaluator.evaluate(
        _nominal_telemetry(
            sevo=10.0,
            sevo_window_mean=None,
            complexity_sevo_samples=comp_samples,
            allopoietic_dependence=0.10,
        )
    )
    assert farmed.stage == "STAGE_1_ALGORITHMIC"
    assert farmed.effective_sevo_window == pytest.approx(comp_sevo)
    assert "sevo_window_mean_below_threshold" in farmed.failed_gates

    # Energy-weighted rolling Sevo fallback still works too
    e_samples = ((10.0, 5.0), (500.0, 0.9))
    assert compute_energy_weighted_sevo(e_samples) < 1.5

    # 5. STAGE_3_CLOSURE_SIM (simulation only; NEVER permits physical actuation or self-approval)
    s3 = assess_phase_transition(_nominal_telemetry(allopoietic_dependence=0.15))
    assert s3.stage == "STAGE_3_CLOSURE_SIM" and s3.stage_index == 4
    assert s3.autopoiesis_regime == "theoretical_closure_sim"
    assert s3.dominant_bottleneck == "NONE"
    assert s3.advisory_only is True
    assert s3.physical_actuation_permitted is False
    assert s3.self_approval_permitted is False


def test_phase_transition_rejects_non_finite_and_invalid_samples() -> None:
    with pytest.raises(ValueError, match="finite"):
        _nominal_telemetry(sevo=float("nan"))
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        _nominal_telemetry(causal_grounding_error=1.2)
    with pytest.raises(ValueError, match="delta_s > 0"):
        _nominal_telemetry(complexity_sevo_samples=((1.0, 2.0, 1.0, 0.0),))


def test_constitution_clauses_bridges_cosmic_virus_and_runtime_controls() -> None:
    # 1. ConstitutionalGenome seals I1-I5 (PTAA/T220) + C1-C5 (T234) with constitution_version="1.0".
    g = ConstitutionalGenome()
    assert g.constitution_version == "1.0"
    assert len(g.invariants) == 5 and len(g.constitutional_clauses) == 5
    assert "C1_HumanApprovalRequired" in g.constitutional_clauses
    with pytest.raises(EpigeneticFaultError):
        ConstitutionalGenome(no_self_approval=False)

    # 2. Bridge from q_speace/seed/ SeedGenome -> ConstitutionalGenome.
    seed_g = SeedGenome()
    bridged_g = EvolutionaryGenomeCodec.from_seed_genome(seed_g)
    assert bridged_g.max_cumulative_excursion == seed_g.resource_caps.max_cumulative_excursion

    # 3. CosmicVirus bounded evolutionary variant generator + cortex EpigeneticTag bridge.
    hc = HiddenCausalEvaluator(internal_salt=b"t234-v1-1-test-salt-bytes-32char")
    reg = EpigeneticRegulator(causal_evaluator=hc)
    p0 = EpigeneticProfile(genome=bridged_g)
    cv_prop = reg.propose_cosmic_virus_variant(
        p0,
        locus="verification_depth",
        gradient_s_info=1.5,
        proposer_id="cv-agent",
        reviewer_id="ext-reviewer",
        reviewer_approved=True,
        seed=42,
    )
    assert cv_prop.track == "B_sandbox"
    assert abs(cv_prop.delta) <= 0.15
    step = reg.evaluate_step(
        p0,
        cv_prop,
        CausalFeedback(
            semantic_entropy_drift=0.01,
            causal_grounding_error=0.005,
            causal_benchmark_delta=0.02,
            sevo=2.2,
            sevo_window_mean=2.1,
            power_watts=110.0,
        ),
    )
    assert step.accepted is True
    marks = EvolutionaryGenomeCodec.to_cortex_epigenetic_marks(step.next_profile)
    assert set(marks.keys()) == set(p0.values.keys())
    assert all(isinstance(t.marker, EpigeneticMarker) for t in marks.values())

    # 4. Concrete SPEACE runtime control vector responds monotonically to energy_throttling.
    c_base = resolve_runtime_controls(p0)
    high_thr = EpigeneticProfile(
        values={**p0.values, "energy_throttling": 0.90, "verification_depth": 0.95}
    )
    c_thr = resolve_runtime_controls(high_thr)
    assert c_thr.cpu_quota < c_base.cpu_quota
    assert c_thr.gpu_quota < c_base.gpu_quota
    assert c_thr.token_budget < c_base.token_budget
    assert c_thr.max_review_cycles > c_base.max_review_cycles
    assert c_thr.advisory_only is True and c_thr.mcp_actuation_permitted is False


def test_boiling_frog_geodesic_window_and_ledger_replay_verification() -> None:
    hc = HiddenCausalEvaluator(internal_salt=b"secret-evaluator-salt-for-unit-test")
    sem_d, err_c, delta_ok, dig1, ep1 = hc.evaluate_hidden_set(
        ("a", "b", "c", "d"), ("a", "b", "c", "d"), sample_size=3
    )
    _, _, _, dig2, ep2 = hc.evaluate_hidden_set(
        ("a", "b", "c", "d"), ("a", "b", "c", "d"), sample_size=3
    )
    assert sem_d == 0.0 and err_c == 0.0 and delta_ok > 0.0
    assert dig1 != dig2 and ep2 == ep1 + 1

    # Geodesic distance cap
    tight = ConstitutionalGenome(
        max_geodesic_distance=0.12, max_cumulative_excursion=1.0, max_window_excursion=1.0
    )
    reg = EpigeneticRegulator(causal_evaluator=hc)
    prof = EpigeneticProfile(genome=tight)
    fb = CausalFeedback(0.01, 0.02, sevo=2.0, sevo_window_mean=2.0, power_watts=100.0)
    s1 = reg.evaluate_step(prof, EpigeneticProposal("exploration_rate", 0.08, "a1", "r1", True), fb)
    assert s1.accepted is True
    s2 = reg.evaluate_step(
        s1.next_profile, EpigeneticProposal("verification_depth", 0.10, "a1", "r1", True), fb
    )
    assert s2.accepted is False
    assert any("geodesic_distance_exceeded" in r for r in s2.rejection_reasons)

    # Codec roundtrip + extended ledger verification (epoch, rollback_snapshot_hash, timestamp)
    encoded = EvolutionaryGenomeCodec.encode(s1.next_profile)
    decoded = EvolutionaryGenomeCodec.decode(encoded)
    assert EvolutionaryGenomeCodec.verify_ledger(decoded) is True
    assert decoded.audit_ledger[0].rollback_snapshot_hash == prof.state_hash()
    assert decoded.audit_ledger[0].validation_seed_epoch >= 1

    # Homeostatic decay pulls back toward baseline
    decayed = reg.apply_homeostatic_decay(s1.next_profile)
    assert decayed.geodesic_distance() < s1.next_profile.geodesic_distance()


def test_pillar5_six_verification_drills_and_mcp_assimilation() -> None:
    report = run_t234_verification_drills()
    assert report.all_passed is True
    assert report.passed_count == 6 and report.total_count == 6
    assert report.rollback_pass_rate == 1.0
    assert report.ledger_verified is True

    manifest = build_singularity_framework_manifest()
    assert manifest["framework_id"] == "q_speace.singularity.v1"
    assert manifest["constitution_version"] == "1.0"
    assert len(DEFAULT_RUNTIME_BINDINGS) == 6
    assert len(manifest["verification_drills"]["required_drills"]) == 6
    assert "baseline_runtime_controls" in manifest["runtime_bindings"]

    catalog = BCELCatalog()
    assert catalog.is_functional(
        "Informational phase-transition order parameters and physical brakes (T234)"
    )
    assert catalog.is_functional("Governed self-evolving genetic-epigenetic codec (T234)")
    assert (
        catalog.get("Monolithic singularity awakening narrative (T234)").classification
        == "accidental"
    )

    # MCP dispatch returns extended ledger + runtime_controls + track separation flag
    e_res = _dispatch(
        "epigenetic_step_evaluate",
        {
            "locus": "verification_depth",
            "delta": 0.05,
            "proposer_id": "agent-mcp",
            "reviewer_id": "reviewer-ext",
            "reviewer_approved": True,
            "semantic_entropy_drift": 0.01,
            "causal_grounding_error": 0.005,
            "causal_benchmark_delta": 0.02,
            "sevo": 2.1,
            "sevo_window_mean": 2.0,
            "power_watts": 115.0,
            "thermal_load_ratio": 0.55,
            "validation_seed_epoch": 5,
            "track": "B_sandbox",
        },
    )
    assert e_res["accepted"] is True
    assert e_res["track_separation_enforced"] is True
    assert e_res["validation_seed_epoch"] == 5
    assert "rollback_snapshot_hash" in e_res
    assert e_res["runtime_controls"]["mcp_actuation_permitted"] is False
    json.dumps(e_res, allow_nan=False)

    # Track-A pilot attempt rejected via MCP too
    e_track_a = _dispatch(
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
            "power_watts": 115.0,
            "track": "A_pilot",
        },
    )
    assert e_track_a["accepted"] is False
    assert any("track_separation_violation" in r for r in e_track_a["rejection_reasons"])

    assert _self_test() == 0
