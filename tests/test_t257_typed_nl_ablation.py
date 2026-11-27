"""T257: Tests for Typed-DAG Multi-Role NL Grounding, Ontology Mutexes & T256 Hardening."""

from __future__ import annotations

import ast
import json
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from q_speace.aacm.typed_dag import ContractSpec, TypedComputationalDAG
from q_speace.bcel.catalog import BCELCatalog
from q_speace.bridge import (
    ClausePolarityAuditor,
    SymbolicGroundingAdapter,
    SymbolRegistry,
    TypedMultiRoleNLGroundingPipeline,
    apply_belief_revision,
    compute_effective_retracted_facts,
)
from q_speace.cli import app
from q_speace.economy.mcp_server import TOOL_REGISTRY
from q_speace.remote_mcp.worker import SCOPES as HTTP_TOOL_SCOPES
from q_speace.spiking.morphogenesis import HomeodynaBalanceController
from q_speace.spiking_brain.myelination import BatchRoleDeliberationCodec
from q_speace.vertical_slice import run_t257_nl_ablation


def test_t257_bcel_ast_zero_eval_and_mcp_invariance() -> None:
    cat = BCELCatalog()
    assert cat.is_functional(
        "Typed-DAG multi-role grounding, clause-polarity screening, and ontology mutex belief revision (T257)"
    )
    assert not cat.is_functional("Anthropomorphic inner-parliament debate personas (T257)")
    assert len(TOOL_REGISTRY) == 14
    assert len(HTTP_TOOL_SCOPES) == 12

    pipeline_file = (
        Path(__file__).resolve().parent.parent / "q_speace" / "bridge" / "typed_nl_pipeline.py"
    )
    tree = ast.parse(pipeline_file.read_text(encoding="utf-8"), filename=str(pipeline_file))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"eval", "exec"}


def test_t256_audit_hardening_timeout_port_collision_codec_and_adjacency() -> None:
    # 1. Duplicate forward target_port collision is rejected fail-closed
    dag = TypedComputationalDAG("hardened_dag")
    dag.add_node("a", lambda _: {"out": 1})
    dag.add_node("b", lambda _: {"out": 2})
    dag.add_node("c", lambda d: {"res": d["x"]})
    dag.connect("a", "c", source_port="out", target_port="x")
    with pytest.raises(ValueError, match="Duplicate forward connection"):
        dag.connect("b", "c", source_port="out", target_port="x")

    # 2. ContractSpec.timeout_s violation marks ticket as timeout_exceeded & skips downstream
    slow_dag = TypedComputationalDAG("timeout_dag")
    c_fast = ContractSpec(name="tight_timeout", timeout_s=0.002)

    def _slow_node(_: object) -> dict[str, int]:
        time.sleep(0.015)
        return {"v": 1}

    slow_dag.add_node("slow", _slow_node, contract=c_fast)
    slow_dag.add_node("downstream", lambda d: {"ok": d.get("in_v", 0)})
    slow_dag.connect("slow", "downstream", source_port="v", target_port="in_v")
    tickets = slow_dag.execute()
    assert tickets["slow"].status == "timeout_exceeded"
    assert tickets["downstream"].status == "skipped_upstream_failure"

    # 3. BatchRoleDeliberationCodec preserves internal non-role '--- note ---' lines
    codec = BatchRoleDeliberationCodec({"extractor": "extract", "critic": "audit"})
    raw = "--- EXTRACTOR ---\nline1\n--- internal separator ---\nline2\n--- CRITIC ---\nfinal"
    parsed = codec.parse_response(raw)
    assert "line2" in parsed["extractor"]
    assert parsed["critic"] == "final"

    # 4. HomeodynaBalanceController.reroute_path respects optional adjacency graph
    adj = {"n_in": {"n_hot"}, "n_hot": {"n_out"}}
    # Without valid bypass or direct n_in -> n_out link, path is preserved rather than broken
    kept = HomeodynaBalanceController.reroute_path(
        ["n_in", "n_hot", "n_out"], "n_hot", [], adjacency=adj
    )
    assert kept == ("n_in", "n_hot", "n_out")


