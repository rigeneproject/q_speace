"""Cold-start admission control for the q_speace_economy (T6.22 §4.10.2).

A new agent cannot enter the SPEACE economy without passing two gates:

1. **Proof of Coherence** — the agent's :class:`CME` vector must have all
   non-fungible capital axes above a minimum threshold ``coherence_min``.
2. **Reference rotation** — the agent must present a non-empty ``reference_set``
   of externally auditable standards (e.g. ISO certifications, peer-reviewed
   benchmarks) that trace its claimed behaviour.

This module is intentionally lightweight: it is a stateless gate, not a
KYC/AML system. The "admission" here is the cold-start admission to the
SPEACE economic graph, **not** to any legal jurisdiction.

BCEL: the gates are *functional*: the coherence check is a measurable
inequality on a 12-dim vector; the reference rotation is a cardinality
check on a list of pointers. Neither is a subjective judgement.
"""

from __future__ import annotations

from dataclasses import dataclass

from .evolutive_capital import CapitalEntry, validate_registry
from .primitives import CME


@dataclass(frozen=True)
class AdmissionDecision:
    """Outcome of an admission attempt."""

    admitted: bool
    reason: str
    coherence_score: float
    reference_count: int


def coherence_score(cme: CME) -> float:
    """Return the minimum of the 12 CME axes.

    A perfectly balanced vector yields 1.0; an axis at 0.0 collapses the
    score to 0.0. The score is in [0, 1].
    """
    arr = cme.as_array()
    return float(arr.min())


def admission_gate(
    cme: CME,
    registry: list[CapitalEntry],
    reference_set: list[str],
    *,
    coherence_min: float = 0.05,
    min_references: int = 2,
) -> AdmissionDecision:
    """Decide whether to admit a new agent.

    Parameters
    ----------
    cme : CME
        The agent's claimed 12-dim capital vector.
    registry : list of CapitalEntry
        The agent's claimed Evolutive Capital registry.
    reference_set : list of str
        Stable identifiers of external standards the agent traces (e.g.
        ``"iso:14001"``, ``"wri:2024"``).
    coherence_min : float
        Minimum acceptable coherence score (default 0.05).
    min_references : int
        Minimum cardinality of the reference set (default 2).
    """
    if not 0.0 <= coherence_min <= 1.0:
        raise ValueError(f"coherence_min must be in [0, 1] (got {coherence_min})")
    if min_references < 0:
        raise ValueError(f"min_references must be >= 0 (got {min_references})")
    score = coherence_score(cme)
    if score < coherence_min:
        return AdmissionDecision(
            admitted=False,
            reason=f"coherence {score:.3f} < min {coherence_min}",
            coherence_score=score,
            reference_count=len(reference_set),
        )
    ref_count = len(reference_set)
    if ref_count < min_references:
        return AdmissionDecision(
            admitted=False,
            reason=f"references {ref_count} < min {min_references}",
            coherence_score=score,
            reference_count=ref_count,
        )
    issues = validate_registry(registry)
    if issues:
        return AdmissionDecision(
            admitted=False,
            reason="registry invalid: " + "; ".join(issues),
            coherence_score=score,
            reference_count=ref_count,
        )
    return AdmissionDecision(
        admitted=True,
        reason="all gates passed",
        coherence_score=score,
        reference_count=ref_count,
    )
