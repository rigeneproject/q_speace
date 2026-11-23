"""Tests for the Q-SPEACE MCP connection test agent (examples/mcp_connection_agent.py)."""

# Optional HTTP dependencies are checked before importing the implementation.
# ruff: noqa: E402
from __future__ import annotations

import asyncio
import json
import socket
import threading
import time
from pathlib import Path

import httpx
import pytest

pytest.importorskip("mcp")
jwt = pytest.importorskip("jwt")
uvicorn = pytest.importorskip("uvicorn")
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from examples.mcp_connection_agent import (
    PolicyConfig,
    QSpeaceConnectionAgent,
    TokenProvider,
    _metadata_url_for,
    main,
)
from q_speace.remote_mcp.config import HTTPConfig
from q_speace.remote_mcp.server import create_app


def test_local_demo_cli_passes_and_writes_clean_evidence(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report_dir = tmp_path / "evidence"
    rc = main(["--local-demo", "--apply-delay", "--report-dir", str(report_dir)])
    out = capsys.readouterr().out

    assert rc == 0
    assert "[PASS]" in out
    assert "Bearer " not in out

    summary = json.loads((report_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["passed"] is True
    assert summary["server_name"] == "q-speace-http"
    assert len(summary["granted_tools"]) == 12
    assert all(step["status"] == "passed" for step in summary["steps"])
    assert "Bearer " not in (report_dir / "events.jsonl").read_text(encoding="utf-8")


def test_partial_scope_token_skips_ungranted_tools(tmp_path: Path) -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = (
        key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    endpoint = f"http://127.0.0.1:{port}/mcp"
    issuer = f"http://127.0.0.1:{port}/partial-issuer/"
    config = HTTPConfig(
        issuer=issuer,
        resource=endpoint,
        public_keys={"k1": public_pem},
        audit_path=tmp_path / "audit.sqlite",
        host="127.0.0.1",
        port=port,
        allowed_hosts=[f"127.0.0.1:{port}"],
        worker_seconds=20.0,
    )
    app = create_app(config)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        meta_url = _metadata_url_for(endpoint)
        for _ in range(50):
            try:
                if httpx.get(meta_url, timeout=1.0).status_code == 200:
                    break
            except Exception:
                time.sleep(0.1)

        now = int(time.time())
        token = jwt.encode(
            {
                "iss": issuer,
                "aud": endpoint,
                "sub": "catalog-only-agent",
                "iat": now,
                "exp": now + 300,
                "scope": "qspeace:catalog.read",
            },
            private_pem,
            algorithm="RS256",
            headers={"kid": "k1"},
        )
        agent = QSpeaceConnectionAgent(
            endpoint=endpoint,
            token_provider=TokenProvider(endpoint=endpoint, token_url="", access_token=token),
            policy=PolicyConfig(),
        )
        report = asyncio.run(agent.run())
    finally:
        server.should_exit = True
        thread.join(timeout=5.0)
        app.audit.db.close()

    assert report.passed is True
    assert set(report.granted_tools) == {"bcel_lookup", "singularity_framework_manifest"}
    by_step = {s.step: s.status for s in report.steps}
    assert by_step["tool_bcel_lookup"] == "passed"
    assert by_step["tool_singularity_manifest"] == "passed"
    assert by_step["tool_adaptive_clock_rate"] == "skipped"
    assert by_step["scenario_a_kl_barycentre"] == "skipped"
    assert by_step["invalid_argument_recovery"] == "skipped"


def test_missing_credentials_fails_closed() -> None:
    provider = TokenProvider(
        endpoint="https://example.invalid/mcp",
        token_url="https://example.invalid/oauth/token",
    )
    with pytest.raises(RuntimeError, match="Missing credentials"):
        asyncio.run(provider.get_token())
