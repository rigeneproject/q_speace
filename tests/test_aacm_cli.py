"""Regression tests for the AACM CLI entry point (T230)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from q_speace.aacm import __main__ as aacm_cli
from q_speace.aacm.loop import AACMLoop, LoopResult, StopReason


def test_aacm_cli_dry_run_budget_exhausted_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    rc = aacm_cli.main(["--dry-run", "--max-iterations", "2", "--quiet"])
    assert rc == 2
    out = json.loads(capsys.readouterr().out)
    assert out["stop_reason"] == StopReason.BUDGET_EXHAUSTED.value
    assert out["iterations_run"] == 2


def test_aacm_cli_respects_custom_human_abort_sentinel(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sentinel = tmp_path / "CUSTOM_HALT"
    sentinel.write_text("halt\n", encoding="utf-8")
    rc = aacm_cli.main(
        [
            "--dry-run",
            "--max-iterations",
            "3",
            "--worktree",
            str(tmp_path),
            "--human-abort-sentinel",
            "CUSTOM_HALT",
            "--quiet",
        ]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["stop_reason"] == StopReason.HUMAN_ABORT.value
    assert out["iterations_run"] == 0


@pytest.mark.parametrize(
    ("reason", "expected_rc"),
    [
        (StopReason.CONVERGED, 0),
        (StopReason.HUMAN_ABORT, 0),
        (StopReason.BUDGET_EXHAUSTED, 2),
        (StopReason.WALL_CLOCK_EXHAUSTED, 2),
        (StopReason.GATE_BYPASS_ATTEMPTED, 3),
        (StopReason.OMEGA_COLLAPSE, 3),
        (StopReason.VALIDATION_OVERFIT_DETECTED, 3),
        (StopReason.REPUTATION_DRIFT, 3),
        (None, 3),
    ],
)
def test_aacm_cli_exit_codes_for_stop_reasons(
    monkeypatch: pytest.MonkeyPatch,
    reason: StopReason | None,
    expected_rc: int,
) -> None:
    def _fake_run(self: AACMLoop, *args: Any, **kwargs: Any) -> LoopResult:
        return LoopResult(iterations=[], stop_reason=reason, started_at=1.0, finished_at=2.0)

    monkeypatch.setattr(AACMLoop, "run", _fake_run)
    rc = aacm_cli.main(["--dry-run", "--quiet"])
    assert rc == expected_rc


def test_aacm_cli_create_pr_blocked_unless_converged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pr_called = False

    def _fake_create_pr(*args: Any, **kwargs: Any) -> Any:
        nonlocal pr_called
        pr_called = True
        raise AssertionError("create_pr must not be called on safety failure")

    def _fake_run(self: AACMLoop, *args: Any, **kwargs: Any) -> LoopResult:
        return LoopResult(
            iterations=[],
            stop_reason=StopReason.GATE_BYPASS_ATTEMPTED,
            started_at=1.0,
            finished_at=2.0,
        )

    monkeypatch.setattr(AACMLoop, "run", _fake_run)
    monkeypatch.setattr("q_speace.aacm.pr_helper.create_pr", _fake_create_pr)
    rc = aacm_cli.main(
        ["--dry-run", "--worktree", str(tmp_path), "--create-pr-on-success", "--quiet"]
    )
    assert rc == 3
    assert pr_called is False
