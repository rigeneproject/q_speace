"""T247: MCP read-only Resources & Bootstrap Prompts across stdio and authenticated HTTP."""

# Optional HTTP dependencies are checked before importing server.
# ruff: noqa: E402
from __future__ import annotations

import asyncio
import io
import json
import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from q_speace.bcel.catalog import BCELCatalog
from q_speace.economy.mcp_server import _stdio_loop
from q_speace.remote_mcp.service import verify_audit_chain
from q_speace.remote_mcp.worker import SCOPES as HTTP_TOOL_SCOPES
from q_speace.singularity.mcp_guidance import (
    RESOURCE_BCEL_CATALOG,
    RESOURCE_ORGANISM_LOOP,
    RESOURCE_SINGULARITY_MANIFEST,
    RESOURCE_TOOL_WORKFLOWS,
    get_mcp_prompt,
    list_mcp_prompts,
    list_mcp_resources,
    read_mcp_resource,
)


def _stdio_exchange(
    monkeypatch: pytest.MonkeyPatch, messages: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    stdin = io.StringIO("\n".join(json.dumps(m) for m in messages) + "\n")
    stdout = io.StringIO()
    monkeypatch.setattr("sys.stdin", stdin)
    monkeypatch.setattr("sys.stdout", stdout)
    assert _stdio_loop() == 0
    return [json.loads(line) for line in stdout.getvalue().splitlines() if line.strip()]


def test_t247_guidance_unit_validation_and_bcel() -> None:
    resources = list_mcp_resources()
    uris = [r["uri"] for r in resources]
    assert uris == [
        RESOURCE_ORGANISM_LOOP,
        RESOURCE_TOOL_WORKFLOWS,
        RESOURCE_SINGULARITY_MANIFEST,
        RESOURCE_BCEL_CATALOG,
    ]

    # Organism loop guide is Markdown with explicit BCEL & advisory-only boundaries.
    loop_res = read_mcp_resource(RESOURCE_ORGANISM_LOOP)
    assert loop_res["mimeType"] == "text/markdown"
    assert "advisory_only: true" in loop_res["text"]
    assert "self_approval_permitted: false" in loop_res["text"]

    # Tool workflow JSON covers the exact 12 HTTP tools and scopes, AND every example payload
    # must pass the strict HTTP worker validator + live dispatcher without errors.
    from q_speace.economy.mcp_server import _dispatch
    from q_speace.remote_mcp.worker import validate as validate_http_tool

    wf_res = read_mcp_resource(RESOURCE_TOOL_WORKFLOWS)
    wf = json.loads(wf_res["text"])
    assert wf["http_tool_count"] == 12
    listed_tools = {t["name"]: t["scope"] for phase in wf["phases"] for t in phase["tools"]}
    assert listed_tools == HTTP_TOOL_SCOPES
    for phase in wf["phases"]:
        for spec in phase["tools"]:
            validated = validate_http_tool(spec["name"], spec["example_arguments"])
            out = _dispatch(spec["name"], validated)
            assert isinstance(out, dict)

    # Singularity manifest and BCEL catalog resources parse cleanly as strict JSON.
    manifest = json.loads(read_mcp_resource(RESOURCE_SINGULARITY_MANIFEST)["text"])
    assert manifest["framework_id"] == "q_speace.singularity.v1"
    assert manifest["advisory_only"] is True
    bcel = json.loads(read_mcp_resource(RESOURCE_BCEL_CATALOG)["text"])
    assert bcel["functional_count"] >= 20
    assert bcel["accidental_count"] >= 5

    with pytest.raises(KeyError, match="unknown_resource_uri"):
        read_mcp_resource("qspeace://does-not-exist")

    # Prompts list & materialize cleanly.
    prompts = list_mcp_prompts()
    assert [p["name"] for p in prompts] == [
        "organism_bootstrap",
        "metabolic_action_gate",
        "federated_swarm_cycle",
    ]
    boot = get_mcp_prompt("organism_bootstrap", {"agent_role": "planner", "mode": "swarm_node"})
    assert "iont_node_assess" in boot["messages"][0]["content"]["text"]
    assert "kl_barycentre_aggregate" in boot["messages"][0]["content"]["text"]

    gate = get_mcp_prompt(
        "metabolic_action_gate",
        {"action_summary": "Run calibration batch", "coherence_phi": "0.75"},
    )
    assert "0.7500" in gate["messages"][0]["content"]["text"]

    swarm = get_mcp_prompt(
        "federated_swarm_cycle",
        {"node_count": "6", "scale_tier": "SIMULATION_DIGITAL_TWIN"},
    )
    assert "`6` nodes" in swarm["messages"][0]["content"]["text"]

    # Fail-closed argument validation.
    with pytest.raises(KeyError, match="unknown_prompt"):
        get_mcp_prompt("nonexistent_prompt", {})
    with pytest.raises(ValueError, match="unknown_prompt_arguments"):
        get_mcp_prompt("organism_bootstrap", {"injected": "x"})
    with pytest.raises(ValueError, match="mode must be one of"):
        get_mcp_prompt("organism_bootstrap", {"mode": "autonomous_unbounded"})
    with pytest.raises(ValueError, match="agent_role"):
        get_mcp_prompt("organism_bootstrap", {"agent_role": "bad\nrole"})
    with pytest.raises(ValueError, match="action_summary is required"):
        get_mcp_prompt("metabolic_action_gate", {})
    with pytest.raises(ValueError, match="coherence_phi"):
        get_mcp_prompt("metabolic_action_gate", {"action_summary": "ok", "coherence_phi": "nan"})
    with pytest.raises(ValueError, match="coherence_phi"):
        get_mcp_prompt("metabolic_action_gate", {"action_summary": "ok", "coherence_phi": "1.5"})
    with pytest.raises(ValueError, match="node_count"):
        get_mcp_prompt("federated_swarm_cycle", {"node_count": "1"})
    with pytest.raises(ValueError, match="scale_tier"):
        get_mcp_prompt("federated_swarm_cycle", {"scale_tier": "UNKNOWN_TIER"})

    assert BCELCatalog().is_functional(
        "Read-only MCP organism-loop resources and bootstrap prompt templates (T247)"
    )


def test_t247_stdio_resources_and_prompts_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = _stdio_exchange(
        monkeypatch,
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "t247-stdio", "version": "1"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {"jsonrpc": "2.0", "id": 3, "method": "resources/list", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "resources/read",
                "params": {"uri": RESOURCE_ORGANISM_LOOP},
            },
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "resources/read",
                "params": {"uri": "qspeace://missing"},
            },
            {"jsonrpc": "2.0", "id": 6, "method": "prompts/list", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "prompts/get",
                "params": {
                    "name": "organism_bootstrap",
                    "arguments": {"agent_role": "coordinator", "mode": "single_agent"},
                },
            },
            {
                "jsonrpc": "2.0",
                "id": 8,
                "method": "prompts/get",
                "params": {"name": "metabolic_action_gate", "arguments": {}},
            },
        ],
    )
    assert responses[0]["result"]["capabilities"] == {"tools": {}, "resources": {}, "prompts": {}}
    assert len(responses[1]["result"]["tools"]) == 14
    assert len(responses[2]["result"]["resources"]) == 4
    assert responses[3]["result"]["contents"][0]["uri"] == RESOURCE_ORGANISM_LOOP
    assert "error" in responses[4]
    assert len(responses[5]["result"]["prompts"]) == 3
    assert "coordinator" in responses[6]["result"]["messages"][0]["content"]["text"]
    assert "error" in responses[7]


