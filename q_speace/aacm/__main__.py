"""CLI entry point for the AACM self-improvement loop.

Usage:
    python -m q_speace.aacm --once
    python -m q_speace.aacm --max-iterations 10 --worktree /tmp/wt
    python -m q_speace.aacm --dry-run
    python -m q_speace.aacm --resume /path/to/ckpt.json

This is a *development-time* tool. It does not auto-merge. It
writes a checkpoint and stops on every StopReason. The human
reviews the diff and merges via PR.

Note: do not run as `python -m q_speace.aacm.loop` — the CLI lives
in `__main__.py`, so the canonical invocation is `python -m q_speace.aacm`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .loop import AACMLoop, LoopResult, StopReason


def _default_validation_set_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "validation_set.json"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m q_speace.aacm",
        description=(
            "Run the AACM self-improvement loop. Bounded, manual review. " "NEVER auto-merges."
        ),
    )
    p.add_argument(
        "--once",
        action="store_true",
        help="Run until a StopReason fires (default).",
    )
    p.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Override MAX_ITERATIONS for this run.",
    )
    p.add_argument(
        "--worktree",
        type=Path,
        default=None,
        help="Path to a git worktree for isolated work. Optional.",
    )
    p.add_argument(
        "--validation-set",
        type=Path,
        default=None,
        help="Path to validation_set.json (default: bundled).",
    )
    p.add_argument(
        "--checkpoint",
        type=Path,
        default=None,
        help="Path to write the loop checkpoint to.",
    )
    p.add_argument(
        "--resume",
        type=Path,
        default=None,
        help="Resume from a checkpoint at this path.",
    )
    p.add_argument(
        "--omega",
        type=float,
        default=0.6,
        help="Initial Omega for the loop (default 0.6).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Run with stub diagnose/propose; no real work.",
    )
    p.add_argument(
        "--human-abort-sentinel",
        type=str,
        default="STOP",
        help="Filename in --worktree that, if present, stops the loop.",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-iteration logging.",
    )
    p.add_argument(
        "--create-pr-on-success",
        action="store_true",
        help=(
            "After a successful run, open a draft PR via `gh pr create` "
            "from the worktree. Opt-in only. No auto-merge."
        ),
    )
    p.add_argument(
        "--pr-base",
        type=str,
        default="main",
        help="Base branch for the PR (default: main).",
    )
    return p


def _emit_summary(result: LoopResult, args: argparse.Namespace) -> None:
    print(
        json.dumps(
            {
                "iterations_run": result.iterations_run,
                "stop_reason": result.stop_reason.value if result.stop_reason else None,
                "started_at": result.started_at,
                "finished_at": result.finished_at,
                "elapsed_s": round(result.finished_at - result.started_at, 3),
            },
            indent=2,
        )
    )


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.resume is not None:
        loop = AACMLoop.from_checkpoint(args.resume, omega=args.omega)
    else:
        loop = AACMLoop(
            worktree=args.worktree,
            validation_set_path=(args.validation_set or _default_validation_set_path()),
            checkpoint_path=args.checkpoint,
            omega=args.omega,
        )
    if args.max_iterations is not None:
        loop.max_iterations = args.max_iterations

    if not args.quiet:
        print(
            f"[aacm-loop] start omega={loop.omega} "
            f"max_iter={loop.max_iterations} dry_run={args.dry_run}",
            file=sys.stderr,
        )

    if args.dry_run:
        # Stub: no proposals emitted, no work done
        result = loop.run(
            diagnose_fn=lambda ctx: None,  # skip every iteration
            propose_fn=lambda it, ctx: None,
            executor=lambda p, v: 0.0,
        )
    else:
        # In production wiring, real diagnose_fn / propose_fn /
        # executor would be injected here. For v0.1 we run the
        # defaults (no proposals), which exercises the orchestrator
        # scaffolding without doing real work.
        result = loop.run()

    _emit_summary(result, args)
    if not args.quiet:
        for i, it in enumerate(result.iterations, 1):
            print(
                f"[aacm-loop] iter {i} strategy={it.strategy} "
                f"admitted={it.proposal_admitted} "
                f"fallback={'reg' if it.fallback_registered else ('discard' if it.fallback_discarded else 'no')}",
                file=sys.stderr,
            )

    # D4: opt-in PR creation. Only if --create-pr-on-success is set,
    # the run ended cleanly, and a worktree is configured.
    if args.create_pr_on_success and args.worktree is not None:
        from .pr_helper import build_pr_body, create_pr

        pr = create_pr(
            args.worktree,
            title="[aacm-loop] automated improvement",
            body=build_pr_body(result),
            base=args.pr_base,
            draft=True,
        )
        print(
            json.dumps(
                {
                    "pr_opened": pr.opened,
                    "pr_url": pr.url,
                    "pr_skipped_reason": pr.skipped_reason,
                },
                indent=2,
            )
        )

    # Exit code: 0 on clean stop, 2 on budget/wallclock (expected), 3 on failure
    if result.stop_reason in {
        StopReason.CONVERGED,
        StopReason.HUMAN_ABORT,
        StopReason.GATE_BYPASS_ATTEMPTED,
        StopReason.OMEGA_COLLAPSE,
        StopReason.VALIDATION_OVERFIT_DETECTED,
        StopReason.REPUTATION_DRIFT,
    }:
        return 0
    if result.stop_reason in {
        StopReason.BUDGET_EXHAUSTED,
        StopReason.WALL_CLOCK_EXHAUSTED,
    }:
        return 2
    return 3


if __name__ == "__main__":
    sys.exit(main())
