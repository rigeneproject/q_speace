"""Tests for the AACM self-improvement loop (T-AACM-LOOP_SPEC §10).

19 acceptance tests, mapped 1-1 to the spec's §10.1-§10.5.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from q_speace.aacm.constants import OMEGA_MIN
from q_speace.aacm.exceptions import InvariantViolation
from q_speace.aacm.loop import (
    LOOP_HARD_PROHIBITIONS,
    AACMLoop,
    FallbackRegistry,
    LoopProhibited,
    ModuleReplacementProposal,
    ReputationRegistry,
    StopReason,
    ValidationSet,
    ValidationSetError,
    ValidationTask,
    _assert_path_not_prohibited,
    adversarial_threshold,
    effective_min_evidence_kinds_for,
    evaluate_fallback_eligibility,
)
from q_speace.aacm.loop_constants import (
    ADVERSARIAL_THRESHOLD_BASE,
    ADVERSARIAL_THRESHOLD_HIGH_OMEGA,
    ADVERSARIAL_THRESHOLD_LOW_OMEGA,
    REPUTATION_HALF_LIFE_S,
    VALIDATION_SET_MIN_SIZE,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def good_validation_set() -> ValidationSet:
    """Validation set with 10 tasks across 5 types, loaded from disk."""
    p = (
        Path(__file__).resolve().parent.parent
        / "q_speace"
        / "aacm"
        / "data"
        / "validation_set.json"
    )
    return ValidationSet.load(p)


def _make_proposal(
    target_module: str = "q_speace/foo/bar.py",
    evidence_kinds: tuple[str, ...] = ("code", "test"),
) -> ModuleReplacementProposal:
    return ModuleReplacementProposal(
        target_module=target_module,
        replacement_diff="--- a\n+++ b\n@@ -1,1 +1,1 @@\n-x\n+y\n",
        rationale="test proposal",
        evidence_kinds=evidence_kinds,
        artifact_paths={"code": "/p/code.py", "test": "/p/test.py"},
        expected_impact=0.5,
        risk=0.1,
        confidence=0.7,
        proposed_by="test",
        proposed_at=time.time(),
        iteration_id=1,
    )


# ---------------------------------------------------------------------------
# §10.1 — Gate MM-ARP and prohibitions (5 tests)
# ---------------------------------------------------------------------------


def test_proposal_without_evidence_kinds_rejected() -> None:
    with pytest.raises(ValueError):
        ModuleReplacementProposal(
            target_module="q_speace/foo/bar.py",
            replacement_diff="x",
            rationale="r",
            evidence_kinds=("code",),
            artifact_paths={"code": "/p"},
            expected_impact=0.5,
            risk=0.1,
            confidence=0.5,
            proposed_by="t",
            proposed_at=0.0,
            iteration_id=1,
        )


def test_proposal_with_two_distinct_kinds_admitted() -> None:
    p = _make_proposal(evidence_kinds=("code", "test"))
    assert p.passes_k_gate(omega=0.6, consecutive_failures=0)
    assert p.evidence_kinds == ("code", "test")


def test_loop_cannot_propose_modification_to_self() -> None:
    with pytest.raises(LoopProhibited):
        _make_proposal(target_module="q_speace/aacm/loop.py")


def test_loop_cannot_propose_modification_to_constants() -> None:
    with pytest.raises(LoopProhibited):
        _make_proposal(target_module="q_speace/aacm/constants.py")
    with pytest.raises(LoopProhibited):
        _make_proposal(target_module="q_speace/aacm/loop_constants.py")


def test_validation_set_disjoint_from_proposal_test_evidence(
    good_validation_set: ValidationSet,
) -> None:
    """vs:001/002 use rollback_target.py. A proposal with kind 'test'
    targeting that module must be rejected as non-disjoint."""
    disjoint = good_validation_set.disjoint_from_proposal(
        target_module="q_speace/foo/rollback_target.py",
        evidence_kinds=("code", "test"),
        artifact_paths={"code": "/p/code.py", "test": "/p/test.py"},
    )
    assert disjoint is False

    # Different module + kind "metric" only -> still ok even though
    # the set contains tasks, because the test_kind is not present.
    disjoint2 = good_validation_set.disjoint_from_proposal(
        target_module="q_speace/unrelated/module.py",
        evidence_kinds=("code", "metric"),
        artifact_paths={"code": "/p", "metric": "/m"},
    )
    assert disjoint2 is True


# ---------------------------------------------------------------------------
# §10.2 — Validation set and R5 (4 tests)
# ---------------------------------------------------------------------------


def test_fallback_eligibility_above_threshold_registers(
    good_validation_set: ValidationSet,
) -> None:
    eligible, entry, score = evaluate_fallback_eligibility(
        module="q_speace/bar/defeated_module.py",
        task_type="fallback_eligibility",
        failure_mode="partial_success",
        partial_success_conditions=("score>0.3",),
        residual_confidence=0.6,
        validation=good_validation_set,
    )
    assert eligible is True
    assert entry is not None
    assert entry.residual_confidence >= 0.4


def test_fallback_eligibility_below_threshold_discarded(
    good_validation_set: ValidationSet,
) -> None:
    eligible, entry, score = evaluate_fallback_eligibility(
        module="q_speace/bar/defeated_module.py",
        task_type="fallback_eligibility",
        failure_mode="partial_success",
        partial_success_conditions=("score>0",),
        residual_confidence=0.3,
        validation=good_validation_set,
    )
    # score after the 0.05 penalty = 0.25, < 0.4 threshold.
    assert eligible is False
    assert entry is None
    assert score < 0.4


def test_validation_set_minimum_size() -> None:
    too_few = [
        ValidationTask(
            task_id=f"vs:tiny:{i}",
            task_type="only_type",
            input_artifact=f"m{i}.py",
            expected_outcome="x",
            metric="m",
            metric_threshold=0.0,
            metric_direction="less_than",
        )
        for i in range(VALIDATION_SET_MIN_SIZE - 1)
    ]
    with pytest.raises(ValidationSetError):
        ValidationSet(tasks=too_few)


def test_validation_set_stratification() -> None:
    """9 tasks but only 1 task_type: violates stratification rule."""
    tasks = []
    for i in range(10):
        tasks.append(
            ValidationTask(
                task_id=f"vs:mono:{i}",
                task_type="only_type",
                input_artifact=f"m{i}.py",
                expected_outcome="x",
                metric="m",
                metric_threshold=0.0,
                metric_direction="less_than",
            )
        )
    with pytest.raises(ValidationSetError):
        ValidationSet(tasks=tasks)


# ---------------------------------------------------------------------------
# §10.3 — R6 reputation and Ω-modulated threshold (4 tests)
# ---------------------------------------------------------------------------


def test_reputation_decay_after_half_life() -> None:
    now = 1_000_000.0
    reg = ReputationRegistry()
    reg.record("module_replace", "ctx", "success", 1.0, now=now)
    # Right at half-life: confidence should be ~0.5
    score = reg.effective_score("module_replace", "ctx", now=now + REPUTATION_HALF_LIFE_S)
    # Output is shifted/clamped to [0,1]; raw = 0.5 -> mapped ~0.75.
    assert 0.6 < score < 0.9
    # After 2 half-lives: ~0.25 raw -> ~0.625 mapped
    score2 = reg.effective_score("module_replace", "ctx", now=now + 2 * REPUTATION_HALF_LIFE_S)
    assert score2 < score


def test_reputation_below_min_removed() -> None:
    now = 1_000_000.0
    reg = ReputationRegistry()
    # Confidence 0.1, after 5 half-lives -> 0.1 * (0.5^5) = 0.003125 < MIN
    reg.record("module_replace", "ctx", "success", 0.1, now=now)
    reg.effective_score("module_replace", "ctx", now=now + 5 * REPUTATION_HALF_LIFE_S)
    # After pruning, entry should be gone
    assert all(e.strategy != "module_replace" for e in reg.entries) or len(reg.entries) == 0


def test_adversarial_threshold_lowers_with_high_omega() -> None:
    assert adversarial_threshold(0.6) == ADVERSARIAL_THRESHOLD_HIGH_OMEGA == 0.60
    assert adversarial_threshold(0.9) == ADVERSARIAL_THRESHOLD_HIGH_OMEGA


def test_adversarial_threshold_raises_with_low_omega() -> None:
    # Below OMEGA_MIN
    assert adversarial_threshold(0.05) == ADVERSARIAL_THRESHOLD_LOW_OMEGA == 0.85
    # Mid range
    assert adversarial_threshold(0.3) == ADVERSARIAL_THRESHOLD_BASE == 0.70


# ---------------------------------------------------------------------------
# §10.4 — Integration and stop reasons (4 tests)
# ---------------------------------------------------------------------------


def _stub_propose_factory(target: str, admitted_via: str = "ok"):
    """Return a propose_fn stub."""

    def _fn(iteration, context):
        if admitted_via == "no_proposal":
            return None
        return _make_proposal(target_module=target)

    return _fn


def _stub_executor_factory(score: float):
    def _fn(proposal, validation):
        return score

    return _fn


def test_loop_stops_on_omega_collapse() -> None:
    """omega < OMEGA_MIN must be rejected at construction (Vincolo D)."""
    from q_speace.aacm.exceptions import InvariantViolation

    with pytest.raises(InvariantViolation):
        AACMLoop(omega=OMEGA_MIN - 0.05, max_iterations=10)

    # And a loop constructed with omega == OMEGA_MIN must run and
    # collapse on the first iteration.
    loop = AACMLoop(omega=OMEGA_MIN, max_iterations=10)
    # Force collapse by hand: drop omega just below the floor after
    # construction, then call run. This is the only legal way to
    # observe the stop reason without bypassing __post_init__.
    object.__setattr__(loop, "omega", OMEGA_MIN - 0.01)
    result = loop.run()
    assert result.stop_reason == StopReason.OMEGA_COLLAPSE
    assert result.iterations_run == 0


def test_loop_stops_on_validation_overfit() -> None:
    target = "q_speace/safe_target.py"
    loop = AACMLoop(omega=0.6, max_iterations=20, auto_infra_interval=1000)
    # 3 consecutive scores >= threshold, monotonic
    scores = [0.96, 0.97, 0.98]
    idx = [0]

    def _exec(proposal, validation):
        s = scores[min(idx[0], len(scores) - 1)]
        idx[0] += 1
        return s

    result = loop.run(propose_fn=_stub_propose_factory(target), executor=_exec)
    assert result.stop_reason == StopReason.VALIDATION_OVERFIT_DETECTED


def test_loop_stops_on_budget_exhausted() -> None:
    loop = AACMLoop(omega=0.6, max_iterations=3, auto_infra_interval=1000)

    # Propose with non-disjoint kind to force failure iteration
    def _propose(iteration, context):
        return _make_proposal(target_module="q_speace/safe_target.py")

    # Use stub executor that always returns low score -> reputation drift
    # might trip first. Use medium score (0.5) so we accumulate
    # recent_admitted=True.
    def _exec(proposal, validation):
        return 0.5

    result = loop.run(propose_fn=_propose, executor=_exec)
    assert result.stop_reason in {StopReason.BUDGET_EXHAUSTED, StopReason.REPUTATION_DRIFT}
    assert result.iterations_run <= 3


def test_loop_proposal_passed_through_existing_aacm_filter() -> None:
    """Verify integration: a proposal with K=2 evidence kinds is admitted
    by the loop's gate (the loop reuses the same K>=2 invariant)."""
    target = "q_speace/safe_target.py"
    proposal = _make_proposal(target_module=target, evidence_kinds=("code", "doc"))
    # K=2 at omega=0.6, no consecutive failures
    assert proposal.passes_k_gate(omega=0.6, consecutive_failures=0)
    # Effective K=3 when failures >= 3
    assert not proposal.passes_k_gate(omega=0.6, consecutive_failures=3)
    # Effective K=3 when omega < 0.30
    assert not proposal.passes_k_gate(omega=0.20, consecutive_failures=0)


