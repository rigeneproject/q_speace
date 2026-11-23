"""T239: Tests for Self-Hosted SPEACE Micro Node failover, certification bundle, and CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from q_speace.bcel.catalog import BCELCatalog
from q_speace.cli import app
from q_speace.singularity import (
    EpigeneticFaultError,
    MicroNodeFailoverClient,
    certify_micro_node,
    verify_evidence_bundle_integrity,
    verify_mcp_surface_bounds,
    verify_slow_plane_quorum_guard,
    verify_track_a_b_ast_isolation,
)


def test_micro_node_failover_client_and_privilege_bounds() -> None:
    # 1. Failover refuses non-HTTP/mutation tools (dat_mint/dat_spend) even locally.
    direct = MicroNodeFailoverClient()
    with pytest.raises(EpigeneticFaultError, match="not in the 12-tool advisory HTTP allowlist"):
        direct.call_advisory_tool("dat_mint", {"amount": 10.0})

    # 2. Direct local call works on advisory tools.
    ok_direct = direct.call_advisory_tool("adaptive_clock_rate", {"coherence_phi": 0.5})
    assert ok_direct.mode == "local_direct"
    assert ok_direct.failover_triggered is False
    assert ok_direct.mcp_actuation_permitted is False

    # 3. Simulated remote outage deterministically fails over to local execution & logs event.
    def _failing_remote(_tool: str, _args: dict[str, Any]) -> dict[str, Any]:
        raise ConnectionError("remote_cloud_down")

    client = MicroNodeFailoverClient(remote_caller=_failing_remote)
    res = client.call_advisory_tool("bcel_lookup", {"concept": "Homeostasis"})
    assert res.mode == "local_failover"
    assert res.failover_triggered is True
    assert res.remote_error is not None and "remote_cloud_down" in res.remote_error
    assert res.mcp_actuation_permitted is False
    assert len(client.failover_events) == 1

    # 4. Healthy remote caller returns mode="remote" without triggering failover.
    def _healthy_remote(_tool: str, _args: dict[str, Any]) -> dict[str, Any]:
        return {"rate": 1.0, "advisory": True}

    remote_client = MicroNodeFailoverClient(remote_caller=_healthy_remote)
    rem = remote_client.call_advisory_tool("adaptive_clock_rate", {"coherence_phi": 0.5})
    assert rem.mode == "remote"
    assert rem.failover_triggered is False


def test_micro_node_evidence_bundle_integrity_tamper_detection_and_cli(tmp_path: Path) -> None:
    # 1. Individual compliance primitives pass.
    assert verify_track_a_b_ast_isolation()["passed"] is True
    assert verify_slow_plane_quorum_guard()["passed"] is True
    assert verify_mcp_surface_bounds()["passed"] is True

    # 2. Certify generates valid SHA-256 hashed bundle with zero self-approval.
    out_file = tmp_path / "evidence_bundle.json"
    bundle = certify_micro_node(
        node_id="speace-micro-test-01",
        seeds=(11, 23, 37, 53),
        output_path=out_file,
    )
    payload = bundle.to_dict()
    assert bundle.overall_compliant is True
    assert bundle.self_approval_permitted is False
    assert bundle.mcp_actuation_permitted is False
    assert bundle.requires_independent_human_review_for_t217 is True
    assert verify_evidence_bundle_integrity(payload) is True
    json.dumps(payload, allow_nan=False)

    # 3. Tampering with any field invalidates bundle_sha256.
    tampered = dict(payload)
    tampered["node_id"] = "tampered-node"
    assert verify_evidence_bundle_integrity(tampered) is False

    # 4. BCEL entries & deploy kit files exist.
    catalog = BCELCatalog()
    assert catalog.is_functional(
        "Self-hosted SPEACE Micro node and cryptographic compliance evidence bundle (T239)"
    )
    assert (
        catalog.get(
            "Sovereign decentralized AI certification authority metaphor (T239)"
        ).classification
        == "accidental"
    )
    repo_root = Path(__file__).resolve().parents[1]
    assert (repo_root / "deploy" / "micro-node" / "docker-compose.yml").exists()
    assert (repo_root / "deploy" / "micro-node" / "bootstrap_local_node.py").exists()

    # 5. CLI certify & verify-bundle round-trip (and tamper failure exit 3).
    cli_bundle = tmp_path / "cli_bundle.json"
    runner = CliRunner()
    r_cert = runner.invoke(
        app,
        [
            "micro-node",
            "certify",
            "--node-id",
            "cli-micro-01",
            "--seeds",
            "11,23",
            "--output",
            str(cli_bundle),
        ],
    )
    assert r_cert.exit_code == 0, r_cert.output
    assert cli_bundle.exists()

    r_ver = runner.invoke(app, ["micro-node", "verify-bundle", "--bundle", str(cli_bundle)])
    assert r_ver.exit_code == 0, r_ver.output
    assert json.loads(r_ver.output)["bundle_valid"] is True

    # Tamper CLI file -> verify-bundle exits with code 3.
    bad_data = json.loads(cli_bundle.read_text(encoding="utf-8"))
    bad_data["overall_compliant"] = False
    cli_bundle.write_text(json.dumps(bad_data), encoding="utf-8")
    r_bad = runner.invoke(app, ["micro-node", "verify-bundle", "--bundle", str(cli_bundle)])
    assert r_bad.exit_code == 3
