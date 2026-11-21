"""Real HTTP lifecycle, ownership, authorization and numeric worker regressions."""

# Optional HTTP dependencies are checked before importing the implementation.
# ruff: noqa: E402
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("mcp")
jwt = pytest.importorskip("jwt")
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from starlette.testclient import TestClient

from q_speace.remote_mcp.config import HTTPConfig
from q_speace.remote_mcp.server import create_app

SCOPES = "qspeace:catalog.read qspeace:compute qspeace:simulation.compute"


@pytest.fixture
def setup(tmp_path: Path) -> tuple[Any, Any, Any]:
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = (
        private.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    config = HTTPConfig(
        issuer="https://issuer.example.test",
        resource="http://127.0.0.1:8000/mcp",
        public_keys={"test": public},
        audit_path=tmp_path / "audit.sqlite",
        allowed_hosts=["testserver", "127.0.0.1:8000"],
        burst=60,
    )
    app = create_app(config)

    def token(sub: str = "alice", scopes: str = SCOPES, **changes: Any) -> str:
        now = int(time.time())
        claims = {
            "iss": config.issuer,
            "aud": config.resource,
            "sub": sub,
            "scope": scopes,
            "iat": now,
            "exp": now + 120,
            **changes,
        }
        return str(jwt.encode(claims, private, algorithm="RS256", headers={"kid": "test"}))

    return app, config, token


def headers(token: str, sid: str | None = None) -> dict[str, str]:
    result = {
        "Authorization": "Bearer " + token,
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-11-25",
    }
    if sid:
        result["Mcp-Session-Id"] = sid
    return result


def initialize(client: TestClient, token: str) -> str:
    response = client.post(
        "/mcp",
        headers=headers(token),
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            },
        },
    )
    assert response.status_code == 200, response.text
    sid = response.headers["mcp-session-id"]
    initialized = client.post(
        "/mcp",
        headers=headers(token, sid),
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
    )
    assert initialized.status_code == 202
    assert initialized.content == b""
    return sid


def rpc(client: TestClient, token: str, sid: str, method: str, params: Any = None) -> Any:
    return client.post(
        "/mcp",
        headers=headers(token, sid),
        json={"jsonrpc": "2.0", "id": 2, "method": method, "params": params or {}},
    )


def test_http_tools_and_worker(setup: Any) -> None:
    app, config, token = setup
    with TestClient(app) as client:
        auth = token()
        sid = initialize(client, auth)
        listing = rpc(client, auth, sid, "tools/list")
        assert listing.status_code == 200, listing.text
        names = {tool["name"] for tool in listing.json()["result"]["tools"]}
        assert len(names) == 8 and "dat_mint" not in names and "activate" not in names
        response = rpc(
            client,
            auth,
            sid,
            "tools/call",
            {"name": "adaptive_clock_rate", "arguments": {"coherence_phi": 0.5}},
        )
        assert response.status_code == 200, response.text
        assert response.json()["result"]["isError"] is False, response.text
        data = json.loads(response.json()["result"]["content"][0]["text"])
        assert data["rate"] == pytest.approx(14.1421356237)
        assert config.audit_path.exists()
        assert client.get("/mcp", headers=headers(auth, sid)).status_code == 405
        assert client.delete("/mcp", headers=headers(auth, sid)).status_code < 300
        assert rpc(client, auth, sid, "ping").status_code == 404


def test_http_auth_and_session_ownership(setup: Any) -> None:
    app, _, token = setup
    with TestClient(app) as client:
        assert client.post("/mcp").status_code == 401
        assert client.get("/.well-known/oauth-protected-resource/mcp").status_code == 200
        sid = initialize(client, token())
        for bad in (
            token(exp=1),
            token(aud="https://other.example/mcp"),
            token(iss="https://evil.example"),
            "invalid",
        ):
            assert rpc(client, bad, sid, "ping").status_code == 401
        assert rpc(client, token(sub="bob"), sid, "ping").status_code == 404
        limited = token(scopes="qspeace:catalog.read")
        listing = rpc(client, limited, sid, "tools/list").json()["result"]["tools"]
        assert [tool["name"] for tool in listing] == ["bcel_lookup"]
        assert (
            rpc(
                client,
                limited,
                sid,
                "tools/call",
                {"name": "adaptive_clock_rate", "arguments": {"coherence_phi": 1}},
            ).status_code
            == 403
        )
        assert (
            rpc(
                client, token(), sid, "tools/call", {"name": "dat_mint", "arguments": {}}
            ).status_code
            == 403
        )
        assert rpc(client, token(), sid, "ping").status_code == 200


