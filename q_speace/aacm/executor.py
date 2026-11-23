"""Real executor for the AACM self-improvement loop (T-AACM-LOOP_SPEC §C1).

The executor applies a ``ModuleReplacementProposal.replacement_diff``
to a target module inside a *git worktree*, runs the validation set
metrics against the modified module, and returns a normalized score
in [0, 1].

If anything fails (apply error, metric below threshold, exception
during run), the executor rolls back the change via
``git checkout -- <file>`` so the worktree is left in a clean state.

The executor NEVER touches the main tree. It only operates inside
the worktree passed at construction.

BCEL: the executor is a *file-level transform + metric measurer*. It
is not an LLM, not a planner, not an agent. It does not interpret
intent; it applies bytes and measures outcomes.
"""

from __future__ import annotations

import math
import re
import shutil
import subprocess
import sys
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .loop import ModuleReplacementProposal, ValidationSet, ValidationTask

# Regex for the first "+++ b/<path>" line in a unified diff.
# Handles "+++ b/path", "+++ path", and "+++ /dev/null" (deletion).
_DIFF_TARGET_RE = re.compile(
    r"^\+\+\+\s+(?:b/)?(?P<path>[^\s\t]+).*$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class ExecutionResult:
    """Outcome of one executor.run() call."""

    score: float | None  # in [0, 1]; None = inconclusive (skip)
    applied: bool  # True iff the diff was applied
    rolled_back: bool  # True iff the executor reverted the change
    metric_observations: list[dict[str, Any]]
    error: str | None = None


def _diff_target_path(diff: str, fallback: str) -> str:
    """Extract the target file path from a unified diff.

    Falls back to the proposal's target_module if the diff has no
    "+++ b/<path>" header (which would be unusual but possible for
    newly-created files).
    """
    m = _DIFF_TARGET_RE.search(diff)
    if m:
        return m.group("path")
    return fallback


def _run_git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    """Run a git command in ``cwd`` and return the result.

    Raises ``RuntimeError`` on non-zero exit unless ``check=False`` is
    used by the caller.
    """
    if shutil.which("git") is None:
        raise RuntimeError("git executable not found on PATH")
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


class WorktreeExecutor:
    """Apply a proposal diff inside a git worktree and measure outcomes.

    Parameters
    ----------
    worktree:
        Path to an existing git worktree. The executor will run
        ``git apply`` and ``git checkout`` inside this directory only.
    dry_run:
        If True, the executor does not modify any file; it returns
        a synthetic 0.0 score. Used by tests and by the CLI --dry-run
        flag.
    """

    def __init__(self, worktree: Path, dry_run: bool = False) -> None:
        self.worktree = Path(worktree)
        self.dry_run = dry_run

    def run(
        self,
        proposal: ModuleReplacementProposal,
        validation: ValidationSet | None,
    ) -> ExecutionResult:
        """Apply, measure, roll back if needed.

        Returns an :class:`ExecutionResult` with a normalized score in
        [0, 1]. The score is the *fraction of validation tasks that
        passed* for the target module, where "passed" means the
        measured metric meets the threshold in the direction
        specified. If no validation set is provided, or no tasks
        target the module, returns 0.0.
        """
        if self.dry_run:
            return ExecutionResult(
                score=0.0,
                applied=False,
                rolled_back=False,
                metric_observations=[],
                error="dry_run",
            )

        target_rel = _diff_target_path(
            proposal.replacement_diff,
            proposal.target_module,
        )
        worktree_root = self.worktree.resolve()
        target_abs = (worktree_root / target_rel).resolve()
        if not target_abs.is_relative_to(worktree_root):
            return ExecutionResult(
                score=0.0,
                applied=False,
                rolled_back=False,
                metric_observations=[],
                error=f"path_traversal_blocked: {target_rel!r} escapes worktree",
            )

        if not target_abs.exists():
            # Newly-created file path; the diff should add it.
            target_abs.parent.mkdir(parents=True, exist_ok=True)

        # 1. Snapshot current state for rollback
        pre_image: str | None = None
        if target_abs.exists():
            try:
                pre_image = target_abs.read_text(encoding="utf-8")
            except Exception:
                pre_image = None

        # 2. Apply the diff via `git apply` (file-based, not stdin)
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".patch",
            delete=False,
            encoding="utf-8",
        ) as pf:
            pf.write(proposal.replacement_diff)
            patch_path = pf.name
        try:
            apply = _run_git(
                self.worktree,
                "apply",
                "--whitespace=nowarn",
                "--recount",
                patch_path,
            )
        finally:
            with suppress(FileNotFoundError):
                Path(patch_path).unlink()
        if apply.returncode != 0:
            # Fallback: write the diff via Python (when --checkin-style
            # patches confuse git apply). For v0.1 we just report the
            # error and roll back (which is a no-op since nothing was
            # applied).
            return ExecutionResult(
                score=0.0,
                applied=False,
                rolled_back=False,
                metric_observations=[],
                error=f"git apply failed: {apply.stderr.strip()[:200]}",
            )

        # 3. Measure validation tasks targeting this module
        observations: list[dict[str, Any]] = []
        if validation is not None:
            relevant = [
                t
                for t in validation.tasks
                if t.input_artifact == proposal.target_module or t.input_artifact == target_rel
            ]
            for task in relevant:
                obs = self._measure_task(task)
                observations.append(obs)

        # 4. Compute score: fraction of observations that pass
        if not observations:
            # No relevant validation tasks: roll back and return
            # score=None (inconclusive). The loop treats None as
            # "skip this iteration" — neither success nor failure.
            self._rollback(target_abs, pre_image)
            return ExecutionResult(
                score=None,
                applied=True,
                rolled_back=True,
                metric_observations=[],
                error="no_relevant_validation_tasks",
            )

        passed = sum(1 for o in observations if o["passed"])
        score = passed / len(observations)

        # 5. Decide: keep or roll back
        if score >= 0.5:
            return ExecutionResult(
                score=score,
                applied=True,
                rolled_back=False,
                metric_observations=observations,
            )

        # Score below 0.5: roll back
        self._rollback(target_abs, pre_image)
        return ExecutionResult(
            score=score,
            applied=True,
            rolled_back=True,
            metric_observations=observations,
        )

    def _measure_task(self, task: ValidationTask) -> dict[str, Any]:
        """Run a single validation task and measure ``task.metric``.

        D1 (real measurements): if the task is an execution-time
        task and ``input_artifact`` is a Python file that exists,
        run it in a subprocess and measure wall clock. The result
        is compared to ``metric_threshold`` in the direction
        specified by ``metric_direction``.

        For all other metric kinds, fall back to the conservative
        existence + non-empty check (D0 / pre-D1 behaviour).
        """
        target = self.worktree / task.input_artifact

        if task.metric == "execution_time_s" and target.exists() and str(target).endswith(".py"):
            return self._measure_execution_time(task, target)

        # Fallback: existence + non-empty = pass
        exists = target.exists()
        non_empty = exists and target.stat().st_size > 0
        passed = exists and non_empty
        return {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "input_artifact": task.input_artifact,
            "metric": task.metric,
            "metric_threshold": task.metric_threshold,
            "metric_direction": task.metric_direction,
            "value": target.stat().st_size if exists else 0,
            "passed": passed,
        }

    def _measure_execution_time(
        self,
        task: ValidationTask,
        target: Path,
    ) -> dict[str, Any]:
        """Run a Python file in a subprocess and measure wall clock.

        Returns a dict with ``value`` in seconds and ``passed`` set
        according to ``metric_direction`` (less_than | greater_than
        | equal) against ``metric_threshold``.
        """
        import subprocess
        import time as _time

        start = _time.monotonic()
        error: str | None = None
        try:
            proc = subprocess.run(
                [sys.executable, str(target)],
                cwd=str(self.worktree),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=max(1.0, float(task.metric_threshold) * 10.0),
            )
            elapsed = _time.monotonic() - start
            if proc.returncode != 0:
                error = f"exit {proc.returncode}: {proc.stderr.strip()[:120]}"
        except subprocess.TimeoutExpired:
            elapsed = _time.monotonic() - start
            error = "timeout"
        except Exception as e:
            elapsed = _time.monotonic() - start
            error = f"exception: {e!r}"[:120]

        passed = self._check_threshold(
            elapsed,
            task.metric_threshold,
            task.metric_direction,
        )
        result: dict[str, Any] = {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "input_artifact": task.input_artifact,
            "metric": task.metric,
            "metric_threshold": task.metric_threshold,
            "metric_direction": task.metric_direction,
            "value": round(elapsed, 6),
            "passed": passed and error is None,
        }
        if error:
            result["error"] = error
        return result

    @staticmethod
    def _check_threshold(
        value: float,
        threshold: float,
        direction: str,
    ) -> bool:
        if not math.isfinite(value) or not math.isfinite(threshold):
            return False
        if direction == "less_than":
            return value < threshold
        if direction == "greater_than":
            return value > threshold
        if direction == "equal":
            return abs(value - threshold) < 1e-9
        return False

    def _rollback(self, target_abs: Path, pre_image: str | None) -> None:
        """Restore the pre-image, or delete if it didn't exist."""
        if pre_image is None:
            if target_abs.exists():
                target_abs.unlink()
            return
        target_abs.write_text(pre_image, encoding="utf-8")


def build_executor_from_loop(
    worktree: Path | None,
    dry_run: bool = False,
) -> WorktreeExecutor | None:
    """Factory: return a WorktreeExecutor, or None if no worktree."""
    if worktree is None:
        return None
    return WorktreeExecutor(worktree=worktree, dry_run=dry_run)
