"""T224-bis causal policy, selection integrity and actual SDK stage separation."""

from __future__ import annotations

import asyncio
import io
import json
from pathlib import Path
from typing import Any

import pytest

from q_speace.bcel.catalog import BCELCatalog
from q_speace.economy.mcp_server import _dispatch
from q_speace.experiments import policy_calibration as study


class Tools:
    def __init__(self, malformed: bool = False) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.malformed = malformed

    async def call(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((name, args.copy()))
        if self.malformed:
            return {"rate": float("nan")}
        return _dispatch(name, args)


def execute(
    name: str, policy: study.Policy | None, partition: str = "calibration"
) -> dict[str, Any]:
    return asyncio.run(
        study.run(name, study.fixtures()[partition][name], policy, Tools(), io.StringIO(), False)
    )


@pytest.mark.parametrize("mapping", ["legacy", "differentiated"])
def test_prior_mapping_bounds_and_causes(mapping: str) -> None:
    p = study.Policy(mapping, "consecutive_errors", 5)
    assert p.telemetry(0, False) == 1
    assert 0 <= p.telemetry(100, True) <= 1
    tools = Tools()
    asyncio.run(
        study.run(
            "burst",
            study.fixtures()["calibration"]["burst_recovery"],
            p,
            tools,
            io.StringIO(),
            False,
        )
    )
    clocks = [a["coherence_phi"] for n, a in tools.calls if n == "adaptive_clock_rate"]
    assert clocks[0] == 1 and clocks[1] == p.telemetry(1, False)
    assert len(clocks) == 6  # no future answer inspection; evidence resets errors before answer
    assert clocks[-1] == 1


def test_equal_caps_and_reservation_before_observation() -> None:
    stream = io.StringIO()
    p = study.Policy("legacy", "consecutive_errors", 8)
    baseline = execute("persistent_error", None)
    result = asyncio.run(
        study.run(
            "persistent_error",
            study.fixtures()["calibration"]["persistent_error"],
            p,
            Tools(),
            stream,
            False,
        )
    )
    assert baseline["steps"] == result["steps"] == 8
    assert baseline["tokens"] == result["tokens"] == 160
    assert baseline["local_dat"] == result["local_dat"] == 8
    events = [json.loads(x) for x in stream.getvalue().splitlines()]
    for step in range(8):
        reservation = next(
            i for i, e in enumerate(events) if e["event"] == "reservation" and e["step"] == step
        )
        observation = next(
            i for i, e in enumerate(events) if e["event"] == "observation" and e["step"] == step
        )
        assert reservation < observation


def test_errors_only_retains_ambiguity_but_fails_shared_prefix_challenge() -> None:
    p = study.Policy("differentiated", "consecutive_errors", 5)
    assert execute("delayed", p)["correct"]
    assert execute("persistent_ambiguity", p)["steps"] == 8
    assert execute("persistent_error", p)["steps"] == 5
    recovered = execute("six_errors_recover", p, "challenge")
    persistent = execute("matching_persistent_error", p, "challenge")
    assert recovered["steps"] == persistent["steps"] == 5
    assert recovered["reason"] == persistent["reason"] == "preventive_stop"
    assert not recovered["correct"]


def test_selection_requires_per_case_non_regression_and_is_deterministic() -> None:
    baseline = [
        {"case": "a", "correct": True, "tokens": 100},
        {"case": "b", "correct": False, "tokens": 100},
    ]
    swap = [
        {
            "case": "a",
            "correct": False,
            "tokens": 20,
            "reason": "preventive_stop",
            "planned_sleep_seconds": 0,
        },
        {
            "case": "b",
            "correct": True,
            "tokens": 20,
            "reason": "answer",
            "planned_sleep_seconds": 0,
        },
    ]
    bad = {
        "policy": {"mapping": "legacy", "signal": "all_no_progress", "threshold": 3},
        "rows": swap,
    }
    assert study.select(baseline, [bad]) is None
    assert study.compare(baseline, swap)["false_early_stops"] == ["a"]
    good = [dict(x, correct=x["case"] == "a") for x in swap]
    a = {
        "policy": {"mapping": "legacy", "signal": "consecutive_errors", "threshold": 5},
        "rows": good,
    }
    b = {
        "policy": {"mapping": "differentiated", "signal": "consecutive_errors", "threshold": 5},
        "rows": good,
    }
    assert study.select(baseline, [a, b]) == study.select(baseline, [b, a])
    assert BCELCatalog().is_functional("Calibrated client feedback experiment (T227)")


def test_malformed_primitive_never_executes_task() -> None:
    stream = io.StringIO()
    with pytest.raises(study.ToolError):
        asyncio.run(
            study.run(
                "bad",
                study.fixtures()["calibration"]["clean"],
                study.GRID[0],
                Tools(True),
                stream,
                False,
            )
        )
    assert "observation" not in stream.getvalue()


def test_official_sdk_frozen_stage_and_tamper_detection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("mcp")
    root = tmp_path / "study"
    calibration = asyncio.run(study.stage(root, "calibrate"))
    assert calibration["selection"]["policy"]["signal"] == "consecutive_errors"
    assert calibration["selection"]["policy"]["threshold"] == 5

    def forbidden_selection(*args: Any) -> None:
        raise AssertionError("verification must not select or retune")

    monkeypatch.setattr(study, "select", forbidden_selection)
    verification = asyncio.run(study.stage(root, "verify"))
    assert verification["partitions"]["verification"]["comparison"][
        "retained_on_constructed_fixture_only"
    ]
    assert verification["partitions"]["challenge"]["comparison"]["lost_completions"] == [
        "six_errors_recover"
    ]
    with pytest.raises(FileExistsError):
        asyncio.run(study.stage(root, "verify"))
    protocol = json.loads((root / "protocol.json").read_text())
    protocol["hard_caps"]["steps"] = 100
    (root / "protocol.json").write_text(json.dumps(protocol))
    with pytest.raises(ValueError, match="integrity"):
        asyncio.run(study.stage(root, "verify"))
