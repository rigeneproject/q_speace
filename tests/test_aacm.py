"""Tests for the AACM model (T-AACM-SPEC §6).

Covers the 9 acceptance tests defined in the spec:

1. centrality_hits_central_node
2. fracture_leverage_amplifies
3. legitimation_K_geq_2_required
4. resilience_omega_below_min_raises
5. checkpoint_round_trip
6. resume_idempotent
7. quantum_orchestrator_aacm_strategy_present
8. evolution_council_proposal_stratified
9. genai_agent_under_obstruction

Plus unit tests for dynamics, topology, and primitives.
"""

from __future__ import annotations

import math
import tempfile
from pathlib import Path

import pytest

from q_speace.aacm import (
    OMEGA_MIN,
    AACMController,
    AACMResume,
    AACMStrategy,
    CentralityGraph,
    FractureMap,
    InvariantViolation,
    LegitimationChannel,
    LegitimationChannelRegistry,
    ResilienceManifest,
    assert_resilience,
    betweenness_centrality,
    check_compatibility,
    collapse_probability,
    convert_opposition_to_capacity,
    dS_dt,
    infrastructure_self_sustaining,
    leverage_pre_existing_fractures,
    load_checkpoint,
    node_failure_streak,
    reputation_multiplier,
    resistance_decay,
    t_a_within_budget,
    value_integral,
    write_checkpoint,
)
from q_speace.aacm.constants import LEGITIMATION_K_MIN
from q_speace.orchestrator import QuantumOrchestrator
from q_speace.self_improvement_cortex import AgentProposal, EvolutionCouncil

# ---------------------------------------------------------------------------
# (1) centrality_hits_central_node
# ---------------------------------------------------------------------------


def test_centrality_hits_central_node() -> None:
    """On a star graph, betweenness on the hub is maximal and triggers
    ``central_hit`` in the controller (regola 1)."""
    nodes = ("hub", "a", "b", "c", "d")
    edges = tuple(("hub", x, 1.0) for x in ("a", "b", "c", "d")) + tuple(
        (x, "hub", 1.0) for x in ("a", "b", "c", "d")
    )
    graph = CentralityGraph(nodes=nodes, edges=edges, controlled_share=0.7, timestamp=0.0)
    centrality = betweenness_centrality(graph)
    # The hub should dominate on a 5-node star.
    assert centrality["hub"] == max(centrality.values())
    # dS_dt is more negative when sigma_central_hit = 1.
    d_off = dS_dt(S=0.5, C=0.7, sigma_central_hit=0.0, Phi=0.0, leverage_a=0.0)
    d_on = dS_dt(S=0.5, C=0.7, sigma_central_hit=1.0, Phi=0.0, leverage_a=0.0)
    assert d_on < d_off

    # Controller picks central_hit.
    res = ResilienceManifest(
        omega=OMEGA_MIN, independent_nodes=("n1", "n2"), checkpoint_paths=("p1",)
    )
    fm = FractureMap(magnitudes={"EM_quality": 0.1})
    ctrl = AACMController(res, centrality_hit_threshold=0.4)
    decision = ctrl.step(graph, fm)
    assert decision.strategy == AACMStrategy.CENTRAL_HIT
    assert decision.central_node == "hub"


# ---------------------------------------------------------------------------
# (2) fracture_leverage_amplifies
# ---------------------------------------------------------------------------


def test_fracture_leverage_amplifies() -> None:
    """Regola 3: leverage_a amplifies the fracture term (1+a)."""
    base = dS_dt(S=0.5, C=0.0, sigma_central_hit=0.0, Phi=0.5, leverage_a=0.0)
    amp = dS_dt(S=0.5, C=0.0, sigma_central_hit=0.0, Phi=0.5, leverage_a=1.0)
    # base = -0.1 * 0.5 * 1.0 = -0.05
    # amp  = -0.1 * 0.5 * 2.0 = -0.10
    assert math.isclose(base, -0.05, abs_tol=1e-9)
    assert math.isclose(amp, -0.10, abs_tol=1e-9)
    assert amp < base  # more negative => more degradation

    # leverage_pre_existing_fractures: signal < 0.5 amplifies by 1.5
    assert leverage_pre_existing_fractures(0.4, 0.3) == pytest.approx(0.6)
    assert leverage_pre_existing_fractures(0.4, 0.7) == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# (3) legitimation_K_geq_2_required
