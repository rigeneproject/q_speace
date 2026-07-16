"""EmbodiedActionActuator — the "muscles" of SPEACE.

Acts on the physical body (the computer) in a sandboxed, reversible, auditable way.
Every action passes through ActionGovernance for safety.
"""

from __future__ import annotations

import re
import subprocess
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from speace_core.cellular_brain.memory.morphology_events import (
    MorphologyEvent,
    MorphologyEventType,
)

try:
    from speace_core.cellular_brain.action_governance.action_governance_models import (
        ActionGovernanceDecision,
        ExternalActionProposal,
        ExternalActionType,
    )
    from speace_core.cellular_brain.action_governance.action_policy_engine import (
        ActionPolicyEngine,
    )
    from speace_core.cellular_brain.action_governance.action_risk_classifier import (
        ActionRiskClassifier,
    )
    from speace_core.cellular_brain.action_governance.reversibility_analyzer import (
        ReversibilityAnalyzer,
    )

    _GOVERNANCE_AVAILABLE = True
except ImportError:  # pragma: no cover
    _GOVERNANCE_AVAILABLE = False


class ActionOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    BLOCKED = "blocked"
    REVERTED = "reverted"


class EmbodiedActionActuator:
    """Sandboxed actuator for file-system and process-level embodied actions."""

    DANGEROUS_ACTIONS = {"execute_command", "delete_file"}
    ALLOWED_SUBDIRS = {"data", "reports", "logs", "temp"}
    ALLOWED_CMD_PATTERNS = [
        r"^echo\s+",
        r"^cat\s+",
        r"^type\s*",
        r"^dir\s*",
        r"^python\s+-c\s+",
        r"^pytest\s+",
    ]
    BLOCKED_CMD_FRAGMENTS = ["rm", "del", "format", "mkfs", "dd", "sudo"]

    def __init__(self, project_root: Optional[Path] = None) -> None:
        if project_root is None:
            # Four parents up from this file: speace_core/cellular_brain/embodiment/ -> project root
            self.project_root = Path(__file__).resolve().parents[3]
        else:
            self.project_root = Path(project_root).resolve()

        self._queue: List[Dict[str, Any]] = []
        self._history: List[Dict[str, Any]] = []
        self._proposals: Dict[str, Dict[str, Any]] = {}

        if _GOVERNANCE_AVAILABLE:
            self._risk_classifier = ActionRiskClassifier()
            self._reversibility_analyzer = ReversibilityAnalyzer()
            self._policy_engine = ActionPolicyEngine()
        else:
            self._risk_classifier = None
            self._reversibility_analyzer = None
            self._policy_engine = None

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _is_allowed_path(self, path: str) -> bool:
        """Verify that *path* resolves inside one of the allowed sub-directories."""
        try:
            target = Path(path).resolve()
        except (OSError, ValueError):
            return False

        # Reject paths that escape the project root entirely
        try:
            target.relative_to(self.project_root)
        except ValueError:
            return False

        for subdir in self.ALLOWED_SUBDIRS:
            allowed = (self.project_root / subdir).resolve()
            try:
                target.relative_to(allowed)
                return True
            except ValueError:
                continue
        return False

    def _is_safe_command(self, cmd: str) -> bool:
        """Sanity-check a shell command before execution."""
        stripped = cmd.strip().lower()

        # Reject redirection that would overwrite files
        if ">|" in cmd:
            return False

        # Reject blocked fragments
        for frag in self.BLOCKED_CMD_FRAGMENTS:
            if frag.lower() in stripped:
                return False

        # Reject PowerShell -Command with dangerous patterns
        if re.search(r"powershell\s+-command", stripped):
            return False

        # Must match an allowed prefix
        for pattern in self.ALLOWED_CMD_PATTERNS:
            if re.match(pattern, stripped):
                return True

        return False

    def _log_event(
        self,
        event_type: MorphologyEventType,
        action_id: str,
        metadata: Dict[str, Any],
    ) -> MorphologyEvent:
        event = MorphologyEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            event_type=event_type,
            timestamp=time.time(),
            source_id="embodied_action_actuator",
            target_id=action_id,
            metadata=metadata,
        )
        # In a full system this would be published to the event bus.
        return event

    def _build_external_proposal(
        self,
        proposal_id: str,
        action_type: str,
        params: Dict[str, Any],
    ) -> ExternalActionProposal:
        """Map an actuator action to an ExternalActionProposal for governance review."""
        if action_type in ("read_file", "list_directory", "monitor_process"):
            ext_type = ExternalActionType.OBSERVE_ONLY
            estimated_risk = 0.0
        elif action_type in ("write_text_file", "create_directory", "send_signal_to_self"):
            ext_type = ExternalActionType.RECONFIGURE_SIMULATED
            estimated_risk = 0.3
        elif action_type == "delete_file":
            ext_type = ExternalActionType.ISOLATE_SIMULATED
            estimated_risk = 0.6
        elif action_type == "execute_command":
            ext_type = ExternalActionType.RESOURCE_SHIFT_SIMULATED
            estimated_risk = 0.5
        else:
            ext_type = ExternalActionType.UNKNOWN
            estimated_risk = 0.5

        return ExternalActionProposal(
            proposal_id=proposal_id,
            action_type=ext_type,
            title=f"Embodied action: {action_type}",
            description=f"Actuator action {action_type}",
            simulated_only=True,
            requested_real_execution=False,
            estimated_risk=estimated_risk,
            estimated_urgency=0.3,
            estimated_benefit=0.3,
            uncertainty_score=0.1,
            metadata={"actuator_action_type": action_type, "params": params},
        )

    # ------------------------------------------------------------------ #
    # Core API
    # ------------------------------------------------------------------ #

    def propose_action(self, action_type: str, params: Dict[str, Any]) -> str:
        """Queue an action proposal and optionally run governance screening."""
        proposal_id = f"prop_{uuid.uuid4().hex[:8]}"
        proposal: Dict[str, Any] = {
            "proposal_id": proposal_id,
            "action_type": action_type,
            "params": params,
            "status": "proposed",
            "governance_decision": None,
        }

        # Governance integration
        if _GOVERNANCE_AVAILABLE and self._policy_engine is not None:
            ext = self._build_external_proposal(proposal_id, action_type, params)
            risk = self._risk_classifier.classify_action_risk(ext)
            rev = self._reversibility_analyzer.assess_reversibility(ext)
            decision = self._policy_engine.evaluate_action_proposal(ext, risk, rev)
            proposal["governance_decision"] = decision.model_dump()

            if decision.blocked:
                proposal["status"] = "blocked"
                self._log_event(
                    MorphologyEventType.ACTION_BLOCKED,
                    proposal_id,
                    {"reason": decision.blocked_reason, "action_type": action_type},
                )
                self._history.append(
                    {
                        "proposal_id": proposal_id,
                        "action_type": action_type,
                        "params": params,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "outcome": ActionOutcome.BLOCKED,
                        "error": decision.blocked_reason,
                        "reverted": False,
                    }
                )
                self._proposals[proposal_id] = proposal
                return proposal_id

        self._queue.append(proposal)
        self._proposals[proposal_id] = proposal
        return proposal_id

    def approve_action(
        self, proposal_id: str, approval_level: str = "automatic"
    ) -> Dict[str, Any]:
        """Approve and execute a previously proposed action."""
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return {
                "success": False,
                "error": "proposal_not_found",
                "proposal_id": proposal_id,
            }
        if proposal["status"] == "blocked":
            return {
                "success": False,
                "error": "proposal_blocked_by_governance",
                "proposal_id": proposal_id,
            }
        if proposal["status"] != "proposed":
            return {
                "success": False,
                "error": "proposal_already_processed",
                "proposal_id": proposal_id,
            }

        # Remove from queue
        self._queue = [
            p for p in self._queue if p["proposal_id"] != proposal_id
        ]
        return self.execute_action(
            proposal["action_type"],
            proposal["params"],
            approval_level=approval_level,
            proposal_id=proposal_id,
        )

    def _mark_proposal_processed(self, proposal_id: Optional[str]) -> None:
        if proposal_id is not None and proposal_id in self._proposals:
            self._proposals[proposal_id]["status"] = "completed"

    def execute_action(
        self,
        action_type: str,
        params: Dict[str, Any],
        approval_level: str = "automatic",
        proposal_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute an action immediately with the given approval level."""
        action_id = proposal_id or f"act_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now(timezone.utc).isoformat()

        # Early command-safety gate for execute_command (blocks unsafe commands
        # regardless of approval level).
        if action_type == "execute_command":
            if not self._is_safe_command(params.get("cmd", "")):
                self._log_event(
                    MorphologyEventType.ACTION_BLOCKED,
                    action_id,
                    {
                        "reason": "command_blocked_by_safety_policy",
                        "action_type": action_type,
                    },
                )
                record = {
                    "proposal_id": proposal_id,
                    "action_type": action_type,
                    "params": params,
                    "timestamp": timestamp,
                    "outcome": ActionOutcome.BLOCKED,
                    "error": "command_blocked_by_safety_policy",
                    "reverted": False,
                }
                self._history.append(record)
                self._mark_proposal_processed(proposal_id)
                return {
                    "success": False,
                    "error": "command_blocked_by_safety_policy",
                    "action_id": action_id,
                }

        # Dangerous-action gate
        if action_type in self.DANGEROUS_ACTIONS and approval_level != "human_review":
            self._log_event(
                MorphologyEventType.ACTION_BLOCKED,
                action_id,
                {
                    "reason": "dangerous_action_requires_human_review",
                    "action_type": action_type,
                },
            )
            record = {
                "proposal_id": proposal_id,
                "action_type": action_type,
                "params": params,
                "timestamp": timestamp,
                "outcome": ActionOutcome.BLOCKED,
                "error": "dangerous_action_requires_human_review",
                "reverted": False,
            }
            self._history.append(record)
            self._mark_proposal_processed(proposal_id)
            return {
                "success": False,
                "error": "dangerous_action_requires_human_review",
                "action_id": action_id,
            }

        try:
            result = self._perform_action(action_type, params)
            outcome = ActionOutcome.SUCCESS
            error = None
            self._log_event(
                MorphologyEventType.ACTION_EXECUTED,
                action_id,
                {"action_type": action_type, "result_summary": str(result)[:200]},
            )
        except Exception as exc:
            result = None
            outcome = ActionOutcome.FAILURE
            error = str(exc)
            self._log_event(
                MorphologyEventType.ACTION_BLOCKED,
                action_id,
                {"action_type": action_type, "error": error},
            )

        record = {
            "proposal_id": proposal_id,
            "action_type": action_type,
            "params": params,
            "timestamp": timestamp,
            "outcome": outcome,
            "error": error,
            "reverted": False,
            "result": result,
        }
        self._history.append(record)
        self._mark_proposal_processed(proposal_id)
        return {
            "success": outcome == ActionOutcome.SUCCESS,
            "result": result,
            "error": error,
            "action_id": action_id,
        }

    # ------------------------------------------------------------------ #
    # Action primitives
    # ------------------------------------------------------------------ #

    def _perform_action(self, action_type: str, params: Dict[str, Any]) -> Any:
        if action_type == "write_text_file":
            return self._act_write_text_file(params)
        if action_type == "read_file":
            return self._act_read_file(params)
        if action_type == "list_directory":
            return self._act_list_directory(params)
        if action_type == "execute_command":
            return self._act_execute_command(params)
        if action_type == "create_directory":
            return self._act_create_directory(params)
        if action_type == "delete_file":
            return self._act_delete_file(params)
        if action_type == "monitor_process":
            return self._act_monitor_process(params)
        if action_type == "send_signal_to_self":
            return self._act_send_signal_to_self(params)
        raise ValueError(f"unknown_action_type: {action_type}")

    def _act_write_text_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = params["path"]
        content = params["content"]
        if not self._is_allowed_path(path):
            raise ValueError("path_outside_allowed_directories")
        if len(content.encode("utf-8")) > 1_048_576:
            raise ValueError("content_exceeds_1mb")
        target = Path(path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        backup = None
        if target.exists():
            backup = target.read_text(encoding="utf-8")
        target.write_text(content, encoding="utf-8")
        return {
            "path": str(target),
            "bytes_written": len(content.encode("utf-8")),
            "backup": backup,
        }

    def _act_read_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = params["path"]
        if not self._is_allowed_path(path):
            raise ValueError("path_outside_allowed_directories")
        target = Path(path).resolve()
        content = target.read_text(encoding="utf-8")
        return {"path": str(target), "content": content}

    def _act_list_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = params["path"]
        if not self._is_allowed_path(path):
            raise ValueError("path_outside_allowed_directories")
        target = Path(path).resolve()
        entries = [e.name for e in target.iterdir()]
        return {"path": str(target), "entries": entries}

    def _act_execute_command(self, params: Dict[str, Any]) -> Dict[str, Any]:
        cmd = params["cmd"]
        timeout = params.get("timeout", 5)
        if not self._is_safe_command(cmd):
            raise ValueError("command_blocked_by_safety_policy")
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    def _act_create_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = params["path"]
        if not self._is_allowed_path(path):
            raise ValueError("path_outside_allowed_directories")
        target = Path(path).resolve()
        existed = target.exists()
        target.mkdir(parents=True, exist_ok=True)
        return {"path": str(target), "existed": existed}

    def _act_delete_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        path = params["path"]
        if not self._is_allowed_path(path):
            raise ValueError("path_outside_allowed_directories")
        target = Path(path).resolve()
        # Wildcard guard (must run before is_file because wildcards never resolve to real files)
        if "*" in str(target.name) or "?" in str(target.name):
            raise ValueError("wildcards_not_allowed")
        if not target.is_file():
            raise ValueError("not_a_file_or_does_not_exist")
        backup = target.read_bytes()
        target.unlink()
        return {"path": str(target), "backup": backup}

    def _act_monitor_process(self, params: Dict[str, Any]) -> Dict[str, Any]:
        pid = params["pid"]
        try:
            import psutil

            proc = psutil.Process(pid)
            return {
                "pid": pid,
                "name": proc.name(),
                "status": proc.status(),
                "cpu_percent": proc.cpu_percent(interval=0.1),
                "memory_info": str(proc.memory_info()),
            }
        except ImportError:
            return {"pid": pid, "info": "psutil_not_installed"}
        except Exception as exc:
            raise RuntimeError(f"monitor_process_failed: {exc}")

    def _act_send_signal_to_self(self, params: Dict[str, Any]) -> Dict[str, Any]:
        signal_type = params["signal_type"]
        allowed = {"request_pause", "request_sleep", "request_resume", "request_shutdown"}
        if signal_type not in allowed:
            raise ValueError(f"invalid_signal_type: {signal_type}")
        return {"signal_type": signal_type, "delivered": True}

    # ------------------------------------------------------------------ #
    # History & revert
    # ------------------------------------------------------------------ #

    def get_action_history(self) -> List[Dict[str, Any]]:
        """Return a copy of the full action history log."""
        return list(self._history)

    def revert_last_action(self) -> Dict[str, Any]:
        """Undo the last successful action if it is reversible."""
        if not self._history:
            return {"success": False, "error": "no_actions_to_revert"}

        target_record: Optional[Dict[str, Any]] = None
        for record in reversed(self._history):
            if record["outcome"] == ActionOutcome.SUCCESS and not record.get(
                "reverted", False
            ):
                target_record = record
                break

        if target_record is None:
            return {"success": False, "error": "no_reversible_actions"}

        action_type = target_record["action_type"]
        params = target_record["params"]
        result = target_record.get("result", {})

        try:
            if action_type == "write_text_file":
                path = Path(params["path"]).resolve()
                backup = result.get("backup")
                if backup is not None:
                    path.write_text(backup, encoding="utf-8")
                else:
                    if path.exists():
                        path.unlink()
            elif action_type == "create_directory":
                path = Path(params["path"]).resolve()
                if path.exists() and path.is_dir():
                    try:
                        path.rmdir()
                    except OSError:
                        pass
            elif action_type == "delete_file":
                path = Path(params["path"]).resolve()
                backup = result.get("backup")
                if backup is not None:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(backup)
            else:
                return {
                    "success": False,
                    "error": "action_not_reversible",
                    "action_type": action_type,
                }

            target_record["reverted"] = True
            target_record["outcome"] = ActionOutcome.REVERTED
            self._log_event(
                MorphologyEventType.ACTION_EXECUTED,
                target_record.get("proposal_id", "unknown"),
                {"action_type": action_type, "reverted": True},
            )
            return {"success": True, "reverted_action_type": action_type}
        except Exception as exc:
            return {"success": False, "error": f"revert_failed: {exc}"}
