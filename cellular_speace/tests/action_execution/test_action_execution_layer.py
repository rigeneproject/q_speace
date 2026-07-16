"""Tests for the AGI team action execution layer — expanded.

Covers:
- ActionCatalog: expanded YAML paths, data prefixes, .py file authorization, ALLOWED_PY_PATHS
- ActionProposal: creation, transitions, audit trail
- ActionSafetyGate: catalog auth, MM-APR bypass, human approval, MANDATORY sandbox for .py
- ActionExecutor: pipeline, runtime params, YAML files, data files, .py file create/modify, rollback
- Orchestrator: supervisor_directed_action_cycle, _find_technician_for
"""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from speace_agi_team.action_catalog import (
    ALLOWED_DATA_PREFIXES,
    ALLOWED_FLAGS,
    ALLOWED_NUMERIC,
    ALLOWED_PROFILES,
    ALLOWED_PY_PATHS,
    ALLOWED_YAML_PATHS,
    ABSOLUTELY_BLOCKED_PATHS,
    BLOCKED_PATH_PATTERNS,
    ActionCatalog,
    ActionCategory,
    ActionRiskLevel,
)
from speace_agi_team.action_proposal import ActionProposal, ActionProposalStatus
from speace_agi_team.action_safety_gate import ActionSafetyGate, ActionSafetyGateResult
from speace_agi_team.action_executor import ActionExecutor, ACTION_AUDIT_DIR


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def catalog():
    return ActionCatalog()


@pytest.fixture
def safety_gate(catalog):
    return ActionSafetyGate(catalog=catalog)


@pytest.fixture
def mock_orchestrator():
    orch = MagicMock()
    orch.learning_rate = 0.01
    orch.plasticity_rate = 0.05
    orch.decay_rate = 0.1
    orch.routing_gain = 1.5
    orch.inhibition_decay = 0.2
    orch.semantic_similarity_threshold = 0.7
    orch.assembly_consolidation_threshold = 0.5
    orch.semantic_memory_enabled = True
    orch.associative_memory_enabled = True
    orch.episodic_policy_enabled = True
    orch.counterfactual_sandbox_enabled = True
    orch.brainstem_controller_enabled = True
    orch.region_stability_controller_enabled = True
    orch.architecture_patch_execution_enabled = True
    return orch


@pytest.fixture
def executor(safety_gate, mock_orchestrator):
    return ActionExecutor(
        safety_gate=safety_gate,
        orchestrator=mock_orchestrator,
    )


# ══════════════════════════════════════════════════════════════════════
# Expanded ActionCatalog tests
# ══════════════════════════════════════════════════════════════════════

