"""Protocol and primitive integration checks for T223."""

from __future__ import annotations

import io
import json
import sys
from typing import Any

import pytest

from q_speace.bcel.catalog import BCELCatalog
from q_speace.economy.mcp_server import _stdio_loop
from q_speace.edd_cvt.ilf import InformationalLogicalField
from q_speace.metabolism.cognitive_cost_model import QuantumCostModel, QuantumOperation


def exchange(monkeypatch: pytest.MonkeyPatch, messages: list[Any]) -> list[dict[str, Any]]:
    source = "\n".join(m if isinstance(m, str) else json.dumps(m) for m in messages)
    output = io.StringIO()
    monkeypatch.setattr(sys, "stdin", io.StringIO(source + "\n"))
    monkeypatch.setattr(sys, "stdout", output)
    assert _stdio_loop() == 0
    return [json.loads(line) for line in output.getvalue().splitlines()]


def request(method: str, params: Any = None, rpc_id: Any = 1) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "method": method,
        "params": {} if params is None else params,
    }


def initialize(version: str = "2025-03-26") -> dict[str, Any]:
    return request(
        "initialize",
        {
            "protocolVersion": version,
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1"},
        },
    )


def call(name: str, arguments: Any) -> dict[str, Any]:
    return request("tools/call", {"name": name, "arguments": arguments})


def payload(response: dict[str, Any]) -> Any:
    assert response["result"]["isError"] is False
    return json.loads(response["result"]["content"][0]["text"])


@pytest.mark.parametrize(
    "version,expected",
    [("2025-03-26", "2025-03-26"), ("2024-11-05", "2024-11-05"), ("future", "2025-03-26")],
)
def test_handshake(monkeypatch: pytest.MonkeyPatch, version: str, expected: str) -> None:
    responses = exchange(
        monkeypatch,
        [
            initialize(version),
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            request("ping", rpc_id=0),
            request("tools/list", rpc_id="list"),
        ],
    )
    assert len(responses) == 3
    assert responses[0]["result"] == {
        "protocolVersion": expected,
        "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
        "serverInfo": {"name": "q-speace-mcp", "version": "0.1.0"},
    }
    assert responses[1] == {"jsonrpc": "2.0", "id": 0, "result": {}}
    tools = responses[2]["result"]["tools"]
    assert len(tools) == 14
    assert all(tool["inputSchema"]["type"] == "object" for tool in tools)
    clock = next(tool for tool in tools if tool["name"] == "adaptive_clock_rate")
    assert clock["inputSchema"]["required"] == ["coherence_phi"]


