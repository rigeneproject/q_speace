"""T221-15 (I4): Transactional wrappers, compensating actions, rollback drills, exemptions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .audit import PTAAAuditLog
from .scc import PTAAViolationError


@dataclass(frozen=True)
class RollbackExemption:
    """Explicitly approved exemption for an inherently irreversible action."""

    action_id: str
    approved_by: str
    justification: str


@dataclass(frozen=True)
class TransactionOutcome:
    """Outcome of a transactional action execution or rollback drill."""

    tx_id: str
    agent_id: str
    committed: bool
    rolled_back: bool
    result: Any = None
    error: str | None = None


class ReversibilityManager:
    """Wraps agent actions with mandatory compensating rollback unless explicitly exempted."""

    def __init__(self, audit: PTAAAuditLog) -> None:
        self._audit = audit
        self._exemptions: dict[str, RollbackExemption] = {}

    def register_exemption(self, exemption: RollbackExemption) -> None:
        if not exemption.action_id or not exemption.approved_by or not exemption.justification:
            raise ValueError("exemption requires action_id, approved_by, and justification")
        self._exemptions[exemption.action_id] = exemption
        self._audit.append(
            agent_id="governance",
            event_type="reversibility_exemption",
            payload={
                "action_id": exemption.action_id,
                "approved_by": exemption.approved_by,
            },
        )

    def execute_transactional(
        self,
        *,
        tx_id: str,
        agent_id: str,
        action_id: str,
        forward_fn: Callable[[], Any],
        compensate_fn: Callable[[], None] | None,
        post_check: Callable[[Any], bool] | None = None,
    ) -> TransactionOutcome:
        if compensate_fn is None and action_id not in self._exemptions:
            raise PTAAViolationError(
                f"I4 violation: action {action_id!r} lacks compensating rollback and has no exemption"
            )
        try:
            res = forward_fn()
            if post_check is not None and not post_check(res):
                raise RuntimeError("post_check failed")
        except Exception as exc:  # noqa: BLE001 — trigger compensating rollback on any failure
            rolled = False
            if compensate_fn is not None:
                compensate_fn()
                rolled = True
            self._audit.append(
                agent_id=agent_id,
                event_type="tx_rolled_back",
                payload={"tx_id": tx_id, "action_id": action_id, "error": str(exc)},
            )
            return TransactionOutcome(
                tx_id=tx_id,
                agent_id=agent_id,
                committed=False,
                rolled_back=rolled,
                error=str(exc),
            )

        self._audit.append(
            agent_id=agent_id,
            event_type="tx_committed",
            payload={"tx_id": tx_id, "action_id": action_id},
        )
        return TransactionOutcome(
            tx_id=tx_id,
            agent_id=agent_id,
            committed=True,
            rolled_back=False,
            result=res,
        )
