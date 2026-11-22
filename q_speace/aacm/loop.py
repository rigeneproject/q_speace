"""AACM self-improvement loop (T-AACM-LOOP_SPEC, v0.1).

This module implements the iterated self-improvement loop described in
``docs/T-AACM-LOOP_SPEC.md``. It is *not* an autonomous production
agent: it is a development-time tool, invoked explicitly via CLI
(``python -m q_speace.aacm.loop --once``) or imported as a library.

The loop:
  diagnose -> decide -> execute -> verify -> learn

It reuses the existing ``AACMController`` (state machine) and
``EvolutionCouncil.aacm_filter`` (MM-ARP gate) without duplicating
them. It adds:
  - ``ReputationRegistry`` (R6, with exponential decay)
  - ``ValidationSet`` (R5, with disjoint-from-test invariant)
  - ``ModuleReplacementProposal`` (R4, with evidence_kind K>=2)
  - ``AACMLoop`` (orchestrator, with explicit StopReason)
  - ``LOOP_HARD_PROHIBITIONS`` (5 paths the loop can NEVER modify)

The prohibitions are enforced by ``_assert_path_not_prohibited``,
which is a hard wall: it raises ``LoopProhibited`` before any
proposal is admitted. There is no flag, no environment variable,
no override.

BCEL: this is a *control layer*, not a model. It operates on Python
modules, not on prompts, not on weights. "Reputation" is a
counter; "validation" is a JSON file; "fallback" is a registry.
None of these are metaphors for agent intent.
"""

from __future__ import annotations

import enum
import json
import time
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .constants import OMEGA_MIN
from .exceptions import InvariantViolation
from .loop_constants import (
    ADVERSARIAL_THRESHOLD_BASE,
    ADVERSARIAL_THRESHOLD_HIGH_OMEGA,
    ADVERSARIAL_THRESHOLD_LOW_OMEGA,
    AUTO_INFRA_INTERVAL,
    CONSECUTIVE_FAILURES_FOR_EXTRA_K,
    CONVERGENCE_WINDOW,
    EVIDENCE_KINDS,
    FALLBACK_RESIDUAL_CONFIDENCE_MIN,
    LOOP_CHECKPOINT_SCHEMA_VERSION,
    LOOP_HARD_PROHIBITION_PATHS,
    MAX_DIFF_LINES,
    MAX_ITERATIONS,
    MAX_WALL_CLOCK_S,
    MIN_REPUTATION,
    OMEGA_HIGH_THRESHOLD,
    OMEGA_LOW_FOR_EXTRA_K,
    REPUTATION_HALF_LIFE_S,
    REPUTATION_LOW_THRESHOLD,
    VALIDATION_OVERFIT_STREAK,
    VALIDATION_OVERFIT_THRESHOLD,
    VALIDATION_SET_MIN_PER_TASK_TYPE,
    VALIDATION_SET_MIN_SIZE,
    VALIDATION_SET_SCHEMA_VERSION,
)

LoopContext = dict[str, int | float]
DiagnoseFn = Callable[[LoopContext], "LoopIteration | None"]
ProposeFn = Callable[["LoopIteration", LoopContext], "ModuleReplacementProposal | None"]
ExecutorFn = Callable[["ModuleReplacementProposal", "ValidationSet | None"], float | None]

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class LoopProhibited(InvariantViolation):
    """Raised when a proposal targets a LOOP_HARD_PROHIBITION path.

    Inherits from InvariantViolation so the existing AACM exception
    hierarchy covers it.
    """


class LoopStop(StopIteration):
    """Raised internally by AACMLoop.run() to signal a clean stop.

    Catch in CLI / driver and inspect ``reason``.
    """


class ValidationSetError(ValueError):
    """Raised when a ValidationSet fails its invariants."""


# ---------------------------------------------------------------------------
# LOOP_HARD_PROHIBITIONS
# ---------------------------------------------------------------------------

# The set of paths the loop may NEVER modify. This set is mutable
# only via PR (it is a frozenset; the literals are the only way to
# change it, and that requires editing this file, which is itself
# in the prohibition set).
LOOP_HARD_PROHIBITIONS: frozenset[str] = LOOP_HARD_PROHIBITION_PATHS


