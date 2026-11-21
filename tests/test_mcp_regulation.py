"""T224: causal client regulation, independent bounds, and real MCP comparison."""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from q_speace.economy.mcp_server import _dispatch
from q_speace.experiments.mcp_regulation import (
    BENCHMARK,
    Config,
    MCPTools,
    Observation,
    ToolError,
    clock_input,
    experiment,
    run_case,
    summarize,
)


class NativeTools:
    def __init__(self, fail_at: str = "", malformed_at: str = "") -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.fail_at = fail_at
        self.malformed_at = malformed_at

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((name, arguments.copy()))
        if name == self.fail_at:
            raise ToolError("injected transport failure")
        if name == self.malformed_at:
            return {"rate": float("nan")}
        return _dispatch(name, arguments)


async def no_sleep(seconds: float) -> None:
    pass


@pytest.mark.parametrize(
    "index,steps,correct", [(0, 2, True), (1, 3, True), (2, 8, False), (3, 5, True)]
)
def test_baseline_ignores_mcp_and_gates(index: int, steps: int, correct: bool) -> None:
    tools = NativeTools(fail_at="adaptive_clock_rate")
    result = asyncio.run(
        run_case(
            BENCHMARK[index],
            "baseline",
            Config(token_budget=1, dat_budget=0.1, stall_limit=1),
            io.StringIO(),
            tools,
            no_sleep,
        )
    )
    assert tools.calls == []
    assert result["iterations"] == steps
    assert result["correct"] is correct
    assert result["executed_synthetic_tokens"] == 20 * steps


def test_stalled_loop_and_causal_backoff() -> None:
    tools = NativeTools()
    stream = io.StringIO()
    delays = []

    async def sleep(seconds: float) -> None:
        delays.append(seconds)

    result = asyncio.run(run_case(BENCHMARK[2], "regulated", Config(), stream, tools, sleep))
    assert result["iterations"] == 3
    assert result["stop_reason"] == "stalled"
    assert len(delays) == 3
    assert 0 < delays[0] < delays[1] < delays[2] <= 0.1
    clock_calls = [args for name, args in tools.calls if name == "adaptive_clock_rate"]
    assert clock_calls == [clock_input(i, False) for i in range(4)]
    assert sum(name == "dat_spend" for name, _ in tools.calls) == 3
    events = [json.loads(line) for line in stream.getvalue().splitlines()]
    first_reservation = next(i for i, row in enumerate(events) if row["event"] == "reservation")
    first_step = next(i for i, row in enumerate(events) if row["event"] == "step")
    assert first_reservation < first_step


@pytest.mark.parametrize(
    "config,expected_steps,reason",
    [
        (Config(token_budget=40, stall_limit=8), 2, "token_budget"),
        (Config(dat_budget=2, stall_limit=8), 2, "dat_budget"),
        (
            Config(estimated_energy_budget_joules=0.0005, stall_limit=8),
            1,
            "estimated_energy_budget",
        ),
        (Config(token_budget=1), 0, "token_budget"),
        (Config(dat_budget=0.5), 0, "dat_budget"),
    ],
)
def test_hard_bounds_before_execution(config: Config, expected_steps: int, reason: str) -> None:
    tools = NativeTools()
    result = asyncio.run(
        run_case(BENCHMARK[2], "regulated", config, io.StringIO(), tools, no_sleep)
    )
    assert result["iterations"] == expected_steps
    assert result["stop_reason"] == reason
    assert result["reserved_tokens"] <= config.token_budget
    assert result["simulated_dat"] <= config.dat_budget
    assert result["estimated_joules"] <= config.estimated_energy_budget_joules
    assert sum(name == "dat_spend" for name, _ in tools.calls) == expected_steps


def test_success_at_exact_budget_and_ground_truth_evaluation() -> None:
    result = asyncio.run(
        run_case(
            BENCHMARK[0],
            "regulated",
            Config(token_budget=40, dat_budget=2),
            io.StringIO(),
            NativeTools(),
            no_sleep,
        )
    )
    assert result["correct"] is True
    wrong = replace(
        BENCHMARK[0],
        case_id="wrong-answer",
        observations=(Observation("answer", True, "80", "archive"),),
    )
    rejected = asyncio.run(run_case(wrong, "baseline", Config(), io.StringIO()))
    assert rejected["stop_reason"] == "answer"
    assert rejected["correct"] is False


@pytest.mark.parametrize(
    "fail_at", ["dat_mint", "adaptive_clock_rate", "metabolism_cost_eval", "dat_spend"]
)
def test_rpc_failure_stops_without_work(fail_at: str) -> None:
    result = asyncio.run(
        run_case(
            BENCHMARK[0],
            "regulated",
            Config(),
            io.StringIO(),
            NativeTools(fail_at=fail_at),
            no_sleep,
        )
    )
    assert result["iterations"] == 0
    assert result["stop_reason"] == "mcp_failure"
    assert result["correct"] is False
    assert result["reserved_tokens"] == (20 if fail_at == "dat_spend" else 0)
    assert summarize([result])["verdict"] == "inconclusive"


