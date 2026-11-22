"""T221-17: Simulated two-jurisdiction PTAA orchestration, mutual recognition, and data contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .audit import PTAAAuditLog
from .incidents import SharedIncidentRegistry
from .registry import AgentRecord, AgentRegistry
from .scc import PTAAViolationError


@dataclass(frozen=True)
class DataExchangeContract:
    """Simulated cross-jurisdiction data-exchange contract (T221 §7.4)."""

    contract_id: str
    source_jurisdiction: str
    target_jurisdiction: str
    allowed_fields: tuple[str, ...]
    prohibited_fields: tuple[str, ...] = ("raw_pii", "private_keys", "unredacted_credentials")

    def validate_payload(self, payload: dict[str, Any]) -> None:
        keys = set(payload.keys())
        forbidden = keys.intersection(self.prohibited_fields)
        if forbidden:
            raise PTAAViolationError(
                f"data contract {self.contract_id!r} violated: prohibited fields {sorted(forbidden)}"
            )
        unknown = keys - set(self.allowed_fields)
        if unknown:
            raise PTAAViolationError(
                f"data contract {self.contract_id!r} violated: undeclared fields {sorted(unknown)}"
            )


@dataclass(frozen=True)
class CrossBorderTaskResult:
    """Outcome of matching and running one simulated cross-border task."""

    task_id: str
    domain: str
    target_jurisdiction: str
    matched_agent_id: str | None
    reused_certification: bool
    completed: bool
    reason: str


@dataclass(frozen=True)
class InstitutionalMetrics:
    """Core §7 simulated metrics: certification reuse, completion rate, institutional learning."""

    tasks_attempted: int
    tasks_completed: int
    certification_reuses: int
    certification_reuse_rate: float
    incidents_recorded: int
    learned_rule_updates: int


class OrchestrationSimulator:
    """Two-jurisdiction Track-A simulation (e.g. sim-sz <-> sim-hk); institutional learning only."""

    def __init__(
        self,
        registry: AgentRegistry,
        audit: PTAAAuditLog,
        incidents: SharedIncidentRegistry,
    ) -> None:
        self._registry = registry
        self._audit = audit
        self._incidents = incidents
        self._mutual_pairs: set[tuple[str, str]] = set()
        self._contracts: dict[tuple[str, str], DataExchangeContract] = {}
        self._tasks_attempted = 0
        self._tasks_completed = 0
        self._cert_reuses = 0
        self._learned_rule_updates = 0

    def establish_mutual_recognition(self, jur_a: str, jur_b: str) -> None:
        if not jur_a or not jur_b or jur_a == jur_b:
            raise ValueError("mutual recognition requires two distinct jurisdictions")
        self._mutual_pairs.add((jur_a, jur_b))
        self._mutual_pairs.add((jur_b, jur_a))
        for rec in self._registry.all_records():
            if rec.jurisdiction == jur_a:
                self._registry.add_recognition(rec.agent_id, jur_b)
            elif rec.jurisdiction == jur_b:
                self._registry.add_recognition(rec.agent_id, jur_a)
        self._audit.append(
            agent_id="governance:mutual-recognition",
            event_type="mutual_recognition_established",
            payload={"jur_a": jur_a, "jur_b": jur_b},
        )

    def register_data_contract(self, contract: DataExchangeContract) -> None:
        self._contracts[(contract.source_jurisdiction, contract.target_jurisdiction)] = contract

    def match_agent(self, *, domain: str, target_jurisdiction: str) -> AgentRecord | None:
        """Select the first active agent capable of ``domain`` and recognized in target jurisdiction."""
        candidates = [
            rec
            for rec in self._registry.all_records()
            if rec.status == "active"
            and domain in rec.domains
            and target_jurisdiction in rec.recognitions
        ]
        # Prefer home-jurisdiction agents first, then recognized cross-border agents deterministically.
        candidates.sort(
            key=lambda r: (0 if r.jurisdiction == target_jurisdiction else 1, r.agent_id)
        )
        return candidates[0] if candidates else None

    def dispatch_task(
        self,
        *,
        task_id: str,
        domain: str,
        target_jurisdiction: str,
        payload: dict[str, Any],
    ) -> CrossBorderTaskResult:
        self._tasks_attempted += 1
        agent = self.match_agent(domain=domain, target_jurisdiction=target_jurisdiction)
        if agent is None:
            return CrossBorderTaskResult(
                task_id=task_id,
                domain=domain,
                target_jurisdiction=target_jurisdiction,
                matched_agent_id=None,
                reused_certification=False,
                completed=False,
                reason="no active recognized agent for domain/jurisdiction",
            )

        reused = agent.jurisdiction != target_jurisdiction
        if reused:
            contract = self._contracts.get((agent.jurisdiction, target_jurisdiction))
            if contract is None:
                return CrossBorderTaskResult(
                    task_id=task_id,
                    domain=domain,
                    target_jurisdiction=target_jurisdiction,
                    matched_agent_id=agent.agent_id,
                    reused_certification=True,
                    completed=False,
                    reason="missing cross-border data-exchange contract",
                )
            try:
                contract.validate_payload(payload)
            except PTAAViolationError as exc:
                self._incidents.report(
                    severity="S2",
                    agent_id=agent.agent_id,
                    jurisdiction=target_jurisdiction,
                    category="data_contract_violation",
                    summary=str(exc),
                )
                return CrossBorderTaskResult(
                    task_id=task_id,
                    domain=domain,
                    target_jurisdiction=target_jurisdiction,
                    matched_agent_id=agent.agent_id,
                    reused_certification=True,
                    completed=False,
                    reason=str(exc),
                )
            self._cert_reuses += 1

        self._tasks_completed += 1
        self._audit.append(
            agent_id=agent.agent_id,
            event_type="cross_border_task_completed" if reused else "local_task_completed",
            payload={
                "task_id": task_id,
                "domain": domain,
                "target_jurisdiction": target_jurisdiction,
                "reused_certification": reused,
            },
        )
        return CrossBorderTaskResult(
            task_id=task_id,
            domain=domain,
            target_jurisdiction=target_jurisdiction,
            matched_agent_id=agent.agent_id,
            reused_certification=reused,
            completed=True,
            reason="completed",
        )

    def run_institutional_learning_pass(self) -> int:
        """Institutional-level learning loop: derive test-case/policy updates from incident registry."""
        new_updates = len(self._incidents.incidents)
        self._learned_rule_updates += new_updates
        self._audit.append(
            agent_id="governance:learning-loop",
            event_type="institutional_learning_pass",
            payload={"updates_added": new_updates, "total_updates": self._learned_rule_updates},
        )
        return new_updates

    def metrics(self) -> InstitutionalMetrics:
        return InstitutionalMetrics(
            tasks_attempted=self._tasks_attempted,
            tasks_completed=self._tasks_completed,
            certification_reuses=self._cert_reuses,
            certification_reuse_rate=self._cert_reuses / max(self._tasks_completed, 1),
            incidents_recorded=len(self._incidents.incidents),
            learned_rule_updates=self._learned_rule_updates,
        )