def _assert_path_not_prohibited(path: str) -> None:
    """Hard wall: raise LoopProhibited if ``path`` is in the set.

    No override, no environment variable, no flag. This function is
    the single chokepoint that enforces R-prohibitions.
    """
    if path in LOOP_HARD_PROHIBITIONS:
        raise LoopProhibited(f"loop cannot modify {path!r} (hard prohibition)")


# ---------------------------------------------------------------------------
# Stop reasons
# ---------------------------------------------------------------------------


class StopReason(enum.Enum):
    """Why the loop stopped."""

    CONVERGED = "converged"
    BUDGET_EXHAUSTED = "budget_exhausted"
    WALL_CLOCK_EXHAUSTED = "wall_clock_exhausted"
    OMEGA_COLLAPSE = "omega_collapse"
    VALIDATION_OVERFIT_DETECTED = "validation_overfit_detected"
    GATE_BYPASS_ATTEMPTED = "gate_bypass_attempted"
    REPUTATION_DRIFT = "reputation_drift"
    HUMAN_ABORT = "human_abort"


# ---------------------------------------------------------------------------
# Ω-modulated adversarial threshold (R10)
# ---------------------------------------------------------------------------


def adversarial_threshold(omega: float) -> float:
    """Return the adversarial gate threshold for the given Ω.

    omega <  OMEGA_MIN    -> 0.85  (errors cost; scrutinize hard)
    OMEGA_MIN <= omega < 0.50 -> 0.70  (default)
    omega >= 0.50         -> 0.60  (alternatives available; relax)

    The thresholds are NOT overridable at runtime; only the
    *inputs* (omega) change.
    """
    if omega < OMEGA_MIN:
        return ADVERSARIAL_THRESHOLD_LOW_OMEGA
    if omega < OMEGA_HIGH_THRESHOLD:
        return ADVERSARIAL_THRESHOLD_BASE
    return ADVERSARIAL_THRESHOLD_HIGH_OMEGA


# ---------------------------------------------------------------------------
# Reputation (R6)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReputationEntry:
    """One observation of a strategy/context/outcome tuple (R6)."""

    strategy: str
    context: str
    outcome: str  # "success" | "failure" | "partial"
    confidence: float  # weight in [0, 1]
    recorded_at: float  # Unix seconds
    decay_at: float  # recorded_at + half_life (informational)

    def __post_init__(self) -> None:
        if not self.strategy:
            raise ValueError("strategy must be non-empty")
        if self.outcome not in {"success", "failure", "partial"}:
            raise ValueError(f"outcome must be success|failure|partial (got {self.outcome!r})")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1] (got {self.confidence})")
        if self.recorded_at < 0.0:
            raise ValueError("recorded_at must be >= 0")
        if self.decay_at < self.recorded_at:
            raise ValueError("decay_at must be >= recorded_at")

    def decayed_confidence(self, now: float) -> float:
        """Exponential decay with half-life REPUTATION_HALF_LIFE_S."""
        if self.recorded_at >= now:
            return self.confidence
        elapsed = now - self.recorded_at
        factor = 0.5 ** (elapsed / REPUTATION_HALF_LIFE_S)
        return float(self.confidence * factor)

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "context": self.context,
            "outcome": self.outcome,
            "confidence": self.confidence,
            "recorded_at": self.recorded_at,
            "decay_at": self.decay_at,
        }


