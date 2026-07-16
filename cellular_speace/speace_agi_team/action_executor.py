"""ActionExecutor — central execution engine for agent actions.

Bridges ActionProposals to the existing SPEACE safety infrastructure:
- ArchitecturePatchExecutor for runtime parameter patches
- YAML file modifications with backup/validate/write cycle
- Data file writes (JSON/JSONL diagnostics)
- Recovery triggers (coherence injection, subsystem restart)
- Self-modification cycle triggers

Every action goes through: snapshot → execute → verify → rollback_if_needed
with full audit trail written to data/agi_team/action_audit.jsonl.
"""

import copy
import json
import logging
import os
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from speace_agi_team.action_catalog import (
    ALLOWED_DATA_PREFIXES,
    ALLOWED_FLAGS,
    ALLOWED_NUMERIC,
    ALLOWED_PROFILES,
    ALLOWED_YAML_PATHS,
    ActionCatalog,
    ActionCategory,
    ActionRiskLevel,
)
from speace_agi_team.action_proposal import ActionProposal, ActionProposalStatus
from speace_agi_team.action_safety_gate import ActionSafetyGate, ActionSafetyGateResult

_logger = logging.getLogger(__name__)

# ── Audit log path ──────────────────────────────────────────────────────

ACTION_AUDIT_DIR = Path("data/agi_team")
ACTION_AUDIT_FILE = ACTION_AUDIT_DIR / "action_audit.jsonl"
PROPOSALS_FILE = ACTION_AUDIT_DIR / "proposals.jsonl"


class ExecutionResult(BaseModel):
    """Result of executing an action proposal through the full pipeline."""
    proposal_id: str = ""
    final_status: str = "unknown"
    gate_result: Optional[Dict[str, Any]] = None
    execution_output: Optional[Dict[str, Any]] = None
    rollback_performed: bool = False
    audit_entries: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