class TestExpandedCatalog:
    def test_all_yaml_paths_count(self):
        """All 19 YAML paths are in the allowlist."""
        assert len(ALLOWED_YAML_PATHS) == 19

    def test_new_yaml_paths_present(self):
        """New YAML paths from the expansion are present."""
        new_paths = [
            "speace_core/dna/genome/regulation/homeostasis.yaml",
            "speace_core/dna/genome/regulation/immune_rules.yaml",
            "speace_core/dna/genome/regulation/emergent_dynamics.yaml",
            "speace_core/dna/genome/morphology/allowed_cell_types.yaml",
            "speace_core/dna/genome/morphology/dynamics_substrate.yaml",
            "speace_core/dna/genome/morphology/embodiment_substrate.yaml",
            "speace_core/dna/genome/morphology/autonomous_drives.yaml",
            "speace_core/dna/genome/core/identity.yaml",
        ]
        for path in new_paths:
            assert path in ALLOWED_YAML_PATHS, f"Missing YAML path: {path}"

    def test_py_paths_present(self):
        """ALLOWED_PY_PATHS contains the expected directories."""
        assert "speace_core/cellular_brain/cells/" in ALLOWED_PY_PATHS
        assert "speace_core/cellular_brain/regions/" in ALLOWED_PY_PATHS
        assert "speace_core/runtime/" in ALLOWED_PY_PATHS

    def test_expanded_data_prefixes(self):
        """Expanded data prefixes include domain-specific directories."""
        expanded = [
            "data/regulation/", "data/evolution/", "data/embodiment/",
            "data/monitoring/", "data/identity_kernel/", "data/drives/",
            "data/language/", "data/dialogue/", "data/self_model/",
        ]
        for prefix in expanded:
            assert prefix in ALLOWED_DATA_PREFIXES, f"Missing data prefix: {prefix}"

    def test_technician_py_actions(self, catalog):
        """Technicians have MODIFY_PY_FILE actions."""
        actions = catalog.get_actions_for("neuron_tech")
        py_actions = [a for a in actions if a["action_category"] == "modify_py_file"]
        assert len(py_actions) >= 1
        assert any("cells/" in t for a in py_actions for t in a["targets"])

    def test_supervisor_py_actions(self, catalog):
        """Supervisors have MODIFY_PY_FILE actions."""
        actions = catalog.get_actions_for("brain_supervisor")
        py_actions = [a for a in actions if a["action_category"] == "modify_py_file"]
        assert len(py_actions) >= 1

    def test_py_authorized_under_allowed_paths(self, catalog):
        """Agents can propose .py modifications under ALLOWED_PY_PATHS."""
        assert catalog.is_authorized(
            "neuron_tech", "modify_py_file", "speace_core/cellular_brain/cells/digital_neuron.py"
        )

    def test_py_blocked_outside_allowed_paths(self, catalog):
        """Agents cannot propose .py modifications outside ALLOWED_PY_PATHS."""
        assert not catalog.is_authorized(
            "neuron_tech", "modify_py_file", "speace_agi_team/web_server.py"
        )

    def test_py_blocked_for_agi_team(self, catalog):
        """AGI team code is absolutely blocked."""
        assert not catalog.is_authorized(
            "chief_architect", "modify_py_file", "speace_agi_team/orchestrator.py"
        )

    def test_py_blocked_for_tests(self, catalog):
        """Test code is absolutely blocked."""
        assert not catalog.is_authorized(
            "chief_architect", "modify_py_file", "tests/runtime/test_runtime.py"
        )

    def test_chief_architect_can_modify_py_under_allowed(self, catalog):
        """Chief architect can modify .py under allowed paths."""
        assert catalog.is_authorized(
            "chief_architect", "modify_py_file", "speace_core/cellular_brain/cells/new_module.py"
        )

    def test_new_yaml_actions_for_genome_tech(self, catalog):
        """genome_tech can modify cell_expression_rules.yaml."""
        assert catalog.is_authorized(
            "genome_tech", "modify_yaml_file", "speace_core/dna/genome/differentiation/cell_expression_rules.yaml"
        )

    def test_defense_tech_can_modify_immune_rules(self, catalog):
        """defense_tech can modify immune_rules.yaml."""
        assert catalog.is_authorized(
            "defense_tech", "modify_yaml_file", "speace_core/dna/genome/regulation/immune_rules.yaml"
        )

    def test_runtime_tech_can_modify_homeostasis(self, catalog):
        """runtime_tech can modify homeostasis.yaml."""
        assert catalog.is_authorized(
            "runtime_tech", "modify_yaml_file", "speace_core/dna/genome/regulation/homeostasis.yaml"
        )

    def test_self_awareness_can_modify_identity(self, catalog):
        """self_awareness_supervisor can modify identity.yaml (CRITICAL)."""
        assert catalog.is_authorized(
            "self_awareness_supervisor", "modify_yaml_file", "speace_core/dna/genome/core/identity.yaml"
        )

    def test_infer_category_py(self, catalog):
        """infer_category returns MODIFY_PY_FILE for .py targets."""
        cat = catalog.infer_category("modify_cell_module", "speace_core/cellular_brain/cells/neuron.py")
        assert cat == ActionCategory.MODIFY_PY_FILE.value

    def test_data_write_expanded_prefixes(self, catalog):
        """Technicians can write to expanded data directories."""
        assert catalog.is_authorized(
            "neuron_tech", "write_data_file", "data/regulation/test.jsonl"
        )
        assert catalog.is_authorized(
            "neuron_tech", "write_data_file", "data/evolution/test.jsonl"
        )
        assert catalog.is_authorized(
            "neuron_tech", "write_data_file", "data/embodiment/test.jsonl"
        )