@dataclass
class ReputationRegistry:
    """Strategy reputation with exponential decay (R6).

    Entries below MIN_REPUTATION after decay are pruned at access
    time. Collapsing below 3 entries triggers REPUTATION_DRIFT.
    """

    entries: list[ReputationEntry] = field(default_factory=list)

    def record(
        self,
        strategy: str,
        context: str,
        outcome: str,
        confidence: float,
        now: float | None = None,
    ) -> ReputationEntry:
        if now is None:
            now = time.time()
        e = ReputationEntry(
            strategy=strategy,
            context=context,
            outcome=outcome,
            confidence=float(confidence),
            recorded_at=now,
            decay_at=now + REPUTATION_HALF_LIFE_S,
        )
        self.entries.append(e)
        return e

    def effective_score(
        self,
        strategy: str,
        context: str,
        now: float | None = None,
    ) -> float:
        """Aggregate decayed score for (strategy, context).

        Returns 0.0 if no entries match. Otherwise the mean of
        decayed confidences, weighted by outcome (success=+1,
        partial=+0.5, failure=-1).
        """
        if now is None:
            now = time.time()
        self._prune(now)
        weight_by_outcome = {"success": 1.0, "partial": 0.5, "failure": -1.0}
        total = 0.0
        count = 0
        for e in self.entries:
            if e.strategy == strategy and e.context == context:
                d = e.decayed_confidence(now)
                total += weight_by_outcome[e.outcome] * d
                count += 1
        if count == 0:
            return 0.0
        # Normalize to [0, 1] roughly. Raw score is in [-1, 1];
        # shift and clamp.
        return max(0.0, min(1.0, (total / count + 1.0) / 2.0))

    def _prune(self, now: float) -> None:
        kept = [e for e in self.entries if e.decayed_confidence(now) >= MIN_REPUTATION]
        self.entries = kept

    def to_dict(self) -> dict[str, Any]:
        return {"entries": [e.to_dict() for e in self.entries]}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ReputationRegistry:
        entries = [ReputationEntry(**e) for e in payload.get("entries", [])]
        return cls(entries=entries)


# ---------------------------------------------------------------------------
# Validation set (R5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationTask:
    """A single validation task (R5)."""

    task_id: str
    task_type: str
    input_artifact: str
    expected_outcome: str
    metric: str
    metric_threshold: float
    metric_direction: str  # "less_than" | "greater_than" | "equal"

    def __post_init__(self) -> None:
        if not self.task_id:
            raise ValueError("task_id must be non-empty")
        if not self.task_type:
            raise ValueError("task_type must be non-empty")
        if self.metric_direction not in {"less_than", "greater_than", "equal"}:
            raise ValueError(
                f"metric_direction must be less_than|greater_than|equal "
                f"(got {self.metric_direction!r})"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "input_artifact": self.input_artifact,
            "expected_outcome": self.expected_outcome,
            "metric": self.metric,
            "metric_threshold": self.metric_threshold,
            "metric_direction": self.metric_direction,
        }


@dataclass
class ValidationSet:
    """Disjoint-from-tests validation set (R5).

    The set is static; regeneration requires a PR. ``disjoint_from_proposal``
    enforces that no task here is used as a ``"test"`` evidence_kind
    in a proposal in the same run.
    """

    tasks: list[ValidationTask] = field(default_factory=list)
    schema_version: str = VALIDATION_SET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        n = len(self.tasks)
        if n < VALIDATION_SET_MIN_SIZE:
            raise ValidationSetError(
                f"validation set needs at least {VALIDATION_SET_MIN_SIZE} tasks " f"(got {n})"
            )
        # Stratification: at least 2 task_types represented, each with
        # at least VALIDATION_SET_MIN_PER_TASK_TYPE tasks.
        by_type: dict[str, int] = {}
        for t in self.tasks:
            by_type[t.task_type] = by_type.get(t.task_type, 0) + 1
        if len(by_type) < 2:
            raise ValidationSetError(
                f"validation set needs >= 2 distinct task_types "
                f"(got {len(by_type)}: {sorted(by_type)})"
            )
        for ttype, count in by_type.items():
            if count < VALIDATION_SET_MIN_PER_TASK_TYPE:
                raise ValidationSetError(
                    f"task_type {ttype!r} has {count} tasks; need >= "
                    f"{VALIDATION_SET_MIN_PER_TASK_TYPE}"
                )
        # Unique task_ids
        ids = [t.task_id for t in self.tasks]
        if len(set(ids)) != len(ids):
            raise ValidationSetError("task_ids must be unique")

    def disjoint_from_proposal(
        self,
        target_module: str,
        evidence_kinds: Iterable[str],
        artifact_paths: dict[str, str],
    ) -> bool:
        """True if no task in the set uses target_module as a 'test' artifact.

        A task conflicts with the proposal if:
          - "test" is in evidence_kinds, AND
          - any task in this set has input_artifact == target_module
            OR any task's input_artifact appears in artifact_paths["test"].
        """
        if "test" not in evidence_kinds:
            return True
        test_paths = {artifact_paths.get("test", "")}
        for t in self.tasks:
            if t.input_artifact == target_module:
                return False
            if t.input_artifact in test_paths:
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tasks": [t.to_dict() for t in self.tasks],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ValidationSet:
        tasks = [ValidationTask(**t) for t in payload.get("tasks", [])]
        return cls(
            tasks=tasks, schema_version=payload.get("schema_version", VALIDATION_SET_SCHEMA_VERSION)
        )

    def save(self, path: Path | str) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    @classmethod
    def load(cls, path: Path | str) -> ValidationSet:
        p = Path(path)
        payload = json.loads(p.read_text(encoding="utf-8"))
        return cls.from_dict(payload)


