"""ActionProposal — structured action proposal with full safety metadata.

Carries an action through the full pipeline:
  PROPOSED → VALIDATED → SANDBOXED → APPROVED → EXECUTING → COMPLETED
                                                               → ROLLED_BACK
                                                               → FAILED
                                                               → VETOED
"""

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ActionRiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class ActionProposalStatus(str, Enum):
    PROPOSED = "proposed"
    VALIDATED = "validated"
    SANDBOXED = "sandboxed"
    VETOED = "vetoed"
    APPROVED = "approved"
    HUMAN_REVIEW = "human_review"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class ActionProposal(BaseModel):
    """A structured action proposal with full safety metadata."""

    proposal_id: str = Field(default_factory=lambda: f"AP-{uuid.uuid4().hex[:12]}")
    agent_id: str = ""
    action_type: str = ""
    action_category: str = ""
    target: str = ""
    operation: str = "set"  # "set", "scale", "enable", "disable", "write", "trigger"
    old_value: Any = None
    new_value: Any = None
    risk_level: ActionRiskLevel = ActionRiskLevel.LOW
    justification: str = ""
    evidence: Dict[str, Any] = Field(default_factory=dict)
    snapshot_pre: Dict[str, Any] = Field(default_factory=dict)
    snapshot_post: Dict[str, Any] = Field(default_factory=dict)
    mm_apr_verdict: Optional[Dict[str, Any]] = None
    sandbox_result: Optional[Dict[str, Any]] = None
    substrate_guard_report: Optional[Dict[str, Any]] = None
    human_approval: Optional[Dict[str, Any]] = None
    status: ActionProposalStatus = ActionProposalStatus.PROPOSED
    created_at: float = Field(default_factory=time.time)
    executed_at: Optional[float] = None
    completed_at: Optional[float] = None
    rollback_at: Optional[float] = None
    audit_trail: List[Dict[str, Any]] = Field(default_factory=list)

    def add_audit_entry(self, from_status: str, to_status: str, reason: str = "", details: Optional[Dict[str, Any]] = None) -> None:
        """Append an audit trail entry."""
        self.audit_trail.append({
            "from": from_status,
            "to": to_status,
            "reason": reason,
            "details": details or {},
            "ts": time.time(),
        })

    def transition_to(self, new_status: ActionProposalStatus, reason: str = "", details: Optional[Dict[str, Any]] = None) -> None:
        """Transition to a new status with audit trail."""
        self.add_audit_entry(self.status.value, new_status.value, reason, details)
        self.status = new_status

    model_config = {"use_enum_values": True}