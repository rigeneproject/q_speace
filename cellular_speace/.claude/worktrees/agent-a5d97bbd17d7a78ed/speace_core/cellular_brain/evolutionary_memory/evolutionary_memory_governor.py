from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from speace_core.cellular_brain.evolutionary_kernel.evolutionary_cycle_models import (
    EvolutionCycleResult,
)
from speace_core.cellular_brain.evolutionary_kernel.multi_cycle_evolution_audit import (
    T56BAggregateVerdict,
)
from speace_core.cellular_brain.evolutionary_memory.consolidation_policy_engine import (
    ConsolidationPolicyEngine,
)
from speace_core.cellular_brain.evolutionary_memory.evolutionary_forgetting_engine import (
    EvolutionaryForgettingEngine,
)
from speace_core.cellular_brain.evolutionary_memory.evolutionary_memory_models import (
    ConsolidationDecision,
    EvolutionaryMemoryRecord,
    EvolutionaryMemoryStatus,
)
from speace_core.cellular_brain.evolutionary_memory.evolutionary_memory_store import (
    EvolutionaryMemoryStore,
)
from speace_core.cellular_brain.evolutionary_memory.memory_conflict_resolver import (
    MemoryConflictResolver,
)
from speace_core.cellular_brain.memory.morphology_events import MorphologyEvent, MorphologyEventType


class EvolutionaryMemoryGovernor:
    """T57 — Orchestrator for evolutionary memory governance."""

    def __init__(
        self,
        store: Optional[EvolutionaryMemoryStore] = None,
        consolidation: Optional[ConsolidationPolicyEngine] = None,
        conflict_resolver: Optional[MemoryConflictResolver] = None,
        forgetting_engine: Optional[EvolutionaryForgettingEngine] = None,
        report_dir: str = "reports/evolutionary_memory",
    ):
        self.store = store or EvolutionaryMemoryStore(report_dir=report_dir)
        self.consolidation = consolidation or ConsolidationPolicyEngine()
        self.conflict_resolver = conflict_resolver or MemoryConflictResolver()
        self.forgetting_engine = forgetting_engine or EvolutionaryForgettingEngine()
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Ingest
    # ------------------------------------------------------------------ #

    def ingest_cycle_result(self, result: EvolutionaryMemoryRecord) -> ConsolidationDecision:
        self.store.add_record(result)
        decision = self.consolidation.evaluate(result)
        if decision.previous_status != decision.new_status:
            self.store.update_status(result.record_id, decision.new_status, decision.reason)
        self._log_event(MorphologyEventType.EVOLUTIONARY_MEMORY_RECORD_INGESTED, result.record_id, decision.new_status)
        return decision

    def ingest_multi_cycle_audit_result(self, verdict: T56BAggregateVerdict) -> List[ConsolidationDecision]:
        decisions: List[ConsolidationDecision] = []
        for profile in verdict.profile_results:
            if profile.mce_result is None:
                continue
            record = EvolutionaryMemoryRecord(
                record_id=f"audit_{profile.profile_name}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                source_cycle_id="t56b",
                source_task="multi_cycle_audit",
                source_profile=profile.profile_name,
                fitness_delta=profile.cumulative_learning_score,
                drift_score=profile.drift_score,
                regression_score=profile.regression_pattern_count / max(1, profile.mce_result.consolidated.total_cycles),
                safety_score=1.0 - (profile.unsafe_cycle_count / max(1, profile.mce_result.consolidated.total_cycles)),
                confidence=profile.multi_cycle_validation_score,
                status=EvolutionaryMemoryStatus.VOLATILE.value,
            )
            decision = self.ingest_cycle_result(record)
            decisions.append(decision)
        return decisions

    # ------------------------------------------------------------------ #
    # Governance cycle
    # ------------------------------------------------------------------ #

    def run_governance_cycle(self) -> Dict[str, Any]:
        self._log_event(MorphologyEventType.EVOLUTIONARY_MEMORY_GOVERNANCE_STARTED, "governor", "cycle_started")
        records = self.store.list_records()

        # 1. Consolidation
        consolidation_decisions = self._consolidate_memory(records)
        for d in consolidation_decisions:
            if d.previous_status != d.new_status:
                self._log_event(
                    MorphologyEventType.EVOLUTIONARY_MEMORY_RECORD_PROMOTED if d.new_status in (EvolutionaryMemoryStatus.STABLE.value, EvolutionaryMemoryStatus.PROBATIONARY.value)
                    else MorphologyEventType.EVOLUTIONARY_MEMORY_RECORD_DEGRADED if d.new_status in (EvolutionaryMemoryStatus.DEPRECATED.value, EvolutionaryMemoryStatus.FORGOTTEN.value)
                    else MorphologyEventType.EVOLUTIONARY_MEMORY_RECORD_QUARANTINED,
                    d.record_id,
                    d.new_status,
                )

        # 2. Conflict resolution
        conflicts = self.conflict_resolver.detect_conflicts(records)
        resolved = 0
        for conflict in conflicts:
            winner_id = self.conflict_resolver.resolve_conflict(conflict, self.store._records)
            if winner_id:
                resolved += 1
                self.store.increment_reuse(winner_id)
            self._log_event(MorphologyEventType.EVOLUTIONARY_MEMORY_CONFLICT_DETECTED, conflict.conflict_id, conflict.conflict_type)

        # 3. Forgetting
        forgetting_decisions = self.forgetting_engine.apply_forgetting_policy(records)
        for d in forgetting_decisions:
            self._log_event(MorphologyEventType.EVOLUTIONARY_MEMORY_RECORD_FORGOTTEN, d.record_id, d.reason)

        self._log_event(MorphologyEventType.EVOLUTIONARY_MEMORY_GOVERNANCE_COMPLETED, "governor", "cycle_completed")
        return {
            "consolidation_decisions": len(consolidation_decisions),
            "conflicts_detected": len(conflicts),
            "conflicts_resolved": resolved,
            "forgotten_records": len(forgetting_decisions),
        }

    def _consolidate_memory(self, records: List[EvolutionaryMemoryRecord]) -> List[ConsolidationDecision]:
        decisions: List[ConsolidationDecision] = []
        for record in records:
            # Skip frozen and forgotten
            if record.status in (EvolutionaryMemoryStatus.FROZEN_POLICY.value, EvolutionaryMemoryStatus.FORGOTTEN.value):
                continue
            decision = self.consolidation.evaluate(record)
            if decision.previous_status != decision.new_status:
                self.store.update_status(record.record_id, decision.new_status, decision.reason)
                decisions.append(decision)
        return decisions

    # ------------------------------------------------------------------ #
    # Reports
    # ------------------------------------------------------------------ #

    def generate_governance_report(self) -> Path:
        return self.store.export_markdown()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _log_event(self, event_type: MorphologyEventType, source_id: str, detail: str) -> None:
        pass  # Events are logged externally via orchestrator memory when available
