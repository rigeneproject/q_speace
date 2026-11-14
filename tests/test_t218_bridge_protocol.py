"""T218-T01 tests — Bridge-v0 update protocol (BR-01).

Acceptance criteria from ``docs/T218_QSPEACE_V0_BRIDGE_SPEC.md`` §4.2:
duplicated messages, reordering, crash recovery, double activation and
stale-authority (fencing) traces must all produce declared outcomes.
"""

from __future__ import annotations

import pytest

from q_speace.bridge.protocol import (
    CoupledCommit,
    ExpiryError,
    FencingError,
    IdempotencyError,
    StateError,
    UpdateLedger,
    UpdateProposal,
    UpdateStatus,
)


def _proposal(
    pid: str = "P1",
    *,
    epoch: int = 1,
    expiry: int = 100,
    attest: str = "attest-1",
) -> UpdateProposal:
    return UpdateProposal(
        proposal_id=pid,
        base_epoch=epoch,
        param_hash=f"hash-{pid}",
        scope=("cell_a",),
        dependencies=(),
        validation_attest=attest,
        expiry=expiry,
    )


# --------------------------------------------------------------------- #
# lifecycle
# --------------------------------------------------------------------- #
def test_submit_is_idempotent_on_same_hash() -> None:
    led = UpdateLedger()
    p = _proposal()
    assert led.submit(p, epoch=1) is UpdateStatus.PROPOSED
    assert led.submit(p, epoch=1) is UpdateStatus.PROPOSED  # duplicate message: no-op
    assert led.status_of("P1") is UpdateStatus.PROPOSED


def test_submit_same_id_different_hash_is_a_violation() -> None:
    led = UpdateLedger()
    led.submit(_proposal(), epoch=1)
    other = UpdateProposal(
        proposal_id="P1",
        base_epoch=1,
        param_hash="hash-DIFFERENT",
        scope=("cell_a",),
        dependencies=(),
        validation_attest="attest-1",
        expiry=100,
    )
    with pytest.raises(IdempotencyError):
        led.submit(other, epoch=1)


def test_activate_requires_validation() -> None:
    led = UpdateLedger()
    led.submit(_proposal(), epoch=1)
    with pytest.raises(StateError):
        led.activate("P1", epoch=1, fencing=1)


def test_full_lifecycle_to_activation() -> None:
    led = UpdateLedger()
    p = _proposal()
    led.submit(p, epoch=1)
    led.mark_validated("P1", epoch=1, fencing=1, attest="attest-1")
    assert led.activate("P1", epoch=1, fencing=1) is UpdateStatus.ACTIVATED
    # Double activation is refused and leaves the state untouched.
    with pytest.raises(StateError):
        led.activate("P1", epoch=1, fencing=1)
    assert led.status_of("P1") is UpdateStatus.ACTIVATED


def test_expiry_blocks_activation_and_marks_expired() -> None:
    led = UpdateLedger()
    led.submit(_proposal(expiry=5), epoch=1)
    led.mark_validated("P1", epoch=1, fencing=1, attest="attest-1")
    with pytest.raises(ExpiryError):
        led.activate("P1", epoch=6, fencing=1)
    assert led.status_of("P1") is UpdateStatus.EXPIRED


def test_activation_on_wrong_epoch_refused() -> None:
    led = UpdateLedger()
    led.submit(_proposal(epoch=1), epoch=1)
    led.mark_validated("P1", epoch=1, fencing=1, attest="attest-1")
    with pytest.raises(StateError):
        led.activate("P1", epoch=2, fencing=1)


# --------------------------------------------------------------------- #
# fencing
# --------------------------------------------------------------------- #
def test_stale_validator_cannot_activate_after_promotion() -> None:
    led = UpdateLedger()
    led.submit(_proposal(), epoch=1)
    led.mark_validated("P1", epoch=1, fencing=1, attest="attest-1")
    led.promote_validator(2, epoch=1)
    with pytest.raises(FencingError):
        led.activate("P1", epoch=1, fencing=1)  # fenced-out old validator
    assert led.activate("P1", epoch=1, fencing=2) is UpdateStatus.ACTIVATED