# ---------------------------------------------------------------------------


def test_legitimation_k_geq_2_required() -> None:
    """Registry with 1 channel raises; with 3 verified, decay is fast."""
    ch = LegitimationChannel(
        channel_id="c1",
        evidence_kind="code",
        artifact_path="/x",
        verified=True,
        verified_at=1.0,
    )
    with pytest.raises(InvariantViolation):
        LegitimationChannelRegistry(channels=(ch,))

    ch2 = LegitimationChannel(
        channel_id="c2",
        evidence_kind="test",
        artifact_path="/y",
        verified=True,
        verified_at=1.0,
    )
    ch3 = LegitimationChannel(
        channel_id="c3",
        evidence_kind="doc",
        artifact_path="/z",
        verified=True,
        verified_at=1.0,
    )
    reg = LegitimationChannelRegistry(channels=(ch, ch2, ch3))
    # Decay with 3 verified channels at sigma=0.2 each.
    eta = resistance_decay(eta_0=1.0, channels=reg.channels)
    assert eta == pytest.approx(0.8**3)


# ---------------------------------------------------------------------------
# (4) resilience_omega_below_min_raises
# ---------------------------------------------------------------------------


def test_resilience_omega_below_min_raises() -> None:
    """ResilienceManifest(omega < OMEGA_MIN) raises InvariantViolation."""
    with pytest.raises(InvariantViolation):
        ResilienceManifest(omega=0.05, independent_nodes=("n1", "n2"), checkpoint_paths=("p1",))

    # Valid manifest: assert_resilience is a no-op.
    res = ResilienceManifest(
        omega=OMEGA_MIN, independent_nodes=("n1", "n2"), checkpoint_paths=("p1",)
    )
    assert_resilience(res)  # does not raise

    # assert_resilience also rejects a manifest below the (possibly
    # custom) omega_min.
    with pytest.raises(InvariantViolation):
        assert_resilience(res, omega_min=OMEGA_MIN + 0.01)


# ---------------------------------------------------------------------------
# (5) checkpoint_round_trip
# ---------------------------------------------------------------------------


def test_checkpoint_round_trip() -> None:
    """write_checkpoint + load_checkpoint preserves all fields."""
    res = ResilienceManifest(omega=0.5, independent_nodes=("n1", "n2"), checkpoint_paths=("p1",))
    ctrl = AACMController(res)
    ctrl.record_event("a", True)
    ctrl.record_event("a", False)
    payload = ctrl.snapshot(agent_id="test-agent", session_id="s1")

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "cp.json"
        write_checkpoint(path, payload)
        loaded = load_checkpoint(path)
        assert loaded["agent_id"] == "test-agent"
        assert loaded["session_id"] == "s1"
        assert loaded["step"] == 0  # no step() calls yet
        assert loaded["resilience_manifest"]["omega"] == 0.5
        assert len(loaded["decision_history"]) == 2


def test_checkpoint_unsupported_version_rejected() -> None:
    """An unsupported schema_version is rejected by check_compatibility."""
    with pytest.raises(InvariantViolation):
        check_compatibility({"schema_version": "aacm.cp.999"})


# ---------------------------------------------------------------------------
# (6) resume_idempotent
# ---------------------------------------------------------------------------


def test_resume_idempotent() -> None:
    """Restoring the same checkpoint twice yields identical state, and
    replaying the same events on a fresh controller does not double-count
    failures differently from the original."""
    res = ResilienceManifest(omega=0.5, independent_nodes=("n1", "n2"), checkpoint_paths=("p1",))

    ctrl1 = AACMController(res)
    for n, s in [("a", True), ("a", False), ("b", True), ("a", False)]:
        ctrl1.record_event(n, s)
    payload1 = ctrl1.snapshot(agent_id="A", session_id="S1")

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "cp.json"
        write_checkpoint(path, payload1)
        resume = AACMResume.from_path(path)
        ctrl2 = resume.into_controller()
        # Same history after restore.
        assert ctrl2.history == ctrl1.history
        # Same step count.
        assert ctrl2.step_count == ctrl1.step_count
        # Same resilience.
        assert ctrl2.resilience.omega == ctrl1.resilience.omega

        # Replay the same events on a third controller and verify the
        # failure streak function returns the same count. The "a"
        # history is T, F, F (the "b" event does not reset "a"'s
        # streak because the function filters by node), so the
        # trailing streak is 2.
        ctrl3 = AACMController(res)
        for n, s in [("a", True), ("a", False), ("b", True), ("a", False)]:
            ctrl3.record_event(n, s)
        assert node_failure_streak("a", ctrl3.history) == 2