def test_invalid_receipt_is_fail_closed() -> None:
    result = asyncio.run(
        run_case(
            BENCHMARK[0],
            "regulated",
            Config(),
            io.StringIO(),
            NativeTools(malformed_at="dat_spend"),
            no_sleep,
        )
    )
    assert result["iterations"] == 0
    assert result["reserved_tokens"] == 20
    assert result["simulated_dat"] == 1
    assert result["stop_reason"] == "mcp_failure"


def test_timeout_becomes_tool_failure() -> None:
    class HangingSession:
        async def call_tool(self, name: str, arguments: dict[str, Any]) -> None:
            await asyncio.sleep(10)

    async def check() -> None:
        with pytest.raises(ToolError, match="TimeoutError"):
            await MCPTools(HangingSession(), 0.01).call("adaptive_clock_rate", {})

    asyncio.run(check())


def test_no_tuning_away_false_stops() -> None:
    results = []
    for case in BENCHMARK:
        for arm in ("baseline", "regulated"):
            result = asyncio.run(
                run_case(
                    case,
                    "baseline" if arm == "baseline" else "regulated",
                    Config(),
                    io.StringIO(),
                    NativeTools() if arm == "regulated" else None,
                    no_sleep,
                )
            )
            results.append(result)
    summary = summarize(results)
    assert summary["arms"]["baseline"]["correct"] == 3
    assert summary["arms"]["regulated"]["correct"] == 2
    assert summary["arms"]["baseline"]["synthetic_tokens"] == 360
    assert summary["arms"]["regulated"]["synthetic_tokens"] == 220
    assert summary["verdict"] == "rejected"
    assert summary["false_preventive_stops"] == 1
    assert summary["preventive_stops_baseline_incomplete"] == 1
    assert summary["pairs"][-1]["regulated"]["stop_reason"] == "stalled"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_iterations": 0},
        {"token_budget": True},
        {"dat_budget": float("nan")},
        {"max_backoff_seconds": 2},
        {"rpc_timeout_seconds": -1},
    ],
)
def test_invalid_configuration(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        Config(**kwargs)


def test_official_sdk_experiment_and_evidence(tmp_path: Path) -> None:
    pytest.importorskip("mcp")
    output = tmp_path / "experiment"
    summary = asyncio.run(experiment(output, Config(max_backoff_seconds=0.001)))
    assert summary["verdict"] == "rejected"
    assert summary["infrastructure_failure"] is False
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["status"] == "completed"
    assert manifest["config"]["max_backoff_seconds"] == 0.001
    canonical = json.dumps(manifest["benchmark"], sort_keys=True).encode()
    assert manifest["benchmark_sha256"] == hashlib.sha256(canonical).hexdigest()
    events = [json.loads(line) for line in (output / "events.jsonl").read_text().splitlines()]
    assert sum(row["event"] == "case_result" for row in events) == 8
    assert all("clock_output" not in row for row in events if row["arm"] == "baseline")
    with pytest.raises(FileExistsError):
        asyncio.run(experiment(output, Config()))


def test_regulated_iteration_limit_is_reported() -> None:
    result = asyncio.run(
        run_case(
            BENCHMARK[2],
            "regulated",
            Config(max_iterations=2, stall_limit=3),
            io.StringIO(),
            NativeTools(),
            no_sleep,
        )
    )
    assert result["iterations"] == 2
    assert result["stop_reason"] == "max_iterations"


def test_sevo_refusal_precedes_spend() -> None:
    class RefusingTools(NativeTools):
        async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
            result = await super().call(name, arguments)
            if name == "metabolism_cost_eval":
                result["passes_sevo"] = False
            return result

    tools = RefusingTools()
    result = asyncio.run(
        run_case(BENCHMARK[0], "regulated", Config(), io.StringIO(), tools, no_sleep)
    )
    assert result["stop_reason"] == "sevo"
    assert result["iterations"] == 0
    assert not any(name == "dat_spend" for name, _ in tools.calls)


def test_nonfinite_receipt_keeps_failure_log_valid_json() -> None:
    stream = io.StringIO()
    result = asyncio.run(
        run_case(
            BENCHMARK[0],
            "regulated",
            Config(),
            stream,
            NativeTools(malformed_at="dat_spend"),
            no_sleep,
        )
    )
    events = [json.loads(line) for line in stream.getvalue().splitlines()]
    failed = next(row for row in events if row["event"] == "failure")
    assert failed["spend_output"]["rate"] == {"invalid_float": "nan"}
    assert result["stop_reason"] == "mcp_failure"

