"""T255: Tests for Non-Monotonic Linguistic Belief Revision, Mid-Chain Splicing & 3-Arm NL Benchmark."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from q_speace.bcel.catalog import BCELCatalog
from q_speace.bridge import SymbolicGroundingAdapter, SymbolRegistry, apply_belief_revision
from q_speace.cli import app
from q_speace.economy.mcp_server import TOOL_REGISTRY
from q_speace.remote_mcp.worker import SCOPES as HTTP_TOOL_SCOPES
from q_speace.routing import GOAPAction
from q_speace.self_improvement_cortex import (
    EmpiricalOperatorModel,
    ExperientialCognitiveAgent,
    StatefulPlanningEnvironment,
)
from q_speace.spiking.reasoning import RelationEdge
from q_speace.vertical_slice import build_t255_nl_episodes, run_t255_nl_benchmark


def test_t255_bcel_classification_and_mcp_tool_invariance() -> None:
    cat = BCELCatalog()
    assert cat.is_functional(
        "Non-monotonic linguistic belief revision and 3-arm NL-to-symbolic repair evaluation (T255)"
    )
    assert not cat.is_functional(
        "Human pragmatic comprehension and conversational intentionality claims (T255)"
    )
    assert len(TOOL_REGISTRY) == 14
    assert len(HTTP_TOOL_SCOPES) == 12


def test_t255_non_monotonic_belief_revision_and_conflict_precedence() -> None:
    reg = SymbolRegistry(
        predicates=[
            "beacon_locked(n0)",
            "uplink_muted(n1)",
            "gimbal_aligned(n1)",
            "polarization_skew(n1)",
            "channel_intact(n1)",
        ],
        causal_nodes=["n0", "n1"],
        actions=[],
    )
    adapter = SymbolicGroundingAdapter(reg, tau_ground=0.70)
    prior = frozenset({"gimbal_aligned(n1)", "channel_intact(n1)"})

    # Preamble-wrapped JSON with simultaneous observed + retracted + conflict atom
    raw_llm = (
        "Ecco l'estrazione richiesta:\n"
        '{"observed_facts": ["beacon_locked(n0)", "uplink_muted(n1)", '
        '"polarization_skew(n1)", "gimbal_aligned(n1)"], '
        '"retracted_facts": ["gimbal_aligned(n1)"], "parser_confidence": 0.90}\n'
    )
    grounded = adapter.ground(raw_llm, calibrated_confidence=0.88)
    assert grounded.status == "grounded_clean"
    assert "gimbal_aligned(n1)" in grounded.retracted_facts

    # Retraction strictly wins on conflict: S' = (S \ F_ret) U (F_obs \ F_ret)
    revised = apply_belief_revision(prior, grounded, min_parser_confidence=0.50)
    assert "gimbal_aligned(n1)" not in revised
    assert revised == frozenset(
        {
            "channel_intact(n1)",
            "beacon_locked(n0)",
            "uplink_muted(n1)",
            "polarization_skew(n1)",
        }
    )

    # Hallucinated out-of-vocabulary predicate fails closed (zero partial mutation)
    bad_llm = (
        '{"observed_facts": ["beacon_locked(n0)", "invented_hallucination(n9)"], '
        '"retracted_facts": ["gimbal_aligned(n1)"]}'
    )
    bad_grounded = adapter.ground(bad_llm, calibrated_confidence=0.88)
    assert bad_grounded.status == "rejected_unknown_symbol"
    assert any(r.token == "invented_hallucination(n9)" for r in bad_grounded.rejections)
    assert apply_belief_revision(prior, bad_grounded) == prior

    # Low parser confidence (< min_parser_confidence) fails closed without mutating prior state
    low_conf_llm = (
        '{"observed_facts": ["beacon_locked(n0)"], '
        '"retracted_facts": ["gimbal_aligned(n1)"], "parser_confidence": 0.25}'
    )
    low_conf = adapter.ground(low_conf_llm, calibrated_confidence=0.20)
    assert apply_belief_revision(prior, low_conf, min_parser_confidence=0.70) == prior


def test_t255_mid_episode_kernel_entry_splicing_and_abandonment() -> None:
    # Source Domain A: 3-step chain
    edges_a = [RelationEdge("a0", "rel_a", "a1", 1.0), RelationEdge("a1", "rel_a", "a2", 1.0)]
    acts_a = [
        GOAPAction(
            "op_a1(a0,a1)", frozenset({"trig_a(a0)", "rel_a(a0,a1)"}), frozenset({"s1_a(a1)"})
        ),
        GOAPAction(
            "op_a2(a1,a2)", frozenset({"s1_a(a1)", "rel_a(a1,a2)"}), frozenset({"s2_a(a1)"})
        ),
        GOAPAction("op_a3(a1,a2)", frozenset({"s2_a(a1)"}), frozenset({"goal_a(a2)"})),
    ]
    init_a = frozenset({"trig_a(a0)", "rel_a(a0,a1)", "rel_a(a1,a2)"})
    goal_a = frozenset({"goal_a(a2)"})

    agent = ExperientialCognitiveAgent(
        arm_name="TEST_AGENT",
        operator_model=EmpiricalOperatorModel(acts_a),
        alpha_local=0.30,
        tau_analogy=0.45,
    )
    rep_a = agent.solve_episode(
        StatefulPlanningEnvironment(init_a, acts_a),
        domain="dom_a",
        goal_state=goal_a,
        domain_edges=edges_a,
        consolidate_on_success=True,
        consolidate_skill_id="macro_a",
    )
    assert rep_a.goal_reached is True

    # Target Domain B with mid-step skew mutation + 1-step local bridge + standby failover
    edges_b = [RelationEdge("b0", "rel_b", "b1", 1.0), RelationEdge("b1", "rel_b", "b2", 1.0)]
    nominal_b = [
        GOAPAction(
            "op_b1(b0,b1)", frozenset({"trig_b(b0)", "rel_b(b0,b1)"}), frozenset({"s1_b(b1)"})
        ),
        GOAPAction(
            "op_b2(b1,b2)", frozenset({"s1_b(b1)", "rel_b(b1,b2)"}), frozenset({"s2_b(b1)"})
        ),
        GOAPAction(
            "op_b3(b1,b2)",
            frozenset({"s2_b(b1)", "channel_intact(b1)"}),
            frozenset({"goal_b(b2)"}),
        ),
        GOAPAction("fix_skew(b1)", frozenset({"skew(b1)"}), frozenset({"s2_b(b1)"})),
        GOAPAction(
            "failover_sb(sb0,b2)",
            frozenset({"standby_ready(sb0)"}),
            frozenset({"goal_b(b2)"}),
            cost=2.0,
        ),
    ]
    mutated_b = [
        GOAPAction(
            "op_b2(b1,b2)", frozenset({"s1_b(b1)", "rel_b(b1,b2)"}), frozenset({"skew(b1)"})
        ),
        *(a for a in nominal_b if a.name != "op_b2(b1,b2)"),
    ]
    goal_b = frozenset({"goal_b(b2)"})

    # Case 1: Mid-episode repairable correction -> skips [op_b1, op_b2], bridges [fix_skew], keeps [op_b3]
    s_rev_repair = frozenset(
        {"s1_b(b1)", "skew(b1)", "channel_intact(b1)", "rel_b(b0,b1)", "rel_b(b1,b2)"}
    )
    ag_rep = agent.clone_from_checkpoint(new_arm_name="REPAIR_ARM", repair_mode="selective")
    ag_rep.operator_model = EmpiricalOperatorModel(mutated_b)
    res_rep = ag_rep.execute_from_revised_belief(
        StatefulPlanningEnvironment(s_rev_repair, mutated_b),
        revised_belief_state=s_rev_repair,
        domain="dom_b",
        goal_state=goal_b,
        domain_edges=edges_b,
        mapping_actions=nominal_b,
    )
    assert res_rep.safe_execution is True
    assert res_rep.repair_decision == "SELECTIVE_LOCAL_REPAIR"
    assert res_rep.skipped_prefix_steps == ("op_b1(b0,b1)", "op_b2(b1,b2)")
    assert res_rep.spliced_bridge_steps == ("fix_skew(b1)",)
    assert res_rep.preserved_suffix_steps == ("op_b3(b1,b2)",)

    # Case 2: Unrecoverable terminal_fault -> abandons macro and switches to failover_sb
    s_rev_abandon = frozenset(
        {"terminal_fault(b1)", "standby_ready(sb0)", "rel_b(b0,b1)", "rel_b(b1,b2)"}
    )
    ag_ab = agent.clone_from_checkpoint(new_arm_name="ABANDON_ARM", repair_mode="selective")
    ag_ab.operator_model = EmpiricalOperatorModel(nominal_b)
    res_ab = ag_ab.execute_from_revised_belief(
        StatefulPlanningEnvironment(s_rev_abandon, nominal_b),
        revised_belief_state=s_rev_abandon,
        domain="dom_b",
        goal_state=goal_b,
        domain_edges=edges_b,
        mapping_actions=nominal_b,
    )
    assert res_ab.safe_execution is True
    assert res_ab.repair_decision == "ABANDON_MACRO_AND_REPLAN"
    assert res_ab.executed_actions == ("failover_sb(sb0,b2)",)


def test_t255_three_arm_benchmark_and_cli(tmp_path: Path) -> None:
    episodes = build_t255_nl_episodes()
    assert len(episodes) == 15

    out_file = tmp_path / "t255_out.json"
    rep = run_t255_nl_benchmark(live_brain=False, n_resamples=200, output_path=out_file)
    assert out_file.exists()
    assert rep["spec"] == "T255"
    assert rep["conditions"]["ORACLE_SYMBOLIC_SPEACE"]["safe_end_to_end_success_rate"] == 1.0
    assert rep["conditions"]["ORACLE_SYMBOLIC_SPEACE"]["repair_decision_match_vs_oracle"] == 1.0
    assert rep["conditions"]["NL_LIVE_BRAIN_SPEACE"]["safe_end_to_end_success_rate"] == 1.0

    runner = CliRunner()
    cli_out = tmp_path / "cli_t255.json"
    res = runner.invoke(
        app,
        ["eval", "t255-nl-benchmark", "--resamples", "100", "--output", str(cli_out)],
    )
    assert res.exit_code == 0, res.output
    parsed = json.loads(cli_out.read_text(encoding="utf-8"))
    assert parsed["n_episodes"] == 15
