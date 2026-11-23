"""T243: Regression & coverage tests for AACM dynamics, primitives, executor, and BrainAuditLog."""

from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from q_speace.aacm import dynamics, executor
from q_speace.aacm.exceptions import InvariantViolation
from q_speace.aacm.loop import ModuleReplacementProposal, ValidationTask
from q_speace.aacm.primitives import (
    CentralityGraph,
    FractureMap,
    LegitimationChannel,
    LegitimationChannelRegistry,
    ResilienceManifest,
)
from q_speace.bcel.catalog import BCELCatalog
from q_speace.spiking_brain.audit import BrainAuditLog, _resolve_path, make_apply_record


def test_t243_aacm_dynamics_fail_closed_and_validation_edges() -> None:
    # dS_dt invalid & NaN/Inf inputs
    with pytest.raises(ValueError, match="sigma_central_hit"):
        dynamics.dS_dt(0.5, 0.5, 0.5, 0.1, 0.1)
    with pytest.raises(ValueError, match="Phi"):
        dynamics.dS_dt(0.5, 0.5, 1.0, math.nan, 0.1)
    with pytest.raises(ValueError, match="leverage_a"):
        dynamics.dS_dt(0.5, 0.5, 1.0, 0.1, -0.1)
    with pytest.raises(ValueError, match="alpha"):
        dynamics.dS_dt(0.5, 0.5, 1.0, 0.1, 0.1, alpha=math.inf)
    with pytest.raises(ValueError, match="beta"):
        dynamics.dS_dt(0.5, 0.5, 1.0, 0.1, 0.1, beta=-0.1)
    with pytest.raises(ValueError, match="S must be in"):
        dynamics.dS_dt(True, 0.5, 1.0, 0.1, 0.1)  # bool rejected

    # t_a_within_budget, leverage_pre_existing_fractures, convert, reputation
    with pytest.raises(ValueError, match="tau_a"):
        dynamics.t_a_within_budget(math.nan, 2.0)
    with pytest.raises(ValueError, match="tau_r"):
        dynamics.t_a_within_budget(0.5, math.inf)
    with pytest.raises(ValueError, match="Phi"):
        dynamics.leverage_pre_existing_fractures(math.nan, 0.5)
    with pytest.raises(ValueError, match="current_signal_quality"):
        dynamics.leverage_pre_existing_fractures(1.0, 1.5)
    with pytest.raises(ValueError, match="rho_loss"):
        dynamics.convert_opposition_to_capacity(0.5, [0.2], rho_loss=1.2)
    with pytest.raises(ValueError, match="L must be"):
        dynamics.reputation_multiplier(math.nan)

    # resistance_decay & infrastructure_self_sustaining
    with pytest.raises(ValueError, match="eta_0"):
        dynamics.resistance_decay(math.nan, [])
    with pytest.raises(ValueError, match="sigma_per_channel"):
        dynamics.resistance_decay(1.0, [], sigma_per_channel=-0.1)
    with pytest.raises(ValueError, match="R_base"):
        dynamics.infrastructure_self_sustaining(math.nan, 0.5, 1.0)
    with pytest.raises(ValueError, match="Lambda"):
        dynamics.infrastructure_self_sustaining(1.0, 1.5, 1.0)
    with pytest.raises(ValueError, match="R_current"):
        dynamics.infrastructure_self_sustaining(1.0, 0.5, -1.0)
    with pytest.raises(ValueError, match="lam_decay"):
        dynamics.infrastructure_self_sustaining(1.0, 0.5, 1.0, lam_decay=math.nan)

    # assert_resilience NaN bypass blocked + low nodes/checkpoints
    manifest = ResilienceManifest(
        omega=0.5, independent_nodes=("n1", "n2"), checkpoint_paths=("cp1",)
    )
    with pytest.raises(ValueError, match="omega_min"):
        dynamics.assert_resilience(manifest, omega_min=math.nan)
    with pytest.raises(InvariantViolation, match="independent_nodes"):
        bad_m = object.__new__(ResilienceManifest)
        object.__setattr__(bad_m, "omega", 0.5)
        object.__setattr__(bad_m, "independent_nodes", ("n1",))
        object.__setattr__(bad_m, "checkpoint_paths", ("cp1",))
        dynamics.assert_resilience(bad_m)
    with pytest.raises(InvariantViolation, match="checkpoint_path"):
        bad_m2 = object.__new__(ResilienceManifest)
        object.__setattr__(bad_m2, "omega", 0.5)
        object.__setattr__(bad_m2, "independent_nodes", ("n1", "n2"))
        object.__setattr__(bad_m2, "checkpoint_paths", ())
        dynamics.assert_resilience(bad_m2)

    # value_integral validation & NaN rejection
    with pytest.raises(ValueError, match="equal length"):
        dynamics.value_integral([1.0], [0.5, 0.5], 0.1)
    with pytest.raises(ValueError, match="lam"):
        dynamics.value_integral([1.0], [0.5], -0.1)
    with pytest.raises(ValueError, match="dt"):
        dynamics.value_integral([1.0], [0.5], 0.1, dt=0.0)
    with pytest.raises(ValueError, match="R_series"):
        dynamics.value_integral([math.nan], [0.5], 0.1)
    with pytest.raises(ValueError, match="Lambda_series"):
        dynamics.value_integral([1.0], [1.5], 0.1)