def test_t257_mutex_auto_retraction_and_zero_invention_polarity_gate() -> None:
    reg = SymbolRegistry(
        predicates=[
            "beacon_locked(n0)",
            "uplink_muted(n1)",
            "gimbal_aligned(n1)",
            "polarization_skew(n1)",
            "channel_intact(n1)",
            "terminal_fault(n1)",
            "glycol_injected(n1)",
        ],
        causal_nodes=["n0", "n1"],
        mutex_pairs=[
            ("polarization_skew(n1)", "gimbal_aligned(n1)"),
            ("terminal_fault(n1)", "channel_intact(n1)"),
        ],
    )
    prior = frozenset({"gimbal_aligned(n1)", "channel_intact(n1)"})

    # Even if LLM leaves retracted_facts empty, observing polarization_skew auto-retracts gimbal_aligned
    adapter = SymbolicGroundingAdapter(reg)
    g = adapter.ground('{"observed_facts": ["polarization_skew(n1)"], "retracted_facts": []}')
    eff_ret = compute_effective_retracted_facts(prior, g, registry=reg)
    assert eff_ret == frozenset({"gimbal_aligned(n1)"})
    s_rev = apply_belief_revision(prior, g, registry=reg)
    assert "gimbal_aligned(n1)" not in s_rev
    assert "polarization_skew(n1)" in s_rev
    assert "channel_intact(n1)" in s_rev

    # Anti-Goodhart zero-invention check: empty LLM output NEVER invents predicates
    glosses = {
        "beacon_locked(n0)": "beacon attivo su n0",
        "uplink_muted(n1)": "uplink silenziato su n1",
        "gimbal_aligned(n1)": "gimbal allineato su n1",
        "polarization_skew(n1)": "skew di polarizzazione su n1",
        "channel_intact(n1)": "canale integro su n1",
        "terminal_fault(n1)": "guasto terminale su n1",
        "glycol_injected(n1)": "glicole iniettato su n1",
    }
    pipe = TypedMultiRoleNLGroundingPipeline(reg)
    empty_res = pipe.run(
        raw_llm_output='--- EXTRACTOR ---\n{"observed_facts": [], "retracted_facts": []}\n--- CRITIC ---\n{"observed_facts": [], "retracted_facts": []}',
        operator_message="Il beacon su n0 era già attivo; si è verificato skew di polarizzazione su n1.",
        prior_state=prior,
        predicate_glosses=glosses,
    )
    assert empty_res.grounded.observed_facts == frozenset()
    assert empty_res.revised_belief_state == prior

    # Noisy LLM output with negated fault + unmentioned glycol + unretracted gimbal is cleaned!
    noisy_llm = (
        "--- EXTRACTOR ---\n"
        '{"observed_facts": ["beacon_locked(n0)", "polarization_skew(n1)", '
        '"terminal_fault(n1)", "glycol_injected(n1)", "gimbal_aligned(n1)"], "retracted_facts": []}\n'
        "--- CRITIC ---\n"
        '{"observed_facts": ["beacon_locked(n0)", "polarization_skew(n1)", '
        '"terminal_fault(n1)", "glycol_injected(n1)"], "retracted_facts": []}'
    )
    msg = (
        "Il beacon su n0 era già attivo; il gimbal su n1 non è allineato per uno skew di "
        "polarizzazione su n1. Non c'è nessun guasto terminale su n1."
    )
    clean_res = pipe.run(
        raw_llm_output=noisy_llm,
        operator_message=msg,
        prior_state=prior,
        predicate_glosses=glosses,
    )
    assert "terminal_fault(n1)" not in clean_res.grounded.observed_facts
    assert "glycol_injected(n1)" not in clean_res.grounded.observed_facts
    assert "gimbal_aligned(n1)" in clean_res.effective_retracted_facts
    assert "gimbal_aligned(n1)" not in clean_res.revised_belief_state
    assert all(t.status == "completed" for t in clean_res.tickets.values())
    assert len(clean_res.myelination_top_paths) == 3

    # Direct check of ClausePolarityAuditor on cleft double-negation ("non ... a mancare, erano già attivi")
    kept_obs, _, _, _ = ClausePolarityAuditor.audit_candidates(
        operator_message="Non è il beacon su n0 a mancare, era già attivo.",
        prior_state=prior,
        predicate_glosses=glosses,
        candidate_observed=["beacon_locked(n0)"],
        candidate_retracted=[],
    )
    assert kept_obs == ["beacon_locked(n0)"]


def test_t257_four_arm_ablation_and_cli(tmp_path: Path) -> None:
    out_path = tmp_path / "t257_ablation.json"
    rep = run_t257_nl_ablation(live_brain=False, n_resamples=100, output_path=out_path)
    assert out_path.exists()
    assert rep["spec"] == "T257"
    assert rep["conditions"]["NL_LIVE_BRAIN_SPEACE_T257"]["safe_end_to_end_success_rate"] == 1.0
    assert rep["conditions"]["NL_LIVE_BRAIN_SPEACE_T257"]["mean_retraction_f1"] == 1.0

    runner = CliRunner()
    cli_out = tmp_path / "cli_t257.json"
    res = runner.invoke(
        app,
        ["eval", "t257-nl-ablation", "--resamples", "100", "--output", str(cli_out)],
    )
    assert res.exit_code == 0, res.output
    parsed = json.loads(cli_out.read_text(encoding="utf-8"))
    assert "NL_LIVE_BRAIN_SPEACE_T257" in parsed["conditions"]
