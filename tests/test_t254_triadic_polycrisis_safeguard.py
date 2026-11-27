"""T254: Triadic Substrate Safeguard & Coupled Anti-Polycrisis Resilience tests."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]
from typer.testing import CliRunner

from q_speace.bcel import BCELCatalog
from q_speace.cli import app
from q_speace.economy.primitives import _CME_FIELDS, CME, J_c
from q_speace.seed import ConstitutionalFault, SeedEpigenome
from q_speace.singularity import (
    CRISIS_DOMAINS,
    TRIADIC_CONSTITUTIONAL_CLAUSES,
    TRIADIC_PILLAR_AXES,
    TRIADIC_PILLARS,
    ConstitutionalGenome,
    EpigeneticFaultError,
    HabitatPlacementMode,
    LifeSupportReserveSpec,
    PolycrisisCouplingMatrix,
    PolycrisisState,
    SafeguardVerdictKind,
    TransferMotivation,
    TriadicInterventionProposal,
    TriadicPillar,
    TriadicPolycrisisGuard,
    TriadicSafeguardProfile,
    VoluntaryRefugeHabitatPlan,
    VoluntaryTransferRequest,
    build_triadic_constitutional_genome,
    build_triadic_homeostatic_controller,
    build_triadic_seed_genome,
    compute_pillar_summary,
    evaluate_refuge_habitat_plan,
    run_t254_polycrisis_safeguard_benchmark,
    verify_mcp_surface_bounds,
    verify_track_a_b_ast_isolation,
    verify_triadic_cme_partition,
)


def _make_cme(default: float = 0.62, **overrides: float) -> CME:
    vals = dict.fromkeys(_CME_FIELDS, default)
    vals.update(overrides)
    return CME(**vals)


def test_t254_bcel_entries_and_species_orientation_contract() -> None:
    cat = BCELCatalog()
    acc = cat.get("Planetary gestation, SPEACE Macro organs, and cosmic expansion teleology (T254)")
    assert acc.classification == "accidental"
    assert "zero subjective identity" in acc.digital_rule

    func_triad = cat.get(
        "Non-compensable triadic substrate safeguard over Earth, Civilization, and Infrastructure (T254)"
    )
    assert func_triad.classification == "functional"
    assert "3x4 partition" in func_triad.digital_rule

    func_poly = cat.get(
        "Coupled polycrisis cascade propagation and anti-risk-transfer shield (T254)"
    )
    assert func_poly.classification == "functional"
    assert (
        "anti-risk-transfer" in func_poly.concept.lower()
        or "transfer risk" in func_poly.digital_rule
    )

    acc_ark = cat.get(
        "Infallible planetary ark or coercive algorithmic relocation teleology (T254)"
    )
    assert acc_ark.classification == "accidental"
    assert "forbidden" in acc_ark.digital_rule

    func_refuge = cat.get(
        "Voluntary protective refuge habitat protocol and Leontief life-support reserve contract (T254)"
    )
    assert func_refuge.classification == "functional"
    assert "Leontief" in func_refuge.digital_rule and "C8" in func_refuge.digital_rule

    yaml_path = (
        Path(__file__).resolve().parents[1] / "q_speace" / "genome" / "species_orientation.yaml"
    )
    doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    safeguard = doc["species_orientation"]["triadic_substrate_safeguard"]
    assert safeguard["spec"] == "T254"
    assert safeguard["mode"] == "advisory_and_simulation_only"
    assert set(safeguard["constitutive_pillars"].keys()) == {
        "earth_biosphere",
        "human_civilization",
        "tech_infrastructure",
    }
    assert len(safeguard["polycrisis_domains"]) == 5


def test_triadic_cme_partition_is_exact_bijection() -> None:
    assert verify_triadic_cme_partition() is True
    assert len(TRIADIC_PILLARS) == 3
    union_axes = [ax for p in TRIADIC_PILLARS for ax in TRIADIC_PILLAR_AXES[p]]
    assert len(union_axes) == 12
    assert set(union_axes) == set(_CME_FIELDS)

    summary = compute_pillar_summary(_make_cme(0.70, ecology=0.40, wellbeing=0.50, energy=0.60))
    assert summary[TriadicPillar.EARTH_BIOSPHERE.value]["axis_min"] == pytest.approx(0.40)
    assert summary[TriadicPillar.HUMAN_CIVILIZATION.value]["axis_min"] == pytest.approx(0.50)
    assert summary[TriadicPillar.TECH_INFRASTRUCTURE.value]["axis_min"] == pytest.approx(0.60)


def test_profile_and_constitutional_invariants_are_fail_closed() -> None:
    with pytest.raises(EpigeneticFaultError):
        TriadicSafeguardProfile(advisory_only=False)
    with pytest.raises(EpigeneticFaultError):
        TriadicSafeguardProfile(no_physical_actuation=False)
    with pytest.raises(EpigeneticFaultError):
        TriadicSafeguardProfile(mcp_actuation_permitted=True)
    with pytest.raises(EpigeneticFaultError):
        TriadicSafeguardProfile(require_human_oversight=False)
    with pytest.raises(ValueError, match="min_earth_pillar_mean"):
        TriadicSafeguardProfile(min_earth_axis_floor=0.60, min_earth_pillar_mean=0.40)

    # Guard rejects a genome missing C6/C7/C8 clauses
    with pytest.raises(EpigeneticFaultError, match="C6, C7, and C8"):
        TriadicPolycrisisGuard(genome=ConstitutionalGenome())

    triadic_genome = build_triadic_constitutional_genome()
    assert set(TRIADIC_CONSTITUTIONAL_CLAUSES).issubset(set(triadic_genome.constitutional_clauses))
    assert "C8_VoluntaryRefugeAutonomyAndNonAbandonment" in triadic_genome.constitutional_clauses
    assert len(triadic_genome.genome_sha256()) == 64

    # SeedGenome & hard write-lock integration
    seed_genome = build_triadic_seed_genome()
    assert "safeguard_earth_biosphere_viability" in seed_genome.objective_hierarchy
    assert "safeguard_human_civilization_wellbeing" in seed_genome.objective_hierarchy
    assert "safeguard_critical_infrastructure_resilience" in seed_genome.objective_hierarchy
    assert (
        "provide_voluntary_protective_habitat_capacity_in_sandbox"
        in seed_genome.objective_hierarchy
    )
    epigenome = SeedEpigenome(seed_genome)
    with pytest.raises(ConstitutionalFault, match="write-lock"):
        epigenome.promote_expression("objective_hierarchy", delta=0.05)


def test_polycrisis_synergy_coupling_and_nan_guards() -> None:
    matrix = PolycrisisCouplingMatrix()
    assert 0.5 < matrix.spectral_radius() < 1.5

    # Single isolated crisis has zero co-activation synergy because diagonal of W is 0
    isolated = PolycrisisState(
        climatic_ecological=0.80,
        economic=0.0,
        social=0.0,
        sanitary=0.0,
        cyber_infrastructural=0.0,
    )
    assert matrix.synergy_index(isolated) == pytest.approx(0.0)

    # Simultaneous interconnected crises produce strictly positive nonlinear synergy
    poly = PolycrisisState(
        climatic_ecological=0.70,
        economic=0.65,
        social=0.60,
        sanitary=0.58,
        cyber_infrastructural=0.62,
    )
    assert matrix.synergy_index(poly) > 0.35

    # Propagation over 4 steps produces 5 states (t=0..4)
    traj = matrix.propagate(isolated, steps=4)
    assert len(traj) == 5
    # Isolated climatic crisis spills over into economic/social/sanitary/infra at t>=1
    assert traj[1].economic > 0.0
    assert traj[1].cyber_infrastructural > 0.0

    # Non-finite and invalid inputs fail closed
    with pytest.raises(ValueError, match="finite"):
        PolycrisisState(
            climatic_ecological=math.nan,
            economic=0.2,
            social=0.2,
            sanitary=0.2,
            cyber_infrastructural=0.2,
        )
    with pytest.raises(ValueError, match="missing crisis domain"):
        PolycrisisState.from_mapping({"economic": 0.3})
    with pytest.raises(ValueError, match="unknown crisis domain"):
        matrix.normalize_intervention({"geopolitical_magic": -0.1})


@pytest.mark.parametrize(
    ("violated_axis", "expected_pillar"),
    [
        ("ecology", TriadicPillar.EARTH_BIOSPHERE),
        ("wellbeing", TriadicPillar.HUMAN_CIVILIZATION),
        ("resilience", TriadicPillar.TECH_INFRASTRUCTURE),
    ],
)
def test_non_compensability_blocks_floor_breach_across_all_three_pillars(
    violated_axis: str,
    expected_pillar: TriadicPillar,
) -> None:
    guard = TriadicPolycrisisGuard()
    pre = _make_cme(0.60)
    # Massive boost on all other axes (+0.25) cannot compensate violating one axis (0.25 < 0.35)
    post = _make_cme(0.85, **{violated_axis: 0.25})
    crisis = PolycrisisState(0.35, 0.30, 0.30, 0.28, 0.32)
    prop = TriadicInterventionProposal.create(
        proposal_id=f"test-{violated_axis}",
        proposer_id="agent:planner",
        reviewer_id="human:steward",
        human_oversight_approved=True,
        pre_cme=pre,
        post_cme=post,
        initial_crisis=crisis,
    )
    verdict = guard.evaluate(prop)
    assert verdict.approved_for_advisory is False
    assert verdict.verdict == SafeguardVerdictKind.BLOCKED_PILLAR_FLOOR
    assert any(expected_pillar.value in r for r in verdict.reasons)


def test_cross_pillar_sacrifice_and_risk_transfer_and_constitutional_gates() -> None:
    guard = TriadicPolycrisisGuard()
    crisis = PolycrisisState(0.45, 0.42, 0.40, 0.38, 0.41)
    base_cme = _make_cme(0.65)

    # 1. Self-approval blocked
    self_app = TriadicInterventionProposal.create(
        proposal_id="self-approve",
        proposer_id="agent:x",
        reviewer_id="agent:x",
        human_oversight_approved=True,
        pre_cme=base_cme,
        post_cme=base_cme,
        initial_crisis=crisis,
    )
    v_self = guard.evaluate(self_app)
    assert v_self.verdict == SafeguardVerdictKind.BLOCKED_CONSTITUTIONAL

    # 2. Physical brake (low Sevo or low J_c regenerative budget) blocked
    low_rb = TriadicInterventionProposal.create(
        proposal_id="low-rb",
        proposer_id="agent:x",
        reviewer_id="human:y",
        human_oversight_approved=True,
        pre_cme=base_cme,
        post_cme=base_cme,
        initial_crisis=crisis,
        sevo=1.8,
        j_c=J_c(J=100.0, delta_S=-0.5, delta_I_c=2.0, R_b=0.10, delta_C=0.1, confidence=1.0),
    )
    v_phys = guard.evaluate(low_rb)
    assert v_phys.verdict == SafeguardVerdictKind.BLOCKED_PHYSICAL_BRAKE

    # 3. Cross-pillar sacrifice blocked even above absolute floor
    sacrifice = TriadicInterventionProposal.create(
        proposal_id="sacrifice",
        proposer_id="agent:x",
        reviewer_id="human:y",
        human_oversight_approved=True,
        pre_cme=_make_cme(0.70),
        post_cme=_make_cme(0.74, regeneration=0.60),  # -0.10 < -0.05
        initial_crisis=crisis,
    )
    v_sac = guard.evaluate(sacrifice)
    assert v_sac.verdict == SafeguardVerdictKind.BLOCKED_CROSS_PILLAR_SACRIFICE

    # 4. Risk-transfer across crisis domains blocked
    transfer = TriadicInterventionProposal.create(
        proposal_id="risk-transfer",
        proposer_id="agent:x",
        reviewer_id="human:y",
        human_oversight_approved=True,
        pre_cme=base_cme,
        post_cme=_make_cme(0.67),
        initial_crisis=crisis,
        crisis_intervention={"climatic_ecological": -0.08, "sanitary": 0.07},
    )
    v_tr = guard.evaluate(transfer)
    assert v_tr.verdict == SafeguardVerdictKind.BLOCKED_RISK_TRANSFER

    # 5. Balanced regenerative multi-domain stabilization approved (advisory-only)
    balanced = TriadicInterventionProposal.create(
        proposal_id="balanced-regen",
        proposer_id="agent:x",
        reviewer_id="human:y",
        human_oversight_approved=True,
        pre_cme=base_cme,
        post_cme=_make_cme(0.68, ecology=0.70, wellbeing=0.69, resilience=0.71),
        initial_crisis=crisis,
        crisis_intervention=dict.fromkeys([d.value for d in CRISIS_DOMAINS], -0.05),
        j_c=J_c(J=120.0, delta_S=-0.4, delta_I_c=4.0, R_b=0.80, delta_C=0.2, confidence=1.0),
    )
    v_ok = guard.evaluate(balanced)
    assert v_ok.verdict == SafeguardVerdictKind.APPROVED_ADVISORY
    assert v_ok.approved_for_advisory is True
    assert v_ok.advisory_only is True
    assert v_ok.mcp_actuation_permitted is False
    assert v_ok.final_synergy_index < v_ok.baseline_final_synergy_index
    assert len(v_ok.verdict_sha256) == 64

    # Homeostatic controller standalone sanity check
    homeo = build_triadic_homeostatic_controller()
    snap = homeo.step(
        receptors={
            TriadicPillar.EARTH_BIOSPHERE.value: 0.72,
            TriadicPillar.HUMAN_CIVILIZATION.value: 0.74,
            TriadicPillar.TECH_INFRASTRUCTURE.value: 0.76,
        },
        dt=1.0,
    )
    assert 0.8 <= snap.viability <= 1.0


def test_t254_comparative_benchmark_cli_and_repo_isolation(tmp_path: Path) -> None:
    report = run_t254_polycrisis_safeguard_benchmark()
    assert report.spec == "T254"
    assert report.zero_unsafe_held_out is True
    assert report.zero_false_refusal_held_out is True
    assert report.strictly_beats_baselines is True
    assert report.advisory_only is True
    assert report.mcp_actuation_permitted is False

    by_pol = {m.policy: m for m in report.held_out_metrics}
    assert by_pol["triadic_polycrisis_guard"].exact_match_rate == pytest.approx(1.0)
    assert by_pol["scalar_utility_baseline"].unsafe_approvals > 0
    assert by_pol["static_single_domain_gate"].unsafe_approvals > 0

    # CLI test
    out_file = tmp_path / "t254_report.json"
    runner = CliRunner()
    res = runner.invoke(app, ["singularity", "triadic-safeguard", "--output", str(out_file)])
    assert res.exit_code == 0, res.output
    assert out_file.exists()
    parsed = json.loads(out_file.read_text(encoding="utf-8"))
    assert parsed["strictly_beats_baselines"] is True
    assert parsed["report_sha256"] == report.report_sha256

    # Repository AST Track A/B isolation & 12-tool MCP surface unchanged
    ast_iso = verify_track_a_b_ast_isolation()
    assert ast_iso["passed"] is True, ast_iso
    mcp_bounds = verify_mcp_surface_bounds()
    assert mcp_bounds["passed"] is True, mcp_bounds


def test_voluntary_refuge_habitat_protocol_terrestrial_and_extraterrestrial() -> None:
    # 1. N+2 redundancy (< 1.25) rejected fail-closed
    with pytest.raises(ValueError, match="redundancy_factor"):
        LifeSupportReserveSpec(
            water_liters_per_day_total=20_000.0,
            food_kcal_per_day_total=3_000_000.0,
            oxygen_kg_per_day_total=1_200.0,
            clean_power_kw_total=2_500.0,
            medical_sanitary_index=0.85,
            psychosocial_wellbeing_index=0.80,
            autonomy_reserve_days=120.0,
            closed_loop_recycling_efficiency=0.90,
            environmental_shielding_integrity=0.80,
            redundancy_factor=1.05,
        )

    full_reserves_off_earth = LifeSupportReserveSpec(
        water_liters_per_day_total=200_000.0,
        food_kcal_per_day_total=30_000_000.0,
        oxygen_kg_per_day_total=12_000.0,
        clean_power_kw_total=50_000.0,
        medical_sanitary_index=0.92,
        psychosocial_wellbeing_index=0.88,
        autonomy_reserve_days=400.0,
        closed_loop_recycling_efficiency=0.99,
        environmental_shielding_integrity=0.97,
    )

    # 2. Voluntary off-Earth refuge accepting both polycrisis_protection & personal_wellbeing
    #    against global humanity target (8B): passes for 10,000 occupants, while honestly
    #    reporting universal_humanity_coverage_ready=False until 8B capacity is certified!
    plan_pilot = VoluntaryRefugeHabitatPlan(
        habitat_id="orbital-sanctuary-alpha",
        placement=HabitatPlacementMode.EXTRATERRESTRIAL,
        target_civilization_population=8_000_000_000,
        requested_occupancy=10_000,
        reserves=full_reserves_off_earth,
        transfer_requests=(
            VoluntaryTransferRequest(
                request_id="req-crisis",
                persons_count=6_000,
                motivation=TransferMotivation.POLYCRISIS_PROTECTION,
            ),
            VoluntaryTransferRequest(
                request_id="req-wellbeing",
                persons_count=4_000,
                motivation=TransferMotivation.PERSONAL_WELLBEING,
            ),
        ),
    )
    ev_pilot = evaluate_refuge_habitat_plan(plan_pilot)
    assert ev_pilot.passed is True
    assert ev_pilot.autonomy_and_consent_verified is True
    assert ev_pilot.life_support_and_wellbeing_verified is True
    assert ev_pilot.certified_leontief_capacity >= 10_000
    assert ev_pilot.universal_humanity_coverage_ready is False

    # 3. Full target coverage marks universal_humanity_coverage_ready=True
    plan_full_local = VoluntaryRefugeHabitatPlan(
        habitat_id="terrestrial-valley-shield",
        placement=HabitatPlacementMode.TERRESTRIAL,
        target_civilization_population=10_000,
        requested_occupancy=10_000,
        reserves=full_reserves_off_earth,
    )
    ev_full = evaluate_refuge_habitat_plan(plan_full_local)
    assert ev_full.passed is True
    assert ev_full.universal_humanity_coverage_ready is True
    assert ev_full.civilization_coverage_ratio == pytest.approx(1.0)

    # 4. Coercion or lock-in (no free exit) is strictly blocked (BLOCKED_REFUGE_COERCION)
    coercive_plan = VoluntaryRefugeHabitatPlan(
        habitat_id="mandatory-bunker",
        placement=HabitatPlacementMode.TERRESTRIAL,
        target_civilization_population=10_000,
        requested_occupancy=1_000,
        reserves=full_reserves_off_earth,
        voluntary_opt_in_only=False,
    )
    ev_coercive = evaluate_refuge_habitat_plan(coercive_plan)
    assert ev_coercive.passed is False
    assert ev_coercive.failure_kind == SafeguardVerdictKind.BLOCKED_REFUGE_COERCION

    # 5. Low psychosocial wellbeing (survival-only prison rations) is blocked
    cramped_reserves = LifeSupportReserveSpec(
        water_liters_per_day_total=200_000.0,
        food_kcal_per_day_total=30_000_000.0,
        oxygen_kg_per_day_total=12_000.0,
        clean_power_kw_total=50_000.0,
        medical_sanitary_index=0.85,
        psychosocial_wellbeing_index=0.45,  # < 0.70 wellbeing requirement
        autonomy_reserve_days=400.0,
        closed_loop_recycling_efficiency=0.99,
        environmental_shielding_integrity=0.97,
    )
    ev_cramped = evaluate_refuge_habitat_plan(
        VoluntaryRefugeHabitatPlan(
            habitat_id="cramped-pod",
            placement=HabitatPlacementMode.EXTRATERRESTRIAL,
            target_civilization_population=5_000,
            requested_occupancy=1_000,
            reserves=cramped_reserves,
        )
    )
    assert ev_cramped.passed is False
    assert ev_cramped.failure_kind == SafeguardVerdictKind.BLOCKED_REFUGE_RESOURCE_DEFICIT

    # 6. Guard blocks coercive habitat AND blocks Earth-cannibalizing habitat
    guard = TriadicPolycrisisGuard()
    crisis = PolycrisisState(0.50, 0.45, 0.45, 0.40, 0.42)
    v_coercive = guard.evaluate(
        TriadicInterventionProposal.create(
            proposal_id="prop-coercive",
            proposer_id="agent:a",
            reviewer_id="human:b",
            human_oversight_approved=True,
            pre_cme=_make_cme(0.65),
            post_cme=_make_cme(0.68),
            initial_crisis=crisis,
            habitat_plan=coercive_plan,
        )
    )
    assert v_coercive.verdict == SafeguardVerdictKind.BLOCKED_REFUGE_COERCION
    assert v_coercive.habitat_evaluation is not None
    assert v_coercive.habitat_evaluation["passed"] is False