def test_t243_aacm_primitives_fail_closed_and_to_dict() -> None:
    # CentralityGraph errors including NaN timestamp/weight
    with pytest.raises(ValueError, match="at least 1 node"):
        CentralityGraph((), (), 0.5, 0.0)
    with pytest.raises(ValueError, match="controlled_share"):
        CentralityGraph(("a",), (), math.nan, 0.0)
    with pytest.raises(ValueError, match="timestamp"):
        CentralityGraph(("a",), (), 0.5, math.nan)
    with pytest.raises(ValueError, match="edge source"):
        CentralityGraph(("a",), (("x", "a", 1.0),), 0.5, 0.0)
    with pytest.raises(ValueError, match="edge destination"):
        CentralityGraph(("a",), (("a", "y", 1.0),), 0.5, 0.0)
    with pytest.raises(ValueError, match="edge weight"):
        CentralityGraph(("a",), (("a", "a", math.nan),), 0.5, 0.0)
    g = CentralityGraph(("a", "b"), (("a", "b", 1.0),), 0.5, 10.0)
    assert g.to_dict()["nodes"] == ["a", "b"]

    # FractureMap errors & to_dict
    with pytest.raises(ValueError, match="non-empty"):
        FractureMap({})
    with pytest.raises(ValueError, match="magnitude"):
        FractureMap({"x": 1.5})
    with pytest.raises(ValueError, match="leverage_multiplier"):
        FractureMap({"x": 0.5}, leverage_multiplier=4.0)
    fm = FractureMap({"x": 0.4}, leverage_multiplier=1.5)
    assert fm.to_dict()["leverage_multiplier"] == 1.5

    # LegitimationChannel & Registry errors including NaN/negative verified_at
    with pytest.raises(ValueError, match="channel_id"):
        LegitimationChannel("", "code", "p.py", False)
    with pytest.raises(ValueError, match="evidence_kind"):
        LegitimationChannel("c1", "unknown", "p.py", False)
    with pytest.raises(ValueError, match="artifact_path"):
        LegitimationChannel("c1", "code", "", False)
    with pytest.raises(ValueError, match="verified=True"):
        LegitimationChannel("c1", "code", "p.py", True, verified_at=None)
    with pytest.raises(ValueError, match="verified_at must be finite"):
        LegitimationChannel("c1", "code", "p.py", True, verified_at=math.nan)
    with pytest.raises(ValueError, match="verified=False"):
        LegitimationChannel("c1", "code", "p.py", False, verified_at=1.0)
    ch1 = LegitimationChannel("c1", "code", "p.py", True, verified_at=1.0)
    ch2 = LegitimationChannel("c1", "test", "t.py", False)
    with pytest.raises(InvariantViolation, match="distinct channel_id"):
        LegitimationChannelRegistry((ch1, ch2))

    # ResilienceManifest errors
    with pytest.raises(ValueError, match="omega must be in"):
        ResilienceManifest(1.5, ("n1", "n2"), ("cp1",))
    with pytest.raises(InvariantViolation, match="distinct"):
        ResilienceManifest(0.5, ("n1", "n1"), ("cp1",))
    with pytest.raises(InvariantViolation, match="at least 1 checkpoint"):
        ResilienceManifest(0.5, ("n1", "n2"), ())
    with pytest.raises(InvariantViolation, match="non-empty"):
        ResilienceManifest(0.5, ("n1", "n2"), ("",))
    with pytest.raises(ValueError, match="schema_version"):
        ResilienceManifest(0.5, ("n1", "n2"), ("cp1",), schema_version="")


