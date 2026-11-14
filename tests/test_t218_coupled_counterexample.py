"""T218-T05 tests — coupled-update primitive (R3 counterexample).

Peer-review counterexample: two cells each consume 0.4 under a shared
limit of 1.0. Independently, increments of +0.15 each are admissible
(0.55 <= 1.0); simultaneous activation gives 1.1 > 1.0. The two-phase
commit of the Bridge must make the unsafe joint state impossible.

Acceptance (spec §4.2): reproducible traces for the rejection case and
for the coordinated case; coupled sets activate together or not at all;
singly activating a coupled proposal is refused by the ledger.
"""

from __future__ import annotations

import pytest

from q_speace.bridge.protocol import (
    CoupledCommit,
    ExpiryError,
    StateError,
    UpdateLedger,
    UpdateProposal,
    UpdateStatus,
)

SHARED_LIMIT = 1.0
BASE = {"cell_a": 0.4, "cell_b": 0.4}


def _increment_proposal(pid: str, cell: str, increment: float) -> UpdateProposal:
    return UpdateProposal(
        proposal_id=pid,
        base_epoch=1,
        param_hash=f"hash-{pid}-{increment}",
        scope=("cell_a", "cell_b"),
        dependencies=("CP2" if pid == "CP1" else "CP1",),
        validation_attest="attest-coupled",
        expiry=100,
    )


def _joint_check(proposals: list[UpdateProposal], increments: dict[str, float]) -> bool:
    """Joint admissibility over the shared resource limit."""
    total = sum(BASE.values()) + sum(increments[p.proposal_id] for p in proposals)
    return total <= SHARED_LIMIT


def test_independent_checks_pass_but_joint_activation_is_unsafe() -> None:
    """The individually-admissible increments sum to an infeasible joint state."""
    increments = {"CP1": 0.15, "CP2": 0.15}
    for pid in ("CP1", "CP2"):
        assert BASE["cell_a"] + increments[pid] <= SHARED_LIMIT  # separate: admissible
    total = sum(BASE.values()) + sum(increments.values())
    assert total > SHARED_LIMIT  # joint: 1.1 > 1.0


def test_two_phase_commit_rejects_unsafe_joint_state() -> None:
    led = UpdateLedger()
    proposals = [
        _increment_proposal("CP1", "cell_a", 0.15),
        _increment_proposal("CP2", "cell_b", 0.15),
    ]
    cc = CoupledCommit(led, "CC-unsafe")
    accepted = cc.prepare(
        proposals,
        epoch=1,
        fencing=1,
        check=lambda ps: _joint_check(ps, {"CP1": 0.15, "CP2": 0.15}),
    )
    assert not accepted
    assert led.status_of("CP1") is UpdateStatus.ABORTED
    assert led.status_of("CP2") is UpdateStatus.ABORTED
    with pytest.raises(StateError):  # noqa: PT011
        cc.commit(epoch=1, fencing=1)
    # nothing was ever activated
    events = [r.event for r in led.records()]
    assert "ACTIVATED" not in events


def test_coordinated_smaller_increments_activate_together() -> None:
    led = UpdateLedger()
    proposals = [
        _increment_proposal("CP1", "cell_a", 0.05),
        _increment_proposal("CP2", "cell_b", 0.05),
    ]
    cc = CoupledCommit(led, "CC-safe")
    assert cc.prepare(
        proposals,
        epoch=1,
        fencing=1,
        check=lambda ps: _joint_check(ps, {"CP1": 0.05, "CP2": 0.05}),
    )
    activated = cc.commit(epoch=1, fencing=1)
    assert sorted(activated) == ["CP1", "CP2"]
    assert led.status_of("CP1") is UpdateStatus.ACTIVATED
    assert led.status_of("CP2") is UpdateStatus.ACTIVATED
    # joint state remains within the shared limit
    assert sum(BASE.values()) + 0.10 <= SHARED_LIMIT


def test_coupled_set_cannot_activate_singly() -> None:
    """Sequential activation of one member of a coupled set is refused."""
    led = UpdateLedger()
    p = _increment_proposal("CP1", "cell_a", 0.15)
    led.submit(p, epoch=1)
    led.mark_validated("CP1", epoch=1, fencing=1, attest="attest-coupled")
    try:
        led.activate("CP1", epoch=1, fencing=1)
        raise AssertionError("singly activating a coupled proposal must be refused")
    except StateError:
        pass
    assert led.status_of("CP1") is UpdateStatus.VALIDATED  # state preserved


def test_expiring_member_rolls_back_whole_commit() -> None:
    """If any member expires during commit, the whole set aborts."""
    led = UpdateLedger()
    p1 = UpdateProposal(
        proposal_id="CP1",
        base_epoch=1,
        param_hash="hash-CP1",
        scope=("cell_a", "cell_b"),
        dependencies=("CP2",),
        validation_attest="attest-coupled",
        expiry=3,  # expires early
    )
    p2 = UpdateProposal(
        proposal_id="CP2",
        base_epoch=1,
        param_hash="hash-CP2",
        scope=("cell_a", "cell_b"),
        dependencies=("CP1",),
        validation_attest="attest-coupled",
        expiry=100,
    )
    cc = CoupledCommit(led, "CC-expiry")
    assert cc.prepare([p1, p2], epoch=1, fencing=1, check=lambda ps: True)
    with pytest.raises(ExpiryError):
        cc.commit(epoch=4, fencing=1)
    assert led.status_of("CP1") is UpdateStatus.ABORTED
    assert led.status_of("CP2") is UpdateStatus.ABORTED
    assert "ACTIVATED" not in [r.event for r in led.records()]


def test_reproducible_trace_of_rejection(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """The unsafe rejection is reproducible from the persisted journal."""
    path = tmp_path / "journal.jsonl"
    led = UpdateLedger(path)
    proposals = [
        _increment_proposal("CP1", "cell_a", 0.15),
        _increment_proposal("CP2", "cell_b", 0.15),
    ]
    cc = CoupledCommit(led, "CC-unsafe")
    assert not cc.prepare(
        proposals,
        epoch=1,
        fencing=1,
        check=lambda ps: _joint_check(ps, {"CP1": 0.15, "CP2": 0.15}),
    )
    recovered = UpdateLedger(path)
    assert recovered.status_of("CP1") is UpdateStatus.ABORTED
    assert recovered.status_of("CP2") is UpdateStatus.ABORTED