def test_lifecycle_and_notification_silence(monkeypatch: pytest.MonkeyPatch) -> None:
    replies = exchange(
        monkeypatch,
        [
            initialize(),
            request("tools/list"),
            {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "dat_mint"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            initialize(),
            request("ping"),
        ],
    )
    assert len(replies) == 4
    assert replies[1]["error"]["code"] == -32602
    assert replies[2]["error"]["code"] == -32602
    assert replies[3]["result"] == {}


@pytest.mark.parametrize("coherence", [0, 0.5, 1])
def test_clock_matches_native(monkeypatch: pytest.MonkeyPatch, coherence: float) -> None:
    result = payload(
        exchange(monkeypatch, [call("adaptive_clock_rate", {"coherence_phi": coherence})])[0]
    )
    assert (
        result["rate"] == InformationalLogicalField(coherence_phi=coherence).adaptive_clock_rate()
    )
    assert result["s_info"] == 1 - coherence


def test_cost_matches_native_and_nonfinite_sevo(monkeypatch: pytest.MonkeyPatch) -> None:
    arguments = {
        "num_qubits": 2,
        "num_gates": 4,
        "num_spikes": 3,
        "duration_s": 2,
        "delta_utility": 3,
        "delta_entropy_info": 1,
    }
    replies = exchange(
        monkeypatch,
        [
            call("metabolism_cost_eval", arguments),
            call("metabolism_cost_eval", {**arguments, "delta_entropy_info": 0}),
        ],
    )
    result = payload(replies[0])
    assert result["estimated_energy_joules"] == QuantumCostModel().energy_joules(
        QuantumOperation(2, 4, num_spikes=3), 2
    )
    assert result["sevo"] == 3
    assert result["passes_sevo"] is True
    rejected = payload(replies[1])
    assert rejected["sevo"] is None
    assert rejected["sevo_defined"] is False
    assert rejected["passes_sevo"] is False


def test_bcel_lookup_read_only_and_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    concept = BCELCatalog().all()[0].concept
    replies = exchange(
        monkeypatch,
        [
            call("bcel_lookup", {}),
            call("bcel_lookup", {"concept": concept}),
            call("bcel_lookup", {"concept": "unknown"}),
        ],
    )
    assert len(payload(replies[0])["entries"]) == len(BCELCatalog().all())
    assert payload(replies[1])["entries"][0]["concept"] == concept
    assert replies[2]["result"]["isError"] is True


@pytest.mark.parametrize(
    "name,arguments",
    [
        ("unknown", {}),
        ("adaptive_clock_rate", {}),
        ("adaptive_clock_rate", {"coherence_phi": 2}),
        ("adaptive_clock_rate", {"coherence_phi": float("inf")}),
        ("adaptive_clock_rate", []),
        (
            "metabolism_cost_eval",
            {"num_qubits": -1, "num_gates": 2, "delta_utility": 2, "delta_entropy_info": 1},
        ),
        ("bcel_lookup", {"extra": True}),
    ],
)
def test_bad_tool_arguments(monkeypatch: pytest.MonkeyPatch, name: str, arguments: Any) -> None:
    response = exchange(monkeypatch, [call(name, arguments)])[0]
    if (
        name == "unknown"
        or not isinstance(arguments, dict)
        or arguments.get("coherence_phi") == float("inf")
    ):
        assert response["error"]["code"] in (-32602, -32700)
    else:
        assert response["result"]["isError"] is True


def test_invalid_envelopes_recover(monkeypatch: pytest.MonkeyPatch) -> None:
    replies = exchange(
        monkeypatch,
        ["bad-json", [], None, request("ping", []), request("unknown"), request("ping")],
    )
    assert [reply["error"]["code"] for reply in replies[:-1]] == [
        -32700,
        -32600,
        -32600,
        -32602,
        -32601,
    ]
    assert replies[-1]["result"] == {}


def test_standard_economy_call_and_error(monkeypatch: pytest.MonkeyPatch) -> None:
    replies = exchange(
        monkeypatch,
        [
            call(
                "compute_jc", {"J": 1, "delta_S": -0.1, "delta_I_c": 0.5, "R_b": 0.5, "delta_C": 0}
            ),
            call("dat_spend", {"token_id": "missing-token", "amount": 1, "target": "test", "t": 0}),
        ],
    )
    assert payload(replies[0])["confidence"] == 1
    assert replies[1]["result"]["isError"] is True


def test_official_sdk_stdio_session() -> None:
    """Optional end-to-end check, run in an environment with the MCP SDK."""
    import asyncio
    from pathlib import Path

    sdk = pytest.importorskip("mcp")
    transport = pytest.importorskip("mcp.client.stdio")

    async def run() -> None:
        params = sdk.StdioServerParameters(
            command=sys.executable,
            args=["-m", "q_speace.economy.mcp_server"],
            cwd=str(Path(__file__).resolve().parents[1]),
        )
        async with (
            transport.stdio_client(params) as (reader, writer),
            sdk.ClientSession(reader, writer) as session,
        ):
            result = await session.initialize()
            assert result.serverInfo.name == "q-speace-mcp"
            await session.send_ping()
            listing = await session.list_tools()
            assert len(listing.tools) == 14
            for name, arguments in (
                ("adaptive_clock_rate", {"coherence_phi": 0.5}),
                (
                    "metabolism_cost_eval",
                    {
                        "num_qubits": 1,
                        "num_gates": 1,
                        "delta_utility": 2,
                        "delta_entropy_info": 1,
                    },
                ),
                ("bcel_lookup", {}),
            ):
                called = await session.call_tool(name, arguments)
                assert called.isError is False
                assert called.content[0].type == "text"
            invalid = await session.call_tool("adaptive_clock_rate", {"coherence_phi": 2})
            assert invalid.isError is True
            await session.send_ping()
            recovered = await session.call_tool("adaptive_clock_rate", {"coherence_phi": 0.5})
            assert recovered.isError is False

    asyncio.run(asyncio.wait_for(run(), timeout=30))
