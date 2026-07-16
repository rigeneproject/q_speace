"""Tests for AGI team action catalog updates (COR, simulator, external tasks)."""
import pytest

from speace_agi_team.action_catalog import ActionCatalog, ActionCategory, ALLOWED_EXTERNAL_TASKS


def test_action_catalog_has_cor_flags():
    catalog = ActionCatalog()
    actions = catalog.get_actions_for("neuron_tech")
    action_types = {a["action_type"] for a in actions}
    assert "toggle_cor" in action_types
    assert "adjust_cor_threshold" in action_types


def test_action_catalog_has_simulator_actions():
    catalog = ActionCatalog()
    actions = catalog.get_actions_for("synapse_tech")
    action_types = {a["action_type"] for a in actions}
    assert "toggle_simulator_backend" in action_types
    assert "adjust_simulator_interval" in action_types


def test_action_catalog_has_external_tasks():
    catalog = ActionCatalog()
    neuron_actions = {a["action_type"] for a in catalog.get_actions_for("neuron_tech")}
    synapse_actions = {a["action_type"] for a in catalog.get_actions_for("synapse_tech")}
    assert "run_capability_assessment" in neuron_actions
    assert "run_associative_recall_task" in synapse_actions


def test_allowed_external_tasks_defined():
    assert "capability_assessment" in ALLOWED_EXTERNAL_TASKS
    assert "associative_recall" in ALLOWED_EXTERNAL_TASKS
    assert "cognitive_prediction" in ALLOWED_EXTERNAL_TASKS
    assert "grid_navigation" in ALLOWED_EXTERNAL_TASKS


def test_is_authorized_for_external_task():
    catalog = ActionCatalog()
    assert catalog.is_authorized("neuron_tech", ActionCategory.RUN_EXTERNAL_TASK.value, "capability_assessment")
    assert catalog.is_authorized("synapse_tech", ActionCategory.RUN_EXTERNAL_TASK.value, "associative_recall")
    assert not catalog.is_authorized("neuron_tech", ActionCategory.RUN_EXTERNAL_TASK.value, "unknown_task")


def test_classify_action_detects_run_external_task():
    catalog = ActionCatalog()
    assert catalog.infer_category("run_capability_assessment", "capability_assessment") == ActionCategory.RUN_EXTERNAL_TASK.value
    assert catalog.infer_category("run_associative_recall_task", "associative_recall") == ActionCategory.RUN_EXTERNAL_TASK.value