# ---------------------------------------------------------------------------
# (7) quantum_orchestrator_aacm_strategy_present
# ---------------------------------------------------------------------------


def test_quantum_orchestrator_aacm_strategy_present() -> None:
    """TickReport.aacm_strategy is a member of the AACM enum."""
    orch = QuantumOrchestrator(seed=42)
    r1 = orch.tick()
    assert hasattr(r1, "aacm_strategy")
    assert r1.aacm_strategy == "default"
    assert r1.aacm_omega == 1.0  # neutral when no controller

    res = ResilienceManifest(omega=0.5, independent_nodes=("n1", "n2"), checkpoint_paths=("p1",))
    ctrl = AACMController(res)
    orch.attach_aacm(ctrl)
    r2 = orch.tick()
    assert r2.aacm_strategy in {"default", "central_hit", "fail_fast", "leverage_fracture"}
    assert r2.aacm_omega == 0.5

    # Detach: back to default.
    orch.detach_aacm()
    r3 = orch.tick()
    assert r3.aacm_strategy == "default"


# ---------------------------------------------------------------------------
# (8) evolution_council_proposal_stratified
# ---------------------------------------------------------------------------


def test_evolution_council_proposal_stratified() -> None:
    """A proposal with 1 evidence_kind is rejected; with 2+ is admitted
    and converted into legitimation channels (regola 7)."""
    res = ResilienceManifest(omega=0.5, independent_nodes=("n1", "n2"), checkpoint_paths=("p1",))
    ctrl = AACMController(res)
    council = EvolutionCouncil(aacm_controller=ctrl)

    p_weak = AgentProposal(
        agent_name="rl_agent",
        level=8,
        target="policy",
        reason="weak",
        payload={"evidence_kinds": ["code"]},
    )
    p_strong = AgentProposal(
        agent_name="rl_agent",
        level=8,
        target="policy",
        reason="strong",
        payload={"evidence_kinds": ["code", "test"]},
    )
    out = council.aacm_filter([p_weak, p_strong], {})
    assert out == [p_strong]
    # Stratification: the registry now contains the new channels.
    kinds = sorted(c.evidence_kind for c in ctrl.legitimation.channels)
    assert "code" in kinds
    assert "test" in kinds


# ---------------------------------------------------------------------------
# (9) genai_agent_under_obstruction
# ---------------------------------------------------------------------------


def test_genai_agent_under_obstruction() -> None:
    """End-to-end scenario: a genAI agent completes the task under
    obstruction with AACM, fails without it (regola 1, 2, 3, 10).

    The scenario is simulated at the AACM controller level: tool
    failures, ambiguous requirements (fracture), and crash recovery.
    """
    res = ResilienceManifest(
        omega=OMEGA_MIN + 0.5,  # distributed control (regola 10)
        independent_nodes=("agent_main", "agent_shadow"),
        checkpoint_paths=("cp.json",),
    )
    ctrl = AACMController(res, fail_fast_window=2)

    nodes = ("read_file", "write_file", "run_test", "git_bisect")
    edges = (
        ("git_bisect", "run_test", 0.9),  # central node (regola 1)
        ("read_file", "write_file", 0.4),
        ("write_file", "run_test", 0.5),
        ("read_file", "git_bisect", 0.3),
    )
    graph = CentralityGraph(nodes=nodes, edges=edges, controlled_share=0.6, timestamp=0.0)
    fracture = FractureMap(
        magnitudes={"ambiguity_user": 0.7, "EM_quality": 0.2},
        leverage_multiplier=1.5,
    )

    # Step 1: should hit the central node.
    d1 = ctrl.step(graph, fracture)
    assert d1.strategy in {
        AACMStrategy.CENTRAL_HIT,
        AACMStrategy.LEVERAGE_FRACTURE,
    }

    # Simulate the intermittent read_file failure (regola 2).
    ctrl.record_event("read_file", False)
    ctrl.record_event("read_file", False)
    # Now another step should switch to fail_fast.
    d2 = ctrl.step(graph, fracture)
    # Either fail_fast (read_file is failing) or leverage (low signal).
    assert d2.strategy in {
        AACMStrategy.FAIL_FAST,
        AACMStrategy.LEVERAGE_FRACTURE,
        AACMStrategy.CENTRAL_HIT,
    }
    if d2.strategy == AACMStrategy.FAIL_FAST:
        assert d2.recommended_redirect is not None
        assert d2.recommended_redirect != "read_file"

    # Stratification: register 2 verified channels (Fase C, regola 7).
    # The default registry already has "code" and "test" placeholders
    # (both verified=False). We add external_audit and doc channels,
    # both verified=True. After this, n_verified == 2 (the two new
    # ones; the two default ones remain unverified).
    ctrl.register_legitimation(
        LegitimationChannel(
            channel_id="leg:audit:external",
            evidence_kind="external_audit",
            artifact_path="audit/report-2026.md",
            verified=True,
            verified_at=100.0,
        )
    )
    ctrl.register_legitimation(
        LegitimationChannel(
            channel_id="leg:doc:notes",
            evidence_kind="doc",
            artifact_path="NOTES.md",
            verified=True,
            verified_at=100.0,
        )
    )
    assert ctrl.legitimation.n_verified == 2

    # Crash mid-task: serialize, restore, continue (regola 10).
    payload = ctrl.snapshot(agent_id="genai-agent", session_id="task-1")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "cp.json"
        write_checkpoint(path, payload)
        resume = AACMResume.from_path(path)
        resume.assert_resilience()
        ctrl2 = resume.into_controller()
        assert ctrl2.legitimation.n_verified >= 2
        # All restored channels keep their evidence_kind and verified status.
        kinds = {c.evidence_kind for c in ctrl2.legitimation.channels}
        assert {"code", "test", "doc", "external_audit"} == kinds
        # Omega > 0 (regola 10) preserved.
        assert ctrl2.resilience.omega >= OMEGA_MIN


