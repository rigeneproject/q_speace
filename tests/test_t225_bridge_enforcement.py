"""Regression tests for the T218/T225 activation trust boundary."""

from __future__ import annotations

import pytest

from q_speace.bridge.protocol import (
    CoupledCommit,
    StateError,
    UpdateLedger,
    UpdateProposal,
    UpdateStatus,
)
from q_speace.bridge.validator import IndependentValidator, ValidatorKey


def proposal(pid: str = "audit", coupled: bool = False) -> UpdateProposal:
    return UpdateProposal(pid, 1, "hash-" + pid, ("a", "b") if coupled else ("a",), (), "", 10)


def test_unconfigured_ledger_denies_activation() -> None:
    ledger = UpdateLedger()
    p = proposal()
    ledger.submit(p, epoch=1)
    ledger.mark_validated(p.proposal_id, epoch=1, fencing=1, attest="forged")
    with pytest.raises(StateError, match="authorizer"):
        ledger.activate(p.proposal_id, epoch=1, fencing=1)
    assert ledger.status_of(p.proposal_id) is UpdateStatus.VALIDATED


@pytest.mark.parametrize("accepted", [False, True])
def test_ledger_enforces_actual_verifier(accepted: bool) -> None:
    validator = IndependentValidator(ValidatorKey(1, b"test-only-key" * 3))
    ledger = UpdateLedger(activation_authorizer=validator.authorize)
    p = proposal()
    attest = validator.attest(p, epoch=1, plant_check=lambda _: accepted)
    ledger.submit(p, epoch=1)
    ledger.mark_validated(p.proposal_id, epoch=1, fencing=1, attest=attest)
    if accepted:
        assert ledger.activate(p.proposal_id, epoch=1, fencing=1) is UpdateStatus.ACTIVATED
    else:
        with pytest.raises(StateError):
            ledger.activate(p.proposal_id, epoch=1, fencing=1)
        assert not any(r.event == "ACTIVATED" for r in ledger.records())


def test_coupled_invalid_member_never_partly_activates() -> None:
    validator = IndependentValidator(ValidatorKey(1, b"test-only-key" * 3))
    ledger = UpdateLedger(activation_authorizer=validator.authorize)
    pairs = [proposal("a", True), proposal("b", True)]
    transaction = CoupledCommit(ledger, "pair")
    transaction.prepare(pairs, epoch=1, fencing=1, check=lambda _: True)
    for p in pairs:
        attest = validator.attest(p, epoch=1, plant_check=lambda _: True)
        ledger.mark_validated(
            p.proposal_id, epoch=1, fencing=1, attest=attest if p.proposal_id == "a" else "forged"
        )
    with pytest.raises(StateError):
        transaction.commit(epoch=1, fencing=1)
    assert not any(r.event == "ACTIVATED" for r in ledger.records())

