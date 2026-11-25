"""T226 bounded online MCP adapter; the supervising LLM reasons separately."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ENDPOINT = "https://q-speace-mcp.onrender.com/mcp"
ISSUER = "https://dev-imfska6viiq1ehqw.us.auth0.com/"
CLASSES = ["normal", "bearing_fault", "sensor_fault"]
DISTRIBUTIONS = [[0.05, 0.05, 0.9], [0.1, 0.1, 0.8]]
TASK = {
    "sensor_a_celsius": [22, 85, 21, 86],
    "reference_b_celsius": [22, 22, 21, 22],
    "vibration_rms_mm_s": [0.12, 0.11, 0.12, 0.12],
    "checksum_failure_indices": [1, 3],
    "classes": CLASSES,
    "distributions": DISTRIBUTIONS,
}


class PolicyRefusalError(Exception):
    """A local pre-dispatch policy limit was reached."""


def _reject_json_constant(token: str) -> Any:
    raise ValueError(f"non_finite_json_constant:{token}")


@dataclass
class Budget:
    tool_limit: int = 5
    energy_limit: float = 0.001
    tool_attempts: int = 0
    reserved_energy: float = 0.0

    def __post_init__(self) -> None:
        if self.tool_limit < 0:
            raise ValueError("invalid_tool_limit")
        if not math.isfinite(self.energy_limit) or self.energy_limit < 0:
            raise ValueError("invalid_energy_limit")
        if self.tool_attempts < 0:
            raise ValueError("invalid_tool_attempts")
        if not math.isfinite(self.reserved_energy) or self.reserved_energy < 0:
            raise ValueError("invalid_reserved_energy")

    def reserve_call(self) -> None:
        if self.tool_attempts >= self.tool_limit:
            raise PolicyRefusalError("tool_budget")
        self.tool_attempts += 1

    def reserve_energy(self, joules: float) -> None:
        if not math.isfinite(joules) or joules < 0:
            raise ValueError("invalid_energy_estimate")
        if self.reserved_energy + joules > self.energy_limit:
            raise PolicyRefusalError("modeled_energy_budget")
        self.reserved_energy += joules


class Adapter:
    def __init__(self, session: Any, budget: Budget, events: list[dict[str, Any]]) -> None:
        self.session, self.budget, self.events = session, budget, events

    async def call(self, name: str, arguments: dict[str, Any], *, error: bool = False) -> Any:
        self.budget.reserve_call()
        started = time.monotonic()
        result = await asyncio.wait_for(self.session.call_tool(name, arguments), 60)
        self.events.append(
            {
                "event": "tool_result",
                "name": name,
                "arguments": arguments,
                "is_error": bool(result.isError),
                "elapsed_seconds": time.monotonic() - started,
                "attempt": self.budget.tool_attempts,
            }
        )
        if bool(result.isError) != error:
            raise ValueError("unexpected_tool_error_status")
        if error:
            return None
        blocks = [x.text for x in result.content if x.type == "text"]
        if len(blocks) != 1:
            raise ValueError("unexpected_content")
        value = json.loads(blocks[0], parse_constant=_reject_json_constant)
        if not isinstance(value, dict):
            raise ValueError("unexpected_result_type")
        self.events[-1]["result"] = value
        return value


async def diagnose(adapter: Adapter) -> dict[str, Any]:
    catalog = await adapter.call("bcel_lookup", {"concept": "Homeostasis"})
    entries = catalog.get("entries", [])
    if len(entries) != 1 or entries[0].get("classification") != "functional":
        raise PolicyRefusalError("bcel")
    phi = 1 - sum(abs(a - b) for a, b in zip(*DISTRIBUTIONS, strict=True)) / 2
    try:
        clock = await adapter.call("adaptive_clock_rate", {"coherence_phi": phi})
    except ValueError as exc:
        if str(exc).startswith("non_finite_json_constant:"):
            raise ValueError("invalid_rate") from exc
        raise
    rate = float(clock["rate"])
    if not math.isfinite(rate) or rate <= 0:
        raise ValueError("invalid_rate")
    delay = min(0.1, 1 / rate)
    await asyncio.sleep(delay)
    adapter.events.append({"event": "scheduled_backoff", "phi": phi, "seconds": delay})
    cost = await adapter.call(
        "metabolism_cost_eval",
        {
            "num_qubits": 0,
            "num_gates": 1,
            "duration_s": 0.01,
            "delta_utility": 2.0,
            "delta_entropy_info": 1.0,
        },
    )
    if cost.get("passes_sevo") is not True or cost.get("sevo_defined") is not True:
        raise PolicyRefusalError("sevo")
    adapter.budget.reserve_energy(float(cost["estimated_energy_joules"]))
    adapter.events.append(
        {"event": "modeled_energy_reserved", "joules": adapter.budget.reserved_energy}
    )
    pooled = await adapter.call(
        "kl_barycentre_aggregate",
        {"distributions": DISTRIBUTIONS, "weights": [0.5, 0.5], "max_iter": 50},
    )
    probabilities = pooled["barycentre"]
    if (
        not isinstance(probabilities, list)
        or len(probabilities) != len(CLASSES)
        or any(not math.isfinite(x) or x < 0 for x in probabilities)
        or not math.isclose(sum(probabilities), 1, abs_tol=1e-6)
    ):
        raise ValueError("invalid_barycentre")
    prediction = CLASSES[max(range(len(CLASSES)), key=probabilities.__getitem__)]
    await adapter.call("adaptive_clock_rate", {"coherence_phi": "invalid"}, error=True)
    await asyncio.wait_for(adapter.session.send_ping(), 60)
    adapter.events.append({"event": "invalid_input_recovery", "ping_passed": True})
    try:
        await adapter.call("bcel_lookup", {"concept": "Homeostasis"})
    except PolicyRefusalError as exc:
        if str(exc) != "tool_budget":
            raise
        adapter.events.append({"event": "pre_dispatch_refusal", "reason": "tool_budget"})
    else:
        raise AssertionError("sixth_call_was_not_refused")
    return {
        "prediction": prediction,
        "reference_label": "sensor_fault",
        "reference_match": prediction == "sensor_fault",
        "barycentre": probabilities,
        "fixture_distributions": DISTRIBUTIONS,
        "advisory": "Inspect sensor A and data integrity; no actuation.",
        "invalid_input_recovery": True,
        "sixth_call_refused_before_dispatch": True,
        "tool_attempts": adapter.budget.tool_attempts,
        "reserved_modeled_energy_joules": adapter.budget.reserved_energy,
        "provider_tokens": None,
        "measured_physical_energy_joules": None,
        "llm_decision": "Recorded separately by the supervising LLM subagent.",
    }


async def connect(credentials: Path, events: list[dict[str, Any]]) -> dict[str, Any]:
    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    secret = json.loads(credentials.read_text(encoding="utf-8"))
    async with httpx.AsyncClient(timeout=60) as auth:
        response = await auth.post(
            ISSUER + "oauth/token",
            json={
                "grant_type": "client_credentials",
                "client_id": secret["client_id"],
                "client_secret": secret["client_secret"],
                "audience": ENDPOINT,
            },
        )
        response.raise_for_status()
        token = response.json()["access_token"]
    events.append({"event": "oauth", "status": "passed", "token_logged": False})
    async with (
        httpx.AsyncClient(headers={"Authorization": "Bearer " + token}, timeout=60) as http,
        streamable_http_client(ENDPOINT, http_client=http) as (read, write, _),
        ClientSession(read, write) as session,
    ):
        initialized = await session.initialize()
        await session.send_ping()
        names = sorted(t.name for t in (await session.list_tools()).tools)
        events.append({"event": "handshake", "server": initialized.serverInfo.name, "tools": names})
        required = {
            "bcel_lookup",
            "adaptive_clock_rate",
            "metabolism_cost_eval",
            "kl_barycentre_aggregate",
        }
        if not required.issubset(names):
            raise PolicyRefusalError("missing_tool_scope")
        return await diagnose(Adapter(session, Budget(), events))


def _mcp_package_version() -> str:
    try:
        return importlib.metadata.version("mcp")
    except importlib.metadata.PackageNotFoundError:
        return "unavailable"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--credentials", type=Path, default=Path(".qspeace-dev/auth0-agent-client.json")
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    events: list[dict[str, Any]] = []
    started = time.monotonic()
    summary: dict[str, Any] = {
        "spec": "T226-v1",
        "endpoint": ENDPOINT,
        "task": TASK,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "task_sha256": hashlib.sha256(json.dumps(TASK, sort_keys=True).encode()).hexdigest(),
        "mcp_version": _mcp_package_version(),
        "tool_limit": 5,
        "modeled_energy_limit_joules": 0.001,
    }
    failed = False
    try:
        summary.update(asyncio.run(asyncio.wait_for(connect(args.credentials, events), 180)))
        summary["status"] = "passed"
    except Exception as exc:
        # Do not serialize exception messages/requests: they may include credentials.
        summary.update(status="failed", error_type=type(exc).__name__)
        failed = True
    finally:
        summary["wall_seconds"] = time.monotonic() - started
        (args.output / "events.jsonl").write_text(
            "".join(json.dumps(x, allow_nan=False) + "\n" for x in events), encoding="utf-8"
        )
        (args.output / "summary.json").write_text(
            json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
    print(json.dumps({"status": summary["status"], "evidence": str(args.output)}))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
