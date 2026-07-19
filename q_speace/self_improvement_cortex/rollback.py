"""RollbackManager — automatic rollback on metric degradation (T39)."""
from __future__ import annotations

from dataclasses import dataclass

from .dna_registry import DNAMutationRecord, MutationRegistry
from .epigenetics import EpigeneticEngine


@dataclass
class RollbackPlan:
    mutation_id: str
    reason: str
    degraded_metrics: dict[str, float]
    threshold_deltas: dict[str, float]
    safe: bool = False

    @property
    def is_actionable(self) -> bool:
        return self.safe and bool(self.degraded_metrics)


class RollbackManager:
    """Monitors metrics and triggers rollback when degradation is detected."""

    def __init__(
        self,
        mutation_registry: MutationRegistry,
        epigenetic_engine: EpigeneticEngine,
        thresholds: dict[str, float] | None = None,
    ) -> None:
        self._registry = mutation_registry
        self._epigenetics = epigenetic_engine
        self._thresholds = thresholds or {
            "coherence_phi": -0.15,
            "mean_energy_w": 2.0,
            "goal_completion": -0.2,
            "resilience": -0.15,
        }

    def evaluate(self, mutation: DNAMutationRecord, current_metrics: dict[str, float]) -> RollbackPlan | None:
        degraded = {}
        for metric, threshold in self._thresholds.items():
            before = mutation.metrics_before.get(metric)
            after = current_metrics.get(metric)
            if before is None or after is None:
                continue
            delta = after - before
            if metric in ("mean_energy_w", "energy_consumption", "prediction_error"):
                if delta > threshold:
                    degraded[metric] = delta
            else:
                if delta < threshold:
                    degraded[metric] = delta

        if not degraded:
            return None

        safe = self._safety_check(mutation)
        return RollbackPlan(
            mutation_id=mutation.mutation_id,
            reason=f"degraded metrics: {degraded}",
            degraded_metrics=degraded,
            threshold_deltas=self._thresholds,
            safe=safe,
        )

    def _safety_check(self, mutation: DNAMutationRecord) -> bool:
        epi_state = self._epigenetics.state_of(mutation.mutation_id)
        if epi_state is None:
            return True
        if epi_state.consolidated:
            return False
        return self._epigenetics.should_rollback(mutation.mutation_id)

    def execute(self, plan: RollbackPlan) -> bool:
        return plan.is_actionable