class ActionExecutor:
    """Central execution engine for agent actions.

    Manages the full lifecycle:
      propose → validate → sandbox → MM-APR → human gate →
      snapshot → execute → verify → rollback_if_needed

    Dispatches to specialized executors based on action category.
    """

    def __init__(
        self,
        catalog: Optional[ActionCatalog] = None,
        safety_gate: Optional[ActionSafetyGate] = None,
        patch_executor: Any = None,
        orchestrator: Any = None,
        self_mod_cycle: Any = None,
        safe_regulation_executor: Any = None,
        data_root: Optional[str] = None,
    ):
        self.catalog = catalog or ActionCatalog()
        self.safety_gate = safety_gate or ActionSafetyGate(catalog=self.catalog)
        self.patch_executor = patch_executor
        self.orchestrator = orchestrator
        self.self_mod_cycle = self_mod_cycle
        self.safe_regulation_executor = safe_regulation_executor
        self.data_root = Path(data_root) if data_root else Path(".")

        # In-memory proposal store
        self._proposals: Dict[str, ActionProposal] = {}

        # Ensure audit directory exists
        ACTION_AUDIT_DIR.mkdir(parents=True, exist_ok=True)

        # Restore proposals from persistent store
        self._load_proposals()

    # ── Full pipeline ───────────────────────────────────────────────────

    def execute_pipeline(
        self,
        proposal: ActionProposal,
        skip_human_approval: bool = False,
    ) -> ExecutionResult:
        """Execute a proposal through the full safety pipeline.

        Steps:
        1. Validate proposal (catalog authorization)
        2. Run safety gate (MM-APR, sandbox, substrate, human approval)
        3. Capture pre-snapshot
        4. Execute the action
        5. Verify post-execution state
        6. Rollback if regression detected

        Returns an ExecutionResult with full trace.
        """
        result = ExecutionResult(proposal_id=proposal.proposal_id)
        self._audit("pipeline_start", proposal.proposal_id, {"action_type": proposal.action_type})

        # ── Step 0: Validate proposal basics ────────────────────────────
        if not proposal.agent_id or not proposal.action_type or not proposal.target:
            result.final_status = "failed"
            result.error = "Proposal missing required fields (agent_id, action_type, target)"
            self._audit("validation_failed", proposal.proposal_id, {"error": result.error})
            return result

        # ── Step 1: Safety gate ─────────────────────────────────────────
        gate_result = self.safety_gate.evaluate(proposal)
        result.gate_result = gate_result.model_dump() if hasattr(gate_result, 'model_dump') else {
            "final_decision": gate_result.final_decision,
            "blocked_reason": gate_result.blocked_reason,
        }

        if gate_result.final_decision == "blocked":
            result.final_status = "vetoed"
            result.error = gate_result.blocked_reason or "Safety gate blocked"
            proposal.transition_to(ActionProposalStatus.VETOED, reason=gate_result.blocked_reason or "safety_gate_blocked")
            self._store_proposal(proposal)
            self._audit("gate_blocked", proposal.proposal_id, {"reason": gate_result.blocked_reason})
            return result

        if gate_result.final_decision == "conditioned":
            # Check if human approval is required and not yet obtained
            if gate_result.human_approval_required and not proposal.human_approval and not skip_human_approval:
                result.final_status = "human_review"
                proposal.transition_to(ActionProposalStatus.HUMAN_REVIEW, reason="Requires human approval")
                self._store_proposal(proposal)
                self._audit("human_review_required", proposal.proposal_id, {
                    "conditions": gate_result.conditions,
                })
                return result

        # ── Step 2: Capture pre-snapshot ────────────────────────────────
        proposal.snapshot_pre = self._capture_snapshot(proposal)
        proposal.transition_to(ActionProposalStatus.APPROVED, reason="safety_gate_passed")
        self._audit("pre_snapshot", proposal.proposal_id, {"snapshot_keys": list(proposal.snapshot_pre.keys())})

        # ── Step 3: Execute ─────────────────────────────────────────────
        proposal.transition_to(ActionProposalStatus.EXECUTING, reason="execution_started")
        self._store_proposal(proposal)

        exec_output = self._execute_action(proposal)
        result.execution_output = exec_output

        if exec_output.get("error"):
            result.final_status = "failed"
            result.error = exec_output["error"]
            proposal.transition_to(ActionProposalStatus.FAILED, reason=exec_output["error"])
            self._store_proposal(proposal)
            self._audit("execution_failed", proposal.proposal_id, {"error": exec_output["error"]})
            return result

        # ── Step 4: Verify (regression check) ───────────────────────────
        proposal.snapshot_post = self._capture_snapshot(proposal)
        regression = self._check_regression(proposal)

        if regression["regressed"]:
            # ── Step 5: Rollback ────────────────────────────────────────
            _logger.warning("Regression detected for %s: %s", proposal.proposal_id, regression["details"])
            rollback_ok = self._rollback(proposal)
            result.rollback_performed = rollback_ok
            if rollback_ok:
                proposal.transition_to(ActionProposalStatus.ROLLED_BACK, reason=regression["details"])
                result.final_status = "rolled_back"
            else:
                proposal.transition_to(ActionProposalStatus.FAILED, reason="rollback_failed")
                result.final_status = "failed"
                result.error = "Regression detected and rollback failed"
            self._store_proposal(proposal)
            self._audit("rollback", proposal.proposal_id, {
                "reason": regression["details"],
                "rollback_success": rollback_ok,
            })
            return result

        # ── Step 6: Mark completed ──────────────────────────────────────
        proposal.transition_to(ActionProposalStatus.COMPLETED, reason="execution_successful")
        proposal.completed_at = time.time()
        result.final_status = "completed"
        self._store_proposal(proposal)
        self._audit("completed", proposal.proposal_id, {"action_type": proposal.action_type})
        return result

    # ── Action dispatch ────────────────────────────────────────────────

    def _execute_action(self, proposal: ActionProposal) -> Dict[str, Any]:
        """Dispatch to the appropriate executor based on action category."""
        category = proposal.action_category

        try:
            if category in (
                ActionCategory.ADJUST_RUNTIME_PARAM.value,
                ActionCategory.TOGGLE_FLAG.value,
                ActionCategory.SCALE_NUMERIC.value,
            ):
                return self._execute_runtime_param(proposal)

            elif category == ActionCategory.MODIFY_YAML_FILE.value:
                return self._execute_yaml_file(proposal)

            elif category == ActionCategory.WRITE_DATA_FILE.value:
                return self._execute_data_file(proposal)

            elif category == ActionCategory.MODIFY_PY_FILE.value:
                return self._execute_py_file(proposal)

            elif category == ActionCategory.TRIGGER_RECOVERY.value:
                return self._execute_recovery(proposal)

            elif category == ActionCategory.TRIGGER_SELF_MOD.value:
                return self._execute_self_modification(proposal)

            elif category == ActionCategory.TRIGGER_SUBSYSTEM_RESTART.value:
                return self._execute_subsystem_restart(proposal)

            elif category == ActionCategory.RUN_EXTERNAL_TASK.value:
                return self._execute_external_task(proposal)

            else:
                return {"error": f"Unknown action category: {category}", "success": False}

        except Exception as e:
            _logger.exception("Action execution error for %s: %s", proposal.proposal_id, e)
            return {"error": str(e), "success": False}

    def _execute_external_task(self, proposal: ActionProposal) -> Dict[str, Any]:
        """Run an external task/assessment via SPEACE environment adapters."""
        target = proposal.target
        start = time.time()
        try:
            from speace_core.environment.environment_adapter import EnvironmentAdapter

            if target == "capability_assessment":
                from run_speace_intelligence_assessment import IntelligenceAssessment
                adapter = EnvironmentAdapter(enable_simulator_backend=False)
                assessment = IntelligenceAssessment(adapter)
                report = assessment.run()
                return {
                    "success": True,
                    "task": target,
                    "composite_score": report.composite_score,
                    "interpretation": report.interpretation,
                    "elapsed_seconds": report.elapsed_seconds,
                    "report_path": None,
                }

            adapter = EnvironmentAdapter(enable_simulator_backend=False)
            if target == "associative_recall":
                result = adapter.run_associative_recall_episode(
                    num_pairs=3, study_repetitions=2, test_length=5
                )
            elif target == "cognitive_prediction":
                from speace_core.environment.cognitive_prediction_environment import SequenceMode
                result = adapter.run_prediction_episode(mode=SequenceMode.PERIODIC, steps=20)
            elif target == "grid_navigation":
                result = adapter.run_grid_episode(dimensions=1, size=5)
            else:
                return {"success": False, "error": f"Unknown external task: {target}"}

            return {
                "success": True,
                "task": target,
                "result": result,
                "elapsed_seconds": time.time() - start,
            }
        except Exception as exc:
            return {"success": False, "task": target, "error": str(exc)}

    def _execute_runtime_param(self, proposal: ActionProposal) -> Dict[str, Any]:
        """Execute a runtime parameter change via ArchitecturePatchExecutor."""
        target = proposal.target
        new_value = proposal.new_value
        operation = proposal.operation

        # Validate target is in allowlist
        all_allowed = ALLOWED_FLAGS | ALLOWED_NUMERIC | ALLOWED_PROFILES
        if target not in all_allowed:
            return {"error": f"Target '{target}' not in allowed set", "success": False}

        old_value = None
        if self.orchestrator is not None:
            old_value = getattr(self.orchestrator, target, None)

        # Prefer ArchitecturePatchExecutor attached to orchestrator
        # Use __dict__ to avoid MagicMock auto-creating attributes
        orch_patch_executor = None
        if self.orchestrator is not None:
            orch_patch_executor = self.orchestrator.__dict__.get('_architecture_patch_executor')
        if orch_patch_executor is not None:
            from speace_core.cellular_brain.self_improvement.architecture_patch_executor import ArchitecturePatch
            patch = ArchitecturePatch(
                patch_id=proposal.proposal_id,
                target=target,
                operation=operation,
                new_value=new_value,
            )
            success = orch_patch_executor.apply_patch(patch)
            _logger.info(
                "orch_patch_executor_used target=%s old_value=%s new_value=%s success=%s",
                target, old_value, new_value, success,
            )
            return {"success": success, "method": "orch_patch_executor"}

        # Fallback to self.patch_executor
        if self.patch_executor is not None:
            from speace_core.cellular_brain.self_improvement.architecture_patch_executor import ArchitecturePatch
            patch = ArchitecturePatch(
                patch_id=proposal.proposal_id,
                target=target,
                operation=operation,
                new_value=new_value,
            )
            success = self.patch_executor.apply_patch(patch)
            _logger.info(
                "patch_executor_used target=%s old_value=%s new_value=%s success=%s",
                target, old_value, new_value, success,
            )
            return {"success": success, "method": "patch_executor"}

        # Last resort: direct setattr on orchestrator
        if self.orchestrator is not None:
            _logger.warning(
                "patch_executor_unavailable target=%s old_value=%s new_value=%s",
                target, old_value, new_value,
            )
            try:
                if operation == "set":
                    setattr(self.orchestrator, target, new_value)
                elif operation == "scale":
                    if old_value is None or not isinstance(old_value, (int, float)):
                        return {"error": f"Cannot scale non-numeric target '{target}'", "success": False}
                    setattr(self.orchestrator, target, old_value * new_value)
                elif operation == "enable":
                    setattr(self.orchestrator, target, True)
                elif operation == "disable":
                    setattr(self.orchestrator, target, False)
                else:
                    setattr(self.orchestrator, target, new_value)

                return {
                    "success": True,
                    "method": "direct_setattr",
                    "target": target,
                    "old_value": str(old_value),
                    "new_value": str(getattr(self.orchestrator, target)),
                }
            except Exception as e:
                return {"error": str(e), "success": False}

        return {"error": "No patch_executor or orchestrator available", "success": False}

    def _execute_yaml_file(self, proposal: ActionProposal) -> Dict[str, Any]:
        """Execute a YAML file modification with backup → write → validate cycle."""
        target = proposal.target
        new_value = proposal.new_value

        # Validate target is in allowed YAML paths
        if target not in ALLOWED_YAML_PATHS:
            return {"error": f"YAML target '{target}' not in allowed paths", "success": False}

        file_path = self.data_root / target

        # Hard block: .py files
        if str(file_path).endswith(".py"):
            return {"error": "Modification of .py files is strictly forbidden", "success": False}

        if not file_path.exists():
            return {"error": f"YAML file not found: {file_path}", "success": False}

        # Step 1: Backup
        backup_path = file_path.with_suffix(
            f".backup.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}{file_path.suffix}"
        )
        try:
            shutil.copy2(file_path, backup_path)
        except Exception as e:
            return {"error": f"Backup failed: {e}", "success": False}

        # Step 2: Read current content, apply modification
        try:
            import yaml
            with open(file_path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)

            # new_value can be a dict of key: value to set, or a full replacement
            if isinstance(new_value, dict):
                if proposal.operation == "set":
                    # Deep merge
                    self._deep_merge(content, new_value)
                elif proposal.operation == "replace":
                    content = new_value
                else:
                    self._deep_merge(content, new_value)
            else:
                return {"error": "YAML modification requires dict new_value", "success": False}

            # Step 3: Write modified content
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(content, f, default_flow_style=False, allow_unicode=True)

            # Step 4: Validate by re-parsing
            with open(file_path, "r", encoding="utf-8") as f:
                validation = yaml.safe_load(f)

            if validation is None:
                # Restore from backup
                shutil.copy2(backup_path, file_path)
                return {"error": "YAML validation failed: parsed to None", "success": False}

            return {
                "success": True,
                "method": "yaml_file_modification",
                "target": target,
                "backup_path": str(backup_path),
            }

        except Exception as e:
            # Restore from backup on any error
            try:
                shutil.copy2(backup_path, file_path)
            except Exception:
                _logger.critical("Failed to restore backup after error: %s", e)
            return {"error": f"YAML modification error: {e}", "success": False}

    def _execute_data_file(self, proposal: ActionProposal) -> Dict[str, Any]:
        """Execute a data file write (JSON/JSONL)."""
        target = proposal.target
        content = proposal.new_value

        # Validate target starts with allowed prefix
        if not any(target.startswith(prefix) for prefix in ALLOWED_DATA_PREFIXES):
            return {"error": f"Data file target '{target}' not in allowed prefixes", "success": False}

        # .py files should use MODIFY_PY_FILE, not WRITE_DATA_FILE
        if target.endswith(".py"):
            return {"error": "Use MODIFY_PY_FILE category for .py files, not WRITE_DATA_FILE", "success": False}

        file_path = self.data_root / target
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if target.endswith(".jsonl"):
                # Append mode for JSONL
                entry = content if isinstance(content, dict) else {"data": content, "ts": time.time()}
                if "ts" not in entry:
                    entry["ts"] = time.time()
                entry["action_proposal_id"] = proposal.proposal_id
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, default=str) + "\n")
            elif target.endswith(".json"):
                # Write mode for JSON
                data = content if isinstance(content, (dict, list)) else {"data": content}
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, default=str)
            else:
                return {"error": f"Unsupported data file format: {target}", "success": False}

            return {
                "success": True,
                "method": "data_file_write",
                "target": target,
                "path": str(file_path),
            }

        except Exception as e:
            return {"error": f"Data file write error: {e}", "success": False}

    def _execute_py_file(self, proposal: ActionProposal) -> Dict[str, Any]:
        """Execute a .py file creation or modification.

        Steps:
        1. Validate target is under ALLOWED_PY_PATHS
        2. If file exists: backup → read → write new content → verify syntax
        3. If file doesn't exist: verify directory exists → write → verify syntax
        4. If syntax check fails: rollback from backup
        """
        from speace_agi_team.action_catalog import ALLOWED_PY_PATHS, ABSOLUTELY_BLOCKED_PATHS

        target = proposal.target
        new_content = proposal.new_value
        operation = proposal.operation

        # Validate target is under an allowed path
        target_norm = target.lower().replace("\\", "/")
        path_allowed = any(target_norm.startswith(allowed.lower()) for allowed in ALLOWED_PY_PATHS)
        if not path_allowed:
            return {"error": f"PY file target '{target}' not in ALLOWED_PY_PATHS", "success": False}

        # Absolutely blocked paths
        for blocked in ABSOLUTELY_BLOCKED_PATHS:
            if target_norm.startswith(blocked.lower()):
                return {"error": f"Path '{target}' is absolutely forbidden", "success": False}

        # new_content must be a string (Python source code)
        if not isinstance(new_content, str):
            return {"error": "MODIFY_PY_FILE new_value must be a string containing Python source code", "success": False}

        file_path = self.data_root / target

        # ── Step 1: Backup if file exists ─────────────────────────────────
        backup_path = None
        if file_path.exists():
            backup_path = file_path.with_suffix(
                file_path.suffix + f".backup.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
            )
            try:
                shutil.copy2(file_path, backup_path)
                # Store old content for rollback
                try:
                    old_content = file_path.read_text(encoding="utf-8")
                except Exception:
                    old_content = ""
            except Exception as e:
                return {"error": f"Backup failed for {file_path}: {e}", "success": False}
        else:
            old_content = ""

        # ── Step 2: Write the new content ────────────────────────────────
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
        except Exception as e:
            # Restore from backup if we had one
            if backup_path and backup_path.exists():
                try:
                    shutil.copy2(backup_path, file_path)
                except Exception:
                    _logger.critical("Failed to restore backup after write error: %s", e)
            return {"error": f"Write failed for {file_path}: {e}", "success": False}

        # ── Step 3: Syntax verification ────────────────────────────────────
        try:
            compile(new_content, str(file_path), "exec")
        except SyntaxError as e:
            _logger.error("Syntax error in %s: %s — rolling back", file_path, e)
            # Rollback
            if backup_path and backup_path.exists():
                try:
                    shutil.copy2(backup_path, file_path)
                    return {
                        "error": f"Syntax error after write, rolled back: {e}",
                        "success": False,
                        "rolled_back": True,
                    }
                except Exception as restore_err:
                    return {
                        "error": f"Syntax error AND rollback failed: {e} / {restore_err}",
                        "success": False,
                        "rolled_back": False,
                    }
            else:
                # New file with syntax error — delete it
                try:
                    file_path.unlink()
                except Exception:
                    pass
                return {
                    "error": f"Syntax error in new file, deleted: {e}",
                    "success": False,
                    "rolled_back": True,
                }

        # ── Step 4: Import verification (optional, best-effort) ──────────
        # We don't actually import the module (could have side effects),
        # but we log that syntax verification passed.
        _logger.info("PY file %s written and syntax-verified successfully", file_path)

        return {
            "success": True,
            "method": "py_file_write",
            "target": target,
            "path": str(file_path),
            "backup_path": str(backup_path) if backup_path else None,
            "is_new_file": not (backup_path is not None),
        }

    def _execute_recovery(self, proposal: ActionProposal) -> Dict[str, Any]:
        """Execute a recovery trigger (coherence injection, neuron activation, etc.).

        Supports action_types:
        - trigger_recovery: standard coherence injection
        - inject_neuron_energy: inject energy into low-energy neurons
        - activate_stalled_neurons: activate neurons below activation threshold
        - force_advance_tick: force the runtime tick counter to advance
        """
        action_type = proposal.action_type
        target = proposal.target

        if self.orchestrator is not None:
            try:
                # ── activate_stalled_neurons: activate neurons below threshold ──
                if action_type == "activate_stalled_neurons":
                    circuit = getattr(self.orchestrator, "circuit", None)
                    if circuit is not None:
                        import random as _rng
                        all_neurons = (
                            list(circuit.input_neurons)
                            + list(circuit.hidden_neurons)
                            + list(circuit.output_neurons)
                        )
                        activated = 0
                        threshold = 0.1
                        # If new_value is a float, use it as threshold
                        if proposal.new_value is not None:
                            try:
                                threshold = float(proposal.new_value)
                            except (TypeError, ValueError):
                                pass
                        for n in all_neurons:
                            if n.activation < threshold:
                                n.activation = threshold + _rng.random() * 0.15
                                n.energy = max(n.energy, 0.4)
                                activated += 1
                        return {
                            "success": True,
                            "method": "activate_stalled_neurons",
                            "neurons_activated": activated,
                            "threshold": threshold,
                        }
                    # Fallback: try runtime's tick method
                    runtime = getattr(self.orchestrator, '_runtime', None)
                    if runtime is not None:
                        return self._inject_via_runtime(runtime, "activate_stalled_neurons")

                # ── inject_neuron_energy: inject energy into low-energy neurons ──
                elif action_type == "inject_neuron_energy":
                    circuit = getattr(self.orchestrator, "circuit", None)
                    if circuit is not None:
                        import random as _rng
                        all_neurons = (
                            list(circuit.input_neurons)
                            + list(circuit.hidden_neurons)
                            + list(circuit.output_neurons)
                        )
                        min_energy = 0.3
                        if proposal.new_value is not None:
                            try:
                                min_energy = float(proposal.new_value)
                            except (TypeError, ValueError):
                                pass
                        injected = 0
                        for n in all_neurons:
                            if n.energy < min_energy:
                                n.energy = max(n.energy, min_energy)
                                n.activation = max(n.activation, 0.05 + _rng.random() * 0.1)
                                injected += 1
                        return {
                            "success": True,
                            "method": "inject_neuron_energy",
                            "neurons_injected": injected,
                            "min_energy": min_energy,
                        }

                # ── force_advance_tick: force the runtime tick counter to advance ──
                elif action_type == "force_advance_tick":
                    # Try to advance the tick counter via the runtime
                    runtime = getattr(self.orchestrator, '_runtime', None)
                    if runtime is not None and hasattr(runtime, '_tick_count_since_start'):
                        old_tick = runtime._tick_count_since_start
                        runtime._tick_count_since_start += 10  # Advance by 10 ticks
                        return {
                            "success": True,
                            "method": "force_advance_tick",
                            "old_tick": old_tick,
                            "new_tick": runtime._tick_count_since_start,
                        }
                    # Fallback: try the orchestrator's tick counter
                    if hasattr(self.orchestrator, 'current_tick'):
                        old_tick = getattr(self.orchestrator, 'current_tick', 0)
                        self.orchestrator.current_tick = old_tick + 10
                        return {
                            "success": True,
                            "method": "force_advance_tick",
                            "old_tick": old_tick,
                            "new_tick": self.orchestrator.current_tick,
                        }
                    return {"error": "No runtime or orchestrator tick counter found", "success": False}

                # ── trigger_recovery: standard coherence injection ──
                elif action_type == "trigger_recovery":
                    circuit = getattr(self.orchestrator, "circuit", None)
                    if circuit is not None:
                        import random as _rng
                        all_neurons = (
                            list(circuit.input_neurons)
                            + list(circuit.hidden_neurons)
                            + list(circuit.output_neurons)
                        )
                        injected = 0
                        for n in all_neurons:
                            if n.activation < 0.05:
                                n.energy = max(n.energy, 0.3)
                                n.activation = 0.05 + _rng.random() * 0.15
                                injected += 1
                        return {
                            "success": True,
                            "method": "coherence_injection",
                            "neurons_injected": injected,
                        }

                    # If no circuit, try SafeRegulationExecutor
                    if self.safe_regulation_executor is not None:
                        proposal_dict = {
                            "proposed_action": "increase stability bias",
                            "proposal_id": proposal.proposal_id,
                            "alert": "coherence_recovery_triggered",
                        }
                        health = getattr(self.orchestrator, "_last_health_score", 0.5)
                        result = self.safe_regulation_executor.execute(proposal_dict, health)
                        return {
                            "success": result.get("outcome") == "success",
                            "method": "safe_regulation_executor",
                            "result": result,
                        }

            except Exception as e:
                return {"error": f"Recovery execution error: {e}", "success": False}

        return {"error": "No orchestrator available for recovery", "success": False}

    def _inject_via_runtime(self, runtime: Any, action: str) -> Dict[str, Any]:
        """Try to inject recovery via the runtime engine."""
        try:
            # Try to access the brain orchestrator through the runtime
            brain_orch = getattr(runtime, 'orchestrator', None)
            if brain_orch is not None:
                circuit = getattr(brain_orch, 'circuit', None)
                if circuit is not None:
                    import random as _rng
                    all_neurons = (
                        list(circuit.input_neurons)
                        + list(circuit.hidden_neurons)
                        + list(circuit.output_neurons)
                    )
                    activated = 0
                    for n in all_neurons:
                        if n.activation < 0.1:
                            n.activation = 0.1 + _rng.random() * 0.15
                            n.energy = max(n.energy, 0.4)
                            activated += 1
                    return {
                        "success": True,
                        "method": f"{action}_via_runtime",
                        "neurons_affected": activated,
                    }
        except Exception as e:
            _logger.warning("Runtime injection failed: %s", e)
        return {"error": f"Could not perform {action} via runtime", "success": False}

    def _execute_self_modification(self, proposal: ActionProposal) -> Dict[str, Any]:
        """Execute a self-modification cycle trigger."""
        if self.self_mod_cycle is not None:
            try:
                metrics = proposal.evidence if proposal.evidence else {}
                result = self.self_mod_cycle.run(metrics=metrics)
                return {
                    "success": True,
                    "method": "self_modification_cycle",
                    "cycle_result": str(result)[:500],
                }
            except Exception as e:
                return {"error": f"Self-modification cycle error: {e}", "success": False}

        return {"error": "SelfModificationCycle not available", "success": False}

    def _execute_subsystem_restart(self, proposal: ActionProposal) -> Dict[str, Any]:
        """Execute a subsystem restart trigger.

        Supports action_types:
        - trigger_subsystem_restart: toggle a subsystem flag off/on
        - reset_neuron_activations: reset all neuron activations to initial values
        """
        action_type = proposal.action_type
        target_subsystem = proposal.target if proposal.target else "unknown"

        if self.orchestrator is not None:
            try:
                # ── reset_neuron_activations: reset all neurons to baseline ──
                if action_type == "reset_neuron_activations":
                    circuit = getattr(self.orchestrator, "circuit", None)
                    if circuit is not None:
                        all_neurons = (
                            list(circuit.input_neurons)
                            + list(circuit.hidden_neurons)
                            + list(circuit.output_neurons)
                        )
                        reset_count = 0
                        for n in all_neurons:
                            n.activation = 0.5  # Reset to mid-range
                            n.energy = 0.7  # Reset to healthy energy
                            reset_count += 1
                        return {
                            "success": True,
                            "method": "reset_neuron_activations",
                            "neurons_reset": reset_count,
                        }
                    # Try via runtime
                    runtime = getattr(self.orchestrator, '_runtime', None)
                    if runtime is not None:
                        return self._inject_via_runtime(runtime, "reset_neuron_activations")
                    return {
                        "error": "No circuit or runtime available for neuron reset",
                        "success": False,
                    }

                # ── trigger_subsystem_restart: toggle subsystem flag ──
                if hasattr(self.orchestrator, 'restart_subsystem'):
                    self.orchestrator.restart_subsystem(target_subsystem)
                    return {
                        "success": True,
                        "method": "subsystem_restart",
                        "target": target_subsystem,
                    }
                else:
                    # Fallback: toggle the subsystem off and on
                    flag_map = {
                        "memory": "semantic_memory_enabled",
                        "evolution": "evolution_enabled",
                        "brainstem": "brainstem_controller_enabled",
                        "counterfactual": "counterfactual_sandbox_enabled",
                        "region_stability": "region_stability_controller_enabled",
                    }
                    flag = flag_map.get(target_subsystem)
                    if flag and hasattr(self.orchestrator, flag):
                        setattr(self.orchestrator, flag, False)
                        time.sleep(0.1)  # Brief pause
                        setattr(self.orchestrator, flag, True)
                        return {
                            "success": True,
                            "method": "subsystem_toggle_restart",
                            "target": target_subsystem,
                            "flag": flag,
                        }
                    return {
                        "error": f"No restart method for subsystem '{target_subsystem}'",
                        "success": False,
                    }
            except Exception as e:
                return {"error": f"Subsystem restart error: {e}", "success": False}

        return {"error": "No orchestrator available for subsystem restart", "success": False}

    # ── Snapshot & regression ───────────────────────────────────────────

    def _capture_snapshot(self, proposal: ActionProposal) -> Dict[str, Any]:
        """Capture a snapshot of the current state of the target and related metrics."""
        snapshot: Dict[str, Any] = {
            "proposal_id": proposal.proposal_id,
            "timestamp": time.time(),
            "target": proposal.target,
        }

        # Capture orchestrator state if available
        if self.orchestrator is not None:
            for flag in ALLOWED_FLAGS:
                val = getattr(self.orchestrator, flag, None)
                if val is not None:
                    snapshot[f"flag_{flag}"] = val
            for num in ALLOWED_NUMERIC:
                val = getattr(self.orchestrator, num, None)
                if val is not None:
                    snapshot[f"numeric_{num}"] = val

            # Capture coherence metrics if available
            metrics = getattr(self.orchestrator, "_last_metrics", None)
            if metrics is not None:
                snapshot["coherence_phi"] = getattr(metrics, "coherence_phi", None)
                snapshot["mean_energy"] = getattr(metrics, "mean_energy", None)
                snapshot["mean_activation"] = getattr(metrics, "mean_activation", None)

        # Use patch executor's snapshot if available
        if self.patch_executor is not None and hasattr(self.patch_executor, 'create_pre_patch_snapshot'):
            try:
                from speace_core.cellular_brain.self_improvement.architecture_patch_executor import ArchitecturePatch
                patch = ArchitecturePatch(
                    patch_id=proposal.proposal_id,
                    target=proposal.target,
                    operation=proposal.operation,
                    new_value=proposal.new_value,
                )
                ps = self.patch_executor.create_pre_patch_snapshot(patch)
                snapshot["patch_snapshot_id"] = ps.snapshot_id if hasattr(ps, 'snapshot_id') else str(uuid.uuid4())
            except Exception:
                pass

        return snapshot

    def _check_regression(self, proposal: ActionProposal) -> Dict[str, Any]:
        """Check for regression after action execution.

        Compares pre-snapshot to post-snapshot. If coherence or energy
        dropped by more than 10%, or substrate guard reports emergency,
        the action is considered regressed.
        """
        pre = proposal.snapshot_pre
        post = proposal.snapshot_post

        if not pre or not post:
            return {"regressed": False, "details": "no snapshots to compare"}

        details = []
        regressed = False

        # Check coherence regression (10% threshold)
        pre_phi = pre.get("coherence_phi")
        post_phi = post.get("coherence_phi")
        if pre_phi is not None and post_phi is not None:
            try:
                pre_phi_f = float(pre_phi)
                post_phi_f = float(post_phi)
                if pre_phi_f > 0 and (pre_phi_f - post_phi_f) / pre_phi_f > 0.10:
                    regressed = True
                    details.append(
                        f"Coherence regression: {pre_phi_f:.4f} → {post_phi_f:.4f} "
                        f"(Δ = {((pre_phi_f - post_phi_f) / pre_phi_f) * 100:.1f}%)"
                    )
            except (TypeError, ValueError, ZeroDivisionError):
                pass

        # Check energy regression (10% threshold)
        pre_energy = pre.get("mean_energy")
        post_energy = post.get("mean_energy")
        if pre_energy is not None and post_energy is not None:
            try:
                pre_energy_f = float(pre_energy)
                post_energy_f = float(post_energy)
                if pre_energy_f > 0 and (pre_energy_f - post_energy_f) / pre_energy_f > 0.10:
                    regressed = True
                    details.append(
                        f"Energy regression: {pre_energy_f:.4f} → {post_energy_f:.4f}"
                    )
            except (TypeError, ValueError, ZeroDivisionError):
                pass

        # Check substrate guard if available
        if self.safety_gate and self.safety_gate.substrate_guard is not None:
            substrate_result = self.safety_gate._check_substrate(proposal)
            if substrate_result == "emergency":
                regressed = True
                details.append("Substrate guard: EMERGENCY")

        return {"regressed": regressed, "details": "; ".join(details) if details else "no regression"}

    def _rollback(self, proposal: ActionProposal) -> bool:
        """Rollback an action using the pre-snapshot."""
        target = proposal.target
        category = proposal.action_category
        pre = proposal.snapshot_pre

        # ── Rollback runtime parameters ────────────────────────────────
        if category in (
            ActionCategory.ADJUST_RUNTIME_PARAM.value,
            ActionCategory.TOGGLE_FLAG.value,
            ActionCategory.SCALE_NUMERIC.value,
        ):
            old_value = pre.get(f"flag_{target}") or pre.get(f"numeric_{target}")
            if old_value is not None and self.orchestrator is not None:
                try:
                    setattr(self.orchestrator, target, old_value)
                    _logger.info("Rolled back %s to %s", target, old_value)
                    return True
                except Exception as e:
                    _logger.error("Rollback failed for %s: %s", target, e)
                    return False

            # Try using patch executor rollback
            if self.patch_executor is not None and hasattr(self.patch_executor, 'rollback_patch'):
                try:
                    from speace_core.cellular_brain.self_improvement.architecture_patch_executor import ArchitecturePatch
                    patch = ArchitecturePatch(
                        patch_id=proposal.proposal_id,
                        target=target,
                        operation=proposal.operation,
                        new_value=proposal.old_value if proposal.old_value is not None else pre.get(f"numeric_{target}", pre.get(f"flag_{target}")),
                    )
                    snapshot_id = pre.get("patch_snapshot_id")
                    if snapshot_id:
                        # Retrieve snapshot and rollback
                        return self.patch_executor.rollback_patch(patch, self._get_snapshot(snapshot_id))
                except Exception as e:
                    _logger.error("Patch executor rollback failed: %s", e)
                    return False

        # ── Rollback YAML files (restore from backup) ──────────────────
        elif category == ActionCategory.MODIFY_YAML_FILE.value:
            # Find the most recent backup for this file
            file_path = self.data_root / target
            backup_dir = file_path.parent
            if backup_dir.exists():
                backups = sorted(backup_dir.glob(f"{file_path.stem}.backup.*{file_path.suffix}"))
                if backups:
                    try:
                        shutil.copy2(backups[-1], file_path)
                        _logger.info("Restored YAML from backup: %s", backups[-1])
                        return True
                    except Exception as e:
                        _logger.error("YAML rollback failed: %s", e)
                        return False

        # ── Rollback PY files (restore from backup) ─────────────────────
        elif category == ActionCategory.MODIFY_PY_FILE.value:
            file_path = self.data_root / target
            backup_dir = file_path.parent
            if backup_dir.exists():
                # .py backups have format: filename.py.backup.20241201T120000Z.py
                backups = sorted(backup_dir.glob(f"{file_path.name}.backup.*"))
                if backups:
                    try:
                        shutil.copy2(backups[-1], file_path)
                        _logger.info("Restored PY from backup: %s", backups[-1])
                        return True
                    except Exception as e:
                        _logger.error("PY rollback failed: %s", e)
                        return False
                else:
                    # If the file was newly created (no backup), delete it
                    if file_path.exists():
                        try:
                            file_path.unlink()
                            _logger.info("Deleted newly created PY file: %s", file_path)
                            return True
                        except Exception as e:
                            _logger.error("Failed to delete new PY file: %s", e)
                            return False

        # ── Rollback other types: best-effort ──────────────────────────
        _logger.warning("Rollback not fully supported for category %s", category)
        return False

    def _get_snapshot(self, snapshot_id: str) -> Any:
        """Retrieve a snapshot from the patch executor's store."""
        if self.patch_executor is not None and hasattr(self.patch_executor, 'snapshot_store'):
            store = self.patch_executor.snapshot_store
            if hasattr(store, 'get'):
                return store.get(snapshot_id)
            if hasattr(store, 'snapshots'):
                return store.snapshots.get(snapshot_id)
        return None

    # ── Proposal management ────────────────────────────────────────────

    def get_proposal(self, proposal_id: str) -> Optional[ActionProposal]:
        """Retrieve a proposal by ID."""
        return self._proposals.get(proposal_id)

    def list_proposals(
        self,
        status: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[ActionProposal]:
        """List proposals with optional filtering."""
        proposals = list(self._proposals.values())
        if status:
            proposals = [p for p in proposals if p.status == status or p.status.value == status]
        if agent_id:
            proposals = [p for p in proposals if p.agent_id == agent_id]
        return proposals[:limit]

    def approve_proposal(self, proposal_id: str, approver: str, notes: str = "") -> Optional[ActionProposal]:
        """Approve a proposal that's in HUMAN_REVIEW status."""
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            return None
        if proposal.status not in (ActionProposalStatus.HUMAN_REVIEW, ActionProposalStatus.HUMAN_REVIEW.value):
            return None

        proposal.human_approval = {
            "approver": approver,
            "notes": notes,
            "timestamp": time.time(),
        }
        proposal.transition_to(ActionProposalStatus.APPROVED, reason=f"Human approved by {approver}")
        self._store_proposal(proposal)
        return proposal

    def reject_proposal(self, proposal_id: str, rejector: str, reason: str = "") -> Optional[ActionProposal]:
        """Reject a proposal that's in HUMAN_REVIEW status."""
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            return None

        proposal.transition_to(ActionProposalStatus.VETOED, reason=f"Human rejected by {rejector}: {reason}")
        self._store_proposal(proposal)
        return proposal

    # ── Audit ───────────────────────────────────────────────────────────

    def _audit(self, event: str, proposal_id: str, details: Dict[str, Any]) -> None:
        """Write an audit trail entry to the append-only JSONL file."""
        entry = {
            "ts": time.time(),
            "event": event,
            "proposal_id": proposal_id,
            **details,
        }
        try:
            ACTION_AUDIT_DIR.mkdir(parents=True, exist_ok=True)
            with open(ACTION_AUDIT_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            _logger.error("Failed to write audit entry: %s", e)

    # ── Helpers ─────────────────────────────────────────────────────────

    def _store_proposal(self, proposal: ActionProposal) -> None:
        """Store a proposal in the in-memory store and persist to disk."""
        self._proposals[proposal.proposal_id] = proposal
        try:
            with open(PROPOSALS_FILE, "a", encoding="utf-8") as f:
                f.write(proposal.model_dump_json(default=str) + "\n")
        except Exception as e:
            _logger.error("Failed to persist proposal %s: %s", proposal.proposal_id, e)

    def _load_proposals(self) -> None:
        """Restore proposals from the persistent JSONL store on disk."""
        if not PROPOSALS_FILE.exists():
            return
        try:
            with open(PROPOSALS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        proposal = ActionProposal(**data)
                        self._proposals[proposal.proposal_id] = proposal
                    except Exception as e:
                        _logger.warning("Skipping corrupted proposal line: %s", e)
            _logger.info("Restored %d proposals from %s", len(self._proposals), PROPOSALS_FILE)
        except Exception as e:
            _logger.error("Failed to load proposals from %s: %s", PROPOSALS_FILE, e)

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Deep merge override into base (mutates base)."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                ActionExecutor._deep_merge(base[key], value)
            else:
                base[key] = value
        return base