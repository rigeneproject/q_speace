#!/usr/bin/env python3
"""Continuous AGI readiness auto-monitor.

Runs the AGI readiness measurement, logs results to data/agi_readiness/,
compares with previous measurement, and returns the score as exit code.

Usage:
    python scripts/continuous_agi_readiness_monitor.py [--iteration N] [--wait SEC]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.measure_agi_readiness import (
    REPORTS_ROOT,
    build_inputs,
)
from speace_core.cellular_brain.agi_readiness.agi_readiness_score import (
    AGIReadinessReport,
    AGIReadinessScore,
)

HISTORY_PATH = PROJECT_ROOT / "data" / "agi_readiness" / "history.jsonl"
AUTO_MEASUREMENTS_PATH = PROJECT_ROOT / "data" / "agi_readiness" / "auto_measurements.jsonl"

logger = logging.getLogger(__name__)


def load_history() -> list[Dict[str, Any]]:
    """Load all past auto-measurements from history.jsonl."""
    records: list[Dict[str, Any]] = []
    if not HISTORY_PATH.exists():
        return records
    try:
        with HISTORY_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return records


def save_measurement(report: AGIReadinessReport) -> None:
    """Append a measurement record to the history log and auto_measurements."""
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": report.timestamp,
        "iteration": report.iteration,
        "aggregate_score": round(report.aggregate_score, 4),
        "is_agi_like": report.is_agi_like,
        "is_agi_robust": report.is_agi_robust,
        "summary": report.summary,
        "dimensions": [
            {
                "name": d.name,
                "score": round(d.score, 4),
                "weighted_contribution": round(d.score * d.weight, 4),
            }
            for d in report.dimensions
        ],
    }
    with HISTORY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    with AUTO_MEASUREMENTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def compute_delta(history: list[Dict[str, Any]]) -> Optional[Dict[str, float]]:
    """Compare the latest two measurements and return deltas."""
    if len(history) < 2:
        return None
    prev = history[-2]
    curr = history[-1]
    delta = curr["aggregate_score"] - prev["aggregate_score"]
    return {
        "delta": round(delta, 4),
        "direction": "improving" if delta > 0 else ("degrading" if delta < 0 else "stable"),
    }


def run_measurement(iteration: int = 0, no_pytest: bool = False) -> AGIReadinessReport:
    """Run a full AGI readiness measurement and return the report."""
    test_state = {"passed": 0, "failed": 0, "skipped": 0} if no_pytest else None
    inputs = build_inputs(test_state)
    evaluator = AGIReadinessScore()
    return evaluator.evaluate(**inputs, iteration=iteration)


def main() -> int:
    parser = argparse.ArgumentParser(description="Continuous AGI readiness auto-monitor.")
    parser.add_argument("--iteration", type=int, default=0, help="Iteration number.")
    parser.add_argument(
        "--wait", type=float, default=0.0, help="Seconds to wait before measurement."
    )
    parser.add_argument("--no-pytest", action="store_true", help="Skip running pytest.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging.")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )

    if args.wait > 0:
        logger.info("Waiting %.1f seconds before measurement...", args.wait)
        time.sleep(args.wait)

    logger.info("=" * 60)
    logger.info("AGI Readiness Auto-Measurement - iteration %s", args.iteration)

    report = run_measurement(args.iteration, args.no_pytest)

    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S", time.localtime(report.timestamp))
    report_path = report.save(REPORTS_ROOT / f"agi_readiness_{ts}.json")
    logger.info("Report saved to: %s", report_path)

    save_measurement(report)

    history = load_history()
    delta_info = compute_delta(history)
    if delta_info:
        logger.info(
            "Change vs previous: %+.4f (%s)",
            delta_info["delta"],
            delta_info["direction"],
        )

    summary: Dict[str, Any] = {
        "timestamp": report.timestamp,
        "iteration": report.iteration,
        "aggregate_score": round(report.aggregate_score, 4),
        "is_agi_like": report.is_agi_like,
        "is_agi_robust": report.is_agi_robust,
        "summary": report.summary,
        "delta": delta_info,
        "report_file": str(report_path),
    }
    logging.info(json.dumps(summary, indent=2))
    exit_code = min(100, max(0, int(round(report.aggregate_score * 100))))
    logger.info("Exit code: %d (score * 100)", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
