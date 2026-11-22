"""Regression tests for T231 MCP server and worker hardening."""

# Optional HTTP dependencies are checked before importing server code.
# ruff: noqa: E402
from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from q_speace.economy.mcp_server import list_tools
from q_speace.remote_mcp import worker

pytest.importorskip("mcp")
jwt = pytest.importorskip("jwt")
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from starlette.testclient import TestClient

from q_speace.remote_mcp.config import HTTPConfig
from q_speace.remote_mcp.server import create_app


def _make_keypair() -> tuple[Any, str]:
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = (
        private.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    return private, public


def _make_token(private: Any, config: HTTPConfig, sub: str = "agent-1") -> str:
    now = int(time.time())
    return str(
        jwt.encode(
            {
                "iss": config.issuer,
                "aud": config.resource,
                "sub": sub,
                "scope": "qspeace:catalog.read qspeace:compute qspeace:simulation.compute",
                "iat": now,
                "exp": now + 120,
            },
            private,
            algorithm="RS256",
            headers={"kid": "k1"},
        )
    )


def test_expired_sessions_are_pruned_before_session_limit_check(tmp_path: Path) -> None:
    """Regression: after sessions expire via idle timeout, initialize must prune
    stale sessions rather than permanently locking out the principal with 429.
    """
    private, public = _make_keypair()
    config = HTTPConfig(
        issuer="https://issuer.example.test",
        resource="http://127.0.0.1:8000/mcp",
        public_keys={"k1": public},
        audit_path=tmp_path / "audit.sqlite",
        allowed_hosts=["testserver", "127.0.0.1:8000"],
        sessions_per_principal=2,
        session_idle_seconds=0.05,
        burst=30,
    )
    app = create_app(config)
    token = _make_token(private, config)
    hdrs = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-11-25",
    }
    init_body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "expiry-regression", "version": "1"},
        },
    }
    with TestClient(app) as client:
        r1 = client.post("/mcp", headers=hdrs, json=init_body)
        r2 = client.post("/mcp", headers=hdrs, json=init_body)
        assert r1.status_code == 200
        assert r2.status_code == 200
        # Immediately opening a 3rd active session hits the limit (429).
        r3 = client.post("/mcp", headers=hdrs, json=init_body)
        assert r3.status_code == 429

        # Once the idle window passes, initialize prunes expired entries and succeeds.
        time.sleep(0.08)
        r4 = client.post("/mcp", headers=hdrs, json=init_body)
        assert r4.status_code == 200


def test_worker_validate_enforces_scopes_limits_and_rejects_nan() -> None:
    # Allowed tool succeeds
    valid = worker.validate("adaptive_clock_rate", {"coherence_phi": 0.5})
    assert valid["coherence_phi"] == 0.5

    # Forbidden/unknown tool fails closed
    with pytest.raises(ValueError, match="tool_not_available"):
        worker.validate("dat_mint", {"amount": 1.0})

    # Non-finite NaN fails closed
    with pytest.raises(ValueError):
        worker.validate("adaptive_clock_rate", {"coherence_phi": float("nan")})

    # Simulation bounds enforced
    with pytest.raises(ValueError, match="simulation_limit"):
        worker.validate(
            "kl_barycentre_aggregate",
            {"distributions": [[0.5, 0.5]] * 65},
        )
    with pytest.raises(ValueError, match="simulation_limit"):
        worker.validate(
            "vtec_allocate",
            {
                "objective_kind": "sum",
                "u_max": [1.0],
                "constraints": {
                    "s_assimilable": 1.0,
                    "e_available": 1.0,
                    "m_available": 1.0,
                    "ecological_threshold": 1.0,
                    "risk_acceptable": 1.0,
                    "human_agency_min": 0.0,
                },
                "horizon": [150, 10],
            },
        )
    with pytest.raises(ValueError, match="operation_limit"):
        worker.validate(
            "metabolism_cost_eval",
            {
                "num_qubits": 65,
                "num_gates": 1,
                "delta_utility": 2.0,
                "delta_entropy_info": 1.0,
            },
        )


def test_worker_main_in_process_success_and_reject_nan(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = json.dumps({"name": "adaptive_clock_rate", "arguments": {"coherence_phi": 0.5}})
    monkeypatch.setattr(sys, "stdin", SimpleNamespaceBuffer(payload.encode("utf-8")))
    assert worker.main() == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert out["result"]["coherence_phi"] == 0.5

    # Reject raw NaN constant in stdin JSON
    bad_payload = b'{"name": "adaptive_clock_rate", "arguments": {"coherence_phi": NaN}}'
    monkeypatch.setattr(sys, "stdin", SimpleNamespaceBuffer(bad_payload))
    assert worker.main() == 0
    bad_out = json.loads(capsys.readouterr().out)
    assert bad_out["ok"] is False

    # Reject oversized payload (> 65536 bytes)
    monkeypatch.setattr(sys, "stdin", SimpleNamespaceBuffer(b" " * 65537))
    assert worker.main() == 0
    big_out = json.loads(capsys.readouterr().out)
    assert big_out["ok"] is False


class SimpleNamespaceBuffer:
    def __init__(self, data: bytes) -> None:
        self.buffer = io.BytesIO(data)


def test_dat_discovery_schema_matches_strict_positive_amount() -> None:
    by_name = {t["name"]: t for t in list_tools()}
    assert by_name["dat_mint"]["inputSchema"]["properties"]["amount"]["exclusiveMinimum"] == 0
    assert by_name["dat_spend"]["inputSchema"]["properties"]["amount"]["exclusiveMinimum"] == 0