def test_invalid_input_and_audit_failure(setup: Any) -> None:
    app, _, token = setup
    with TestClient(app) as client:
        auth = token()
        sid = initialize(client, auth)
        for args in ({"coherence_phi": 2}, {"coherence_phi": "0.5"}):
            response = rpc(
                client, auth, sid, "tools/call", {"name": "adaptive_clock_rate", "arguments": args}
            )
            assert response.status_code == 200
            assert response.json()["result"]["isError"] is True
        invalid = client.post(
            "/mcp", headers={**headers(auth, sid), "Origin": "https://evil.example"}, json={}
        )
        assert invalid.status_code == 403
        oversized = client.post("/mcp", headers=headers(auth, sid), content=b"x" * 65537)
        assert oversized.status_code == 413
        app.audit.db.close()
        refused = rpc(client, auth, sid, "tools/call", {"name": "bcel_lookup", "arguments": {}})
        assert refused.status_code == 503


def test_rate_session_limits_and_no_reset(setup: Any) -> None:
    app, config, token = setup
    with TestClient(app) as client:
        auth = token()
        ids = [initialize(client, auth) for _ in range(4)]
        response = client.post(
            "/mcp",
            headers=headers(auth),
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            },
        )
        assert response.status_code == 429
        owner = app.identity("Bearer " + auth)[0]
        app.rates[owner] = (0, time.monotonic())
        response = rpc(client, auth, ids[0], "ping")
        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert rpc(client, token(sub="bob"), ids[0], "ping").status_code == 404


def test_official_sdk_over_real_http(setup: Any, tmp_path: Path) -> None:
    import asyncio
    import socket
    import threading

    import httpx
    import uvicorn
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    _, config, token = setup
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    port = listener.getsockname()[1]
    resource = f"http://127.0.0.1:{port}/mcp"
    config = config.model_copy(
        update={
            "resource": resource,
            "allowed_hosts": [f"127.0.0.1:{port}"],
            "audit_path": tmp_path / "socket-audit.sqlite",
        }
    )
    app = create_app(config)
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    for _ in range(500):
        if server.started:
            break
        time.sleep(0.01)
    assert server.started

    async def check() -> None:
        async with (
            httpx.AsyncClient(
                headers={"Authorization": "Bearer " + token(aud=resource)}, timeout=15
            ) as http,
            streamable_http_client(resource, http_client=http) as (read, write, session_id),
            ClientSession(read, write) as session,
        ):
            initialized = await session.initialize()
            assert initialized.serverInfo.name == "q-speace-http"
            await session.send_ping()
            assert len((await session.list_tools()).tools) == 8
            assert session_id() is not None
            for name, arguments in (
                ("bcel_lookup", {"concept": "Homeostasis"}),
                (
                    "metabolism_cost_eval",
                    {
                        "num_qubits": 0,
                        "num_gates": 1,
                        "delta_utility": 2,
                        "delta_entropy_info": 1,
                    },
                ),
                ("adaptive_clock_rate", {"coherence_phi": 0.5}),
            ):
                result = await session.call_tool(name, arguments)
                assert result.isError is False, result
            invalid = await session.call_tool("adaptive_clock_rate", {"coherence_phi": 2})
            assert invalid.isError is True
            await session.send_ping()

    try:
        asyncio.run(asyncio.wait_for(check(), 30))
    finally:
        server.should_exit = True
        thread.join(5)
        listener.close()
    assert not thread.is_alive()


def test_worker_timeout_and_concurrent_admission(setup: Any) -> None:
    import asyncio

    from q_speace.remote_mcp.service import Execution, ServiceError

    _, config, _ = setup

    async def check() -> None:
        execution = Execution(config.model_copy(update={"worker_seconds": 0.001}))
        with pytest.raises(ServiceError, match="worker_timeout"):
            await execution.compute("alice", "bcel_lookup", {})
        assert execution.total == 0 and execution.active == {}
        execution = Execution(config)
        results = await asyncio.gather(
            *[execution.compute("alice", "bcel_lookup", {}) for _ in range(3)],
            return_exceptions=True,
        )
        assert sum(isinstance(r, dict) for r in results) == 2
        refused = [r for r in results if isinstance(r, ServiceError)]
        assert len(refused) == 1 and refused[0].status == 429
        assert execution.total == 0 and execution.active == {}

    asyncio.run(check())


def test_public_config_builder_and_key_rotation(
    setup: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys

    import httpx

    from examples.mcp_http_config_from_jwks import main

    _, _, _ = setup
    public = rsa.generate_private_key(public_exponent=65537, key_size=2048).public_key()
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(public, as_dict=True)
    jwk.update(kid="rotated-public", use="sig", alg="RS256")
    calls = []

    def response(url: str, **kwargs: Any) -> httpx.Response:
        calls.append(url)
        return httpx.Response(200, json={"keys": [jwk]}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", response)
    output = tmp_path / "public-config.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "builder",
            "--issuer",
            "https://issuer.example.test/",
            "--resource",
            "https://service.example.test/mcp",
            "--output",
            str(output),
        ],
    )
    main()
    config = HTTPConfig.load(output)
    assert calls == ["https://issuer.example.test/.well-known/jwks.json"]
    assert list(config.public_keys) == ["rotated-public"]
    assert config.host == "0.0.0.0" and config.total_workers == 1
    assert "PRIVATE KEY" not in output.read_text()
    with pytest.raises(FileExistsError):
        main()

