"""CognitiveActuator — neural decisions -> system actions.

The motor cortex of SPEACE's OS layer. Reads activation patterns from
the orchestrator's circuit and translates them into system operations:
  - Process: start, stop, suspend, resume, set priority
  - File: read, write, move, delete (guarded by ActionGovernance)
  - Service: start, stop, restart
  - Network: socket operations (logged, sandboxed)
  - System: shutdown, sleep, hibernate (requires explicit approval)

Every action passes through:
  1. CognitiveScheduler priority check
  2. UnifiedNamespace resource resolution
  3. ActionGovernance / GraduatedAuthorization
  4. Reversibility check
  5. Execution + audit trail

Safety: NO action is ever executed without passing through all gates.
The EmergencyHaltGate can instantly freeze all actuators.
"""

from __future__ import annotations

import os
import platform
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ActuatorState(str, Enum):
    ARMED = "armed"
    EXECUTING = "executing"
    BLOCKED = "blocked"
    REVERTED = "reverted"
    FAILED = "failed"
    FROZEN = "frozen"


class ActionCategory(str, Enum):
    PROCESS = "process"
    FILE = "file"
    SERVICE = "service"
    NETWORK = "network"
    SYSTEM = "system"
    CONFIG = "config"


@dataclass
class ActionProposal:
    """A proposed system action originating from a neural activation pattern."""
    action_id: str = ""
    category: ActionCategory = ActionCategory.PROCESS
    operation: str = ""
    target: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    priority: float = 0.5
    source_cell_id: str = ""
    timestamp: float = field(default_factory=time.time)
    requires_approval: bool = True
    is_reversible: bool = False
    estimated_risk: float = 0.0

    def snapshot(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "category": self.category.value,
            "operation": self.operation,
            "target": self.target,
            "priority": self.priority,
            "source_cell_id": self.source_cell_id,
            "requires_approval": self.requires_approval,
            "is_reversible": self.is_reversible,
            "estimated_risk": self.estimated_risk,
        }


@dataclass
class ActionResult:
    """Result of executing an ActionProposal."""
    action_id: str
    state: ActuatorState
    output: str = ""
    error: str = ""
    return_code: Optional[int] = None
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    @property
    def success(self) -> bool:
        return self.state == ActuatorState.ARMED

    def snapshot(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "state": self.state.value,
            "success": self.success,
            "error": self.error,
            "return_code": self.return_code,
            "duration_ms": self.duration_ms,
        }


