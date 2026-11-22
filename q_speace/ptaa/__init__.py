"""PTAA Track-A governance demonstrator package (T221-10..17; A1–A4 only, zero A5 imports)."""

from __future__ import annotations

from .audit import AuditEntry, ExternalAuditReplica, PTAAAuditLog
from .delegation import DelegationToken, ScopeEnforcer
from .halt import HALT_SLA_SECONDS, HaltAction, HaltChannel, HaltDrillResult, HaltRuntime
from .incidents import IncidentRecord, IncidentSeverity, SharedIncidentRegistry
from .orchestration_sim import (
    CrossBorderTaskResult,
    DataExchangeContract,
    InstitutionalMetrics,
    OrchestrationSimulator,
)
from .registry import AgentRecord, AgentRegistry, AgentStatus
from .reversibility import ReversibilityManager, RollbackExemption, TransactionOutcome
from .scc import (
    ALLOWED_AUTONOMY_CLASSES,
    AutonomyClass,
    PTAAViolationError,
    SCCProfile,
    SCCValidator,
)

__all__ = [
    "ALLOWED_AUTONOMY_CLASSES",
    "AgentRecord",
    "AgentRegistry",
    "AgentStatus",
    "AuditEntry",
    "AutonomyClass",
    "CrossBorderTaskResult",
    "DataExchangeContract",
    "DelegationToken",
    "ExternalAuditReplica",
    "HALT_SLA_SECONDS",
    "HaltAction",
    "HaltChannel",
    "HaltDrillResult",
    "HaltRuntime",
    "IncidentRecord",
    "IncidentSeverity",
    "InstitutionalMetrics",
    "OrchestrationSimulator",
    "PTAAAuditLog",
    "PTAAViolationError",
    "ReversibilityManager",
    "RollbackExemption",
    "SCCProfile",
    "SCCValidator",
    "ScopeEnforcer",
    "SharedIncidentRegistry",
    "TransactionOutcome",
]
