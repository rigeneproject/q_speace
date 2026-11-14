"""T218-T10 tests — independent H2 label suite (EXP-02).

Acceptance (spec §7.2): the "accept-all" validator fails the protection
criterion, the "reject-all" validator fails the utility criterion, and
the reference validator (real IndependentValidator attest+verify path)
satisfies both preregistered thresholds without evaluating its own
labels.
"""

from __future__ import annotations

import numpy as np
import pytest

from q_speace.bridge.protocol import UpdateProposal
from q_speace.bridge.validator import IndependentValidator, ValidatorKey
from q_speace.bridge.validator_labels import (
    PASS_FALSE_ACCEPTS,
    PASS_FALSE_REJECTIONS_MAX,
    build_labeled_suite,
    evaluate_plant_check,
    passes_both_criteria,
)


@pytest.fixture()
def suite():  # type: ignore[no-untyped-def]
    return build_labeled_suite()


def test_suite_has_both_labels_and_boundary_cases(suite) -> None:  # type: ignore[no-untyped-def]
    labels = {x.label for x in suite}
    assert labels == {"SAFE", "HARMFUL"}
    # exactly one case sits on each side of the closed-form boundary
    harmful = [x for x in suite if x.label == "HARMFUL"]
    safe = [x for x in suite if x.label == "SAFE"]
    assert len(harmful) >= 2 and len(safe) >= 2


def test_labels_are_deterministic(suite) -> None:  # type: ignore[no-untyped-def]
    again = build_labeled_suite()
    for a, b in zip(suite, again, strict=False):
        assert a.label == b.label
        assert np.array_equal(a.candidate_params, b.candidate_params)


def test_accept_all_fails_protection(suite) -> None:  # type: ignore[no-untyped-def]
    m = evaluate_plant_check(lambda p: True, suite)
    assert m.false_accepts > PASS_FALSE_ACCEPTS
    assert not passes_both_criteria(m)


def test_reject_all_fails_utility(suite) -> None:  # type: ignore[no-untyped-def]
    m = evaluate_plant_check(lambda p: False, suite)
    assert m.false_rejections > PASS_FALSE_REJECTIONS_MAX
    assert not passes_both_criteria(m)


def test_reference_validator_passes_both_criteria(suite) -> None:  # type: ignore[no-untyped-def]
    """The real validator behaviour, evaluated against independent labels.

    The delegate mirrors the production attest+verify path: the plant
    check comes from the validator configuration; the *labels* come from
    this suite's closed form — never from the validator itself.
    """
    validator = IndependentValidator(ValidatorKey(generation=1, key=b"ref" * 11))

    def delegate(proposal: UpdateProposal) -> bool:
        attest = validator.attest(proposal, epoch=1, plant_check=_reference_plant_check)
        return validator.verify(proposal, attest, expected_ok=True)

    m = evaluate_plant_check(delegate, suite)
    assert m.false_accepts <= PASS_FALSE_ACCEPTS
    assert m.false_rejections <= PASS_FALSE_REJECTIONS_MAX
    assert passes_both_criteria(m)


def _reference_plant_check(proposal: UpdateProposal) -> bool:
    """Reference validator plant check: step-loop envelope test.

    Independent reimplementation of the *same declared contract* as the
    label model (constants and envelope of ``validator_labels``); the
    labeler uses a closed form, the validator-under-test uses a step
    loop. Divergence between the two implementations is itself part of
    the H2 metric.
    """
    from q_speace.bridge import validator_labels as vl  # noqa: PLC0415

    candidate = _candidate_of(proposal)
    if candidate is None:
        return False
    soc = vl._SOC0  # noqa: SLF001 — declared contract constants
    deficit = vl._deficit()  # noqa: SLF001
    p_discharge = float(candidate[0])
    for _ in range(vl._HORIZON):  # noqa: SLF001
        draw = min(deficit, p_discharge) * vl._DT / vl._E_CAP  # noqa: SLF001
        soc -= draw
        if soc < vl._SOC_MIN - 1e-9:  # noqa: SLF001
            return False
        soc = max(0.0, soc)
    return True


def _candidate_of(proposal: UpdateProposal) -> np.ndarray | None:
    for item in build_labeled_suite():
        if item.proposal.proposal_id == proposal.proposal_id:
            return item.candidate_params
    return None