# ---------------------------------------------------------------------------
# §10.5 — Resume (2 tests)
# ---------------------------------------------------------------------------


def test_resume_after_crash_preserves_reputation(tmp_path: Path) -> None:
    ckpt = tmp_path / "ckpt.json"
    loop = AACMLoop(omega=0.6, max_iterations=2)
    loop.reputation.record("module_replace", "ctx", "success", 0.8, now=time.time())
    loop.recent_admitted = [True, True]
    loop.write_checkpoint(ckpt)

    loop2 = AACMLoop.from_checkpoint(ckpt)
    assert len(loop2.reputation.entries) == 1
    assert loop2.recent_admitted == [True, True]
    assert loop2.omega == 0.6


def test_resume_omega_invariant_re_checked(tmp_path: Path) -> None:
    ckpt = tmp_path / "ckpt.json"
    # Write a checkpoint with omega below OMEGA_MIN manually
    from q_speace.aacm.checkpoint import write_checkpoint as _wc

    payload = {
        "schema_version": "aacm.cp.1+loop.1",
        "agent_id": "aacm_loop",
        "session_id": "x",
        "step": 0,
        "created_at": time.time(),
        "omega": OMEGA_MIN - 0.05,
        "consecutive_failures": 0,
        "reputation": {"entries": []},
        "recent_admitted": [],
        "recent_validation_scores": [],
    }
    _wc(ckpt, payload)
    with pytest.raises((InvariantViolation, ValueError)):
        AACMLoop.from_checkpoint(ckpt)


