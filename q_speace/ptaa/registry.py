"""T221-11: Distributed-style agent registry with dependency status propagation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .scc import AutonomyClass, PTAAViolationError, SCCProfile, SCCValidator

AgentStatus = Literal["active", "paused", "suspended", "terminated"]


@dataclass
class AgentRecord:
    """Registry record for one certified Track-A agent."""

    agent_id: str
    status: AgentStatus
    autonomy_class: AutonomyClass
    jurisdiction: str
    domains: tuple[str, ...]
    recognitions: set[str] = field(default_factory=set)
    dependencies: tuple[str, ...] = ()
    profile_hash: str = ""


class AgentRegistry:
    """Authoritative registry enforcing verified SCC profiles and dependency status propagation."""

    def __init__(self, validator: SCCValidator) -> None:
        self._validator = validator
        self._records: dict[str, AgentRecord] = {}

    def register(
        self,
        profile: SCCProfile,
        *,
        dependencies: tuple[str, ...] = (),
        recognitions: tuple[str, ...] = (),
    ) -> AgentRecord:
        self._validator.verify(profile)
        rec = AgentRecord(
            agent_id=profile.agent_id,
            status="active",
            autonomy_class=profile.autonomy_class,
            jurisdiction=profile.jurisdiction,
            domains=profile.domains,
            recognitions={profile.jurisdiction, *recognitions},
            dependencies=tuple(dependencies),
            profile_hash=profile.profile_hash(),
        )
        self._records[profile.agent_id] = rec
        return rec

    def get(self, agent_id: str) -> AgentRecord:
        if agent_id not in self._records:
            raise KeyError(f"unknown agent_id: {agent_id!r}")
        return self._records[agent_id]

    def all_records(self) -> tuple[AgentRecord, ...]:
        return tuple(self._records.values())

    def add_recognition(self, agent_id: str, jurisdiction: str) -> None:
        if not jurisdiction.strip():
            raise ValueError("jurisdiction must be non-empty")
        self.get(agent_id).recognitions.add(jurisdiction)

    def set_status(self, agent_id: str, new_status: AgentStatus) -> list[str]:
        """Update agent status and propagate suspension/termination to dependent agents."""
        rec = self.get(agent_id)
        if rec.status == "terminated" and new_status != "terminated":
            raise PTAAViolationError(f"terminated agent {agent_id!r} cannot be reactivated")
        rec.status = new_status
        affected = [agent_id]

        if new_status in ("suspended", "terminated"):
            propagated: AgentStatus = "suspended"
            queue = [agent_id]
            while queue:
                target = queue.pop(0)
                for other in self._records.values():
                    if target in other.dependencies and other.status == "active":
                        other.status = propagated
                        affected.append(other.agent_id)
                        queue.append(other.agent_id)
        return affected
