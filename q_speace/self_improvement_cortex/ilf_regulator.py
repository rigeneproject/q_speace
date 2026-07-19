"""ILFRegulator — evaluates mutations against global coherence (T40)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MutationVerdict:
    approved: bool
    coherence_delta: float
    resilience_delta: float
    energy_delta: float
    overall_score: float
    reason: str = ""


class ILFRegulator:
    """Assesses mutations against the Informational Logical Field.

    Every mutation is evaluated on four axes:
    - Performance impact
    - Coherence (ILF) impact
    - Resilience impact
    - Energy impact

    The final decision prevents local improvements that degrade the global state.
    """

    def __init__(
        self,
        coherence_weight: float = 0.4,
        resilience_weight: float = 0.3,
        energy_weight: float = 0.2,
        performance_weight: float = 0.1,
        min_threshold: float = 0.3,
    ) -> None:
        self._coherence_weight = coherence_weight
        self._resilience_weight = resilience_weight
        self._energy_weight = energy_weight
        self._performance_weight = performance_weight
        self._min_threshold = min_threshold
        self._ilf_coherence: float = 1.0

    def update_coherence(self, ilf_coherence: float) -> None:
        self._ilf_coherence = ilf_coherence

    def assess(
        self,
        performance_impact: float,
        coherence_impact: float,
        resilience_impact: float,
        energy_impact: float,
    ) -> MutationVerdict:
        coherence_delta = coherence_impact * self._ilf_coherence
        score = (
            self._performance_weight * performance_impact
            + self._coherence_weight * coherence_delta
            + self._resilience_weight * resilience_impact
            - self._energy_weight * abs(energy_impact)
        )
        approved = score >= self._min_threshold
        return MutationVerdict(
            approved=approved,
            coherence_delta=coherence_delta,
            resilience_delta=resilience_impact,
            energy_delta=energy_impact,
            overall_score=score,
            reason="approved" if approved else f"score {score:.3f} below threshold {self._min_threshold}",
        )
