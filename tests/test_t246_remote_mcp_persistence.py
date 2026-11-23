"""T246: Remote MCP persistent SQLite state store & verifiable hash-chained audit checkpoints."""

# Optional HTTP dependencies are checked before importing server.
# ruff: noqa: E402
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("mcp")
jwt = pytest.importorskip("jwt")
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import ValidationError
from starlette.testclient import TestClient

from q_speace.bcel.catalog import BCELCatalog
from q_speace.remote_mcp.config import HTTPConfig
from q_speace.remote_mcp.server import create_app
from q_speace.remote_mcp.service import (
    Audit,
    ServiceError,
    verify_audit_chain,
    verify_audit_checkpoint,
)

SCOPES = "qspeace:catalog.read qspeace:compute qspeace:simulation.compute"


def _make_keypair_and_token(
    issuer: str = "https://issuer.example.test",
    resource: str = "http://127.0.0.1:8000/mcp",
) -> tuple[str, Any]:
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = (
        private.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )

    def make_token(sub: str = "alice", scopes: str = SCOPES) -> str:
        now = int(time.time())
        claims = {
            "iss": issuer,
            "aud": resource,
            "sub": sub,
            "scope": scopes,
            "iat": now,
            "exp": now + 180,
        }
        return str(jwt.encode(claims, private, algorithm="RS256", headers={"kid": "t246"}))

    return public, make_token


def _headers(token: str, sid: str | None = None) -> dict[str, str]:
    out = {
        "Authorization": "Bearer " + token,
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-11-25",
    }
    if sid:
        out["Mcp-Session-Id"] = sid
    return out


def _initialize(client: TestClient, token: str) -> str:
    resp = client.post(
        "/mcp",
        headers=_headers(token),
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "t246", "version": "1"},
            },
        },
    )
    assert resp.status_code == 200, resp.text
    sid = resp.headers["mcp-session-id"]
    init_resp = client.post(
        "/mcp",
        headers=_headers(token, sid),
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
    )
    assert init_resp.status_code == 202
    return sid


def _rpc(client: TestClient, token: str, sid: str, method: str, params: Any = None) -> Any:
    return client.post(
        "/mcp",
        headers=_headers(token, sid),
        json={"jsonrpc": "2.0", "id": 2, "method": method, "params": params or {}},
    )


def test_t246_config_rejects_same_audit_and_state_path(tmp_path: Path) -> None:
    public, _ = _make_keypair_and_token()
    same = tmp_path / "shared.sqlite"
    with pytest.raises(ValidationError, match="state_db_path must be distinct"):
        HTTPConfig(
            issuer="https://issuer.example.test",
            resource="http://127.0.0.1:8000/mcp",
            public_keys={"t246": public},
            audit_path=same,
            state_db_path=same,
            allowed_hosts=["testserver"],
        )


def test_t246_persistent_sessions_and_rate_quotas_survive_restart(tmp_path: Path) -> None:
    public, make_token = _make_keypair_and_token()
    audit_db = tmp_path / "audit.sqlite"
    state_db = tmp_path / "state.sqlite"
    config = HTTPConfig(
        issuer="https://issuer.example.test",
        resource="http://127.0.0.1:8000/mcp",
        public_keys={"t246": public},
        audit_path=audit_db,
        state_db_path=state_db,
        allowed_hosts=["testserver"],
        sessions_per_principal=2,
        session_idle_seconds=60.0,
        requests_per_minute=1,
        burst=10,
    )
    auth = make_token("alice")

    # Instance 1: open 2 sessions (reaching sessions_per_principal=2) and check 12 tools.
    app1 = create_app(config)
    with TestClient(app1) as client1:
        sid1 = _initialize(client1, auth)
        sid2 = _initialize(client1, auth)
        listing = _rpc(client1, auth, sid1, "tools/list")
        assert listing.status_code == 200
        assert len(listing.json()["result"]["tools"]) == 12
        # Third session refused on instance 1.
        refused = client1.post(
            "/mcp",
            headers=_headers(auth),
            json={
                "jsonrpc": "2.0",
                "id": 9,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "t246", "version": "1"},
                },
            },
        )
        assert refused.status_code == 429
        assert refused.json()["error"] == "session_limit"

    # Instance 2 (simulated process restart with same state_db_path):
    # alice still has 2 persisted active sessions -> cannot bypass session_limit!
    app2 = create_app(config)
    assert sid1 in app2.sessions and sid2 in app2.sessions
    with TestClient(app2) as client2:
        refused_after_restart = client2.post(
            "/mcp",
            headers=_headers(auth),
            json={
                "jsonrpc": "2.0",
                "id": 10,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "t246", "version": "1"},
                },
            },
        )
        assert refused_after_restart.status_code == 429
        assert refused_after_restart.json()["error"] == "session_limit"

    # Rate-limit persistence across restart: exhaust bob's burst=1 on Instance 2,
    # then immediately verify Instance 3 still enforces 429 rate_limit!
    rate_cfg = config.model_copy(
        update={"burst": 1, "requests_per_minute": 1, "sessions_per_principal": 4}
    )
    bob = make_token("bob")
    app_r1 = create_app(rate_cfg)
    with TestClient(app_r1) as client_r1:
        # 1st POST consumes the sole burst token (returns 400 session_required, rate now ~0).
        first = client_r1.post(
            "/mcp", headers=_headers(bob), json={"jsonrpc": "2.0", "method": "ping"}
        )
        assert first.status_code == 400
    app_r2 = create_app(rate_cfg)
    with TestClient(app_r2) as client_r2:
        second = client_r2.post(
            "/mcp", headers=_headers(bob), json={"jsonrpc": "2.0", "method": "ping"}
        )
        assert second.status_code == 429
        assert second.json()["error"] == "rate_limit"

    # Expired sessions are pruned automatically from SQLite upon restart.
    short_idle_cfg = config.model_copy(update={"session_idle_seconds": 0.05})
    time.sleep(0.08)
    app3 = create_app(short_idle_cfg)
    assert app3.sessions == {}
    if app3.state_store is not None:
        assert app3.state_store.load_sessions() == {}
        app3.state_store.close()
    app3.audit.db.close()


