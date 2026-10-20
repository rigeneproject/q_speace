"""Tests for the PR helper (T-AACM-LOOP_SPEC §D4)."""

from __future__ import annotations

import shutil
from dataclasses import FrozenInstanceError

import pytest

from q_speace.aacm.loop import LoopIteration, LoopResult, StopReason
from q_speace.aacm.pr_helper import PRResult, build_pr_body, create_pr


def test_build_pr_body_contains_stop_reason() -> None:
    result = LoopResult(
        iterations=[
            LoopIteration(iteration_id=1, strategy="module_replace", proposal_admitted=True),
        ],
        stop_reason=StopReason.CONVERGED,
    )
    body = build_pr_body(result)
    assert "AACM loop result" in body
    assert "converged" in body
    assert "Iterations run: 1" in body
    assert "Auto-generated" in body


def test_build_pr_body_with_no_stop_reason() -> None:
    result = LoopResult(iterations=[], stop_reason=None)
    body = build_pr_body(result)
    assert "n/a" in body


@pytest.mark.skipif(
    shutil.which("gh") is not None,
    reason="gh is installed; the missing-gh test would be a false positive",
)
def test_create_pr_skips_when_gh_missing(tmp_path) -> None:
    pr = create_pr(
        tmp_path,
        title="t",
        body="b",
    )
    assert pr.opened is False
    assert pr.skipped_reason == "gh not installed"


def test_pr_result_is_frozen() -> None:
    """PRResult is a frozen dataclass."""
    pr = PRResult(
        opened=False,
        url=None,
        skipped_reason="x",
        stdout="",
        stderr="",
    )
    with pytest.raises(FrozenInstanceError):
        pr.opened = True  # type: ignore[misc]


def test_build_pr_body_is_valid_json_parseable_lines() -> None:
    """The body is plain text but contains structured lines; the
    summary section must include the iteration count."""
    result = LoopResult(
        iterations=[LoopIteration(iteration_id=i, strategy="default") for i in range(1, 4)],
        stop_reason=StopReason.BUDGET_EXHAUSTED,
    )
    body = build_pr_body(result)
    # The summary line appears
    assert "Iterations run: 3" in body
    # The stop reason appears
    assert "budget_exhausted" in body