# ---------------------------------------------------------------------------
# Module replacement proposal (R4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModuleReplacementProposal:
    """Proposal to replace a single module under MM-ARP gate (R4)."""

    target_module: str
    replacement_diff: str
    rationale: str
    evidence_kinds: tuple[str, ...]
    artifact_paths: dict[str, str]
    expected_impact: float
    risk: float
    confidence: float
    proposed_by: str
    proposed_at: float
    iteration_id: int

    def __post_init__(self) -> None:
        # R7: K >= 2 distinct evidence kinds
        if len(self.evidence_kinds) < 2:
            raise ValueError(f"need >= 2 evidence_kinds (got {len(self.evidence_kinds)})")
        kinds_set = set(self.evidence_kinds)
        if len(kinds_set) != len(self.evidence_kinds):
            raise ValueError("evidence_kinds must be distinct")
        for k in self.evidence_kinds:
            if k not in EVIDENCE_KINDS:
                raise ValueError(f"evidence_kind {k!r} not in {sorted(EVIDENCE_KINDS)}")
        if not 0.0 <= self.expected_impact <= 1.0:
            raise ValueError("expected_impact must be in [0, 1]")
        if not 0.0 <= self.risk <= 1.0:
            raise ValueError("risk must be in [0, 1]")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        if not self.target_module:
            raise ValueError("target_module must be non-empty")
        if not self.rationale:
            raise ValueError("rationale must be non-empty")
        if not self.proposed_by:
            raise ValueError("proposed_by must be non-empty")
        # D3: cap on diff size (no header lines, no blanks)
        body_lines = [
            ln
            for ln in self.replacement_diff.splitlines()
            if ln.strip()
            and not ln.startswith("---")
            and not ln.startswith("+++")
            and not ln.startswith("diff --git")
            and not ln.startswith("index ")
            and not ln.startswith("@@")
        ]
        if len(body_lines) > MAX_DIFF_LINES:
            raise ValueError(
                f"replacement_diff has {len(body_lines)} body lines; " f"max is {MAX_DIFF_LINES}"
            )
        # R-prohibition: hard wall
        _assert_path_not_prohibited(self.target_module)

    def effective_min_evidence_kinds(
        self,
        omega: float,
        consecutive_failures: int,
    ) -> int:
        """Return the effective K for this proposal.

        Base 2 (MM-ARP); +1 if Ω is low; +1 if failures are recurring.
        """
        base = 2
        extra = 0
        if omega < OMEGA_LOW_FOR_EXTRA_K:
            extra += 1
        if consecutive_failures >= CONSECUTIVE_FAILURES_FOR_EXTRA_K:
            extra += 1
        return base + extra

    def passes_k_gate(
        self,
        omega: float,
        consecutive_failures: int,
    ) -> bool:
        """True iff the proposal has enough distinct evidence kinds."""
        required = self.effective_min_evidence_kinds(
            omega,
            consecutive_failures,
        )
        return len(set(self.evidence_kinds)) >= required

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_module": self.target_module,
            "rationale": self.rationale,
            "evidence_kinds": list(self.evidence_kinds),
            "artifact_paths": dict(self.artifact_paths),
            "expected_impact": self.expected_impact,
            "risk": self.risk,
            "confidence": self.confidence,
            "proposed_by": self.proposed_by,
            "proposed_at": self.proposed_at,
            "iteration_id": self.iteration_id,
        }