# ══════════════════════════════════════════════════════════════════════
# MODIFY_PY_FILE safety gate tests
# ══════════════════════════════════════════════════════════════════════

class TestPyFileSafetyGate:
    def test_py_file_blocked_without_sandbox(self, safety_gate):
        """MODIFY_PY_FILE is blocked when sandbox is not available."""
        p = ActionProposal(
            agent_id="neuron_tech",
            action_type="modify_cell_module",
            action_category=ActionCategory.MODIFY_PY_FILE.value,
            target="speace_core/cellular_brain/cells/digital_neuron.py",
            operation="set",
            new_value="# test",
            risk_level=ActionRiskLevel.HIGH,
        )
        result = safety_gate.evaluate(p)
        # Sandbox not available → should be blocked
        assert result.final_decision == "blocked"
        assert "sandbox" in (result.blocked_reason or "").lower()

    def test_py_file_blocked_by_sandbox_reject(self, safety_gate):
        """MODIFY_PY_FILE is blocked when sandbox rejects it."""
        mock_sandbox = MagicMock()
        mock_sandbox.run_scenario.return_value = MagicMock(verdict="unsafe")
        safety_gate.counterfactual_sandbox = mock_sandbox

        p = ActionProposal(
            agent_id="neuron_tech",
            action_type="modify_cell_module",
            action_category=ActionCategory.MODIFY_PY_FILE.value,
            target="speace_core/cellular_brain/cells/digital_neuron.py",
            operation="set",
            new_value="# test",
            risk_level=ActionRiskLevel.HIGH,
        )
        result = safety_gate.evaluate(p)
        assert result.final_decision == "blocked"

    def test_py_file_allowed_when_sandbox_passes(self, safety_gate):
        """MODIFY_PY_FILE is allowed when sandbox passes (conditioned for HIGH risk)."""
        mock_sandbox = MagicMock()
        mock_sandbox.run_scenario.return_value = MagicMock(verdict="accept")
        safety_gate.counterfactual_sandbox = mock_sandbox

        p = ActionProposal(
            agent_id="neuron_tech",
            action_type="modify_cell_module",
            action_category=ActionCategory.MODIFY_PY_FILE.value,
            target="speace_core/cellular_brain/cells/digital_neuron.py",
            operation="set",
            new_value="# test modification",
            risk_level=ActionRiskLevel.HIGH,
        )
        result = safety_gate.evaluate(p)
        # HIGH risk → conditioned (human approval), but not blocked
        assert result.final_decision in ("allow", "conditioned")
        assert result.final_decision != "blocked"

    def test_py_file_blocked_for_unauthorized_agent(self, safety_gate):
        """Unknown agent cannot modify .py files."""
        p = ActionProposal(
            agent_id="unknown_agent",
            action_type="modify_cell_module",
            action_category=ActionCategory.MODIFY_PY_FILE.value,
            target="speace_core/cellular_brain/cells/digital_neuron.py",
            operation="set",
            new_value="# malicious",
            risk_level=ActionRiskLevel.HIGH,
        )
        result = safety_gate.evaluate(p)
        assert result.final_decision == "blocked"


# ══════════════════════════════════════════════════════════════════════
# PY file executor tests
# ══════════════════════════════════════════════════════════════════════

