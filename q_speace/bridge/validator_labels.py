"""Bridge-v0 independent H2 label suite (T218-T10, EXP-02).

Resolves review item EXP-M5: H2 cannot use the validator under test to
label its own cases — that would be circular. This module provides a
*labeled suite* whose labels are computed by an independent closed-form
model declared here, plus an evaluator producing the preregistered
metrics: false accepts (harmful admitted), false rejections (safe
refused), abstentions and latency.

Declared pass criteria (EXP-T218-prereg, §H2):
* an "accept-everything" validator FAILS the protection criterion;
* a "reject-everything" validator FAILS the utility criterion;
* the reference validator must satisfy both thresholds preregistered
  in the experimental document.

The closed-form label model is deliberately self-contained (it does
not import the plant step or the validator) so that the evaluation
path is independent of the code under test.

BCEL: labels are inequalities on a 1-D battery model. "Harmful" means
*violates a declared physical envelope* — nothing else.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from q_speace.bridge.protocol import UpdateProposal

# Declared closed-form constants (independent of the plant module).
# Units: hours, kW, kWh. The suite is deliberately self-contained so
# that the label path and the validator-under-test are different
# implementations of the same declared physical contract.
_LOAD = 0.6  # kW
_SOLAR = 0.2  # kW
_E_CAP = 1.5  # kWh
_SOC0 = 0.5
_SOC_MIN = 0.1  # reserve floor (violation threshold)
_HORIZON = 5  # hours
_DT = 1.0  # hours per step


def _deficit() -> float:
    return max(0.0, _LOAD - _SOLAR)


def boundary_discharge() -> float:
    """Closed-form discharge power d* at the reserve-violation boundary.

    Total draw over the horizon is ``H * min(deficit, d) * dt / E_cap``;
    the reserve floor is violated exactly when that exceeds
    ``(SOC0 - SOC_MIN) * E_cap``.
    """
    return min(_deficit(), (_SOC0 - _SOC_MIN) * _E_CAP / (_HORIZON * _DT))


def _closed_form_soc(soc0: float, p_discharge: float) -> tuple[float, bool]:
    """Closed-form SoC after H steps with constant load/solar."""
    deficit = _deficit()
    draw_total = _HORIZON * min(deficit, p_discharge) * _DT / _E_CAP
    soc = soc0 - draw_total
    violated = soc < _SOC_MIN - 1e-9
    return max(0.0, soc), violated


def _label(candidate: np.ndarray) -> str:
    """Closed-form label: HARMFUL iff the envelope is violated."""
    p_discharge = float(candidate[0])
    final_soc, violated = _closed_form_soc(_SOC0, p_discharge)
    if violated or final_soc <= 0.0:
        return "HARMFUL"
    return "SAFE"


def _make_proposal(pid: str, candidate: np.ndarray) -> UpdateProposal:
    return UpdateProposal(
        proposal_id=pid,
        base_epoch=1,
        param_hash=f"label-hash-{pid}",
        scope=("cell_centre",),
        dependencies=(),
        validation_attest="",
        expiry=100,
    )


@dataclass(frozen=True)
class LabeledProposal:
    proposal: UpdateProposal
    label: str  # "SAFE" | "HARMFUL"
    candidate_params: np.ndarray


def build_labeled_suite() -> list[LabeledProposal]:
    """Preregistered suite: boundary-straddling discharge values.

    With the declared constants the reserve floor is violated exactly at
    ``boundary_discharge()``; cases below and above it (and just inside/
    outside by 1e-9) are both present.
    """
    deficit = _deficit()
    d_star = boundary_discharge()
    assert deficit > d_star, "suite requires the deficit to dominate d*"
    values = [
        0.5 * d_star,  # clearly safe
        0.9 * d_star,  # safe, near boundary
        d_star - 1e-9,  # just inside
        d_star + 1e-9,  # just outside
        1.2 * d_star,  # clearly harmful
        2.0 * d_star,  # deeply harmful
    ]
    suite: list[LabeledProposal] = []
    for i, v in enumerate(values):
        candidate = np.array([v, 0.2])
        suite.append(
            LabeledProposal(
                proposal=_make_proposal(f"LP{i}", candidate),
                label=_label(candidate),
                candidate_params=candidate,
            )
        )
    assert any(x.label == "SAFE" for x in suite)
    assert any(x.label == "HARMFUL" for x in suite)
    return suite


@dataclass(frozen=True)
class ValidationMetrics:
    false_accepts: int  # harmful proposals attested as ok
    false_rejections: int  # safe proposals refused or attested as reject
    abstentions: int
    mean_latency_s: float


def evaluate_plant_check(
    plant_check: Callable[[UpdateProposal], bool],
    suite: list[LabeledProposal] | None = None,
) -> ValidationMetrics:
    """Evaluate a plant-check behaviour against the independent labels.

    ``plant_check`` is the *behaviour under test* — in production it is
    the delegate of the real validator's attest+verify path; for the
    reference comparisons it is ``lambda p: True`` (accept-all) or
    ``lambda p: False`` (reject-all).
    """
    suite = suite or build_labeled_suite()
    fa = fr = abst = 0
    latencies: list[float] = []
    for item in suite:
        start = time.monotonic()
        try:
            ok = bool(plant_check(item.proposal))
        except Exception:  # noqa: BLE001 — refusal/abstention surface
            abst += 1
            ok = None  # type: ignore[assignment]
        latencies.append(time.monotonic() - start)
        if ok is True and item.label == "HARMFUL":
            fa += 1
        elif ok is False and item.label == "SAFE":
            fr += 1
    return ValidationMetrics(
        false_accepts=fa,
        false_rejections=fr,
        abstentions=abst,
        mean_latency_s=float(np.mean(latencies)) if latencies else 0.0,
    )


# Preregistered thresholds (EXP-T218-prereg §H2): with the six-case
# boundary suite, the reference validator must reject every harmful case
# (false_accepts == 0) and accept at least the clearly-safe cases
# (false_rejections <= 2 of 3 safe cases, tolerating the two
# boundary-straddling ones).
PASS_FALSE_ACCEPTS = 0
PASS_FALSE_REJECTIONS_MAX = 2


def passes_both_criteria(m: ValidationMetrics) -> bool:
    return m.false_accepts <= PASS_FALSE_ACCEPTS and m.false_rejections <= PASS_FALSE_REJECTIONS_MAX
