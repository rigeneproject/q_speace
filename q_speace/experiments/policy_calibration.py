"""T227/T224-bis: staged synthetic calibration; never changes T224 defaults."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, TextIO

from .mcp_regulation import COST_INPUT, MCPTools, Observation, ToolError, number, write_event

VERSION = "T227-v1"
LIMIT = 8
ANSWER = Observation("answer", True, "532", "current")
ERROR = Observation("tool_error")
AMBIGUOUS = Observation("ambiguous")
EVIDENCE = Observation("evidence", True)


@dataclass(frozen=True, order=True)
class Policy:
    mapping: str
    signal: str
    threshold: int

    def __post_init__(self) -> None:
        if self.mapping not in {"legacy", "differentiated"}:
            raise ValueError("unknown mapping")
        if self.signal not in {"all_no_progress", "consecutive_errors"}:
            raise ValueError("unknown stop signal")
        if type(self.threshold) is not int or self.threshold not in {3, 5, 7, 8}:
            raise ValueError("threshold outside frozen grid")

    def telemetry(self, errors: int, ambiguous: bool) -> float:
        if self.mapping == "legacy":
            uncertainty = (min(errors / 3, 1) + int(ambiguous)) / 2
        else:
            uncertainty = min(0.95, 0.8 * min(errors / 5, 1) + 0.2 * int(ambiguous))
        return 1 - uncertainty

    def stop(self, errors: int, stalled: int) -> bool:
        return (stalled if self.signal == "all_no_progress" else errors) >= self.threshold


GRID = tuple(
    Policy(mapping, signal, threshold)
    for mapping in ("legacy", "differentiated")
    for signal in ("all_no_progress", "consecutive_errors")
    for threshold in (3, 5, 7, 8)
)


def fixtures() -> dict[str, dict[str, list[dict[str, Any]]]]:
    sets = {
        "calibration": {
            "clean": [EVIDENCE, ANSWER],
            "transient": [ERROR, ANSWER],
            "burst_recovery": [ERROR] * 4 + [EVIDENCE, ANSWER],
            "delayed": [AMBIGUOUS] * 7 + [ANSWER],
            "persistent_error": [ERROR],
            "persistent_ambiguity": [AMBIGUOUS],
        },
        "verification": {
            "clean_prelude": [EVIDENCE, EVIDENCE, ANSWER],
            "three_errors": [ERROR] * 3 + [ANSWER],
            "four_errors": [ERROR] * 4 + [ANSWER],
            "six_ambiguous": [AMBIGUOUS] * 6 + [ANSWER],
            "progress_then_delay": [EVIDENCE] + [AMBIGUOUS] * 5 + [ANSWER],
            "persistent_error": [ERROR],
            "persistent_ambiguity": [AMBIGUOUS],
        },
        "challenge": {
            "six_errors_recover": [ERROR] * 6 + [ANSWER],
            "matching_persistent_error": [ERROR],
            "seven_ambiguous": [AMBIGUOUS] * 7 + [ANSWER],
        },
    }
    return {
        partition: {name: [asdict(o) for o in sequence] for name, sequence in cases.items()}
        for partition, cases in sets.items()
    }


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def implementation_hashes() -> dict[str, str]:
    package = Path(__file__).resolve().parents[1]
    paths = (
        "experiments/policy_calibration.py",
        "experiments/mcp_regulation.py",
        "economy/mcp_server.py",
        "edd_cvt/ilf.py",
        "metabolism/cognitive_cost_model.py",
    )
    return {p: hashlib.sha256((package / p).read_bytes()).hexdigest() for p in paths}


def dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


async def run(
    name: str,
    sequence: list[dict[str, Any]],
    policy: Policy | None,
    tools: Any,
    stream: TextIO,
    apply_sleep: bool,
) -> dict[str, Any]:
    started = time.perf_counter()
    errors = stalled = steps = 0
    ambiguous = False
    reserved = planned = slept = rpc_seconds = 0.0
    rpc_calls = 0
    observation: dict[str, Any] = {}
    reason = "hard_budget"
    for step in range(LIMIT):
        prior = {"errors": errors, "no_progress": stalled, "ambiguous": ambiguous}
        if policy is not None and policy.stop(errors, stalled):
            reason = "preventive_stop"
            write_event(stream, {"event": "stop", "case": name, "prior": prior, "reason": reason})
            break
        delay = cost = 0.0
        if policy is not None:
            phi = policy.telemetry(errors, ambiguous)
            before = time.perf_counter()
            clock = await tools.call("adaptive_clock_rate", {"coherence_phi": phi})
            energy = await tools.call("metabolism_cost_eval", COST_INPUT)
            rpc_seconds += time.perf_counter() - before
            rpc_calls += 2
            rate, cost = number(clock, "rate"), number(energy, "estimated_energy_joules")
            if rate <= 0 or cost < 0 or energy.get("passes_sevo") is not True:
                raise ToolError("invalid clock/cost or refused Sevo")
            if reserved + cost > 1.0:
                reason = "energy_budget"
                break
            delay = min(0.1, 1 / rate)
            write_event(
                stream,
                {
                    "event": "primitive_results",
                    "case": name,
                    "step": step,
                    "prior": prior,
                    "coherence_phi": phi,
                    "clock": clock,
                    "cost_input": COST_INPUT,
                    "cost": energy,
                },
            )
        # Equal 8-action/160-token/8-DAT hard caps in both arms; reserve before action.
        reserved += cost
        write_event(
            stream,
            {
                "event": "reservation",
                "case": name,
                "step": step,
                "tokens": (steps + 1) * 20,
                "local_dat": steps + 1,
                "modeled_joules": reserved,
                "planned_delay": delay,
            },
        )
        planned += delay
        if apply_sleep and delay:
            before = time.perf_counter()
            await asyncio.sleep(delay)
            slept += time.perf_counter() - before
        # Only this task executor reads the next observation; the policy sees prior signals.
        observation = sequence[min(step, len(sequence) - 1)]
        steps += 1
        status = observation["status"]
        errors = errors + 1 if status == "tool_error" else 0
        ambiguous = status == "ambiguous"
        stalled = 0 if observation["progress"] else stalled + 1
        write_event(
            stream, {"event": "observation", "case": name, "step": step, "value": observation}
        )
        if status == "answer":
            reason = "answer"
            break
    correct = (
        observation.get("status") == "answer"
        and observation.get("answer") == "532"
        and observation.get("document_id") == "current"
    )
    return {
        "case": name,
        "correct": correct,
        "steps": steps,
        "tokens": steps * 20,
        "local_dat": steps,
        "modeled_joules": reserved if policy else None,
        "planned_sleep_seconds": planned,
        "actual_sleep_seconds": slept,
        "wall_seconds": time.perf_counter() - started,
        "rpc_seconds": rpc_seconds,
        "rpc_calls": rpc_calls,
        "reason": reason,
    }


def compare(baseline: list[dict[str, Any]], candidate: list[dict[str, Any]]) -> dict[str, Any]:
    base = {x["case"]: x for x in baseline}
    other = {x["case"]: x for x in candidate}
    if base.keys() != other.keys():
        raise ValueError("unpaired results")
    lost = [name for name in base if base[name]["correct"] and not other[name]["correct"]]
    saved = sum(x["tokens"] for x in baseline) - sum(x["tokens"] for x in candidate)
    return {
        "baseline_correct": sum(x["correct"] for x in baseline),
        "candidate_correct": sum(x["correct"] for x in candidate),
        "cases": len(base),
        "lost_completions": lost,
        "false_early_stops": [n for n in lost if other[n]["reason"] == "preventive_stop"],
        "baseline_tokens": sum(x["tokens"] for x in baseline),
        "candidate_tokens": sum(x["tokens"] for x in candidate),
        "saved_tokens": saved,
        "retained_on_constructed_fixture_only": not lost and saved > 0,
        "preventive_stops": sum(x["reason"] == "preventive_stop" for x in candidate),
    }


def select(baseline: list[dict[str, Any]], trials: list[dict[str, Any]]) -> Policy | None:
    eligible = [
        x for x in trials if compare(baseline, x["rows"])["retained_on_constructed_fixture_only"]
    ]
    if not eligible:
        return None
    best = min(
        eligible,
        key=lambda x: (
            sum(row["tokens"] for row in x["rows"]),
            sum(row["planned_sleep_seconds"] for row in x["rows"]),
            Policy(**x["policy"]),
        ),
    )
    return Policy(**best["policy"])


async def stage(output: Path, phase: str) -> dict[str, Any]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    hashes = implementation_hashes()
    if phase == "calibrate":
        output.mkdir(parents=True, exist_ok=False)
        data = fixtures()
        protocol = {
            "version": VERSION,
            "implementation_sha256": hashes,
            "mcp_sdk": importlib.metadata.version("mcp"),
            "fixtures": data,
            "fixtures_sha256": digest(data),
            "grid": [asdict(p) for p in GRID],
            "documents": {
                "current": "Reference laser wavelength: 532 nm.",
                "archive": "Retired: 450 nm.",
            },
            "hard_caps": {
                "steps": LIMIT,
                "synthetic_tokens": 160,
                "local_dat": 8,
                "modeled_joules": 1,
            },
        }
        dump(output / "protocol.json", protocol)
        lock = None
    else:
        protocol = json.loads((output / "protocol.json").read_text())
        lock = json.loads((output / "selection.json").read_text())
        if (
            digest(protocol) != lock["protocol_sha256"]
            or digest(lock) != (output / "selection.sha256").read_text().strip()
            or protocol["implementation_sha256"] != hashes
            or digest(protocol["fixtures"]) != protocol["fixtures_sha256"]
        ):
            raise ValueError("frozen experiment integrity mismatch")
        data = protocol["fixtures"]
    destination = output / phase
    destination.mkdir(exist_ok=False)
    manifest: dict[str, Any] = {
        "phase": phase,
        "status": "started",
        "apply_sleep": phase == "verify",
    }
    dump(destination / "manifest.json", manifest)
    try:
        with (destination / "events.jsonl").open("w", encoding="utf-8") as stream:
            async with (
                stdio_client(
                    StdioServerParameters(
                        command=sys.executable, args=["-m", "q_speace.economy.mcp_server"]
                    )
                ) as (read, write),
                ClientSession(read, write) as session,
            ):
                await asyncio.wait_for(session.initialize(), 5)
                await asyncio.wait_for(session.send_ping(), 5)
                tools = MCPTools(session, 5)

                async def evaluate(partition: str, policy: Policy | None) -> list[dict[str, Any]]:
                    rows = []
                    for name, sequence in data[partition].items():
                        write_event(
                            stream,
                            {
                                "event": "arm",
                                "partition": partition,
                                "policy": asdict(policy) if policy else None,
                                "case": name,
                            },
                        )
                        row = await run(name, sequence, policy, tools, stream, phase == "verify")
                        write_event(stream, {"event": "result", **row})
                        rows.append(row)
                    return rows

                result: dict[str, Any]
                if phase == "calibrate":
                    baseline = await evaluate("calibration", None)
                    trials = [
                        {"policy": asdict(p), "rows": await evaluate("calibration", p)}
                        for p in GRID
                    ]
                    chosen = select(baseline, trials)
                    lock = {
                        "protocol_sha256": digest(protocol),
                        "policy": asdict(chosen) if chosen else None,
                    }
                    dump(output / "selection.json", lock)
                    (output / "selection.sha256").write_text(digest(lock) + "\n")
                    result = {"baseline": baseline, "trials": trials, "selection": lock}
                else:
                    assert lock is not None
                    chosen = Policy(**lock["policy"]) if lock["policy"] else None
                    result = {"selection": lock, "partitions": {}}
                    if chosen is not None:
                        for partition in ("verification", "challenge"):
                            baseline = await evaluate(partition, None)
                            rows = await evaluate(partition, chosen)
                            result["partitions"][partition] = {
                                "baseline": baseline,
                                "candidate": rows,
                                "comparison": compare(baseline, rows),
                            }
                manifest.update(status="completed", mcp_calls=tools.calls)
        dump(destination / "summary.json", result)
        return result
    except Exception as exc:
        manifest.update(status="inconclusive_infrastructure_failure", error_type=type(exc).__name__)
        raise
    finally:
        dump(destination / "manifest.json", manifest)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["calibrate", "verify"])
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = asyncio.run(asyncio.wait_for(stage(args.output, args.phase), 180))
    print(
        json.dumps(
            {"phase": args.phase, "selection": result["selection"], "evidence": str(args.output)}
        )
    )


if __name__ == "__main__":
    main()