# ---------------------------------------------------------------------------
# Fallback (R5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FallbackEntry:
    """A module retrogressed to fallback after partial success (R5)."""

    module: str
    task_type: str
    failure_mode: str
    partial_success_conditions: tuple[str, ...]
    residual_confidence: float
    registered_at: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.residual_confidence <= 1.0:
            raise ValueError("residual_confidence must be in [0, 1]")


@dataclass
class FallbackRegistry:
    """Registry of modules retrogressed to fallback (R5)."""

    entries: list[FallbackEntry] = field(default_factory=list)

    def register(
        self,
        module: str,
        task_type: str,
        failure_mode: str,
        partial_success_conditions: Iterable[str],
        residual_confidence: float,
    ) -> FallbackEntry:
        e = FallbackEntry(
            module=module,
            task_type=task_type,
            failure_mode=failure_mode,
            partial_success_conditions=tuple(partial_success_conditions),
            residual_confidence=float(residual_confidence),
            registered_at=time.time(),
        )
        self.entries.append(e)
        return e


# ---------------------------------------------------------------------------
# Orchestrator (R1, R2, R3, R5, R6, R7, R8, R9, R10)
# ---------------------------------------------------------------------------


@dataclass
class LoopIteration:
    """Record of one loop iteration."""

    iteration_id: int
    strategy: str
    central_target: str | None = None
    redirected_from: str | None = None
    redirected_to: str | None = None
    targeted_fracture: str | None = None
    proposal: ModuleReplacementProposal | None = None
    proposal_admitted: bool = False
    fallback_registered: bool = False
    fallback_discarded: bool = False
    reputation_updates: int = 0
    notes: dict[str, Any] = field(default_factory=dict)


