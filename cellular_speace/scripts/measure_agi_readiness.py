#!/usr/bin/env python3
"""Measure SPEACE AGI readiness and persist a JSON report.

Usage:
    python scripts/measure_agi_readiness.py [--iteration N] [--compare]

The script collects observable state from SPEACE data files, computes the
AGI readiness score, and writes a timestamped report under
reports/agi_readiness/.  With --compare it also prints the delta versus the
previous report.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure the project root is on sys.path when running as a script.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from speace_core.cellular_brain.agi_readiness.agi_readiness_score import (
    AGIReadinessReport,
    AGIReadinessScore,
    load_last_report,
)

DATA_ROOT = PROJECT_ROOT / "data"
REPORTS_ROOT = PROJECT_ROOT / "reports" / "agi_readiness"


def _load_jsonl_last(path: Path) -> Optional[Dict[str, Any]]:
    """Return the last valid JSON object in a JSONL file."""
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    except OSError:
        pass
    return None


def _count_jsonl(path: Path) -> int:
    """Count valid JSON lines in a file."""
    if not path.exists():
        return 0
    count = 0
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    json.loads(line)
                    count += 1
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return count


def _load_json(path: Path, default: Optional[Any] = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _unique_values_jsonl(path: Path, key: str) -> int:
    """Count unique values for ``key`` across valid JSONL entries."""
    if not path.exists():
        return 0
    seen: set = set()
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    val = obj.get(key)
                    if val is not None:
                        seen.add(str(val))
                except (json.JSONDecodeError, AttributeError):
                    continue
    except OSError:
        pass
    return len(seen)


def _run_pytest(target: str = "") -> Dict[str, int]:
    """Run pytest in quiet mode and parse pass/fail counts.

    Args:
        target: Optional test path or keyword to limit scope.
    """
    cmd = [sys.executable, "-m", "pytest", "-q", "--no-header"]
    if target:
        cmd.append(target)
    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return {"passed": 0, "failed": 0, "skipped": 0}

    output = result.stdout + result.stderr
    passed = failed = skipped = 0
    import re
    match = re.search(r"(\d+) passed", output)
    if match:
        passed = int(match.group(1))
    match = re.search(r"(\d+) failed", output)
    if match:
        failed = int(match.group(1))
    match = re.search(r"(\d+) skipped", output)
    if match:
        skipped = int(match.group(1))

    return {"passed": passed, "failed": failed, "skipped": skipped}


def _run_quick_tests() -> Dict[str, int]:
    """Run a targeted subset of fast tests for the generalization dimension."""
    targets = [
        "tests/agi_readiness/",
        "tests/world_model/test_causal_world_model.py",
    ]
    total = {"passed": 0, "failed": 0, "skipped": 0}
    for target in targets:
        result = _run_pytest(target)
        total["passed"] += result["passed"]
        total["failed"] += result["failed"]
        total["skipped"] += result["skipped"]
    return total


def collect_runtime_state() -> Dict[str, Any]:
    """Collect runtime/tick/coherence state from available data files."""
    # Prefer organism_observer/topology_history.jsonl; fallback to morphological_memory.
    snap_path = DATA_ROOT / "organism_observer" / "topology_history.jsonl"
    fallback = DATA_ROOT / "morphological_memory" / "snapshots.jsonl"
    state: Dict[str, Any] = {"runtime_hours": 0.0, "tick_count": 0, "coherence_phi": 0.0, "anomaly_count": 0}

    for path in (snap_path, fallback):
        last = _load_jsonl_last(path)
        if last:
            state["tick_count"] = int(last.get("tick", last.get("tick_count", 0)) or 0)
            state["coherence_phi"] = float(last.get("coherence_phi", last.get("phi", 0.0)) or 0.0)
            break

    # Runtime hours are hard to estimate from snapshots alone; use activations log.
    activations_path = DATA_ROOT / "sandbox" / "runtime_mode_activations.jsonl"
    count = _count_jsonl(activations_path)
    # Heuristic: each activation ~ 1 minute of runtime.
    state["runtime_hours"] = count / 60.0

    # Anomaly count from immune system logs if present.
    immune_path = DATA_ROOT / "immune" / "anomaly_events.jsonl"
    state["anomaly_count"] = _count_jsonl(immune_path)

    return state


logger = logging.getLogger(__name__)


def collect_learning_state() -> Dict[str, Any]:
    """Collect prediction-error samples from dynamics/world-model logs.

    Parses prediction_error values from JSONL, then computes mean, variance,
    and trend (improving vs degrading) for the AGI readiness evaluator.
    """
    errors: List[float] = []
    # Look for a file that may contain prediction errors.
    candidates = [
        DATA_ROOT / "dynamics" / "prediction_errors.jsonl",
        DATA_ROOT / "embodiment" / "causal_world_model" / "prediction_errors.jsonl",
        DATA_ROOT / "world_model" / "prediction_errors.jsonl",
        DATA_ROOT / "agi_runtime" / "prediction_errors.jsonl",
    ]
    found_path = None
    for path in candidates:
        logger.debug("Checking prediction error path: %s (exists=%s)", path, path.exists())
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            err = obj.get("prediction_error", obj.get("error"))
                            if isinstance(err, (int, float)):
                                errors.append(float(err))
                        except (json.JSONDecodeError, TypeError):
                            continue
            except OSError:
                logger.warning("Failed to read %s", path)
                continue
            if errors:
                found_path = str(path)
                logger.info("Loaded %d prediction errors from %s", len(errors), found_path)
                break

    n = len(errors)
    if n > 0:
        mean_err = sum(errors) / n
        variance = sum((e - mean_err) ** 2 for e in errors) / n if n > 1 else 0.0
        if n >= 2:
            # Simple linear trend via slope over index
            xs = list(range(n))
            x_mean = (n - 1) / 2.0
            num = sum((x - x_mean) * (e - mean_err) for x, e in zip(xs, errors))
            den = sum((x - x_mean) ** 2 for x in xs)
            slope = num / den if den != 0 else 0.0
        else:
            slope = 0.0
        # Negative slope = improving (error decreasing)
        trend = slope
        improvement_signal = max(0.0, min(1.0, -trend * 10.0))
    else:
        mean_err = 0.0
        variance = 0.0
        trend = 0.0
        improvement_signal = 0.0

    return {
        "prediction_errors": errors,
        "sample_count": n,
        "mean_prediction_error": round(mean_err, 6),
        "variance": round(variance, 6),
        "trend_slope": round(trend, 8),
        "improvement_signal": round(improvement_signal, 4),
    }


def collect_causal_state() -> Dict[str, Any]:
    """Collect causal world-model statistics from all known locations."""
    obs_paths = [
        DATA_ROOT / "embodiment" / "causal_world_model" / "observations.jsonl",
        DATA_ROOT / "agi_runtime" / "causal_world_model" / "observations.jsonl",
    ]

    count = 0
    unique_actions = 0
    total_conf = 0.0
    conf_count = 0

    for obs_path in obs_paths:
        count += _count_jsonl(obs_path)
        unique_actions += _unique_values_jsonl(obs_path, "action_name")
        if obs_path.exists():
            try:
                with obs_path.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            conf = obj.get("confidence")
                            if isinstance(conf, (int, float)):
                                total_conf += float(conf)
                                conf_count += 1
                        except (json.JSONDecodeError, TypeError):
                            continue
            except OSError:
                continue

    accuracy = total_conf / max(conf_count, 1)
    return {
        "observation_count": count,
        "unique_actions": unique_actions,
        "prediction_accuracy": round(accuracy, 4),
    }


def collect_metacognition_state() -> Dict[str, Any]:
    """Collect metacognition / limitation detection statistics."""
    signals_path = DATA_ROOT / "self_improvement" / "limitation_signals.jsonl"
    diagnoses_path = DATA_ROOT / "self_improvement" / "diagnoses.jsonl"
    signals = _count_jsonl(signals_path)
    diagnoses = _count_jsonl(diagnoses_path)

    # Accuracy proxy: ratio of accepted proposals to total proposals.
    proposals_path = DATA_ROOT / "self_improvement" / "proposals.jsonl"
    total = _count_jsonl(proposals_path)
    accepted = 0
    if proposals_path.exists():
        try:
            with proposals_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if obj.get("status") == "accepted":
                            accepted += 1
                    except (json.JSONDecodeError, TypeError):
                        continue
        except OSError:
            pass
    accuracy = accepted / max(total, 1.0)

    return {
        "limitation_signals": signals,
        "diagnoses": diagnoses,
        "detection_accuracy": round(accuracy, 4),
    }


def _recent_accepted(proposals_path: Path, limit: int) -> List[int]:
    """Return the last `limit` accepted counts (1 per accepted line)."""
    results: List[int] = []
    if not proposals_path.exists():
        return results
    try:
        with proposals_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if obj.get("status") == "accepted":
                        results.append(1)
                except (json.JSONDecodeError, TypeError):
                    continue
    except OSError:
        pass
    return results[-limit:] if len(results) > limit else results


def collect_self_improvement_state() -> Dict[str, Any]:
    """Collect self-improvement proposal and patch statistics."""
    proposals_path = DATA_ROOT / "self_improvement" / "proposals.jsonl"
    total = _count_jsonl(proposals_path)
    accepted = 0
    executed = 0
    successful = 0
    if proposals_path.exists():
        try:
            with proposals_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        status = obj.get("status")
                        if status == "accepted":
                            accepted += 1
                        if status in ("executed", "applied", "accepted"):
                            executed += 1
                        if obj.get("outcome") in ("success", "successful"):
                            successful += 1
                    except (json.JSONDecodeError, TypeError):
                        continue
        except OSError:
            pass

    recent_total = min(total, 1000)
    recent_accepted = len(_recent_accepted(proposals_path, recent_total))

    return {
        "proposals_total": total,
        "proposals_accepted": accepted,
        "recent_total": recent_total,
        "recent_accepted": recent_accepted,
        "patches_executed": executed,
        "patches_successful": successful,
    }


def collect_language_state() -> Dict[str, Any]:
    """Collect language / thought grounding statistics."""
    grounding_path = DATA_ROOT / "language" / "symbolic_groundings.json"
    grounding_data = _load_json(grounding_path, {})
    groundings = len(grounding_data.get("assembly_to_label", {}))

    coherence_vals: List[float] = []
    utterances = 0
    narrative_path = DATA_ROOT / "experience" / "narrative" / "events.jsonl"
    if narrative_path.exists():
        try:
            with narrative_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if obj.get("type") == "spontaneous_utterance":
                            utterances += 1
                            c = obj.get("coherence")
                            if isinstance(c, (int, float)):
                                coherence_vals.append(float(c))
                    except (json.JSONDecodeError, TypeError):
                        continue
        except OSError:
            pass

    coherence = sum(coherence_vals) / max(len(coherence_vals), 1)

    return {
        "grounding_count": groundings,
        "dialogue_coherence": coherence,
        "spontaneous_utterances": utterances,
    }


def _load_jsonl_last_with_sensors(path: Path) -> Optional[Dict[str, Any]]:
    """Return the most recent JSON object whose 'sensors' field is a list of dicts.

    Scans from the end of the file so that lines written by
    ``scripts/log_embodiment_state.py`` are preferred.
    """
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                sensors = obj.get("sensors")
                if isinstance(sensors, list):
                    if sensors and isinstance(sensors[0], dict):
                        return obj
            except json.JSONDecodeError:
                continue
    except OSError:
        pass
    return None


def collect_embodiment_state() -> Dict[str, Any]:
    """Collect embodiment sensor / action statistics from all sources."""
    env_paths = [
        DATA_ROOT / "embodiment" / "environment_state.jsonl",
        DATA_ROOT / "agi_runtime" / "environment_state.jsonl",
    ]
    sensors = 0
    for env_path in env_paths:
        if env_path.exists():
            last = _load_jsonl_last_with_sensors(env_path) or _load_jsonl_last(env_path)
            if last and isinstance(last.get("sensors"), (list, dict)):
                sensors = max(sensors, len(last["sensors"]))
            elif last and isinstance(last.get("state"), dict):
                sensors = max(sensors, len(last["state"]))

    audit_paths = [
        DATA_ROOT / "embodiment" / "embodied_action_actuator" / "embodied_action_audit.jsonl",
        DATA_ROOT / "agi_runtime" / "embodied_action_actuator" / "embodied_action_audit.jsonl",
    ]
    actions = 0
    successful = 0
    for audit_path in audit_paths:
        actions += _count_jsonl(audit_path)
        if audit_path.exists():
            try:
                with audit_path.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                            if obj.get("outcome") in ("success", "SUCCESS"):
                                successful += 1
                        except (json.JSONDecodeError, TypeError):
                            continue
            except OSError:
                continue

    return {
        "sensor_count": sensors,
        "action_count": actions,
        "successful_actions": successful,
    }


def build_inputs(test_state: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """Aggregate all inputs for the AGI readiness evaluator."""
    return {
        "runtime_state": collect_runtime_state(),
        "learning_state": collect_learning_state(),
        "causal_state": collect_causal_state(),
        "test_state": test_state or _run_pytest(),
        "metacognition_state": collect_metacognition_state(),
        "self_improvement_state": collect_self_improvement_state(),
        "language_state": collect_language_state(),
        "embodiment_state": collect_embodiment_state(),
    }


def print_report(report: AGIReadinessReport, previous: Optional[AGIReadinessReport] = None) -> None:
    logger.info("SPEACE AGI Readiness Report - iteration %s", report.iteration)
    logger.info("Timestamp: %s", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(report.timestamp)))
    logger.info(
        "Aggregate score: %.4f  (agi_like=%s, robust=%s)",
        report.aggregate_score,
        report.agi_like_threshold,
        report.agi_robust_threshold,
    )
    logger.info("Status: %s", report.summary)
    logger.info("Dimensions:")
    for d in report.dimensions:
        extra = ""
        if previous:
            prev = next((p for p in previous.dimensions if p.name == d.name), None)
            if prev:
                delta = d.score - prev.score
                extra = f"  delta={delta:+.4f}"
        print(
            f"  {d.name:24s} {d.score:.4f}  (weight={d.weight:.2f}, contrib={d.score*d.weight:.4f}){extra}"
        )
    if previous:
        delta = report.aggregate_score - previous.aggregate_score
        logger.info("Aggregate delta vs previous: %+.4f", delta)


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure SPEACE AGI readiness.")
    parser.add_argument("--iteration", type=int, default=0, help="Iteration number.")
    parser.add_argument("--compare", action="store_true", help="Compare with previous report.")
    parser.add_argument("--no-pytest", action="store_true", help="Skip running pytest entirely.")
    parser.add_argument("--coverage", action="store_true", help="Run full test suite (all tests).")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s")

    test_state: Optional[Dict[str, int]] = None
    if args.no_pytest:
        test_state = {"passed": 0, "failed": 0, "skipped": 0}
    elif args.coverage:
        test_state = _run_pytest()
    else:
        test_state = _run_quick_tests()

    inputs = build_inputs(test_state)
    evaluator = AGIReadinessScore()
    report = evaluator.evaluate(**inputs, iteration=args.iteration)

    previous = load_last_report(REPORTS_ROOT) if args.compare else None
    print_report(report, previous)

    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S", time.localtime(report.timestamp))
    path = report.save(REPORTS_ROOT / f"agi_readiness_{ts}.json")
    logger.info("Report saved to: %s", path)
    # Non-zero exit if below threshold to allow CI/loop reactions.
    return 0 if report.is_agi_like else 1


if __name__ == "__main__":
    sys.exit(main())