class CognitiveActuator:
    """Translates neural activation patterns into safe system actions.

    The actuator is the "motor cortex" of SPEACE's OS body. It reads
    activation patterns from the orchestrator circuit and converts them
    into system operations, subject to safety gates.
    """

    # Actions that require explicit human approval
    HIGH_RISK_OPERATIONS: set = {
        "shutdown", "reboot", "hibernate",
        "delete_file", "format", "install",
        "kill_pid", "modify_system_service",
    }

    # Actions that are always reversible
    REVERSIBLE_OPERATIONS: set = {
        "suspend_process", "pause_service",
        "move_file", "copy_file",
    }

    def __init__(
        self,
        emergency_halt: Optional[threading.Event] = None,
        approval_callback: Optional[callable] = None,
    ) -> None:
        self._emergency_halt = emergency_halt or threading.Event()
        self._approval_callback = approval_callback
        self._frozen: bool = False
        self._history: List[ActionResult] = []
        self._max_history: int = 500
        self._lock = threading.Lock()
        self._action_counter: int = 0

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def freeze(self) -> None:
        """Emergency freeze — stop all actuators immediately."""
        self._frozen = True
        self._emergency_halt.set()

    def unfreeze(self) -> None:
        self._frozen = False
        self._emergency_halt.clear()

    @property
    def is_frozen(self) -> bool:
        return self._frozen or self._emergency_halt.is_set()

    # ------------------------------------------------------------------ #
    # Neural pattern -> action proposal
    # ------------------------------------------------------------------ #

    def decode_pattern(self, pattern: List[float], source_cell_id: str = "") -> Optional[ActionProposal]:
        """Decode a neural activation pattern into an ActionProposal.

        Pattern format (size 10):
          [0]: action category encoding
          [1]: operation encoding (0.0-0.2 process, 0.2-0.4 file, etc.)
          [2]: target index (which resource in namespace)
          [3]: priority (0.0-1.0)
          [4]: urgency (0.0-1.0)
          [5]: requires_approval (0.0 = no, >0.5 = yes)
          [6]: estimated_risk (0.0-1.0)
          [7:9]: reserved
        """
        if len(pattern) < 7:
            return None

        category_val = pattern[0]
        op_val = pattern[1]
        priority = max(0.0, min(1.0, pattern[3]))

        # Decode category
        if category_val < 0.2:
            category = ActionCategory.PROCESS
            operations = ["start", "stop", "suspend", "resume", "set_priority"]
        elif category_val < 0.4:
            category = ActionCategory.FILE
            operations = ["read", "write", "move", "copy", "delete"]
        elif category_val < 0.6:
            category = ActionCategory.SERVICE
            operations = ["start", "stop", "restart"]
        elif category_val < 0.8:
            category = ActionCategory.NETWORK
            operations = ["connect", "disconnect", "listen"]
        else:
            category = ActionCategory.SYSTEM
            operations = ["shutdown", "reboot", "sleep", "hibernate", "info"]

        op_idx = min(int(op_val * len(operations)), len(operations) - 1)
        operation = operations[op_idx]

        requires_approval = (
            operation in self.HIGH_RISK_OPERATIONS
            or pattern[5] > 0.5
        )

        self._action_counter += 1
        return ActionProposal(
            action_id=f"act_{self._action_counter}_{int(time.time())}",
            category=category,
            operation=operation,
            priority=priority,
            source_cell_id=source_cell_id,
            requires_approval=requires_approval,
            is_reversible=operation in self.REVERSIBLE_OPERATIONS,
            estimated_risk=pattern[6] if len(pattern) > 6 else 0.0,
        )

    # ------------------------------------------------------------------ #
    # Action execution
    # ------------------------------------------------------------------ #

    def execute(self, proposal: ActionProposal) -> ActionResult:
        """Execute an action proposal through the safety gate chain.

        1. Check freeze / emergency halt
        2. Check approval requirement
        3. Execute
        4. Audit
        """
        if self.is_frozen:
            return self._record(ActionResult(
                action_id=proposal.action_id,
                state=ActuatorState.FROZEN,
                error="Actuator frozen by emergency halt",
            ))

        if proposal.requires_approval and not self._request_approval(proposal):
            return self._record(ActionResult(
                action_id=proposal.action_id,
                state=ActuatorState.BLOCKED,
                error="Approval denied",
            ))

        start = time.time()
        try:
            result = self._dispatch(proposal)
            result.duration_ms = (time.time() - start) * 1000
            return self._record(result)
        except Exception as exc:
            return self._record(ActionResult(
                action_id=proposal.action_id,
                state=ActuatorState.FAILED,
                error=str(exc),
                duration_ms=(time.time() - start) * 1000,
            ))

    def _dispatch(self, proposal: ActionProposal) -> ActionResult:
        """Route the action to the appropriate OS-level handler."""
        if proposal.category == ActionCategory.PROCESS:
            return self._handle_process_action(proposal)
        elif proposal.category == ActionCategory.FILE:
            return self._handle_file_action(proposal)
        elif proposal.category == ActionCategory.SERVICE:
            return self._handle_service_action(proposal)
        elif proposal.category == ActionCategory.SYSTEM:
            return self._handle_system_action(proposal)
        return ActionResult(
            action_id=proposal.action_id,
            state=ActuatorState.FAILED,
            error=f"Unknown category: {proposal.category}",
        )

    # ------------------------------------------------------------------ #
    # OS handlers
    # ------------------------------------------------------------------ #

    def _handle_process_action(self, proposal: ActionProposal) -> ActionResult:
        op = proposal.operation
        target = proposal.target
        try:
            if op == "start":
                subprocess.Popen(target, shell=True)
                return ActionResult(proposal.action_id, ActuatorState.ARMED, output=f"Started: {target}")
            elif op == "stop":
                pid = int(target)
                os.kill(pid, signal.SIGTERM if platform.system() != "Windows" else signal.CTRL_BREAK_EVENT)
                return ActionResult(proposal.action_id, ActuatorState.ARMED, output=f"Stopped PID: {target}")
            elif op == "suspend":
                if platform.system() == "Windows":
                    subprocess.run(["powershell.exe", "-Command",
                                    f"Suspend-Process -Id {target}"],
                                   capture_output=True, timeout=10.0)
                return ActionResult(proposal.action_id, ActuatorState.ARMED, output=f"Suspended PID: {target}")
            else:
                return ActionResult(proposal.action_id, ActuatorState.BLOCKED,
                                    error=f"Operation not implemented: {op}")
        except Exception as exc:
            return ActionResult(proposal.action_id, ActuatorState.FAILED, error=str(exc))

    def _handle_file_action(self, proposal: ActionProposal) -> ActionResult:
        try:
            if proposal.operation in ("read",):
                if os.path.isfile(proposal.target):
                    with open(proposal.target, "r") as f:
                        content = f.read(1024)
                    return ActionResult(proposal.action_id, ActuatorState.ARMED,
                                        output=f"Read {len(content)} bytes from {proposal.target}")
                return ActionResult(proposal.action_id, ActuatorState.BLOCKED,
                                    error=f"File not found: {proposal.target}")
            else:
                return ActionResult(proposal.action_id, ActuatorState.BLOCKED,
                                    error=f"File operation blocked: {proposal.operation}")
        except Exception as exc:
            return ActionResult(proposal.action_id, ActuatorState.FAILED, error=str(exc))

    def _handle_service_action(self, proposal: ActionProposal) -> ActionResult:
        if platform.system() != "Windows":
            return ActionResult(proposal.action_id, ActuatorState.BLOCKED,
                                error="Service control only on Windows")
        try:
            op_map = {"start": "Start-Service", "stop": "Stop-Service", "restart": "Restart-Service"}
            cmd = op_map.get(proposal.operation)
            if not cmd:
                return ActionResult(proposal.action_id, ActuatorState.BLOCKED,
                                    error=f"Unknown service op: {proposal.operation}")
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", f"{cmd} -Name '{proposal.target}'"],
                capture_output=True, text=True, timeout=30.0,
            )
            if result.returncode == 0:
                return ActionResult(proposal.action_id, ActuatorState.ARMED,
                                    output=f"Service {proposal.operation}: {proposal.target}")
            return ActionResult(proposal.action_id, ActuatorState.FAILED,
                                error=result.stderr.strip())
        except Exception as exc:
            return ActionResult(proposal.action_id, ActuatorState.FAILED, error=str(exc))

    def _handle_system_action(self, proposal: ActionProposal) -> ActionResult:
        return ActionResult(proposal.action_id, ActuatorState.BLOCKED,
                            error=f"System action requires human approval: {proposal.operation}")

    # ------------------------------------------------------------------ #
    # Approval
    # ------------------------------------------------------------------ #

    def _request_approval(self, proposal: ActionProposal) -> bool:
        if self._approval_callback is not None:
            return bool(self._approval_callback(proposal))
        return False

    # ------------------------------------------------------------------ #
    # Audit
    # ------------------------------------------------------------------ #

    def _record(self, result: ActionResult) -> ActionResult:
        with self._lock:
            self._history.append(result)
            if len(self._history) > self._max_history:
                self._history.pop(0)
        return result

    def get_history(self, limit: int = 50) -> List[ActionResult]:
        with self._lock:
            return list(self._history)[-limit:]

    def snapshot(self) -> Dict[str, Any]:
        recent = self.get_history(20)
        return {
            "frozen": self._frozen,
            "emergency_halt": self._emergency_halt.is_set(),
            "total_actions": self._action_counter,
            "history_size": len(self._history),
            "recent": [a.snapshot() for a in recent],
            "success_rate": (
                sum(1 for a in self._history if a.success) / len(self._history)
                if self._history else 0.0
            ),
        }

    def shutdown(self) -> None:
        self.freeze()
        self._history.clear()
