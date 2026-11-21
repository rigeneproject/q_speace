"""T226 client policy tests; no credentials or network required."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest

from q_speace.bcel.catalog import BCELCatalog
from q_speace.experiments.online_agent import Adapter, Budget, PolicyRefusalError, diagnose


class Session:
    def __init__(self, overrides: dict[str, Any] | None = None) -> None:
        self.calls: list[str] = []
        self.pings = 0
        self.overrides = overrides or {}

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        self.calls.append(name)
        error = arguments.get("coherence_phi") == "invalid"
        payload = {
            "bcel_lookup": {"entries": [{"classification": "functional"}]},
            "adaptive_clock_rate": {"rate": 30.0},
            "metabolism_cost_eval": {
                "passes_sevo": True,
                "sevo_defined": True,
                "estimated_energy_joules": 0.0003,
            },
            "kl_barycentre_aggregate": {"barycentre": [0.07, 0.07, 0.86]},
        }
        payload.update(self.overrides)
        return SimpleNamespace(
            isError=error,
            content=[SimpleNamespace(type="text", text=json.dumps(payload[name]))],
        )

    async def send_ping(self) -> None:
        self.pings += 1


def test_success_reserves_before_dispatch_and_recovers() -> None:
    session = Session()
    events: list[dict[str, Any]] = []
    budget = Budget()
    result = asyncio.run(diagnose(Adapter(session, budget, events)))
    assert result["reference_match"] and result["prediction"] == "sensor_fault"
    assert len(session.calls) == 5 and session.pings == 1
    assert budget.reserved_energy == 0.0003
    assert events[-1] == {"event": "pre_dispatch_refusal", "reason": "tool_budget"}
    reservation = next(i for i, e in enumerate(events) if e["event"] == "modeled_energy_reserved")
    aggregate = next(i for i, e in enumerate(events) if e.get("name") == "kl_barycentre_aggregate")
    assert reservation < aggregate
    assert BCELCatalog().is_functional("Bounded diagnostic feedback agent (T226)")


def test_budget_refusal_does_not_contact_server() -> None:
    session = Session()
    adapter = Adapter(session, Budget(tool_limit=0), [])
    with pytest.raises(PolicyRefusalError, match="tool_budget"):
        asyncio.run(adapter.call("bcel_lookup", {}))
    assert session.calls == []


@pytest.mark.parametrize("joules", [float("nan"), float("inf"), -1.0])
def test_invalid_energy_is_refused(joules: float) -> None:
    budget = Budget()
    with pytest.raises(ValueError, match="invalid_energy"):
        budget.reserve_energy(joules)
    assert budget.reserved_energy == 0


def test_energy_budget_prevents_aggregation() -> None:
    session = Session()
    adapter = Adapter(session, Budget(energy_limit=0), [])
    with pytest.raises(PolicyRefusalError, match="modeled_energy_budget"):
        asyncio.run(diagnose(adapter))
    assert "kl_barycentre_aggregate" not in session.calls
    assert adapter.budget.tool_attempts == 3


@pytest.mark.parametrize(
    ("tool", "payload", "reason"),
    [
        ("bcel_lookup", {"entries": [{"classification": "accidental"}]}, "bcel"),
        ("adaptive_clock_rate", {"rate": 0}, "invalid_rate"),
        ("adaptive_clock_rate", {"rate": float("nan")}, "invalid_rate"),
        ("metabolism_cost_eval", {"passes_sevo": False}, "sevo"),
        ("kl_barycentre_aggregate", {"barycentre": [0.5, 0.6, -0.1]}, "invalid_barycentre"),
        ("kl_barycentre_aggregate", {"barycentre": [0.1, 0.1, 0.1]}, "invalid_barycentre"),
    ],
)
def test_bad_results_fail_closed(tool: str, payload: dict[str, Any], reason: str) -> None:
    session = Session({tool: payload})
    with pytest.raises((PolicyRefusalError, ValueError), match=reason):
        asyncio.run(diagnose(Adapter(session, Budget(), [])))
    assert session.pings == 0


def test_unexpected_tool_error_consumes_budget() -> None:
    session = Session()
    budget = Budget()
    with pytest.raises(ValueError, match="unexpected_tool_error"):
        asyncio.run(
            Adapter(session, budget, []).call("adaptive_clock_rate", {"coherence_phi": "invalid"})
        )
    assert budget.tool_attempts == 1