class TestPyFileExecutor:
    def test_create_new_py_file(self, executor):
        """Test creating a new .py file in an allowed directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            executor.data_root = Path(tmpdir)
            # Create the target directory
            cells_dir = Path(tmpdir) / "speace_core" / "cellular_brain" / "cells"
            cells_dir.mkdir(parents=True, exist_ok=True)

            p = ActionProposal(
                agent_id="neuron_tech",
                action_type="modify_cell_module",
                action_category=ActionCategory.MODIFY_PY_FILE.value,
                target="speace_core/cellular_brain/cells/test_new_module.py",
                operation="set",
                new_value='# New module\n"""A test module."""\n\ndef hello():\n    return "world"\n',
                risk_level=ActionRiskLevel.HIGH,
            )
            # Bypass safety gate for this test
            p.transition_to(ActionProposalStatus.APPROVED, reason="test")

            result = executor._execute_py_file(p)
            assert result["success"], f"Expected success but got: {result}"
            assert result["is_new_file"] is True

            # Verify file was written
            fpath = Path(tmpdir) / "speace_core" / "cellular_brain" / "cells" / "test_new_module.py"
            assert fpath.exists()
            content = fpath.read_text(encoding="utf-8")
            assert "def hello" in content

    def test_modify_existing_py_file(self, executor):
        """Test modifying an existing .py file with backup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            executor.data_root = Path(tmpdir)
            cells_dir = Path(tmpdir) / "speace_core" / "cellular_brain" / "cells"
            cells_dir.mkdir(parents=True, exist_ok=True)

            # Create existing file
            existing_file = cells_dir / "existing_module.py"
            existing_file.write_text('# Old content\nold_var = 1\n', encoding="utf-8")

            p = ActionProposal(
                agent_id="neuron_tech",
                action_type="modify_cell_module",
                action_category=ActionCategory.MODIFY_PY_FILE.value,
                target="speace_core/cellular_brain/cells/existing_module.py",
                operation="set",
                new_value='# New content\nnew_var = 2\n',
                risk_level=ActionRiskLevel.HIGH,
            )
            p.transition_to(ActionProposalStatus.APPROVED, reason="test")

            result = executor._execute_py_file(p)
            assert result["success"], f"Expected success but got: {result}"
            assert result["backup_path"] is not None

            # Verify backup was created
            backups = list(cells_dir.glob("existing_module.py.backup.*"))
            assert len(backups) >= 1

            # Verify new content
            content = existing_file.read_text(encoding="utf-8")
            assert "new_var = 2" in content

    def test_syntax_error_causes_rollback(self, executor):
        """Test that a syntax error in .py content causes rollback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            executor.data_root = Path(tmpdir)
            cells_dir = Path(tmpdir) / "speace_core" / "cellular_brain" / "cells"
            cells_dir.mkdir(parents=True, exist_ok=True)

            # Create existing file
            existing_file = cells_dir / "good_module.py"
            original_content = '# Good module\ngood_var = 1\n'
            existing_file.write_text(original_content, encoding="utf-8")

            p = ActionProposal(
                agent_id="neuron_tech",
                action_type="modify_cell_module",
                action_category=ActionCategory.MODIFY_PY_FILE.value,
                target="speace_core/cellular_brain/cells/good_module.py",
                operation="set",
                new_value='# Broken code\ndef broken(\n',  # Syntax error
                risk_level=ActionRiskLevel.HIGH,
            )
            p.transition_to(ActionProposalStatus.APPROVED, reason="test")

            result = executor._execute_py_file(p)
            assert not result["success"]
            assert "Syntax error" in result["error"]

            # Verify original content was restored
            content = existing_file.read_text(encoding="utf-8")
            assert "good_var = 1" in content

    def test_py_file_blocked_outside_allowed_paths(self, executor):
        """Test that .py files outside ALLOWED_PY_PATHS are blocked."""
        p = ActionProposal(
            agent_id="neuron_tech",
            action_type="modify_cell_module",
            action_category=ActionCategory.MODIFY_PY_FILE.value,
            target="speace_agi_team/web_server.py",
            operation="set",
            new_value="# malicious",
            risk_level=ActionRiskLevel.LOW,
        )
        result = executor._execute_py_file(p)
        assert not result["success"]
        assert "not in ALLOWED_PY_PATHS" in result["error"]

    def test_py_file_blocked_absolutely(self, executor):
        """Test that absolutely blocked paths cannot be modified."""
        p = ActionProposal(
            agent_id="chief_architect",
            action_type="modify_test",
            action_category=ActionCategory.MODIFY_PY_FILE.value,
            target="tests/test_runtime.py",
            operation="set",
            new_value="# malicious",
            risk_level=ActionRiskLevel.LOW,
        )
        result = executor._execute_py_file(p)
        assert not result["success"]

    def test_py_file_requires_string_content(self, executor):
        """Test that non-string new_value is rejected."""
        p = ActionProposal(
            agent_id="neuron_tech",
            action_type="modify_cell_module",
            action_category=ActionCategory.MODIFY_PY_FILE.value,
            target="speace_core/cellular_brain/cells/test.py",
            operation="set",
            new_value={"key": "value"},  # Not a string
            risk_level=ActionRiskLevel.LOW,
        )
        result = executor._execute_py_file(p)
        assert not result["success"]
        assert "string" in result["error"].lower()


# ══════════════════════════════════════════════════════════════════════
# Existing tests (keep passing)
# ══════════════════════════════════════════════════════════════════════

class TestActionCatalog:
    def test_chief_architect_can_do_anything(self, catalog):
        assert catalog.is_authorized("chief_architect", "adjust_runtime_param", "learning_rate")

    def test_chief_architect_blocked_absolutely(self, catalog):
        assert not catalog.is_authorized("chief_architect", "modify_py_file", "speace_agi_team/action_catalog.py")

    def test_technician_authorized_action(self, catalog):
        assert catalog.is_authorized("neuron_tech", "adjust_runtime_param", "plasticity_rate")

    def test_technician_unauthorized_action(self, catalog):
        assert not catalog.is_authorized("neuron_tech", "modify_yaml_file", "speace_core/dna/genome/default_genome.yaml")

    def test_supervisor_inherits_technician_actions(self, catalog):
        assert catalog.is_authorized("brain_supervisor", "adjust_runtime_param", "plasticity_rate")

    def test_blocked_pyc_files(self, catalog):
        assert not catalog.is_authorized("neuron_tech", "write_data_file", "__pycache__/module.pyc")

    def test_blocked_path_traversal(self, catalog):
        assert not catalog.is_authorized("neuron_tech", "write_data_file", "../etc/passwd")

    def test_data_file_prefix_match(self, catalog):
        assert catalog.is_authorized("neuron_tech", "write_data_file", "data/diagnostics/test.jsonl")

    def test_get_risk_level(self, catalog):
        risk = catalog.get_risk_level("neuron_tech", "adjust_runtime_param", "plasticity_rate")
        assert risk == ActionRiskLevel.LOW

    def test_infer_category_runtime_param(self, catalog):
        cat = catalog.infer_category("adjust", "learning_rate")
        assert cat == ActionCategory.ADJUST_RUNTIME_PARAM.value

    def test_infer_category_yaml(self, catalog):
        cat = catalog.infer_category("modify", "speace_core/dna/genome/default_genome.yaml")
        assert cat == ActionCategory.MODIFY_YAML_FILE.value

    def test_infer_category_py(self, catalog):
        cat = catalog.infer_category("modify_cell_module", "speace_core/cellular_brain/cells/neuron.py")
        assert cat == ActionCategory.MODIFY_PY_FILE.value


class TestActionProposal:
    def test_create_proposal(self):
        p = ActionProposal(
            agent_id="neuron_tech",
            action_type="adjust_neuron_threshold",
            action_category="adjust_runtime_param",
            target="plasticity_rate",
            operation="set",
            new_value=0.1,
            risk_level=ActionRiskLevel.LOW,
            justification="Test adjustment",
        )
        assert p.agent_id == "neuron_tech"
        assert p.status == ActionProposalStatus.PROPOSED
        assert p.proposal_id.startswith("AP-")

    def test_transition(self):
        p = ActionProposal(agent_id="test", action_type="test", action_category="test", target="test")
        p.transition_to(ActionProposalStatus.VALIDATED, reason="passed safety gate")
        assert p.status == ActionProposalStatus.VALIDATED
        assert len(p.audit_trail) == 1

    def test_audit_trail_appends(self):
        p = ActionProposal(agent_id="test", action_type="test", action_category="test", target="test")
        p.transition_to(ActionProposalStatus.VALIDATED, reason="validated")
        p.transition_to(ActionProposalStatus.APPROVED, reason="approved")
        p.transition_to(ActionProposalStatus.EXECUTING, reason="executing")
        assert len(p.audit_trail) == 3


class TestActionExecutorPipeline:
    def test_execute_runtime_param_set(self, executor, mock_orchestrator):
        p = ActionProposal(
            agent_id="neuron_tech",
            action_type="adjust_neuron_threshold",
            action_category=ActionCategory.ADJUST_RUNTIME_PARAM.value,
            target="plasticity_rate",
            operation="set",
            new_value=0.15,
            risk_level=ActionRiskLevel.LOW,
        )
        result = executor.execute_pipeline(p)
        assert result.final_status == "completed"
        assert mock_orchestrator.plasticity_rate == 0.15

    def test_execute_runtime_param_scale(self, executor, mock_orchestrator):
        p = ActionProposal(
            agent_id="runtime_tech",
            action_type="adjust_circadian_params",
            action_category=ActionCategory.SCALE_NUMERIC.value,
            target="learning_rate",
            operation="scale",
            new_value=2.0,
            risk_level=ActionRiskLevel.MODERATE,
        )
        result = executor.execute_pipeline(p)
        assert result.final_status == "completed"
        assert mock_orchestrator.learning_rate == pytest.approx(0.02)

    def test_blocked_unauthorized_target(self, executor):
        p = ActionProposal(
            agent_id="neuron_tech",
            action_type="modify_genome",
            action_category=ActionCategory.MODIFY_YAML_FILE.value,
            target="speace_core/dna/genome/default_genome.yaml",
            operation="set",
            new_value={"key": "value"},
            risk_level=ActionRiskLevel.HIGH,
        )
        result = executor.execute_pipeline(p)
        assert result.final_status == "vetoed"

    def test_missing_required_fields(self, executor):
        p = ActionProposal(
            agent_id="",
            action_type="",
            action_category=ActionCategory.ADJUST_RUNTIME_PARAM.value,
            target="",
            operation="set",
            new_value=0.1,
            risk_level=ActionRiskLevel.LOW,
        )
        result = executor.execute_pipeline(p)
        assert result.final_status == "failed"
        assert result.error is not None

    def test_data_file_write(self, executor):
        with tempfile.TemporaryDirectory() as tmpdir:
            executor.data_root = Path(tmpdir)
            p = ActionProposal(
                agent_id="neuron_tech",
                action_type="write_neuron_diagnostic",
                action_category=ActionCategory.WRITE_DATA_FILE.value,
                target="data/diagnostics/test_diagnostic.jsonl",
                operation="set",
                new_value={"metric": "coherence", "value": 0.85},
                risk_level=ActionRiskLevel.LOW,
            )
            result = executor.execute_pipeline(p)
            assert result.final_status == "completed"
            fpath = Path(tmpdir) / "data" / "diagnostics" / "test_diagnostic.jsonl"
            assert fpath.exists()

    def test_full_pipeline_low_risk(self, mock_orchestrator):
        catalog = ActionCatalog()
        safety_gate = ActionSafetyGate(catalog=catalog)
        executor = ActionExecutor(
            catalog=catalog,
            safety_gate=safety_gate,
            orchestrator=mock_orchestrator,
        )
        proposal = ActionProposal(
            agent_id="neuron_tech",
            action_type="adjust_neuron_threshold",
            action_category=ActionCategory.ADJUST_RUNTIME_PARAM.value,
            target="plasticity_rate",
            operation="set",
            new_value=0.08,
            risk_level=ActionRiskLevel.LOW,
            justification="Optimize plasticity",
            evidence={"coherence_phi": 0.34},
        )
        result = executor.execute_pipeline(proposal)
        assert result.final_status == "completed"
        assert mock_orchestrator.plasticity_rate == 0.08