def test_promotion_must_be_monotonic() -> None:
    led = UpdateLedger()
    led.promote_validator(3, epoch=1)
    with pytest.raises(FencingError):
        led.promote_validator(3, epoch=1)
    with pytest.raises(FencingError):
        led.promote_validator(2, epoch=1)


# --------------------------------------------------------------------- #
# crash recovery
# --------------------------------------------------------------------- #
def test_crash_recovery_from_journal(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "journal.jsonl"
    led = UpdateLedger(path)
    led.submit(_proposal(), epoch=1)
    led.mark_validated("P1", epoch=1, fencing=1, attest="attest-1")
    led.activate("P1", epoch=1, fencing=1)

    recovered = UpdateLedger(path)
    assert recovered.status_of("P1") is UpdateStatus.ACTIVATED
    # Activation is at-most-once across recovery: no double apply.
    with pytest.raises(StateError):
        recovered.activate("P1", epoch=1, fencing=1)


def test_recovery_truncated_journal_allows_resubmit(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "journal.jsonl"
    led = UpdateLedger(path)
    led.submit(_proposal(), epoch=1)
    recovered = UpdateLedger(path)
    # Body was persisted in the side file, so recovery is complete.
    p = recovered.proposal_of("P1")
    assert p.param_hash == "hash-P1"
    assert recovered.status_of("P1") is UpdateStatus.PROPOSED


# --------------------------------------------------------------------- #
# coupled updates (R3: partial activation hazard)
# --------------------------------------------------------------------- #
def _coupled_pair(attest: str = "attest-c") -> list[UpdateProposal]:
    return [
        UpdateProposal(
            proposal_id="CP1",
            base_epoch=1,
            param_hash="hash-CP1",
            scope=("cell_a", "cell_b"),
            dependencies=("CP2",),
            validation_attest=attest,
            expiry=100,
        ),
        UpdateProposal(
            proposal_id="CP2",
            base_epoch=1,
            param_hash="hash-CP2",
            scope=("cell_a", "cell_b"),
            dependencies=("CP1",),
            validation_attest=attest,
            expiry=100,
        ),
    ]


def test_coupled_proposal_cannot_activate_singly() -> None:
    led = UpdateLedger()
    cp1 = _coupled_pair()[0]
    led.submit(cp1, epoch=1)
    led.mark_validated("CP1", epoch=1, fencing=1, attest="attest-c")
    with pytest.raises(StateError):
        led.activate("CP1", epoch=1, fencing=1)


def test_coupled_commit_all_or_nothing() -> None:
    led = UpdateLedger()
    proposals = _coupled_pair()
    cc = CoupledCommit(led, "CC-1")
    assert cc.prepare(proposals, epoch=1, fencing=1, check=lambda ps: True)
    assert led.status_of("CP1") is UpdateStatus.PREPARED
    assert led.status_of("CP2") is UpdateStatus.PREPARED
    activated = cc.commit(epoch=1, fencing=1)
    assert activated == ["CP1", "CP2"]
    assert led.status_of("CP1") is UpdateStatus.ACTIVATED
    assert led.status_of("CP2") is UpdateStatus.ACTIVATED


def test_coupled_commit_failed_joint_check_aborts_all() -> None:
    led = UpdateLedger()
    proposals = _coupled_pair()
    cc = CoupledCommit(led, "CC-1")
    assert not cc.prepare(proposals, epoch=1, fencing=1, check=lambda ps: False)
    assert led.status_of("CP1") is UpdateStatus.ABORTED
    assert led.status_of("CP2") is UpdateStatus.ABORTED
    with pytest.raises(StateError):
        cc.commit(epoch=1, fencing=1)


def test_journal_records_are_ordered_and_complete() -> None:
    led = UpdateLedger()
    p = _proposal()
    led.submit(p, epoch=1)
    led.mark_validated("P1", epoch=1, fencing=1, attest="attest-1")
    led.activate("P1", epoch=1, fencing=1)
    events = [r.event for r in led.records()]
    assert events == ["SUBMITTED", "VALIDATED", "ACTIVATED"]
    assert all(r.param_hash == "hash-P1" for r in led.records())
