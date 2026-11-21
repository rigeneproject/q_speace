"""T218 refinement R3 — coordinator-free timeout for coupled commits.

Acceptance: a peer that loses observability after VALIDATED but before
ACTIVATED cannot deadlock the surviving cell — any peer may invoke
``expire_on_timeout``; the whole prepared set aborts atomically once a
member's expiry passes and the reserved capacity is released
immediately, without waiting for an external coordinator.
"""

from __future__ import annotations

# State-machine-only tests use an explicit trust stub; see test_t225_bridge_enforcement.
import pytest

from q_speace.bridge.protocol import (
    CoupledCommit,
    StateError,
    UpdateLedger,
    UpdateProposal,
    UpdateStatus,
)


def _pair(expiry_1: int = 100, expiry_2: int = 100) -> list[UpdateProposal]:
    return [
        UpdateProposal(
            proposal_id="CP1",
            base_epoch=1,
            param_hash="hash-CP1",
            scope=("cell_a", "cell_b"),
            dependencies=("CP2",),
            validation_attest="attest-coupled",
            expiry=expiry_1,
        ),
        UpdateProposal(
            proposal_id="CP2",
            base_epoch=1,
            param_hash="hash-CP2",
            scope=("cell_a", "cell_b"),
            dependencies=("CP1",),
            validation_attest="attest-coupled",
            expiry=expiry_2,
        ),
    ]


def test_timeout_aborts_whole_prepared_set_and_releases_capacity() -> None:
    led = UpdateLedger(activation_authorizer=lambda *_: None)
    cc = CoupledCommit(led, "CC-1")
    assert cc.prepare(
        _pair(expiry_1=5),
        epoch=1,
        fencing=1,
        check=lambda ps: True,
        reservations={"cell_a": 0.15, "cell_b": 0.15},
    )
    assert cc.reserved_capacity == {"cell_a": 0.15, "cell_b": 0.15}
    # cell_b loses observability; cell_a (survivor) invokes the timeout
    # WITHOUT an external coordinator
    aborted = cc.expire_on_timeout(epoch=6)
    assert sorted(aborted) == ["CP1", "CP2"]
    assert led.status_of("CP1") is UpdateStatus.ABORTED
    assert led.status_of("CP2") is UpdateStatus.ABORTED
    assert cc.reserved_capacity == {}  # released immediately
    assert "ACTIVATED" not in [r.event for r in led.records()]


def test_timeout_before_expiry_is_a_noop() -> None:
    led = UpdateLedger(activation_authorizer=lambda *_: None)
    cc = CoupledCommit(led, "CC-1")
    assert cc.prepare(_pair(), epoch=1, fencing=1, check=lambda ps: True)
    assert cc.expire_on_timeout(epoch=5) == []
    assert led.status_of("CP1") is UpdateStatus.PREPARED
    assert led.status_of("CP2") is UpdateStatus.PREPARED


def test_timeout_without_members_returns_empty() -> None:
    led = UpdateLedger(activation_authorizer=lambda *_: None)
    cc = CoupledCommit(led, "CC-1")
    assert cc.expire_on_timeout(epoch=10) == []


def test_timeout_refused_after_partial_activation_is_impossible() -> None:
    """Activation of a coupled set is atomic, so a mixed state must not
    exist; if observed, the timeout abort is refused loudly."""
    led = UpdateLedger(activation_authorizer=lambda *_: None)
    cc = CoupledCommit(led, "CC-1")
    assert cc.prepare(_pair(), epoch=1, fencing=1, check=lambda ps: True)
    # simulate a protocol violation by flipping one member to ACTIVATED
    st = led._require("CP1")  # noqa: SLF001 — direct violation injection
    st.status = UpdateStatus.ACTIVATED
    with pytest.raises(StateError):
        cc.expire_on_timeout(epoch=200)


def test_commit_releases_reservations_on_success() -> None:
    led = UpdateLedger(activation_authorizer=lambda *_: None)
    cc = CoupledCommit(led, "CC-1")
    assert cc.prepare(
        _pair(),
        epoch=1,
        fencing=1,
        check=lambda ps: True,
        reservations={"cell_a": 0.05, "cell_b": 0.05},
    )
    activated = cc.commit(epoch=1, fencing=1)
    assert sorted(activated) == ["CP1", "CP2"]
    assert cc.reserved_capacity == {}  # consumed by activation


def test_timeout_is_reproducible_from_journal(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "journal.jsonl"
    led = UpdateLedger(path, activation_authorizer=lambda *_: None)
    cc = CoupledCommit(led, "CC-1")
    assert cc.prepare(_pair(expiry_1=5), epoch=1, fencing=1, check=lambda ps: True)
    assert sorted(cc.expire_on_timeout(epoch=6)) == ["CP1", "CP2"]
    recovered = UpdateLedger(path, activation_authorizer=lambda *_: None)
    assert recovered.status_of("CP1") is UpdateStatus.ABORTED
    assert recovered.status_of("CP2") is UpdateStatus.ABORTED
