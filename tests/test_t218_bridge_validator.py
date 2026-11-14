"""T218-T03 tests — independent validator (BR-03).

Acceptance (spec §4.3): forged attestation refused; stale-generation
attestation refused after promotion; proposer cannot bypass validation
nor saturate the validator; "reject" attestation cannot be presented
as "ok".
"""

from __future__ import annotations

import pytest

from q_speace.bridge.protocol import FencingError, UpdateLedger, UpdateProposal
from q_speace.bridge.validator import (
    IndependentValidator,
    ValidationBudgetExhaustedError,
    ValidatorKey,
    attestation_digest,
    authorize_activation,
    promote_successor,
)


def _proposal(pid: str = "P1") -> UpdateProposal:
    return UpdateProposal(
        proposal_id=pid,
        base_epoch=1,
        param_hash=f"hash-{pid}",
        scope=("cell_a",),
        dependencies=(),
        validation_attest="",
        expiry=100,
    )


def _validator(generation: int = 1) -> IndependentValidator:
    return IndependentValidator(ValidatorKey(generation=generation, key=b"k" * 32))


def test_attest_and_verify_roundtrip() -> None:
    v = _validator()
    p = _proposal()
    attest = v.attest(p, epoch=1, plant_check=lambda pr: True)
    assert v.verify(p, attest, expected_ok=True)


def test_forged_attestation_is_refused() -> None:
    v = _validator()
    p = _proposal()
    forged = "f" * 64
    assert not v.verify(p, forged, expected_ok=True)
    with pytest.raises(Exception):  # noqa: B017, PT011  (StateError on authorize)
        authorize_activation(UpdateLedger(), p, forged, v, epoch=1)


def test_attestation_binds_proposal_content() -> None:
    """A valid attestation for P1 must not verify for a different candidate."""
    v = _validator()
    attest = v.attest(_proposal("P1"), epoch=1, plant_check=lambda pr: True)
    other = _proposal("P1").__class__(
        proposal_id="P1",
        base_epoch=1,
        param_hash="hash-TAMPERED",
        scope=("cell_a",),
        dependencies=(),
        validation_attest="",
        expiry=100,
    )
    assert not v.verify(other, attest, expected_ok=True)


def test_reject_attestation_cannot_pass_as_ok() -> None:
    v = _validator()
    p = _proposal()
    attest = v.attest(p, epoch=1, plant_check=lambda pr: False)
    assert not v.verify(p, attest, expected_ok=True)


def test_stale_generation_refused_after_promotion() -> None:
    led = UpdateLedger()
    v1 = _validator(1)
    p = _proposal()
    led.submit(p, epoch=1)
    attest1 = v1.attest(p, epoch=1, plant_check=lambda pr: True)
    led.mark_validated("P1", epoch=1, fencing=1, attest=attest1)
    v2 = promote_successor(led, ValidatorKey(generation=2, key=b"n" * 32), epoch=1)
    with pytest.raises(FencingError):
        authorize_activation(led, p, attest1, v1, epoch=1)
    # The successor signs its own attestation and activation succeeds.
    attest2 = v2.attest(p, epoch=1, plant_check=lambda pr: True)
    led.mark_validated("P1", epoch=1, fencing=2, attest=attest2)
    authorize_activation(led, p, attest2, v2, epoch=1)


def test_call_budget_exhaustion_refuses_saturation() -> None:
    v = IndependentValidator(ValidatorKey(generation=1, key=b"k" * 32), max_evals=2)
    p = _proposal()
    v.attest(p, epoch=1, plant_check=lambda pr: True)
    v.attest(p, epoch=1, plant_check=lambda pr: True)
    with pytest.raises(ValidationBudgetExhaustedError):
        v.attest(p, epoch=1, plant_check=lambda pr: True)


def test_time_budget_exhaustion_on_slow_plant_check() -> None:
    import time

    v = IndependentValidator(ValidatorKey(generation=1, key=b"k" * 32), max_eval_seconds=0.01)
    p = _proposal()

    def slow_check(proposal: UpdateProposal) -> bool:
        time.sleep(0.05)
        return True

    with pytest.raises(ValidationBudgetExhaustedError):
        v.attest(p, epoch=1, plant_check=slow_check)


def test_attest_requires_matching_epoch() -> None:
    v = _validator()
    with pytest.raises(Exception):  # noqa: B017, PT011
        v.attest(_proposal(), epoch=2, plant_check=lambda pr: True)


def test_attestation_digest_deterministic_and_key_bound() -> None:
    p = _proposal()
    d1 = attestation_digest(p, b"k" * 32, extra="ok")
    d2 = attestation_digest(p, b"k" * 32, extra="ok")
    d3 = attestation_digest(p, b"other", extra="ok")
    assert d1 == d2
    assert d1 != d3
