"""Tests for the q_speace_economy MCP server wrapper (T6.11)."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from q_speace.economy.mcp_server import (
    TOOL_REGISTRY,
    _dispatch,
    _handle_cme_evaluate,
    _handle_compute_jc,
    _handle_dat_mint,
    _handle_dat_spend,
    _handle_elasticity_test,
    _handle_kl_barycentre,
    _handle_vtec_allocate,
    list_tools,
    main,
)

# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------


def test_tool_registry_has_expected_tools() -> None:
    names = {s.name for s in TOOL_REGISTRY}
    assert names == {
        "compute_jc",
        "kl_barycentre_aggregate",
        "vtec_allocate",
        "cme_evaluate",
        "dat_mint",
        "dat_spend",
        "elasticity_test",
        "adaptive_clock_rate",
        "metabolism_cost_eval",
        "bcel_lookup",
        "singularity_framework_manifest",
        "phase_transition_assess",
        "epigenetic_step_evaluate",
    }


def test_list_tools_returns_all() -> None:
    tools = list_tools()
    assert len(tools) == 13
    assert all("name" in t and "description" in t for t in tools)


# ---------------------------------------------------------------------------
# Individual handlers
# ---------------------------------------------------------------------------


def test_compute_jc_handler() -> None:
    out = _handle_compute_jc(
        {
            "J": 10.0,
            "delta_S": -0.5,
            "delta_I_c": 4.0,
            "R_b": 0.6,
            "delta_C": 0.1,
            "measured_components": 5,
        }
    )
    assert out["confidence"] == 1.0
    assert out["J"] == 10.0


def test_kl_barycentre_handler() -> None:
    out = _handle_kl_barycentre(
        {
            "distributions": [[0.7, 0.2, 0.1], [0.1, 0.2, 0.7]],
        }
    )
    s = sum(out["barycentre"])
    assert abs(s - 1.0) < 1e-6


def test_vtec_allocate_handler_sum() -> None:
    out = _handle_vtec_allocate(
        {
            "objective_kind": "sum",
            "u_max": [1.0, 1.0, 1.0],
            "constraints": {
                "s_assimilable": 1.0,
                "e_available": 10.0,
                "m_available": 5.0,
                "ecological_threshold": 0.8,
                "risk_acceptable": 0.7,
                "human_agency_min": 0.0,
            },
        }
    )
    assert out["feasible"]
    assert "u" in out


def test_vtec_allocate_handler_unknown_kind() -> None:
    with pytest.raises(ValueError, match="unknown objective_kind"):
        _handle_vtec_allocate(
            {
                "objective_kind": "nope",
                "u_max": [1.0],
                "constraints": {
                    "s_assimilable": 1.0,
                    "e_available": 10.0,
                    "m_available": 5.0,
                    "ecological_threshold": 0.8,
                    "risk_acceptable": 0.7,
                    "human_agency_min": 0.0,
                },
            }
        )


def test_cme_evaluate_handler() -> None:
    out = _handle_cme_evaluate(
        dict.fromkeys(
            (
                "energy",
                "matter",
                "information",
                "time",
                "ecology",
                "resilience",
                "wellbeing",
                "innovation",
                "reversibility",
                "distribution",
                "coherence",
                "regeneration",
            ),
            0.5,
        )
    )
    assert len(out["cme"]) == 12
    assert isinstance(out["weak_axes"], list)


def test_dat_mint_then_spend() -> None:
    mint = _handle_dat_mint(
        {
            "amount": 100.0,
            "bound_to": "exergy",
            "decay_half_life": 3600.0,
            "mint_time": 0.0,
            "token_id": "test-1",
        }
    )
    assert mint["token_id"] == "test-1"
    spend = _handle_dat_spend(
        {
            "token_id": "test-1",
            "amount": 25.0,
            "target": "exergy",
            "t": 0.0,
        }
    )
    assert spend["remaining_amount"] == 75.0


def test_elasticity_test_handler() -> None:
    out = _handle_elasticity_test(
        {
            "claim": {"claim_id": "c1", "trajectory": [1.0, 2.0, 3.0], "claim_threshold": 1.0},
            "external": {"standard_id": "x1", "trajectory": [1.01, 2.0, 2.99], "threshold": 1.0},
            "tol": 0.05,
        }
    )
    assert out["decision"] == "ACCEPT"


# ---------------------------------------------------------------------------
# Dispatch + stdio framing
# ---------------------------------------------------------------------------


def test_dispatch_unknown_method_raises() -> None:
    with pytest.raises(ValueError, match="unknown method"):
        _dispatch("does_not_exist", {})


def test_stdio_loop_single_call() -> None:
    """Pipe one JSON-RPC request into _stdio_loop; check response."""
    from q_speace.economy.mcp_server import _stdio_loop

    request = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "compute_jc",
            "params": {
                "J": 1.0,
                "delta_S": -0.1,
                "delta_I_c": 0.5,
                "R_b": 0.5,
                "delta_C": 0.0,
                "measured_components": 3,
            },
        }
    )
    saved_stdin = sys.stdin
    saved_stdout = sys.stdout
    try:
        sys.stdin = io.StringIO(request + "\n")
        sys.stdout = io.StringIO()
        rc = _stdio_loop()
        assert rc == 0
        out = sys.stdout.getvalue()
    finally:
        sys.stdin = saved_stdin
        sys.stdout = saved_stdout
    lines = [ln for ln in out.split("\n") if ln.strip()]
    assert len(lines) == 1
    response = json.loads(lines[0])
    assert response["id"] == 1
    assert "result" in response
    assert response["result"]["confidence"] == pytest.approx(0.6, abs=1e-9)


def test_stdio_loop_tools_list() -> None:
    from q_speace.economy.mcp_server import _stdio_loop

    request = json.dumps({"jsonrpc": "2.0", "id": "list", "method": "tools/list"})
    saved_stdin = sys.stdin
    saved_stdout = sys.stdout
    try:
        sys.stdin = io.StringIO(request + "\n")
        sys.stdout = io.StringIO()
        _stdio_loop()
        out = sys.stdout.getvalue()
    finally:
        sys.stdin = saved_stdin
        sys.stdout = saved_stdout
    response = json.loads(out.strip().split("\n")[-1])
    assert response["id"] == "list"
    assert len(response["result"]["tools"]) == 13


def test_stdio_loop_parse_error() -> None:
    from q_speace.economy.mcp_server import _stdio_loop

    saved_stdin = sys.stdin
    saved_stdout = sys.stdout
    try:
        sys.stdin = io.StringIO("not-json\n")
        sys.stdout = io.StringIO()
        _stdio_loop()
        out = sys.stdout.getvalue()
    finally:
        sys.stdin = saved_stdin
        sys.stdout = saved_stdout
    response = json.loads(out.strip().split("\n")[-1])
    assert "error" in response
    assert response["error"]["code"] == -32700


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def test_main_self_test_returns_zero(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["--self-test"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "all 13 tools green" in captured.out


def test_main_self_test_subprocess() -> None:
    """Spawn the module as a subprocess to verify the entry point works."""
    repo_root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "q_speace.economy.mcp_server", "--self-test"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"stderr={result.stderr}"
    assert "all 13 tools green" in result.stdout