def test_t246_audit_hash_chain_checkpoint_and_tamper_detection(tmp_path: Path) -> None:
    public, make_token = _make_keypair_and_token()
    audit_db = tmp_path / "audit.sqlite"
    state_db = tmp_path / "state.sqlite"
    cp_file = tmp_path / "audit_checkpoint.json"
    hmac_key = b"t246-external-audit-anchor-key"

    config = HTTPConfig(
        issuer="https://issuer.example.test",
        resource="http://127.0.0.1:8000/mcp",
        public_keys={"t246": public},
        audit_path=audit_db,
        state_db_path=state_db,
        allowed_hosts=["testserver"],
        burst=30,
    )
    auth = make_token("alice")
    app = create_app(config)
    with TestClient(app) as client:
        sid = _initialize(client, auth)
        for phi in (0.25, 0.50):
            resp = _rpc(
                client,
                auth,
                sid,
                "tools/call",
                {"name": "adaptive_clock_rate", "arguments": {"coherence_phi": phi}},
            )
            assert resp.status_code == 200 and resp.json()["result"]["isError"] is False

        # Verify chain + export HMAC-authenticated checkpoint atomically.
        chain = app.audit.verify_chain()
        assert chain["valid"] is True
        assert chain["row_count"] == 4
        assert chain["first_seq"] == 1 and chain["last_seq"] == 4
        checkpoint = app.audit.export_checkpoint(cp_file, hmac_key=hmac_key)
        assert cp_file.exists()
        assert json.loads(cp_file.read_text(encoding="utf-8")) == checkpoint

        # Append one more tool call AFTER checkpoint -> checkpoint remains valid!
        resp3 = _rpc(
            client,
            auth,
            sid,
            "tools/call",
            {"name": "adaptive_clock_rate", "arguments": {"coherence_phi": 0.75}},
        )
        assert resp3.status_code == 200 and resp3.json()["result"]["isError"] is False

    # Offline verification after server shutdown:
    assert verify_audit_chain(audit_db)["row_count"] == 6
    cp_ok = verify_audit_checkpoint(audit_db, checkpoint, hmac_key=hmac_key)
    assert cp_ok["valid"] is True
    assert cp_ok["current_row_count"] == 6
    assert cp_ok["checkpoint_seq"] == 4

    # Wrong HMAC key fails closed.
    bad_hmac = verify_audit_checkpoint(audit_db, checkpoint, hmac_key=b"wrong-key")
    assert bad_hmac["valid"] is False
    assert bad_hmac["reason"] == "checkpoint_hmac_mismatch"

    # Tampered checkpoint digest fails closed.
    forged_cp = dict(checkpoint, row_count=99)
    assert verify_audit_checkpoint(audit_db, forged_cp)["reason"] == "checkpoint_digest_mismatch"

    # Tail truncation below checkpoint seq is caught by verify_audit_checkpoint!
    trunc_db = tmp_path / "audit_trunc.sqlite"
    trunc_db.write_bytes(audit_db.read_bytes())
    conn = sqlite3.connect(trunc_db)
    conn.execute("DELETE FROM audit WHERE seq >= 4")
    conn.commit()
    conn.close()
    assert verify_audit_chain(trunc_db)["valid"] is True  # internal 1..3 intact
    trunc_check = verify_audit_checkpoint(trunc_db, checkpoint, hmac_key=hmac_key)
    assert trunc_check["valid"] is False
    assert trunc_check["reason"] == "audit_truncated"

    # Mid-log row deletion is caught as seq_gap.
    gap_db = tmp_path / "audit_gap.sqlite"
    gap_db.write_bytes(audit_db.read_bytes())
    conn = sqlite3.connect(gap_db)
    conn.execute("DELETE FROM audit WHERE seq = 2")
    conn.commit()
    conn.close()
    gap_res = verify_audit_chain(gap_db)
    assert gap_res["valid"] is False
    assert gap_res["reason"] == "seq_gap"

    # Payload modification is caught as digest_mismatch and blocks checkpoint export.
    tamper_db = tmp_path / "audit_tamper.sqlite"
    tamper_db.write_bytes(audit_db.read_bytes())
    conn = sqlite3.connect(tamper_db)
    conn.execute("UPDATE audit SET payload = '{\"tampered\":true}' WHERE seq = 3")
    conn.commit()
    conn.close()
    tamper_res = verify_audit_chain(tamper_db)
    assert tamper_res["valid"] is False
    assert tamper_res["reason"] == "digest_mismatch"
    assert tamper_res["failure_seq"] == 3

    tampered_audit = Audit(tamper_db)
    try:
        with pytest.raises(ServiceError, match="audit_chain_corrupted"):
            tampered_audit.export_checkpoint()
    finally:
        tampered_audit.db.close()

    assert BCELCatalog().is_functional(
        "Persistent SQLite MCP state store and verifiable hash-chained audit checkpoints (T246)"
    )
