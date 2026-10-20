"""Tests for the AACM real executor (T-AACM-LOOP_SPEC §C1 + §C3).

3 tests:
  1. test_executor_dry_run_returns_zero
  2. test_executor_applies_diff_in_worktree_and_rolls_back
  3. test_loop_runs_real_executor_in_worktree
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from q_speace.aacm.executor import WorktreeExecutor
from q_speace.aacm.loop import (
    AACMLoop,
    ModuleReplacementProposal,
    ValidationSet,
    ValidationTask,
)

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None,
    reason="git executable not available",
)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a tiny git repo with one tracked file."""
    repo = tmp_path / "repo"
    repo.mkdir()
    # git init + config user (required for some git versions)
    subprocess.run(
        ["git", "init", "-q", "-b", "main"],
        cwd=str(repo),
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=str(repo),
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(repo),
        check=True,
    )
    # Tracked file
    target = repo / "foo.py"
    target.write_text("x = 1\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "foo.py"],
        cwd=str(repo),
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-q", "-m", "init"],
        cwd=str(repo),
        check=True,
    )
    return repo


def _make_simple_proposal(target_module: str) -> ModuleReplacementProposal:
    """A no-op proposal that changes x = 1 -> x = 2.

    evidence_kinds is ("code", "metric") — NOT ("code", "test") —
    so the validation set's disjointness rule does not fire on
    foo.py as a 'test' artifact.
    """
    diff = (
        "diff --git a/foo.py b/foo.py\n"
        "--- a/foo.py\n"
        "+++ b/foo.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-x = 1\n"
        "+x = 2\n"
    )
    return ModuleReplacementProposal(
        target_module=target_module,
        replacement_diff=diff,
        rationale="change x to 2",
        evidence_kinds=("code", "metric"),
        artifact_paths={"code": "foo.py", "metric": "metric_foo.py"},
        expected_impact=0.5,
        risk=0.1,
        confidence=0.7,
        proposed_by="test",
        proposed_at=0.0,
        iteration_id=1,
    )


def test_executor_dry_run_returns_zero() -> None:
    executor = WorktreeExecutor(worktree=Path("/nonexistent"), dry_run=True)
    proposal = _make_simple_proposal("foo.py")
    result = executor.run(proposal, validation=None)
    assert result.applied is False
    assert result.rolled_back is False
    assert result.score == 0.0
    assert result.error == "dry_run"


def test_executor_applies_diff_in_worktree_and_rolls_back(
    git_repo: Path,
) -> None:
    """The executor applies the diff, measures, and rolls back when
    the score is below the keep threshold (no relevant validation
    tasks)."""
    target_abs = git_repo / "foo.py"
    pre_image = target_abs.read_text(encoding="utf-8")
    assert pre_image == "x = 1\n"

    executor = WorktreeExecutor(worktree=git_repo, dry_run=False)
    proposal = _make_simple_proposal("foo.py")
    result = executor.run(proposal, validation=None)

    # No relevant validation tasks -> score is None (inconclusive)
    # -> executor rolled back.
    assert result.rolled_back is True
    assert result.score is None
    assert result.error == "no_relevant_validation_tasks"

    # File content should be restored to pre_image.
    assert target_abs.read_text(encoding="utf-8") == pre_image


def test_executor_measures_real_execution_time(
    git_repo: Path,
) -> None:
    """D1: the executor runs a Python file in a subprocess and
    measures wall clock."""
    # Write a tiny Python script that sleeps for 0.05s
    target = git_repo / "sleeper.py"
    target.write_text("import time; time.sleep(0.05)\n", encoding="utf-8")
    subprocess.run(["git", "add", "sleeper.py"], cwd=str(git_repo), check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "sleeper"],
        cwd=str(git_repo),
        check=True,
    )

    task = ValidationTask(
        task_id="vs:exec:001",
        task_type="exec_time",
        input_artifact="sleeper.py",
        expected_outcome="under_2s",
        metric="execution_time_s",
        metric_threshold=2.0,
        metric_direction="less_than",
    )
    validation = ValidationSet(
        tasks=[
            task,
            ValidationTask(
                task_id="vs:exec:002",
                task_type="exec_time",
                input_artifact="sleeper.py",
                expected_outcome="under_2s",
                metric="execution_time_s",
                metric_threshold=2.0,
                metric_direction="less_than",
            ),
            ValidationTask(
                task_id="vs:dummy1",
                task_type="dt_a",
                input_artifact="da.py",
                expected_outcome="x",
                metric="m",
                metric_threshold=0.0,
                metric_direction="less_than",
            ),
            ValidationTask(
                task_id="vs:dummy1b",
                task_type="dt_a",
                input_artifact="da.py",
                expected_outcome="x",
                metric="m",
                metric_threshold=0.0,
                metric_direction="less_than",
            ),
            ValidationTask(
                task_id="vs:dummy2",
                task_type="dt_b",
                input_artifact="db.py",
                expected_outcome="x",
                metric="m",
                metric_threshold=0.0,
                metric_direction="less_than",
            ),
            ValidationTask(
                task_id="vs:dummy2b",
                task_type="dt_b",
                input_artifact="db.py",
                expected_outcome="x",
                metric="m",
                metric_threshold=0.0,
                metric_direction="less_than",
            ),
            ValidationTask(
                task_id="vs:dummy3",
                task_type="dt_c",
                input_artifact="dc.py",
                expected_outcome="x",
                metric="m",
                metric_threshold=0.0,
                metric_direction="less_than",
            ),
            ValidationTask(
                task_id="vs:dummy3b",
                task_type="dt_c",
                input_artifact="dc.py",
                expected_outcome="x",
                metric="m",
                metric_threshold=0.0,
                metric_direction="less_than",
            ),
            ValidationTask(
                task_id="vs:dummy4",
                task_type="dt_d",
                input_artifact="dd.py",
                expected_outcome="x",
                metric="m",
                metric_threshold=0.0,
                metric_direction="less_than",
            ),
            ValidationTask(
                task_id="vs:dummy4b",
                task_type="dt_d",
                input_artifact="dd.py",
                expected_outcome="x",
                metric="m",
                metric_threshold=0.0,
                metric_direction="less_than",
            ),
        ],
    )
    executor = WorktreeExecutor(worktree=git_repo, dry_run=False)
    proposal = _make_simple_proposal("sleeper.py")
    result = executor.run(proposal, validation=validation)
    # Both relevant tasks target sleeper.py and should pass (< 2s).
    assert result.score == 1.0
    assert len(result.metric_observations) == 2
    for obs in result.metric_observations:
        assert obs["metric"] == "execution_time_s"
        assert obs["value"] < 2.0
        assert obs["passed"] is True
        assert "error" not in obs


