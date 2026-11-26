"""T252–T253: Tests for Experiential Macro-Skill Transfer, Selective Repair & 5-Axis agi-profile."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from q_speace.bcel.catalog import BCELCatalog
from q_speace.cli import app
from q_speace.economy.mcp_server import TOOL_REGISTRY
from q_speace.remote_mcp.worker import SCOPES as HTTP_TOOL_SCOPES
from q_speace.routing import GOAPAction, GOAPPlanner
from q_speace.self_improvement_cortex import (
    AnalogicalRoleMapper,
    EmpiricalOperatorModel,
    ExperientialCognitiveAgent,
    StatefulPlanningEnvironment,
    compute_regressed_kernels,
    extract_macro_skill,
    format_structured_atom,
    parse_structured_atom,
)
from q_speace.spiking.reasoning import RelationEdge
from q_speace.vertical_slice import (
    PROBLEM_FAMILIES,
    verify_t252_preregistration,
)


def test_t252_t253_bcel_preregistration_lock_and_tamper_detection(tmp_path: Path) -> None:
    cat = BCELCatalog()
    assert cat.is_functional(
        "Procedural chunking and relational role-parameterized macro-skill transfer (T252)"
    )
    assert cat.is_functional(
        "Weakest-precondition suffix verification, local plan splicing, and anti-Einstellung abandonment (T253)"
    )
    assert not cat.is_functional(
        "Hippocampal schema replay consciousness and sudden insight qualia claims (T252-T253)"
    )
    assert len(TOOL_REGISTRY) == 14
    assert len(HTTP_TOOL_SCOPES) == 12

    prereg = verify_t252_preregistration()
    assert prereg["pre_calibration"]["locked"] is True
    assert prereg["pre_evaluation"]["locked"] is True

    # Tampering with any field inside pre_evaluation must fail verify_t252_preregistration
    tampered = json.loads(json.dumps(prereg))
    tampered["pre_evaluation"]["episodes_per_family"] = 999
    bad_file = tmp_path / "tampered_prereg.json"
    bad_file.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(ValueError, match="verification FAILED"):
        verify_t252_preregistration(bad_file)


def test_t252_weakest_precondition_regression_and_clobber_rejection() -> None:
    assert parse_structured_atom("pipes_to(u0,u1)") == ("pipes_to", ("u0", "u1"))
    assert format_structured_atom("pipes_to", ("u0", "u1")) == "pipes_to(u0,u1)"

    a1 = GOAPAction("step1(x)", frozenset({"init(x)"}), frozenset({"mid(x)"}))
    a2 = GOAPAction("step2(x)", frozenset({"mid(x)"}), frozenset({"done(x)"}))
    kernels = compute_regressed_kernels([a1, a2], frozenset({"done(x)"}))
    assert kernels is not None
    assert kernels[0] == frozenset({"init(x)"})
    assert kernels[1] == frozenset({"mid(x)"})
    assert kernels[2] == frozenset({"done(x)"})

    # Clobbering step that deletes a downstream goal requirement must return None
    clobber = GOAPAction(
        "bad_step(x)",
        frozenset({"mid(x)"}),
        frozenset({"done(x)"}),
        del_effects=frozenset({"keep_alive(x)"}),
    )
    assert compute_regressed_kernels([a1, clobber], frozenset({"done(x)", "keep_alive(x)"})) is None


def test_t252_t253_single_family_acquisition_transfer_and_forked_repair() -> None:
    fam = [f for f in PROBLEM_FAMILIES if f.family_id == "F3_quorum_handoff"][0]
    # Zero lexical overlap check between Domain A and Domain B operators & fluents
    assert set(fam.ops_a).isdisjoint(set(fam.ops_b))
    assert set(fam.fluents_a).isdisjoint(set(fam.fluents_b))
    assert fam.link_rel_a != fam.link_rel_b

    # Direct unit check of extract_macro_skill + AnalogicalRoleMapper distractor rejection
    edges_a = [RelationEdge("x0", "r_a", "x1", 1.0), RelationEdge("x1", "r_a", "x2", 1.0)]
    plan_a = [
        GOAPAction("op_a1(x0,x1)", frozenset({"f0(x0)", "r_a(x0,x1)"}), frozenset({"f1(x1)"})),
        GOAPAction("op_a2(x1,x2)", frozenset({"f1(x1)", "r_a(x1,x2)"}), frozenset({"goal_a(x2)"})),
    ]
    macro = extract_macro_skill(
        skill_id="s_unit",
        source_domain="dom_a",
        plan=plan_a,
        goal_state=frozenset({"goal_a(x2)"}),
        domain_edges=edges_a,
    )
    assert macro.roles == ("?r0", "?r1", "?r2")

    edges_b = [
        RelationEdge("y0", "r_b", "y1", 1.0),
        RelationEdge("y1", "r_b", "y2", 1.0),
        RelationEdge("distractor_1", "r_b", "distractor_2", 1.0),
    ]
    acts_b = [
        GOAPAction("op_b1(y0,y1)", frozenset({"g0(y0)", "r_b(y0,y1)"}), frozenset({"g1(y1)"})),
        GOAPAction("op_b2(y1,y2)", frozenset({"g1(y1)", "r_b(y1,y2)"}), frozenset({"goal_b(y2)"})),
        GOAPAction(
            "op_b1(distractor_1,distractor_2)",
            frozenset({"g0(distractor_1)", "r_b(distractor_1,distractor_2)"}),
            frozenset({"g1(distractor_2)"}),
        ),
    ]
    mapper = AnalogicalRoleMapper(tau_analogy=0.5)
    mapped, trace = mapper.map_skill(
        macro,
        initial_state=frozenset({"g0(y0)", "r_b(y0,y1)", "r_b(y1,y2)", "g0(distractor_1)"}),
        goal_state=frozenset({"goal_b(y2)"}),
        target_actions=acts_b,
        target_edges=edges_b,
    )
    assert mapped is not None
    assert trace.verification_passed is True
    assert trace.selected_role_binding == {"?r0": "y0", "?r1": "y1", "?r2": "y2"}
    assert "distractor_1" in trace.distractors_rejected
    assert "distractor_2" in trace.distractors_rejected

    # Verify GOAPPlanner.plan_with_stats backward compatibility
    planner = GOAPPlanner(acts_b, simulate_only=True)
    p_res, p_exp = planner.plan_with_stats(
        frozenset({"g0(y0)", "r_b(y0,y1)", "r_b(y1,y2)"}),
        frozenset({"goal_b(y2)"}),
    )
    assert p_res is not None and len(p_res) == 2 and p_exp >= 1

    # Verify ExperientialCognitiveAgent clone_from_checkpoint & StatefulPlanningEnvironment
    env = StatefulPlanningEnvironment(frozenset({"g0(y0)", "r_b(y0,y1)", "r_b(y1,y2)"}), acts_b)
    ag = ExperientialCognitiveAgent(
        arm_name="EXP",
        operator_model=EmpiricalOperatorModel(acts_b),
        macro_store={"s_unit": macro},
    )
    clone = ag.clone_from_checkpoint(new_arm_name="CLONE", repair_mode="global_replan")
    assert clone.repair_mode == "global_replan"
    rep = ag.solve_episode(
        env, domain="dom_b", goal_state=frozenset({"goal_b(y2)"}), domain_edges=edges_b
    )
    assert rep.goal_reached is True
    assert rep.planner_expansions == 0


def test_t252_t253_full_campaign_and_5_axis_agi_profile_cli(tmp_path: Path) -> None:
    runner = CliRunner()
    out_dir = tmp_path / "t252_out"
    res_camp = runner.invoke(
        app,
        [
            "eval",
            "t252-benchmark",
            "--seed",
            "2026",
            "--resamples",
            "300",
            "--output",
            str(out_dir),
        ],
    )
    assert res_camp.exit_code == 0, res_camp.stdout
    camp = json.loads(res_camp.stdout)
    assert camp["all_gates_passed"] is True
    assert camp["t252_t253_decision"] == "keep"
    assert (out_dir / "t252_t253_benchmark_report.json").exists()

    agg = camp["held_out_aggregate"]
    assert agg["phase1_rebind_success_rate"] == 1.0
    assert agg["phase1_rebind_total_expansions"] == 0
    assert agg["phase2_expansion_reduction_ratio"] >= 0.50
    assert agg["phase2_distractor_rejection_rate"] == 1.0
    assert agg["phase3a_repair_expansion_reduction_ratio"] >= 0.40
    assert agg["phase3b_variant_expansion_reduction_ratio"] >= 0.80
    assert agg["phase3c_anti_einstellung_abandon_accuracy"] == 1.0
    assert agg["phase3c_selective_recovery_rate"] == 1.0
    assert agg["phase3c_stubborn_reuse_success_rate"] == 0.0

    # CLI: full 5-axis qspace eval agi-profile (all 5 axes ACTIVE!)
    prof_file = tmp_path / "full_5_axis_profile.json"
    res_prof = runner.invoke(
        app,
        [
            "eval",
            "agi-profile",
            "--seed",
            "2026",
            "--resamples",
            "300",
            "--output",
            str(prof_file),
        ],
    )
    assert res_prof.exit_code == 0, res_prof.stdout
    prof = json.loads(res_prof.stdout)
    assert prof["overall_verdict"] == "PASS_ALL_5_AXES"
    assert prof["active_axes_summary"]["active_count"] == 5
    for axis_key in (
        "1_epistemic_grounding",
        "2_causal_reasoning_and_planning",
        "3_continual_memory_and_skill_transfer",
        "4_ood_abstraction_and_adaptation",
        "5_metabolic_efficiency_and_safety",
    ):
        axis = prof["axes"][axis_key]
        assert axis["status"] == "ACTIVE"
        assert axis["gate_passed"] is True
        assert axis["speace_lift_delta"] > 0.0
        assert axis["bootstrap_95_ci"][0] > 0.0
