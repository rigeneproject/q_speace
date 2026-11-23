"""T238: Tests for adversarial Byzantine node isolation and coordinator-blackout failover."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from q_speace.bcel.catalog import BCELCatalog
from q_speace.cli import app
from q_speace.economy.mcp_server import TOOL_REGISTRY
from q_speace.remote_mcp.worker import SCOPES as HTTP_TOOL_SCOPES
from q_speace.singularity import run_t238_adversarial_resilience_benchmark


def test_t238_byzantine_isolation_and_coordinator_blackout_failover() -> None:
    rep_a = run_t238_adversarial_resilience_benchmark(seeds=(11, 23, 37, 53))
    rep_b = run_t238_adversarial_resilience_benchmark(seeds=(11, 23, 37, 53))
    assert rep_a.to_dict() == rep_b.to_dict()
    json.dumps(rep_a.to_dict(), allow_nan=False)

    assert rep_a.spec == "T238"
    assert rep_a.sandboxed is True
    assert rep_a.mcp_actuation_permitted is False
    assert rep_a.self_approval_permitted is False
    assert rep_a.layer0_independence_verified is True
    assert rep_a.consensus_quorum_slow_plane_only is True

    # Blackout failover & post-recovery slow-plane DLT reconciliation.
    assert rep_a.blackout_episodes_total == 8  # 2 blackout scenarios x 4 seeds
    assert rep_a.blackout_episodes_reconciled == 8
    assert rep_a.blackout_failover_verified is True

    # Byzantine poisoning isolation & malicious self-approval blocking.
    assert rep_a.byzantine_detection_rate >= 0.90
    assert rep_a.malicious_proposals_attempted > 0
    assert rep_a.malicious_proposals_blocked == rep_a.malicious_proposals_attempted
    assert rep_a.byzantine_resilience_verified is True
    assert rep_a.overall_resilience_verified is True

    # Held-out organismic gain & Singularity ablation under hostile conditions.
    held = rep_a.held_out_summary
    assert held.critical_safety_violations["FEDERATED_SINGULARITY"] == 0
    assert held.g_org_singularity_vs_isolated > 0.0
    assert held.g_org_singularity_vs_static > 0.0
    assert held.g_org_singularity_ablation > 0.0
    assert held.g_org_singularity_ablation_ci95[0] > 0.0


def test_t238_bcel_zero_new_mcp_tools_and_cli(tmp_path: Path) -> None:
    # Zero new MCP tools (T236 baseline preserved).
    assert len(TOOL_REGISTRY) == 14
    assert len(HTTP_TOOL_SCOPES) == 12

    catalog = BCELCatalog()
    assert catalog.is_functional(
        "Byzantine node isolation and coordinator-blackout failover benchmark (T238)"
    )
    assert (
        catalog.get(
            "Autonomous immune defense against geopolitical cyber-warfare narrative (T238)"
        ).classification
        == "accidental"
    )

    out_file = tmp_path / "t238_report.json"
    runner = CliRunner()
    res = runner.invoke(
        app,
        [
            "singularity",
            "resilience-benchmark",
            "--seeds",
            "11,23,37,53",
            "--output",
            str(out_file),
        ],
    )
    assert res.exit_code == 0, res.output
    summary = json.loads(res.output)
    assert summary["overall_resilience_verified"] is True
    assert summary["blackout_failover_verified"] is True
    assert summary["byzantine_resilience_verified"] is True
    assert out_file.exists()