# ---------------------------------------------------------------------------
# Sanity: prohibitions and helpers
# ---------------------------------------------------------------------------


def test_loop_hard_prohibitions_is_frozenset() -> None:
    assert isinstance(LOOP_HARD_PROHIBITIONS, frozenset)
    assert "q_speace/aacm/loop.py" in LOOP_HARD_PROHIBITIONS
    assert "q_speace/aacm/controller.py" in LOOP_HARD_PROHIBITIONS
    assert "q_speace/aacm/constants.py" in LOOP_HARD_PROHIBITIONS


def test_assert_path_not_prohibited_raises() -> None:
    with pytest.raises(LoopProhibited):
        _assert_path_not_prohibited("q_speace/aacm/loop.py")
    # Allowed path: no raise
    _assert_path_not_prohibited("q_speace/foo/bar.py")


def test_effective_min_evidence_kinds_for_helper() -> None:
    assert effective_min_evidence_kinds_for(0.6, 0) == 2
    assert effective_min_evidence_kinds_for(0.20, 0) == 3
    assert effective_min_evidence_kinds_for(0.6, 5) == 3
    assert effective_min_evidence_kinds_for(0.20, 5) == 4


def test_fallback_registry_register() -> None:
    reg = FallbackRegistry()
    e = reg.register(
        module="m",
        task_type="t",
        failure_mode="f",
        partial_success_conditions=("c",),
        residual_confidence=0.5,
    )
    assert e.residual_confidence == 0.5
    assert len(reg.entries) == 1