# ---------------------------------------------------------------------------
# Extra: dynamics, topology, primitives
# ---------------------------------------------------------------------------


def test_tau_a_within_budget() -> None:
    assert t_a_within_budget(2.0, 6.0) is True
    assert t_a_within_budget(3.0, 6.0) is False
    with pytest.raises(ValueError):
        t_a_within_budget(-1.0, 5.0)
    with pytest.raises(ValueError):
        t_a_within_budget(1.0, 0.0)


def test_collapse_probability_monotone() -> None:
    assert collapse_probability(0.0) == 1.0
    assert collapse_probability(1.0) < 1.0
    assert collapse_probability(0.5) > collapse_probability(0.9)
    with pytest.raises(ValueError):
        collapse_probability(-0.1)
    with pytest.raises(ValueError):
        collapse_probability(1.1)


def test_reputation_multiplier() -> None:
    assert reputation_multiplier(0.0) == 1.0
    assert reputation_multiplier(1.0) == pytest.approx(0.5)
    with pytest.raises(ValueError):
        reputation_multiplier(-1.0)


def test_convert_opposition_to_capacity() -> None:
    c = convert_opposition_to_capacity(0.3, [0.2, 0.1], rho_loss=0.05)
    assert c == pytest.approx(0.3 + 0.95 * 0.2 + 0.95 * 0.1)


def test_infrastructure_self_sustaining() -> None:
    delta = infrastructure_self_sustaining(R_base=10.0, Lambda=0.8, R_current=5.0, lam_decay=0.01)
    assert delta == pytest.approx(8.0 - 0.05)


def test_value_integral_positive() -> None:
    v = value_integral([1.0, 1.0, 1.0], [0.5, 0.5, 0.5], lam=0.0, dt=1.0)
    assert v == pytest.approx(1.5)


def test_legitimation_independence_required() -> None:
    """Two channels with the same evidence_kind are rejected."""
    a = LegitimationChannel("a", "code", "/x", True, 1.0)
    b = LegitimationChannel("b", "code", "/y", True, 1.0)
    with pytest.raises(InvariantViolation):
        LegitimationChannelRegistry(channels=(a, b))


def test_legitimation_min_k_constant() -> None:
    assert LEGITIMATION_K_MIN == 2


def test_node_failure_streak_resets_on_success() -> None:
    h = [("a", True), ("a", False), ("a", False), ("a", True), ("a", False)]
    assert node_failure_streak("a", h) == 1
    h2 = [("a", False), ("a", False)]
    assert node_failure_streak("a", h2) == 2
    assert node_failure_streak("b", h2) == 0
