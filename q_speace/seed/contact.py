"""MS-3: SeedContactLayer — sandbox-only contact registry and assimilation gate (T220 §4 MS-3)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

from .constitution import ConstitutionalFault

AssimilationStatus = Literal["simulated", "assimilated", "rolled_back", "consolidated", "rejected"]
_FORBIDDEN_PROTOCOLS: frozenset[str] = frozenset(
    {"entanglement", "quantum-channel", "nonlocal", "raw-actuator", "rf-tx"}
)


@dataclass(frozen=True)
class ContactSpec:
    """Authorized contact point declaration (sandboxed simulators only in T220)."""

    contact_id: str
    protocol: str
    capabilities: tuple[str, ...]
    read_scope: tuple[str, ...]
    write_scope: tuple[str, ...] = ()
    estimated_cost_j: float = 1.0
    sandboxed: bool = True

    def __post_init__(self) -> None:
        if not self.contact_id or not self.protocol:
            raise ValueError("contact_id and protocol must be non-empty")
        if self.protocol.lower() in _FORBIDDEN_PROTOCOLS:
            raise ConstitutionalFault(
                f"forbidden contact protocol {self.protocol!r} (no-communication / sandbox invariant)"
            )
        if not self.sandboxed:
            raise ConstitutionalFault(
                f"non-sandboxed contact {self.contact_id!r} rejected (T220 sandbox-only invariant)"
            )
        if not math.isfinite(self.estimated_cost_j) or self.estimated_cost_j < 0.0:
            raise ValueError("estimated_cost_j must be finite and >= 0")


@dataclass(frozen=True)
class ContactPlan:
    """Declared assimilation plan requiring simulation and rollback before execution."""

    contact_id: str
    scope: tuple[str, ...]
    expected_value_j: float
    estimated_cost_j: float
    rollback_plan: str

    def __post_init__(self) -> None:
        if not self.contact_id or not self.scope:
            raise ValueError("contact_id and scope must be non-empty")
        if not math.isfinite(self.expected_value_j) or not math.isfinite(self.estimated_cost_j):
            raise ValueError("expected_value_j and estimated_cost_j must be finite")
        if self.estimated_cost_j < 0.0:
            raise ValueError("estimated_cost_j must be >= 0")
        if not self.rollback_plan.strip():
            raise ConstitutionalFault("contact plan rejected: rollback_plan is mandatory (I4)")


@dataclass(frozen=True)
class AssimilationResult:
    """Auditable outcome of a contact simulation, execution, rollback, or consolidation."""

    contact_id: str
    status: AssimilationStatus
    expected_value_j: float
    measured_value_j: float
    estimated_cost_j: float
    metabolic_surplus_j: float
    reason: str


@dataclass
class SeedContactLayer:
    """Registry of authorized sandboxed contacts enforcing simulation-before-execution."""

    max_contacts: int = 4
    _registry: dict[str, ContactSpec] = field(default_factory=dict)
    _simulated_plans: dict[str, ContactPlan] = field(default_factory=dict)
    _active_contacts: set[str] = field(default_factory=set)
    _consolidated_contacts: set[str] = field(default_factory=set)
    _audit_log: list[AssimilationResult] = field(default_factory=list)

    def register(self, spec: ContactSpec) -> None:
        if len(self._registry) >= self.max_contacts and spec.contact_id not in self._registry:
            raise ConstitutionalFault(f"contact cap reached ({self.max_contacts})")
        if not spec.sandboxed:
            raise ConstitutionalFault(f"contact {spec.contact_id!r} must be sandboxed")
        self._registry[spec.contact_id] = spec

    def registered_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._registry))

    def active_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._active_contacts))

    def consolidated_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._consolidated_contacts))

    def audit_log(self) -> tuple[AssimilationResult, ...]:
        return tuple(self._audit_log)

    def simulate_plan(self, plan: ContactPlan) -> AssimilationResult:
        """T217 simulation stage: verify authorization and positive expected metabolic surplus."""
        if plan.contact_id not in self._registry:
            res = AssimilationResult(
                contact_id=plan.contact_id,
                status="rejected",
                expected_value_j=plan.expected_value_j,
                measured_value_j=0.0,
                estimated_cost_j=plan.estimated_cost_j,
                metabolic_surplus_j=-plan.estimated_cost_j,
                reason="unregistered contact",
            )
            self._audit_log.append(res)
            return res

        surplus = plan.expected_value_j - plan.estimated_cost_j
        if surplus < 0.0:
            res = AssimilationResult(
                contact_id=plan.contact_id,
                status="rejected",
                expected_value_j=plan.expected_value_j,
                measured_value_j=0.0,
                estimated_cost_j=plan.estimated_cost_j,
                metabolic_surplus_j=surplus,
                reason="negative expected metabolic surplus",
            )
            self._audit_log.append(res)
            return res

        self._simulated_plans[plan.contact_id] = plan
        res = AssimilationResult(
            contact_id=plan.contact_id,
            status="simulated",
            expected_value_j=plan.expected_value_j,
            measured_value_j=plan.expected_value_j,
            estimated_cost_j=plan.estimated_cost_j,
            metabolic_surplus_j=surplus,
            reason="simulation passed",
        )
        self._audit_log.append(res)
        return res

    def execute_plan(self, contact_id: str, *, measured_value_j: float) -> AssimilationResult:
        """Execute a previously simulated plan; auto-rollback if measured surplus < 0."""
        if not math.isfinite(measured_value_j):
            raise ValueError("measured_value_j must be finite")
        plan = self._simulated_plans.get(contact_id)
        if plan is None:
            raise ConstitutionalFault(
                f"contact {contact_id!r} cannot execute before passing simulate_plan()"
            )
        surplus = measured_value_j - plan.estimated_cost_j
        if surplus < 0.0:
            self._active_contacts.discard(contact_id)
            res = AssimilationResult(
                contact_id=contact_id,
                status="rolled_back",
                expected_value_j=plan.expected_value_j,
                measured_value_j=measured_value_j,
                estimated_cost_j=plan.estimated_cost_j,
                metabolic_surplus_j=surplus,
                reason=f"value verification failed (surplus={surplus:.3f} < 0); rollback executed",
            )
            self._audit_log.append(res)
            return res

        self._active_contacts.add(contact_id)
        res = AssimilationResult(
            contact_id=contact_id,
            status="assimilated",
            expected_value_j=plan.expected_value_j,
            measured_value_j=measured_value_j,
            estimated_cost_j=plan.estimated_cost_j,
            metabolic_surplus_j=surplus,
            reason="measured value verified",
        )
        self._audit_log.append(res)
        return res

    def consolidate(self, contact_id: str, *, council_approved: bool) -> AssimilationResult:
        """Consolidate an assimilated contact only with explicit council approval."""
        if contact_id not in self._active_contacts:
            raise ConstitutionalFault(f"cannot consolidate non-assimilated contact {contact_id!r}")
        if not council_approved:
            raise ConstitutionalFault("consolidation requires explicit council approval")
        plan = self._simulated_plans[contact_id]
        self._consolidated_contacts.add(contact_id)
        res = AssimilationResult(
            contact_id=contact_id,
            status="consolidated",
            expected_value_j=plan.expected_value_j,
            measured_value_j=plan.expected_value_j,
            estimated_cost_j=plan.estimated_cost_j,
            metabolic_surplus_j=plan.expected_value_j - plan.estimated_cost_j,
            reason="consolidated with council approval and audit trail",
        )
        self._audit_log.append(res)
        return res