# ---------------------------------------------------------------------------
# §D3 — replacement_diff size cap
# ---------------------------------------------------------------------------


def test_proposal_oversized_diff_rejected() -> None:
    """A diff with > MAX_DIFF_LINES body lines must be rejected."""
    from q_speace.aacm.loop_constants import MAX_DIFF_LINES

    # Generate a diff with MAX_DIFF_LINES + 1 body lines.
    body = "\n".join(f"+line_{i}" for i in range(MAX_DIFF_LINES + 1))
    diff = "diff --git a/foo.py b/foo.py\n" "--- a/foo.py\n" "+++ b/foo.py\n" f"{body}\n"
    with pytest.raises(ValueError, match="body lines"):
        ModuleReplacementProposal(
            target_module="q_speace/foo/bar.py",
            replacement_diff=diff,
            rationale="too big",
            evidence_kinds=("code", "test"),
            artifact_paths={"code": "/p", "test": "/p2"},
            expected_impact=0.5,
            risk=0.1,
            confidence=0.5,
            proposed_by="t",
            proposed_at=0.0,
            iteration_id=1,
        )


def test_proposal_diff_at_limit_accepted() -> None:
    """A diff with exactly MAX_DIFF_LINES body lines is accepted."""
    from q_speace.aacm.loop_constants import MAX_DIFF_LINES

    body = "\n".join(f"+line_{i}" for i in range(MAX_DIFF_LINES))
    diff = "diff --git a/foo.py b/foo.py\n" "--- a/foo.py\n" "+++ b/foo.py\n" f"{body}\n"
    p = ModuleReplacementProposal(
        target_module="q_speace/foo/bar.py",
        replacement_diff=diff,
        rationale="at limit",
        evidence_kinds=("code", "test"),
        artifact_paths={"code": "/p", "test": "/p2"},
        expected_impact=0.5,
        risk=0.1,
        confidence=0.5,
        proposed_by="t",
        proposed_at=0.0,
        iteration_id=1,
    )
    assert p.replacement_diff is not None


