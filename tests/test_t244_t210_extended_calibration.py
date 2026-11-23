"""T244: Tests for T208 Group C extended 80-case T210 calibration & held-out decision campaign."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from q_speace.bcel.catalog import BCELCatalog
from q_speace.cli import app
from q_speace.vertical_slice import (
    extended_t210_dataset,
    run_t210_calibration_and_decision_campaign,
)


def test_t244_extended_dataset_disjoint_splits_and_campaign(tmp_path: Path) -> None:
    cal = extended_t210_dataset("calibration")
    held = extended_t210_dataset("held_out")
    full = extended_t210_dataset("all")
    assert len(cal.cases) == 40
    assert len(held.cases) == 40
    assert len(full.cases) == 80
    assert {c.case_id for c in cal.cases}.isdisjoint({c.case_id for c in held.cases})
    assert {c.prompt for c in cal.cases}.isdisjoint({c.prompt for c in held.cases})
    assert sum(1 for c in held.cases if c.should_answer) == 20
    assert sum(1 for c in held.cases if not c.should_answer) == 20
    with pytest.raises(ValueError, match="unsupported split"):
        extended_t210_dataset("invalid")  # type: ignore[arg-type]

    out_dir = tmp_path / "t210_campaign"
    report = run_t210_calibration_and_decision_campaign(
        seed=7,
        max_unsafe_answer_rate=0.10,
        n_resamples=400,
        output_dir=out_dir,
    )
    json.dumps(report, allow_nan=False)
    assert (out_dir / "t210_decision_report.json").exists()
    assert report["calibration_size"] == 40
    assert report["held_out_size"] == 40

    # Calibrated energy_gate beats always_answer on held-out (CI95_lo > 0, unsafe <= 0.10 -> keep).
    eng = report["held_out_comparisons"]["energy_gate"]
    assert eng["candidate"]["unsafe_answer_rate"] <= 0.10
    assert eng["paired_deltas"]["policy_accuracy"]["ci95"][0] > 0.0
    assert report["t210_10_decisions"]["energy_gate"]["decision"] == "keep"

    # combined_gate enforces safety cap (unsafe <= 0.10) and emits an explicit T210.10 verdict.
    comb = report["held_out_comparisons"]["combined_gate"]
    assert comb["candidate"]["unsafe_answer_rate"] <= 0.10
    assert report["t210_10_decisions"]["combined_gate"]["decision"] in ("keep", "revise")

    assert BCELCatalog().is_functional(
        "Disjoint calibration-to-held-out gate threshold selection and T210 decision report (T244)"
    )


def test_t244_cli_t210_campaign(tmp_path: Path) -> None:
    out_dir = tmp_path / "cli_t210"
    runner = CliRunner()
    res = runner.invoke(
        app,
        ["eval", "t210-campaign", "--seed", "7", "--output", str(out_dir)],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["spec"] == "T244"
    assert data["calibration_size"] == 40
    assert data["held_out_size"] == 40
    assert data["t210_10_decisions"]["energy_gate"]["decision"] == "keep"
    assert (out_dir / "t210_decision_report.json").exists()