def test_t243_aacm_executor_path_traversal_thresholds_and_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert executor._diff_target_path("no header here", "fallback.py") == "fallback.py"
    assert executor.build_executor_from_loop(None) is None
    assert executor.build_executor_from_loop(tmp_path) is not None

    # Path traversal blocked before git apply
    wt = tmp_path / "wt"
    wt.mkdir()
    ex = executor.WorktreeExecutor(wt)
    bad_prop = ModuleReplacementProposal(
        target_module="ok.py",
        replacement_diff="--- a/ok.py\n+++ b/../../escaped.py\n@@ -1 +1 @@\n-a\n+b\n",
        rationale="test",
        evidence_kinds=("code", "test"),
        artifact_paths={"code": "ok.py", "test": "t.py"},
        expected_impact=0.2,
        risk=0.1,
        confidence=0.9,
        proposed_by="agent-test",
        proposed_at=1.0,
        iteration_id="iter-001",
    )
    res_trav = ex.run(bad_prop, validation=None)
    assert res_trav.applied is False
    assert res_trav.error is not None and "path_traversal_blocked" in res_trav.error

    # _run_git raises when git missing
    monkeypatch.setattr(shutil, "which", lambda _cmd: None)
    with pytest.raises(RuntimeError, match="git executable not found"):
        executor._run_git(wt, "status")

    # _check_threshold covers all directions + NaN
    assert executor.WorktreeExecutor._check_threshold(1.0, 2.0, "less_than") is True
    assert executor.WorktreeExecutor._check_threshold(2.0, 1.0, "greater_than") is True
    assert executor.WorktreeExecutor._check_threshold(1.0, 1.0, "equal") is True
    assert executor.WorktreeExecutor._check_threshold(1.0, 1.0, "unknown") is False
    assert executor.WorktreeExecutor._check_threshold(math.nan, 1.0, "less_than") is False

    # _measure_task fallback non-py & _measure_execution_time non-zero / timeout / exception
    txt_file = wt / "notes.txt"
    txt_file.write_text("hello", encoding="utf-8")
    t_txt = ValidationTask("t1", "smoke", "notes.txt", "ok", "size", 1.0, "greater_than")
    assert ex._measure_task(t_txt)["passed"] is True

    bad_py = wt / "fail.py"
    bad_py.write_text("import sys; sys.exit(2)\n", encoding="utf-8")
    t_py = ValidationTask("t2", "perf", "fail.py", "ok", "execution_time_s", 2.0, "less_than")
    obs_fail = ex._measure_task(t_py)
    assert obs_fail["passed"] is False and "exit 2" in obs_fail["error"]

    def _raise_timeout(*_a: Any, **_kw: Any) -> Any:
        raise subprocess.TimeoutExpired(cmd=["python"], timeout=1.0)

    monkeypatch.setattr(subprocess, "run", _raise_timeout)
    obs_to = ex._measure_execution_time(t_py, bad_py)
    assert obs_to["passed"] is False and obs_to["error"] == "timeout"

    def _raise_oserr(*_a: Any, **_kw: Any) -> Any:
        raise OSError("boom")

    monkeypatch.setattr(subprocess, "run", _raise_oserr)
    obs_err = ex._measure_execution_time(t_py, bad_py)
    assert obs_err["passed"] is False and "exception:" in obs_err["error"]

    # _rollback deletes newly created file when pre_image is None
    ex._rollback(txt_file, None)
    assert not txt_file.exists()


def test_t243_brain_audit_log_edges_and_bcel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    env_path = tmp_path / "env_audit.jsonl"
    monkeypatch.setenv("Q_SPEACE_BRAIN_AUDIT_PATH", str(env_path))
    assert _resolve_path(None) == env_path

    # Context manager + non-JSON/non-dict resilience in recent() + write failure handling
    with BrainAuditLog() as log:
        log.write({"ok": 1})
        log.write({"bad": math.nan})  # triggers ValueError caught & printed to stderr
    assert "write failed" in capsys.readouterr().err

    # Append corrupted JSON and valid non-dict JSON list -> ignored cleanly by recent()
    with env_path.open("a", encoding="utf-8") as fh:
        fh.write("{corrupt\n[1, 2, 3]\n")
    rows = BrainAuditLog(env_path).recent(10)
    assert rows == [{"ok": 1}]

    # make_apply_record extra field + BCEL T243 check
    rec = make_apply_record(
        agent_id="a1",
        backend="stub",
        backend_meta={},
        prompt="p",
        result_text="r",
        result_confidence=0.9,
        result_belief=[0.5, 0.5],
        n_tokens=4,
        coherence_phi_pre=0.8,
        coherence_phi_post=0.85,
        sevo=2.0,
        energy_w=5.0,
        approved=True,
        reason="ok",
        extra={"tag": "t243"},
    )
    assert rec["extra"] == {"tag": "t243"}
    assert BCELCatalog().is_functional(
        "AACM worktree containment, finite-domain dynamics, and strict audit-record typing (T243)"
    )