def test_executor_failing_subprocess_marks_passed_false(
    git_repo: Path,
) -> None:
    """D1: a script that exits non-zero is marked passed=False."""
    target = git_repo / "fails.py"
    target.write_text(
        "import sys; sys.exit(1)\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "fails.py"], cwd=str(git_repo), check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "fails"],
        cwd=str(git_repo),
        check=True,
    )

    task = ValidationTask(
        task_id="vs:fail:001",
        task_type="exec_time",
        input_artifact="fails.py",
        expected_outcome="x",
        metric="execution_time_s",
        metric_threshold=10.0,
        metric_direction="less_than",
    )
    # 2 relevant + 8 dummies to satisfy ValidationSet invariants
    tasks = [
        task,
        ValidationTask(
            task_id="vs:fail:002",
            task_type="exec_time",
            input_artifact="fails.py",
            expected_outcome="x",
            metric="execution_time_s",
            metric_threshold=10.0,
            metric_direction="less_than",
        ),
    ]
    for i in range(4):
        for j in range(2):
            tasks.append(
                ValidationTask(
                    task_id=f"vs:fd:{i}:{j}",
                    task_type=f"fd_t_{i}",
                    input_artifact=f"fd_{i}.py",
                    expected_outcome="x",
                    metric="m",
                    metric_threshold=0.0,
                    metric_direction="less_than",
                )
            )
    validation = ValidationSet(tasks=tasks)
    executor = WorktreeExecutor(worktree=git_repo, dry_run=False)
    proposal = _make_simple_proposal("fails.py")
    result = executor.run(proposal, validation=validation)
    assert result.score == 0.0
    for obs in result.metric_observations:
        assert obs["passed"] is False
        assert "error" in obs


def test_loop_runs_real_executor_in_worktree(
    git_repo: Path,
) -> None:
    """End-to-end: the loop, with no executor_fn injected, picks up
    the worktree and runs a real WorktreeExecutor."""
    # Validation set with 2 tasks that target 'foo.py'.
    task = ValidationTask(
        task_id="vs:test:001",
        task_type="module_replace_rollback",
        input_artifact="foo.py",
        expected_outcome="rolled_back",
        metric="execution_time_s",
        metric_threshold=2.0,
        metric_direction="less_than",
    )
    task2 = ValidationTask(
        task_id="vs:test:002",
        task_type="module_replace_rollback",
        input_artifact="foo.py",
        expected_outcome="rolled_back",
        metric="execution_time_s",
        metric_threshold=2.0,
        metric_direction="less_than",
    )
    extra = []
    for i in range(4):
        for j in range(2):
            extra.append(
                ValidationTask(
                    task_id=f"vs:dummy:{i}:{j}",
                    task_type=f"dummy_type_{i}",
                    input_artifact=f"dummy_{i}.py",
                    expected_outcome="x",
                    metric="m",
                    metric_threshold=0.0,
                    metric_direction="less_than",
                )
            )
    val = ValidationSet(tasks=[task, task2, *extra])
    val_path = git_repo / "validation_set.json"
    val.save(val_path)

    loop = AACMLoop(
        worktree=git_repo,
        validation_set_path=val_path,
        omega=0.6,
        max_iterations=4,
        auto_infra_interval=1000,
    )

    def _propose(iteration, context):
        return _make_simple_proposal("foo.py")

    result = loop.run(propose_fn=_propose)

    assert result.iterations_run >= 1
    assert any(it.proposal_admitted for it in result.iterations)
    target = git_repo / "foo.py"
    content = target.read_text(encoding="utf-8")
    assert content in {"x = 1\n", "x = 2\n"}
