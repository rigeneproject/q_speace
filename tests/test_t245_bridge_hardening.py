"""T245: Tests for T218 §13 ProcessIsolatedValidator (preemptive kill) and CrashAtomicCoupledCommit WAL."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from q_speace.bcel.catalog import BCELCatalog
from q_speace.bridge import (
    CrashAtomicCoupledCommit,
    ProcessIsolatedValidator,
    SimulatedCrashError,
    UpdateLedger,
    UpdateProposal,
    UpdateStatus,
    ValidatorKey,
    canonical_param_hash,
    recover_coupled_wal,
)
from q_speace.bridge.validator import ValidationBudgetExhaustedError


def _make_proposal(
    pid: str,
    val: float,
    *,
    epoch: int = 1,
    expiry: int = 5,
    attest: str = "",
) -> UpdateProposal:
    return UpdateProposal(
        proposal_id=pid,
        base_epoch=epoch,
        param_hash=canonical_param_hash([val]),
        scope=("cell-1",),
        expiry=expiry,
        dependencies=(),
        validation_attest=attest,
    )


def test_t245_process_isolated_validator_preemptive_kill_and_allowlist() -> None:
    key = ValidatorKey(generation=1, key=b"super-secret-parent-only-key")
    validator = ProcessIsolatedValidator(key, max_eval_seconds=0.8, max_evals=10)
    prop = _make_proposal("p-iso-1", 0.25)

    # 1. Valid isolated plant check produces verifiable HMAC attestation signed by parent only.
    att_ok = validator.attest_isolated(
        prop,
        epoch=1,
        check_target="q_speace.bridge.validator:_demo_plant_ok",
    )
    assert validator.verify(prop, att_ok, expected_ok=True) is True

    # 2. Rejecting isolated plant check produces a reject attestation (cannot authorize activation).
    att_rej = validator.attest_isolated(
        prop,
        epoch=1,
        check_target="q_speace.bridge.validator:_demo_plant_reject",
    )
    assert validator.verify(prop, att_rej, expected_ok=True) is False
    assert validator.verify(prop, att_rej, expected_ok=False) is True

    # 3. Allowlist blocks arbitrary module targets outside q_speace.*.
    with pytest.raises(ValueError, match="not in allowlist"):
        validator.attest_isolated(prop, epoch=1, check_target="os:system")

    # 4. Preemptive timeout kills hanging worker well before its 30s sleep completes.
    fast_val = ProcessIsolatedValidator(key, max_eval_seconds=0.5, max_evals=5)
    t0 = time.monotonic()
    with pytest.raises(ValidationBudgetExhaustedError, match="preemptive timeout"):
        fast_val.attest_isolated(
            prop,
            epoch=1,
            check_target="q_speace.bridge.validator:_demo_plant_hang",
        )
    elapsed = time.monotonic() - t0
    assert elapsed < 5.0


def test_t245_crash_atomic_coupled_commit_recovery_and_bcel(tmp_path: Path) -> None:
    key = ValidatorKey(generation=1, key=b"coupled-wal-secret-key")
    validator = ProcessIsolatedValidator(key, max_eval_seconds=1.5, max_evals=10)
    ledger = UpdateLedger(activation_authorizer=validator.authorize)
    ledger.promote_validator(1, epoch=1)

    p1 = _make_proposal("cp-1", 0.30)
    p2 = _make_proposal("cp-2", 0.40)
    att1 = validator.attest_isolated(
        p1, epoch=1, check_target="q_speace.bridge.validator:_demo_plant_ok"
    )
    att2 = validator.attest_isolated(
        p2, epoch=1, check_target="q_speace.bridge.validator:_demo_plant_ok"
    )
    p1 = _make_proposal("cp-1", 0.30, attest=att1)
    p2 = _make_proposal("cp-2", 0.40, attest=att2)

    wal_path = tmp_path / "coupled_wal.json"
    cc = CrashAtomicCoupledCommit(ledger, "coupled-crash-1", wal_path)
    assert cc.prepare([p1, p2], epoch=1, fencing=1, check=lambda _ps: True) is True
    assert json.loads(wal_path.read_text(encoding="utf-8"))["state"] == "PREPARED"

    # Simulate crash immediately after activating member 0 (leaving partial state 1, 0 in RAM).
    with pytest.raises(SimulatedCrashError):
        cc.commit(epoch=1, fencing=1, crash_after_member_index=0)
    assert json.loads(wal_path.read_text(encoding="utf-8"))["state"] == "COMMITTING"
    assert ledger.status_of("cp-1") is UpdateStatus.ACTIVATED
    assert ledger.status_of("cp-2") is UpdateStatus.PREPARED

    # Crash recovery deterministically rolls back BOTH members -> zero mixed (1, 0) state!
    rec = recover_coupled_wal(ledger, wal_path, epoch=2)
    assert rec["action"] == "rolled_back"
    assert rec["state"] == "ROLLED_BACK"
    assert ledger.status_of("cp-1") is UpdateStatus.ABORTED
    assert ledger.status_of("cp-2") is UpdateStatus.ABORTED

    # Idempotent second recovery call is a clean noop.
    rec2 = recover_coupled_wal(ledger, wal_path, epoch=2)
    assert rec2["action"] == "noop"

    # Happy-path crash-atomic commit transitions WAL to COMMITTED and activates both members.
    p3 = _make_proposal("cp-3", 0.50, epoch=2, expiry=6)
    p4 = _make_proposal("cp-4", 0.60, epoch=2, expiry=6)
    p3 = _make_proposal(
        "cp-3",
        0.50,
        epoch=2,
        expiry=6,
        attest=validator.attest_isolated(
            p3, epoch=2, check_target="q_speace.bridge.validator:_demo_plant_ok"
        ),
    )
    p4 = _make_proposal(
        "cp-4",
        0.60,
        epoch=2,
        expiry=6,
        attest=validator.attest_isolated(
            p4, epoch=2, check_target="q_speace.bridge.validator:_demo_plant_ok"
        ),
    )
    wal2 = tmp_path / "coupled_wal_ok.json"
    cc2 = CrashAtomicCoupledCommit(ledger, "coupled-ok-2", wal2)
    assert cc2.prepare([p3, p4], epoch=2, fencing=1, check=lambda _ps: True) is True
    activated = cc2.commit(epoch=2, fencing=1)
    assert activated == ["cp-3", "cp-4"]
    assert json.loads(wal2.read_text(encoding="utf-8"))["state"] == "COMMITTED"
    assert recover_coupled_wal(ledger, wal2, epoch=3)["action"] == "noop"

    assert BCELCatalog().is_functional(
        "Process-isolated preemptive Bridge validator and crash-atomic coupled WAL (T245)"
    )