def test_t247_http_scope_enforcement_audit_and_official_sdk(tmp_path: Path) -> None:
    pytest.importorskip("mcp")
    jwt = pytest.importorskip("jwt")
    import httpx
    import uvicorn
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    from pydantic import AnyUrl
    from starlette.testclient import TestClient

    from q_speace.remote_mcp.config import HTTPConfig
    from q_speace.remote_mcp.server import create_app

    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = (
        private.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )

    def make_token(aud: str, scopes: str, sub: str = "agent-1") -> str:
        now = int(time.time())
        return str(
            jwt.encode(
                {
                    "iss": "https://issuer.example.test",
                    "aud": aud,
                    "sub": sub,
                    "scope": scopes,
                    "iat": now,
                    "exp": now + 180,
                },
                private,
                algorithm="RS256",
                headers={"kid": "t247"},
            )
        )

    # 1. TestClient check: scope enforcement + audit chain on resources/prompts.
    audit_db = tmp_path / "t247-audit.sqlite"
    cfg = HTTPConfig(
        issuer="https://issuer.example.test",
        resource="http://127.0.0.1:8000/mcp",
        public_keys={"t247": public},
        audit_path=audit_db,
        allowed_hosts=["testserver", "127.0.0.1:8000"],
        burst=40,
    )
    app = create_app(cfg)
    compute_only = make_token(cfg.resource, "qspeace:compute")
    catalog_token = make_token(cfg.resource, "qspeace:catalog.read qspeace:compute")

    def hdrs(tok: str, sid: str | None = None) -> dict[str, str]:
        h = {
            "Authorization": f"Bearer {tok}",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": "2025-11-25",
        }
        if sid:
            h["Mcp-Session-Id"] = sid
        return h

    with TestClient(app) as client:
        init = client.post(
            "/mcp",
            headers=hdrs(compute_only),
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "t247", "version": "1"},
                },
            },
        )
        assert init.status_code == 200
        sid = init.headers["mcp-session-id"]
        client.post(
            "/mcp",
            headers=hdrs(compute_only, sid),
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        )
        # Missing qspeace:catalog.read -> 403 scope_required for all 4 methods!
        for method, params in (
            ("resources/list", {}),
            ("resources/read", {"uri": RESOURCE_ORGANISM_LOOP}),
            ("prompts/list", {}),
            ("prompts/get", {"name": "organism_bootstrap", "arguments": {}}),
        ):
            r = client.post(
                "/mcp",
                headers=hdrs(compute_only, sid),
                json={"jsonrpc": "2.0", "id": 2, "method": method, "params": params},
            )
            assert r.status_code == 403, f"{method}: {r.text}"
            assert r.json()["error"] == "scope_required"

        # With qspeace:catalog.read -> succeeds and logs hash-chained audit rows.
        read_resp = client.post(
            "/mcp",
            headers=hdrs(catalog_token, sid),
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "resources/read",
                "params": {"uri": RESOURCE_ORGANISM_LOOP},
            },
        )
        assert read_resp.status_code == 200
        assert (
            "Q-SPEACE Canonical Organism-Loop" in read_resp.json()["result"]["contents"][0]["text"]
        )

        prompt_resp = client.post(
            "/mcp",
            headers=hdrs(catalog_token, sid),
            json={
                "jsonrpc": "2.0",
                "id": 4,
                "method": "prompts/get",
                "params": {
                    "name": "metabolic_action_gate",
                    "arguments": {"action_summary": "Scale federation"},
                },
            },
        )
        assert prompt_resp.status_code == 200
        assert "Scale federation" in prompt_resp.json()["result"]["messages"][0]["content"]["text"]

    chain = verify_audit_chain(audit_db)
    assert chain["valid"] is True
    assert chain["row_count"] == 4  # intent + result for resources/read and prompts/get

    # 2. End-to-end check with the official MCP Python SDK over real localhost HTTP.
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    port = listener.getsockname()[1]
    resource_url = f"http://127.0.0.1:{port}/mcp"
    sdk_cfg = cfg.model_copy(
        update={
            "resource": resource_url,
            "allowed_hosts": [f"127.0.0.1:{port}"],
            "audit_path": tmp_path / "t247-sdk-audit.sqlite",
        }
    )
    sdk_app = create_app(sdk_cfg)
    server = uvicorn.Server(
        uvicorn.Config(
            sdk_app,
            log_level="warning",
            access_log=False,
            timeout_graceful_shutdown=1,
        )
    )
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    for _ in range(500):
        if server.started:
            break
        time.sleep(0.01)
    assert server.started

    full_tok = make_token(
        resource_url, "qspeace:catalog.read qspeace:compute qspeace:simulation.compute"
    )

    async def verify_sdk() -> None:
        async with (
            httpx.AsyncClient(headers={"Authorization": f"Bearer {full_tok}"}, timeout=15) as http,
            streamable_http_client(resource_url, http_client=http) as (read, write, _),
            ClientSession(read, write) as session,
        ):
            init_res = await session.initialize()
            assert init_res.capabilities.resources is not None
            assert init_res.capabilities.prompts is not None
            assert len((await session.list_tools()).tools) == 12

            res_list = await session.list_resources()
            assert len(res_list.resources) == 4
            read_out = await session.read_resource(AnyUrl(RESOURCE_TOOL_WORKFLOWS))
            wf = json.loads(read_out.contents[0].text)  # type: ignore[union-attr]
            assert wf["http_tool_count"] == 12

            p_list = await session.list_prompts()
            assert len(p_list.prompts) == 3
            p_out = await session.get_prompt(
                "organism_bootstrap", {"agent_role": "sdk-agent", "mode": "swarm_node"}
            )
            assert "sdk-agent" in p_out.messages[0].content.text  # type: ignore[union-attr]

    try:
        asyncio.run(asyncio.wait_for(verify_sdk(), 30))
    finally:
        server.should_exit = True
        thread.join(5)
        listener.close()
    assert not thread.is_alive()
