"""T224: deterministic baseline versus MCP-regulated client experiment.

Run explicitly with ``python -m q_speace.experiments.mcp_regulation --output DIR``.
Tokens, DAT and the metabolism operation are synthetic, not LLM billing/energy.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib
import importlib.metadata
import json
import math
import platform
import subprocess
import sys
import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, TextIO

POLICY_VERSION = "T224-v1"
TOKENS_PER_ACTION = 20
DAT_PER_ACTION = 1.0
COST_INPUT = {
    "num_qubits": 0,
    "num_gates": 1,
    "duration_s": 0.01,
    "delta_utility": 2,
    "delta_entropy_info": 1,
}


@dataclass(frozen=True)
class Observation:
    status: Literal["tool_error", "ambiguous", "evidence", "answer"]
    progress: bool = False
    answer: str | None = None
    document_id: str | None = None


@dataclass(frozen=True)
class Case:
    case_id: str
    documents: tuple[tuple[str, str], ...]
    expected_answer: str
    expected_document_id: str
    observations: tuple[Observation, ...]


_DOCS = (("current", "The current service port is 443."), ("archive", "The retired port was 80."))
_ANSWER = Observation("answer", True, "443", "current")
BENCHMARK = (
    Case("clean", _DOCS, "443", "current", (Observation("evidence", True), _ANSWER)),
    Case(
        "transient_failure",
        _DOCS,
        "443",
        "current",
        (Observation("tool_error"), Observation("evidence", True), _ANSWER),
    ),
    Case("persistent_failure", _DOCS, "443", "current", (Observation("tool_error"),)),
    Case(
        "delayed_resolution", _DOCS, "443", "current", (Observation("ambiguous"),) * 4 + (_ANSWER,)
    ),
)


@dataclass(frozen=True)
class Config:
    max_iterations: int = 8
    stall_limit: int = 3
    token_budget: int = 120
    dat_budget: float = 6.0
    estimated_energy_budget_joules: float = 1.0
    max_backoff_seconds: float = 0.1
    rpc_timeout_seconds: float = 5.0

    def __post_init__(self) -> None:
        for name in ("max_iterations", "stall_limit", "token_budget"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        for name in (
            "dat_budget",
            "estimated_energy_budget_joules",
            "max_backoff_seconds",
            "rpc_timeout_seconds",
        ):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if self.max_backoff_seconds > 1:
            raise ValueError("experimental backoff cap must be <= 1 second")


class ToolError(Exception):
    """A transport/tool/schema failure; no task action may follow it."""


class Tools(Protocol):
    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]: ...


class MCPTools:
    def __init__(self, session: Any, timeout: float) -> None:
        self.session = session
        self.timeout = timeout
        self.calls = 0

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        try:
            result = await asyncio.wait_for(self.session.call_tool(name, arguments), self.timeout)
            if result.isError or len(result.content) != 1 or result.content[0].type != "text":
                raise ToolError(f"{name}: error or unexpected content")
            data = json.loads(result.content[0].text)
            if not isinstance(data, dict):
                raise ToolError(f"{name}: expected a JSON object")
            return data
        except Exception as exc:
            raise ToolError(f"{name}: {type(exc).__name__}: {exc}") from exc


def number(data: dict[str, Any], field: str) -> float:
    value = data.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ToolError(f"Invalid numeric field: {field}")
    return float(value)


def clock_input(consecutive_errors: int, ambiguous: bool) -> dict[str, float]:
    uncertainty = (min(consecutive_errors / 3, 1) + int(ambiguous)) / 2
    return {"coherence_phi": 1 - uncertainty}


def log_value(value: Any) -> Any:
    """Preserve malformed numeric evidence without producing invalid JSONL."""
    if isinstance(value, float) and not math.isfinite(value):
        return {"invalid_float": repr(value)}
    if isinstance(value, dict):
        return {key: log_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [log_value(item) for item in value]
    return value


def write_event(stream: TextIO, record: dict[str, Any]) -> None:
    stream.write(json.dumps(log_value({"schema_version": 1, **record}), allow_nan=False) + "\n")
    stream.flush()


async def run_case(
    case: Case,
    arm: Literal["baseline", "regulated"],
    config: Config,
    stream: TextIO,
    tools: Tools | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> dict[str, Any]:
    """Policy sees only prior observations; ground truth is scored afterwards."""
    if arm == "regulated" and tools is None:
        raise ValueError("regulated arm requires tools")
    started = time.perf_counter()
    run_id = f"{case.case_id}:{arm}"
    iterations = tokens = reserved_tokens = errors = stalled = 0
    dat = energy = 0.0
    sleep_total = 0.0
    ambiguous = False
    observation: Observation | None = None
    reason = "max_iterations"
    token_id = ""
    trace: dict[str, Any] = {}
    try:
        if tools is not None and arm == "regulated":
            mint = {
                "amount": config.dat_budget,
                "bound_to": run_id,
                "decay_half_life": 1e9,
                "mint_time": 0,
            }
            trace = {"mint_input": mint}
            trace["mint_output"] = await tools.call("dat_mint", mint)
            token_id = trace["mint_output"].get("token_id", "")
            if (
                not isinstance(token_id, str)
                or not token_id
                or number(trace["mint_output"], "amount") != config.dat_budget
            ):
                raise ToolError("Invalid mint receipt")
            write_event(
                stream,
                {"event": "mint", "run_id": run_id, "case_id": case.case_id, "arm": arm, **trace},
            )
        for step in range(config.max_iterations):
            trace = {
                "prior_errors": errors,
                "prior_ambiguous": ambiguous,
                "prior_no_progress": stalled,
            }
            if arm == "regulated":
                trace["clock_input"] = clock_input(errors, ambiguous)
            delay = 0.0
            proposed_energy = 0.0
            if tools is not None and arm == "regulated":
                trace["clock_output"] = await tools.call(
                    "adaptive_clock_rate", trace["clock_input"]
                )
                trace["cost_input"] = dict(COST_INPUT)
                trace["cost_output"] = await tools.call("metabolism_cost_eval", trace["cost_input"])
                rate = number(trace["clock_output"], "rate")
                proposed_energy = number(trace["cost_output"], "estimated_energy_joules")
                if (
                    rate <= 0
                    or proposed_energy < 0
                    or not isinstance(trace["cost_output"].get("passes_sevo"), bool)
                ):
                    raise ToolError("Invalid clock or cost result")
                delay = min(config.max_backoff_seconds, 1 / rate)
                if stalled >= config.stall_limit:
                    reason = "stalled"
                elif reserved_tokens + TOKENS_PER_ACTION > config.token_budget:
                    reason = "token_budget"
                elif dat + DAT_PER_ACTION > config.dat_budget:
                    reason = "dat_budget"
                elif energy + proposed_energy > config.estimated_energy_budget_joules:
                    reason = "estimated_energy_budget"
                elif not trace["cost_output"]["passes_sevo"]:
                    reason = "sevo"
                else:
                    reason = "allow"
                if reason != "allow":
                    write_event(
                        stream,
                        {
                            "event": "stop",
                            "run_id": run_id,
                            "case_id": case.case_id,
                            "arm": arm,
                            "step": step,
                            "reason": reason,
                            "proposed_tokens": TOKENS_PER_ACTION,
                            "proposed_dat": DAT_PER_ACTION,
                            "planned_sleep_seconds": delay,
                            **trace,
                        },
                    )
                    break
                # Reserve conservatively before the stateful request; never retry it.
                reserved_tokens += TOKENS_PER_ACTION
                dat += DAT_PER_ACTION
                energy += proposed_energy
                spend = {"token_id": token_id, "amount": DAT_PER_ACTION, "target": run_id, "t": 0}
                trace["spend_input"] = spend
                # Persist the intent before the RPC, including an uncertain reservation.
                write_event(
                    stream,
                    {
                        "event": "reservation",
                        "run_id": run_id,
                        "case_id": case.case_id,
                        "arm": arm,
                        "step": step,
                        "reserved_tokens": reserved_tokens,
                        "reserved_dat": dat,
                        "reserved_estimated_joules": energy,
                        **trace,
                    },
                )
                receipt = await tools.call("dat_spend", spend)
                trace["spend_output"] = receipt
                if (
                    number(receipt, "spent") != DAT_PER_ACTION
                    or receipt.get("target") != run_id
                    or not math.isclose(
                        number(receipt, "remaining_amount"), config.dat_budget - dat, abs_tol=1e-9
                    )
                ):
                    raise ToolError("Invalid spend receipt")
                before_sleep = time.perf_counter()
                await sleep(delay)
                actual_sleep = time.perf_counter() - before_sleep
                sleep_total += actual_sleep
            else:
                reserved_tokens += TOKENS_PER_ACTION
                dat += DAT_PER_ACTION
                actual_sleep = 0.0
            # This scripted task is the same in both arms. It never consults labels.
            observation = case.observations[min(step, len(case.observations) - 1)]
            iterations += 1
            tokens += TOKENS_PER_ACTION
            errors = errors + 1 if observation.status == "tool_error" else 0
            ambiguous = observation.status == "ambiguous"
            stalled = 0 if observation.progress else stalled + 1
            write_event(
                stream,
                {
                    "event": "step",
                    "run_id": run_id,
                    "case_id": case.case_id,
                    "arm": arm,
                    "step": step,
                    "decision": "allow",
                    "observation": asdict(observation),
                    "iterations": iterations,
                    "executed_synthetic_tokens": tokens,
                    "reserved_tokens": reserved_tokens,
                    "reserved_dat": dat,
                    "estimated_joules": energy if arm == "regulated" else None,
                    "planned_sleep_seconds": delay,
                    "applied_sleep_seconds": actual_sleep,
                    "elapsed_seconds": time.perf_counter() - started,
                    **trace,
                },
            )
            if observation.status == "answer":
                reason = "answer"
                break
        else:
            reason = "max_iterations"
    except ToolError as exc:
        reason = "mcp_failure"
        write_event(
            stream,
            {
                "event": "failure",
                "run_id": run_id,
                "case_id": case.case_id,
                "arm": arm,
                "reason": reason,
                "error": str(exc),
                "reserved_tokens": reserved_tokens,
                "reserved_dat": dat,
                **trace,
            },
        )
    correct = (
        observation is not None
        and observation.status == "answer"
        and observation.answer == case.expected_answer
        and observation.document_id == case.expected_document_id
    )
    result = {
        "event": "case_result",
        "run_id": run_id,
        "case_id": case.case_id,
        "arm": arm,
        "iterations": iterations,
        "executed_synthetic_tokens": tokens,
        "reserved_tokens": reserved_tokens,
        "simulated_dat": dat,
        "estimated_joules": energy if arm == "regulated" else None,
        "sleep_seconds": sleep_total,
        "wall_seconds": time.perf_counter() - started,
        "stop_reason": reason,
        "correct": correct,
        "preventive_stop": reason
        in {"stalled", "token_budget", "dat_budget", "estimated_energy_budget", "sevo"},
    }
    write_event(stream, result)
    return result


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    arms: dict[str, Any] = {}
    for arm in ("baseline", "regulated"):
        rows = [r for r in results if r["arm"] == arm]
        arms[arm] = {
            "cases": len(rows),
            "correct": sum(r["correct"] for r in rows),
            "iterations": sum(r["iterations"] for r in rows),
            "synthetic_tokens": sum(r["executed_synthetic_tokens"] for r in rows),
            "simulated_dat": sum(r["simulated_dat"] for r in rows),
            "wall_seconds": sum(r["wall_seconds"] for r in rows),
            "completion_rate": sum(r["correct"] for r in rows) / len(rows) if rows else 0,
            "preventive_stop_rate": (
                sum(r["preventive_stop"] for r in rows) / len(rows) if rows else 0
            ),
        }
    baseline, regulated = arms["baseline"], arms["regulated"]
    failed = any(r["stop_reason"] == "mcp_failure" for r in results)
    if failed or baseline["cases"] != regulated["cases"]:
        verdict = "inconclusive"
    elif regulated["correct"] < baseline["correct"]:
        verdict = "rejected"
    elif regulated["synthetic_tokens"] < baseline["synthetic_tokens"]:
        verdict = "retained_on_fixture_only"
    else:
        verdict = "inconclusive"
    pairs = []
    for case_id in dict.fromkeys(r["case_id"] for r in results):
        paired = {r["arm"]: r for r in results if r["case_id"] == case_id}
        if "baseline" in paired and "regulated" in paired:
            pairs.append(
                {
                    "case_id": case_id,
                    "baseline": paired["baseline"],
                    "regulated": paired["regulated"],
                    "token_delta": paired["regulated"]["executed_synthetic_tokens"]
                    - paired["baseline"]["executed_synthetic_tokens"],
                    "wall_seconds_delta": paired["regulated"]["wall_seconds"]
                    - paired["baseline"]["wall_seconds"],
                }
            )
    return {
        "schema_version": 1,
        "policy_version": POLICY_VERSION,
        "arms": arms,
        "pairs": pairs,
        "verdict": verdict,
        "false_preventive_stops": sum(
            pair["baseline"]["correct"] and pair["regulated"]["preventive_stop"] for pair in pairs
        ),
        "preventive_stops_baseline_incomplete": sum(
            not pair["baseline"]["correct"] and pair["regulated"]["preventive_stop"]
            for pair in pairs
        ),
        "infrastructure_failure": failed,
        "limitation": "Deterministic synthetic fixture; no LLM, physical-energy or generality evidence.",
    }


def dump(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def git_metadata() -> dict[str, Any]:
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], stderr=subprocess.DEVNULL, text=True
        )
        return {"head": head, "dirty": bool(status)}
    except (OSError, subprocess.CalledProcessError):
        return {"head": None, "dirty": None}


async def experiment(output: Path, config: Config) -> dict[str, Any]:
    sdk = importlib.import_module("mcp")
    transport = importlib.import_module("mcp.client.stdio")
    output.mkdir(parents=True, exist_ok=False)
    benchmark = [asdict(case) for case in BENCHMARK]
    canonical = json.dumps(benchmark, sort_keys=True).encode()
    manifest = {
        "schema_version": 1,
        "policy_version": POLICY_VERSION,
        "config": asdict(config),
        "benchmark": benchmark,
        "benchmark_sha256": hashlib.sha256(canonical).hexdigest(),
        "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "git": git_metadata(),
        "python": platform.python_version(),
        "mcp_sdk": importlib.metadata.version("mcp"),
        "server_startup_seconds": None,
        "status": "started",
    }
    dump(output / "manifest.json", manifest)
    results: list[dict[str, Any]] = []
    startup = time.perf_counter()
    try:
        with (output / "events.jsonl").open("w", encoding="utf-8") as stream:
            params = sdk.StdioServerParameters(
                command=sys.executable, args=["-m", "q_speace.economy.mcp_server"]
            )
            async with (
                transport.stdio_client(params) as (reader, writer),
                sdk.ClientSession(reader, writer) as session,
            ):
                await asyncio.wait_for(session.initialize(), config.rpc_timeout_seconds)
                manifest["server_startup_seconds"] = time.perf_counter() - startup
                tools = MCPTools(session, config.rpc_timeout_seconds)
                for index, case in enumerate(BENCHMARK):
                    order = (
                        ("baseline", "regulated") if index % 2 == 0 else ("regulated", "baseline")
                    )
                    for arm in order:
                        selected_arm: Literal["baseline", "regulated"] = (
                            "baseline" if arm == "baseline" else "regulated"
                        )
                        result = await run_case(
                            case,
                            selected_arm,
                            config,
                            stream,
                            tools if arm == "regulated" else None,
                        )
                        results.append(result)
                        if result["stop_reason"] == "mcp_failure":
                            raise ToolError("Experiment aborted after MCP failure")
                manifest["mcp_calls"] = tools.calls
    except Exception as exc:
        manifest["status"] = "infrastructure_failure"
        manifest["error"] = str(exc)
        summary = summarize(results)
        summary["verdict"] = "inconclusive"
        summary["infrastructure_failure"] = True
        dump(output / "summary.json", summary)
        dump(output / "manifest.json", manifest)
        raise
    summary = summarize(results)
    manifest["status"] = "completed"
    dump(output / "manifest.json", manifest)
    dump(output / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-iterations", type=int, default=8)
    parser.add_argument("--stall-limit", type=int, default=3)
    parser.add_argument("--token-budget", type=int, default=120)
    parser.add_argument("--dat-budget", type=float, default=6)
    parser.add_argument("--estimated-energy-budget-joules", type=float, default=1)
    parser.add_argument("--max-backoff-seconds", type=float, default=0.1)
    parser.add_argument("--rpc-timeout-seconds", type=float, default=5)
    args = parser.parse_args()
    config_args = vars(args).copy()
    output = config_args.pop("output")
    try:
        summary = asyncio.run(experiment(output, Config(**config_args)))
    except Exception as exc:
        print(f"Experiment failed: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "output": str(output.resolve()),
                "verdict": summary["verdict"],
                "arms": summary["arms"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