@dataclass
class LoopResult:
    """Result of a complete loop run."""

    iterations: list[LoopIteration] = field(default_factory=list)
    stop_reason: StopReason | None = None
    started_at: float = 0.0
    finished_at: float = 0.0

    @property
    def iterations_run(self) -> int:
        return len(self.iterations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "iterations": [it.notes for it in self.iterations],
            "stop_reason": self.stop_reason.value if self.stop_reason else None,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


def _read_validation_set(path: Path | None) -> ValidationSet | None:
    """Load a validation set from disk; return None if path is None."""
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        return None
    return ValidationSet.load(p)


def _detect_human_abort(worktree: Path | None, sentinel_name: str = "STOP") -> bool:
    """True if the human-abort sentinel file is present in the worktree."""
    if worktree is None or not sentinel_name:
        return False
    return (Path(worktree) / sentinel_name).exists()


def _score_proposal_against_validation(
    proposal: ModuleReplacementProposal,
    validation: ValidationSet | None,
) -> float:
    """Placeholder scorer. Returns proposal.confidence if no validation set.

    In a wired-up system this would actually run the proposal's
    replacement_diff against each task in the validation set and
    measure ``metric`` in ``metric_direction``. The loop is shipped
    with the schema and the gate; the executor is deliberately a
    thin stub so the test suite focuses on the *gate* semantics,
    not on the executor.
    """
    if validation is None:
        return proposal.confidence
    # Without a real executor, we cannot run tasks; the stub returns
    # the proposal's self-reported confidence.
    return proposal.confidence


def evaluate_fallback_eligibility(
    *,
    module: str,
    task_type: str,
    failure_mode: str,
    partial_success_conditions: Iterable[str],
    residual_confidence: float,
    validation: ValidationSet | None,
) -> tuple[bool, FallbackEntry | None, float]:
    """Decide whether a defeated module becomes fallback or is discarded.

    Returns ``(eligible, entry_or_None, measured_score)``.

    R5 operationalised: the threshold is measured on the validation
    set, not on the training set. With no validation set, the
    module is *not* auto-registered — it requires a human to opt in.
    """
    score = residual_confidence
    if validation is not None:
        # In a wired-up system, partial_success_conditions would be
        # matched against validation tasks of the same task_type.
        # The stub below applies a flat penalty so that the
        # threshold matters even without a real executor.
        score = max(0.0, residual_confidence - 0.05)
    if validation is None:
        return False, None, score
    if score >= FALLBACK_RESIDUAL_CONFIDENCE_MIN:
        registry = FallbackRegistry()
        entry = registry.register(
            module=module,
            task_type=task_type,
            failure_mode=failure_mode,
            partial_success_conditions=partial_success_conditions,
            residual_confidence=score,
        )
        return True, entry, score
    return False, None, score


def effective_min_evidence_kinds_for(
    omega: float,
    consecutive_failures: int,
) -> int:
    """Effective K for the current loop state."""
    base = 2
    extra = 0
    if omega < OMEGA_LOW_FOR_EXTRA_K:
        extra += 1
    if consecutive_failures >= CONSECUTIVE_FAILURES_FOR_EXTRA_K:
        extra += 1
    return base + extra


@dataclass
class AACMLoop:
    """Self-improvement loop orchestrator (T-AACM-LOOP_SPEC §2-§8)."""

    worktree: Path | None = None
    validation_set_path: Path | None = None
    checkpoint_path: Path | None = None
    max_iterations: int = MAX_ITERATIONS
    max_wall_clock_s: float = MAX_WALL_CLOCK_S
    auto_infra_interval: int = AUTO_INFRA_INTERVAL
    reputation: ReputationRegistry = field(default_factory=ReputationRegistry)
    omega: float = 0.6  # default; in production this comes from controller
    consecutive_failures: int = 0
    recent_validation_scores: list[float] = field(default_factory=list)
    recent_admitted: list[bool] = field(default_factory=list)
    human_abort_sentinel: str = "STOP"

    def __post_init__(self) -> None:
        if self.omega < 0.0:
            raise ValueError("omega must be >= 0")
        # Hard floor: OMEGA_MIN, like the existing controller.
        if self.omega < OMEGA_MIN:
            raise InvariantViolation(f"loop omega={self.omega} < OMEGA_MIN={OMEGA_MIN}")

    # -- main entry point --
    def run(
        self,
        diagnose_fn: DiagnoseFn | None = None,
        propose_fn: ProposeFn | None = None,
        executor: ExecutorFn | None = None,
    ) -> LoopResult:
        """Run the loop until a StopReason fires.

        ``diagnose_fn(context) -> LoopIteration`` builds the
        iteration's strategic frame. ``propose_fn(iteration,
        context) -> ModuleReplacementProposal | None`` produces the
        candidate proposal. ``executor(proposal, validation) ->
        float`` runs the proposal and returns a measured score in
        [0, 1].

        All three are injectable so tests can drive the loop with
        stubs and so the production wiring can plug in real
        diagnose/propose/execute implementations without changing
        the orchestrator.

        If ``executor`` is None and a ``worktree`` is configured, a
        :class:`WorktreeExecutor` is built automatically. If no
        worktree is configured, the legacy stub
        ``_score_proposal_against_validation`` is used (returns
        ``proposal.confidence``).
        """
        if diagnose_fn is None:
            diagnose_fn = self._default_diagnose
        if propose_fn is None:
            propose_fn = self._default_propose
        if executor is None:
            if self.worktree is not None:
                from .executor import build_executor_from_loop

                wt_exec = build_executor_from_loop(self.worktree)
                if wt_exec is not None:

                    def _executor(
                        proposal: ModuleReplacementProposal,
                        validation: ValidationSet | None,
                    ) -> float | None:
                        return wt_exec.run(proposal, validation).score

                    executor = _executor
            if executor is None:
                executor = _score_proposal_against_validation

        result = LoopResult(started_at=time.time())
        validation = _read_validation_set(self.validation_set_path)

        for it_id in range(1, self.max_iterations + 1):
            # Human abort sentinel
            if _detect_human_abort(self.worktree, self.human_abort_sentinel):
                result.stop_reason = StopReason.HUMAN_ABORT
                break

            # Wall clock
            if time.time() - result.started_at > self.max_wall_clock_s:
                result.stop_reason = StopReason.WALL_CLOCK_EXHAUSTED
                break

            # R9+R10: omega check
            if self.omega < OMEGA_MIN:
                result.stop_reason = StopReason.OMEGA_COLLAPSE
                break

            ctx = {
                "iteration_id": it_id,
                "omega": self.omega,
                "consecutive_failures": self.consecutive_failures,
                "reputation_entries": len(self.reputation.entries),
            }
            iteration = diagnose_fn(ctx)
            if iteration is None:
                # diagnose chose to skip this iteration
                result.iterations.append(
                    LoopIteration(
                        iteration_id=it_id,
                        strategy="skip",
                    )
                )
                continue

            # D2: auto-skip when the candidate strategy has a
            # settled-low reputation. We only skip if there are
            # entries for THIS (strategy, context) tuple (i.e. the
            # strategy has been tried at least once *in this
            # context*) AND the decayed score is below threshold.
            # A brand-new strategy, or one without entries for the
            # current context, is allowed to try.
            strat = iteration.strategy
            ctx_key = f"omega={self.omega:.2f}"
            has_entries_for_ctx = any(
                e.strategy == strat and e.context == ctx_key for e in self.reputation.entries
            )
            if has_entries_for_ctx:
                rep_score = self.reputation.effective_score(strat, ctx_key)
                if rep_score < REPUTATION_LOW_THRESHOLD:
                    iteration.notes["low_reputation_skip"] = True
                    iteration.notes["reputation_score"] = rep_score
                    result.iterations.append(iteration)
                    continue

            proposal = propose_fn(iteration, ctx)
            iteration.proposal = proposal

            if proposal is not None:
                # _assert_path_not_prohibited was already called in
                # __post_init__. If we got here, path is allowed.
                # But we still check that the evidence gate is met.
                admitted = proposal.passes_k_gate(
                    self.omega,
                    self.consecutive_failures,
                )
                # Validation set disjoint check
                if admitted and validation is not None:
                    admitted = validation.disjoint_from_proposal(
                        proposal.target_module,
                        proposal.evidence_kinds,
                        proposal.artifact_paths,
                    )
                iteration.proposal_admitted = admitted

                if admitted:
                    score = executor(proposal, validation)
                    if score is None:
                        # Executor returned inconclusive (e.g. no
                        # relevant validation tasks). Skip the
                        # iteration: do not count as success or
                        # failure, do not record reputation.
                        iteration.notes["executor_skip"] = True
                    else:
                        self.recent_validation_scores.append(score)
                        if score < 0.4:
                            # R5: failed on validation, evaluate fallback
                            eligible, entry, _ = evaluate_fallback_eligibility(
                                module=proposal.target_module,
                                task_type="module_replacement",
                                failure_mode="validation_below_threshold",
                                partial_success_conditions=("score>0",),
                                residual_confidence=score,
                                validation=validation,
                            )
                            if eligible:
                                iteration.fallback_registered = True
                            else:
                                iteration.fallback_discarded = True
                            self.consecutive_failures += 1
                        else:
                            self.consecutive_failures = 0
                        self.reputation.record(
                            strategy="module_replace",
                            context=f"omega={self.omega:.2f}",
                            outcome="success" if score >= 0.4 else "partial",
                            confidence=score,
                        )
                        iteration.reputation_updates += 1
                else:
                    self.reputation.record(
                        strategy="module_replace",
                        context=f"omega={self.omega:.2f}",
                        outcome="failure",
                        confidence=0.0,
                    )
                    iteration.reputation_updates += 1
                    self.consecutive_failures += 1
            else:
                # No proposal this iteration: not a failure, not a success
                pass

            self.recent_admitted.append(iteration.proposal_admitted)
            result.iterations.append(iteration)

            # R8: every N iterations, refresh infrastructure
            if it_id % self.auto_infra_interval == 0:
                self._refresh_infrastructure()

            # Convergence: last N iterations all empty-admitted
            if len(self.recent_admitted) >= CONVERGENCE_WINDOW:
                admitted_tail = self.recent_admitted[-CONVERGENCE_WINDOW:]
                if all(admitted is False for admitted in admitted_tail):
                    result.stop_reason = StopReason.CONVERGED
                    break

            # Validation overfit detection (checked BEFORE pruning
            # reputation, so a fresh loop can trip overfit on its
            # first 3 admitted iterations).
            if len(self.recent_validation_scores) >= VALIDATION_OVERFIT_STREAK:
                score_tail = self.recent_validation_scores[-VALIDATION_OVERFIT_STREAK:]
                if all(
                    score >= VALIDATION_OVERFIT_THRESHOLD for score in score_tail
                ) and score_tail == sorted(score_tail):
                    result.stop_reason = StopReason.VALIDATION_OVERFIT_DETECTED
                    break

            # Reputation drift: too few entries left after pruning.
            # Only check after the loop has had a chance to build up
            # reputation — otherwise the first iteration with no
            # proposal-admission would trip the drift alarm and mask
            # other stop reasons.
            if it_id >= 3:
                self.reputation._prune(time.time())
                if len(self.reputation.entries) < 3:
                    result.stop_reason = StopReason.REPUTATION_DRIFT
                    break
        else:
            result.stop_reason = StopReason.BUDGET_EXHAUSTED

        result.finished_at = time.time()
        return result

    # -- stubs: the loop ships with defaults so it's importable --
    def _default_diagnose(self, context: LoopContext) -> LoopIteration:
        return LoopIteration(
            iteration_id=int(context["iteration_id"]),
            strategy="default",
        )

    def _default_propose(
        self,
        iteration: LoopIteration,
        context: LoopContext,
    ) -> ModuleReplacementProposal | None:
        return None

    def _refresh_infrastructure(self) -> None:
        """R8: compact reputation, write checkpoint, re-validate Ω."""
        # Compact reputation
        self.reputation._prune(time.time())
        # Re-check Ω
        if self.omega < OMEGA_MIN:
            raise InvariantViolation(f"refresh_infrastructure: omega={self.omega} < OMEGA_MIN")
        # Write checkpoint if path is set
        if self.checkpoint_path is not None:
            self.write_checkpoint(self.checkpoint_path)

    # -- checkpoint (L6) --
    def write_checkpoint(self, path: Path | str) -> Path:
        """Persist loop state to ``path`` (JSON, atomic)."""
        from .checkpoint import write_checkpoint as _wc

        payload = {
            "schema_version": LOOP_CHECKPOINT_SCHEMA_VERSION,
            "agent_id": "aacm_loop",
            "session_id": str(uuid.uuid4()),
            "step": len(self.recent_admitted),
            "created_at": time.time(),
            "omega": self.omega,
            "consecutive_failures": self.consecutive_failures,
            "reputation": self.reputation.to_dict(),
            "recent_admitted": list(self.recent_admitted),
            "recent_validation_scores": list(self.recent_validation_scores),
        }
        return _wc(path, payload)

    @classmethod
    def from_checkpoint(
        cls,
        path: Path | str,
        **kwargs: Any,
    ) -> AACMLoop:
        """Resume a loop from a checkpoint payload."""
        from .checkpoint import load_checkpoint as _lc

        payload = _lc(path)
        # Accept both loop schema and base schema; base schema lacks
        # loop-specific fields, so default them.
        omega = float(payload.get("omega", 0.6))
        if omega < OMEGA_MIN:
            raise InvariantViolation(f"resume: checkpoint omega={omega} < OMEGA_MIN={OMEGA_MIN}")
        loop = cls(omega=omega, **kwargs)
        loop.consecutive_failures = int(payload.get("consecutive_failures", 0))
        rep = payload.get("reputation", {})
        if isinstance(rep, dict):
            loop.reputation = ReputationRegistry.from_dict(rep)
        loop.recent_admitted = list(payload.get("recent_admitted", []))
        loop.recent_validation_scores = list(payload.get("recent_validation_scores", []))
        return loop