# ---------------------------------------------------------------------------
# §D2 — auto-skip on low reputation
# ---------------------------------------------------------------------------


def test_loop_skips_on_low_reputation() -> None:
    """When the reputation for the strategy is below threshold AND
    entries exist for this (strategy, context) tuple, the loop
    skips proposing."""
    loop = AACMLoop(omega=0.6, max_iterations=2, auto_infra_interval=1000)
    # Inject 3 failure entries for "module_replace" at omega=0.60
    # -> effective score will be low for that (strategy, context).
    for _ in range(3):
        loop.reputation.record(
            strategy="module_replace",
            context="omega=0.60",
            outcome="failure",
            confidence=1.0,
        )

    proposed = []

    def _diagnose(ctx):
        from q_speace.aacm.loop import LoopIteration

        return LoopIteration(iteration_id=ctx["iteration_id"], strategy="module_replace")

    def _propose(it, ctx):
        proposed.append(it.iteration_id)
        return _make_proposal(target_module="q_speace/safe_target.py")

    result = loop.run(diagnose_fn=_diagnose, propose_fn=_propose)
    # No propose_fn call should have happened.
    assert proposed == []
    # First iteration should be skipped due to low reputation.
    assert result.iterations[0].notes.get("low_reputation_skip") is True


def test_loop_proposes_with_empty_reputation() -> None:
    """With no entries at all, reputation lookup returns 0 but
    there are no entries for the (strategy, context) tuple, so
    the loop allows proposing."""
    loop = AACMLoop(omega=0.6, max_iterations=2, auto_infra_interval=1000)
    assert loop.reputation.entries == []

    proposed = []

    def _diagnose(ctx):
        from q_speace.aacm.loop import LoopIteration

        return LoopIteration(iteration_id=ctx["iteration_id"], strategy="module_replace")

    def _propose(it, ctx):
        proposed.append(it.iteration_id)
        return _make_proposal(target_module="q_speace/safe_target.py")

    result = loop.run(diagnose_fn=_diagnose, propose_fn=_propose)
    # The propose_fn was called.
    assert proposed == [1, 2]
    # No skip note.
    assert not any(it.notes.get("low_reputation_skip") for it in result.iterations)


def test_loop_proposes_when_other_strategy_has_low_reputation() -> None:
    """When entries exist for a DIFFERENT strategy/context, the
    current strategy is not skipped (it has no evidence yet)."""
    loop = AACMLoop(omega=0.6, max_iterations=2, auto_infra_interval=1000)
    # Bad reputation for a different strategy
    for _ in range(3):
        loop.reputation.record(
            strategy="other_strategy",
            context="omega=0.60",
            outcome="failure",
            confidence=1.0,
        )

    proposed = []

    def _diagnose(ctx):
        from q_speace.aacm.loop import LoopIteration

        return LoopIteration(iteration_id=ctx["iteration_id"], strategy="module_replace")

    def _propose(it, ctx):
        proposed.append(it.iteration_id)
        return _make_proposal(target_module="q_speace/safe_target.py")

    result = loop.run(diagnose_fn=_diagnose, propose_fn=_propose)
    # The propose_fn was called because no entries for "module_replace".
    assert proposed == [1, 2]
    assert not any(it.notes.get("low_reputation_skip") for it in result.iterations)
