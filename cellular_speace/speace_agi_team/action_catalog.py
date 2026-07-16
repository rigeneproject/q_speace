"""ActionCatalog — scoped action permissions for SPEACE AGI team agents.

Defines which actions each agent type can propose, with risk classification
and target constraints. Reuses the ArchitecturePatchExecutor allowlists for
runtime parameter modifications.

CRITICAL: .py files are now permitted for technicians BUT only under
ALLOWED_PY_PATHS and with MANDATORY sandbox verification. The sandbox
must be available; otherwise, .py modifications are blocked.
"""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


# ── Enums ──────────────────────────────────────────────────────────────

class ActionCategory(str, Enum):
    ADJUST_RUNTIME_PARAM = "adjust_runtime_param"
    TOGGLE_FLAG = "toggle_flag"
    SCALE_NUMERIC = "scale_numeric"
    MODIFY_YAML_FILE = "modify_yaml_file"
    MODIFY_PY_FILE = "modify_py_file"          # NEW: create/modify .py files
    WRITE_DATA_FILE = "write_data_file"
    TRIGGER_RECOVERY = "trigger_recovery"
    TRIGGER_SELF_MOD = "trigger_self_mod"
    TRIGGER_SUBSYSTEM_RESTART = "trigger_subsystem_restart"
    RUN_EXTERNAL_TASK = "run_external_task"


class ActionRiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


# ── Allowlists (reuse ArchitecturePatchExecutor) ──────────────────────

ALLOWED_FLAGS: Set[str] = {
    "semantic_memory_enabled",
    "associative_memory_enabled",
    "episodic_policy_enabled",
    "counterfactual_sandbox_enabled",
    "brainstem_controller_enabled",
    "region_stability_controller_enabled",
    "architecture_patch_execution_enabled",
    # T-COR / simulator / lazy-activation / quantum / periodic-table flags
    "cor_enabled",
    "simulator_backend_enabled",
    "functional_activation_enabled",
    "quantum_genes_enabled",
    "periodic_table_genes_enabled",
}

ALLOWED_PROFILES: Set[str] = {
    "recovery_policy_profile",
    "energy_control_profile",
    "brainstem_gain_profile",
    "routing_profile",
    "plasticity_tuning_profile",
}

ALLOWED_NUMERIC: Set[str] = {
    "learning_rate",
    "plasticity_rate",
    "decay_rate",
    "routing_gain",
    "inhibition_decay",
    "semantic_similarity_threshold",
    "assembly_consolidation_threshold",
    # T-COR / simulator tunables
    "cor_phi_threshold_factor",
    "cor_min_latent_states",
    "cor_max_hypotheses",
    "cor_collapse_refractory_ticks",
    "simulator_backend_interval_ticks",
    "simulator_backend_duration_ms",
    "quantum_gate_noise",
}

# ── YAML file allowlist (expanded to all 19 genome files) ────────────

ALLOWED_YAML_PATHS: Set[str] = {
    # Original 4
    "speace_core/dna/genome/default_genome.yaml",
    "speace_core/dna/genome/bootstrap.yaml",
    "speace_core/dna/genome/morphology/linguistic_curriculum.yaml",
    "speace_core/dna/genome/core/species_orientation.yaml",
    # Regulation
    "speace_core/dna/genome/regulation/homeostasis.yaml",
    "speace_core/dna/genome/regulation/immune_rules.yaml",
    "speace_core/dna/genome/regulation/emergent_dynamics.yaml",
    # Morphology
    "speace_core/dna/genome/morphology/allowed_cell_types.yaml",
    "speace_core/dna/genome/morphology/dynamics_substrate.yaml",
    "speace_core/dna/genome/morphology/embodiment_substrate.yaml",
    "speace_core/dna/genome/morphology/autonomous_drives.yaml",
    "speace_core/dna/genome/morphology/distributed_identity.yaml",
    "speace_core/dna/genome/morphology/social_cognition.yaml",
    "speace_core/dna/genome/morphology/multi_body_embodiment.yaml",
    # Core
    "speace_core/dna/genome/core/identity.yaml",
    "speace_core/dna/genome/core/ilf_principles.yaml",
    "speace_core/dna/genome/core/edd_cvt_principles.yaml",
    # Differentiation
    "speace_core/dna/genome/differentiation/cell_expression_rules.yaml",
    # Monitoring
    "speace_core/dna/genome/monitoring_dashboard.yaml",
}

# ── Python file paths (technicians can create/modify .py under these) ─

ALLOWED_PY_PATHS: Set[str] = {
    "speace_core/cellular_brain/cells/",
    "speace_core/cellular_brain/regions/",
    "speace_core/cellular_brain/memory/",
    "speace_core/cellular_brain/analysis/",
    "speace_core/cellular_brain/evolutionary_memory/",
    "speace_core/cellular_brain/self_improvement/",
    "speace_core/cellular_brain/cognition/",
    "speace_core/cellular_brain/embodiment/",
    "speace_core/cellular_brain/language/",
    "speace_core/cellular_brain/experience/",
    "speace_core/cellular_brain/metacognition/",
    "speace_core/cellular_brain/distributed/",
    "speace_core/cellular_brain/regulation/",
    "speace_core/cellular_brain/evolutionary_kernel/",
    "speace_core/cellular_brain/identity_kernel/",
    "speace_core/cellular_brain/harmony/",
    "speace_core/cellular_brain/action_governance/",
    "speace_core/monitoring/",
    "speace_core/runtime/",
}

# ── Data directory prefixes (expanded to all active data directories) ─

ALLOWED_DATA_PREFIXES: Set[str] = {
    # Original 4
    "data/diagnostics/",
    "data/agi_team/",
    "data/self_improvement/",
    "data/runtime/",
    # COR / quantum / neuroperiodic / assessment / environments
    "data/dynamics/",
    "data/quantum/",
    "data/neuroperiodic/",
    "data/assessment/",
    "data/environment/",
    # Regulation & evolution
    "data/regulation/",
    "data/evolution/",
    "data/evolution_daemon/",
    "data/evolution_t20_baseline/",
    # Memory
    "data/morphological_memory/",
    "data/episodic_memory/",
    "data/cognitive_evolution/",
    # Embodiment
    "data/embodiment/",
    "data/embodiment_audit/",
    "data/simulated_embodiment/",
    # Monitoring & analysis
    "data/monitoring/",
    "data/analysis/",
    "data/architecture_patches/",
    "data/sandbox/",
    # Ecosystem & network
    "data/ecosystem/",
    "data/knowledge_graph/",
    # Identity & drives
    "data/identity_kernel/",
    "data/drives/",
    "data/self_model/",
    # Language & dialogue
    "data/language/",
    "data/dialogue/",
    "data/linguistic_curriculum/",
    # Experience & narrative
    "data/experience/",
    "data/persistent_process/",
    # Observer & organism
    "data/organism_observer/",
    "data/morphological_memory/",
    # Failure & testing
    "data/failure_memory/",
    "data/arc_agi/",
    # Web & node
    "data/web_gateway/",
    "data/node_identity/",
}

# ── Allowed external task names (run via environment adapters) ────────

ALLOWED_EXTERNAL_TASKS: Set[str] = {
    "capability_assessment",
    "associative_recall",
    "cognitive_prediction",
    "grid_navigation",
}

# ── Hard blocks: paths and patterns that are NEVER allowed ──────────────
# NOTE: .py is NO LONGER a hard block — it's handled via ALLOWED_PY_PATHS
# with mandatory sandbox verification. Only truly forbidden patterns remain.

BLOCKED_PATH_PATTERNS: Set[str] = {
    ".pyc",
    ".pyo",
    "__pycache__",
}

# ── Absolutely forbidden paths (can never be modified by any agent) ────

ABSOLUTELY_BLOCKED_PATHS: Set[str] = {
    "speace_agi_team/",          # AGI team code itself — never modify
    "tests/",                    # Test code — never modify
    "scripts/",                  # Build/run scripts — never modify
    "pyproject.toml",            # Project config — never modify
    "setup.py",                  # Setup — never modify
    "requirements.txt",          # Dependencies — never modify
}


# ── Agent-specific action definitions ──────────────────────────────────

_TECHNICIAN_ACTIONS: Dict[str, List[tuple]] = {
    "neuron_tech": [
        ("adjust_neuron_threshold", ActionCategory.ADJUST_RUNTIME_PARAM, {"plasticity_rate"}, ActionRiskLevel.LOW),
        ("adjust_plasticity_rate", ActionCategory.SCALE_NUMERIC, {"plasticity_rate"}, ActionRiskLevel.LOW),
        ("trigger_neurogenesis", ActionCategory.TOGGLE_FLAG, {"architecture_patch_execution_enabled"}, ActionRiskLevel.MODERATE),
        ("toggle_cor", ActionCategory.TOGGLE_FLAG, {"cor_enabled"}, ActionRiskLevel.MODERATE),
        ("adjust_cor_threshold", ActionCategory.SCALE_NUMERIC, {"cor_phi_threshold_factor"}, ActionRiskLevel.MODERATE),
        ("run_capability_assessment", ActionCategory.RUN_EXTERNAL_TASK, ALLOWED_EXTERNAL_TASKS, ActionRiskLevel.LOW),
        ("write_neuron_diagnostic", ActionCategory.WRITE_DATA_FILE, ALLOWED_DATA_PREFIXES, ActionRiskLevel.LOW),
        ("modify_cell_types_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/morphology/allowed_cell_types.yaml"}, ActionRiskLevel.HIGH),
        ("modify_cell_expression_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/differentiation/cell_expression_rules.yaml"}, ActionRiskLevel.HIGH),
        ("modify_cell_module", ActionCategory.MODIFY_PY_FILE, {"speace_core/cellular_brain/cells/"}, ActionRiskLevel.HIGH),
        ("modify_analysis_module", ActionCategory.MODIFY_PY_FILE, {"speace_core/cellular_brain/analysis/"}, ActionRiskLevel.HIGH),
    ],
    "synapse_tech": [
        ("adjust_decay_rate", ActionCategory.SCALE_NUMERIC, {"decay_rate"}, ActionRiskLevel.LOW),
        ("adjust_routing_gain", ActionCategory.SCALE_NUMERIC, {"routing_gain"}, ActionRiskLevel.LOW),
        ("toggle_stdp", ActionCategory.TOGGLE_FLAG, {"semantic_memory_enabled"}, ActionRiskLevel.LOW),
        ("toggle_simulator_backend", ActionCategory.TOGGLE_FLAG, {"simulator_backend_enabled"}, ActionRiskLevel.MODERATE),
        ("adjust_simulator_interval", ActionCategory.SCALE_NUMERIC, {"simulator_backend_interval_ticks"}, ActionRiskLevel.LOW),
        ("run_associative_recall_task", ActionCategory.RUN_EXTERNAL_TASK, ALLOWED_EXTERNAL_TASKS, ActionRiskLevel.LOW),
        ("write_synapse_diagnostic", ActionCategory.WRITE_DATA_FILE, ALLOWED_DATA_PREFIXES, ActionRiskLevel.LOW),
        ("modify_dynamics_substrate_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/morphology/dynamics_substrate.yaml"}, ActionRiskLevel.HIGH),
        ("modify_cell_module", ActionCategory.MODIFY_PY_FILE, {"speace_core/cellular_brain/cells/"}, ActionRiskLevel.HIGH),
    ],
    "region_tech": [
        ("toggle_region_routing", ActionCategory.TOGGLE_FLAG, {"region_stability_controller_enabled"}, ActionRiskLevel.LOW),
        ("adjust_inhibition_decay", ActionCategory.SCALE_NUMERIC, {"inhibition_decay"}, ActionRiskLevel.LOW),
        ("toggle_region_stability", ActionCategory.TOGGLE_FLAG, {"region_stability_controller_enabled"}, ActionRiskLevel.LOW),
        ("write_region_diagnostic", ActionCategory.WRITE_DATA_FILE, ALLOWED_DATA_PREFIXES, ActionRiskLevel.LOW),
        ("modify_dynamics_substrate_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/morphology/dynamics_substrate.yaml"}, ActionRiskLevel.HIGH),
        ("modify_region_module", ActionCategory.MODIFY_PY_FILE, {"speace_core/cellular_brain/regions/"}, ActionRiskLevel.HIGH),
    ],
    "genome_tech": [
        ("modify_genome_yaml", ActionCategory.MODIFY_YAML_FILE, ALLOWED_YAML_PATHS, ActionRiskLevel.HIGH),
        ("modify_bootstrap_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/bootstrap.yaml"}, ActionRiskLevel.CRITICAL),
        ("modify_cell_expression_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/differentiation/cell_expression_rules.yaml"}, ActionRiskLevel.HIGH),
        ("modify_monitoring_dashboard_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/monitoring_dashboard.yaml"}, ActionRiskLevel.HIGH),
        ("write_genome_diagnostic", ActionCategory.WRITE_DATA_FILE, ALLOWED_DATA_PREFIXES, ActionRiskLevel.LOW),
        ("modify_evolutionary_memory_module", ActionCategory.MODIFY_PY_FILE, {"speace_core/cellular_brain/evolutionary_memory/"}, ActionRiskLevel.CRITICAL),
    ],
    "runtime_tech": [
        ("adjust_circadian_params", ActionCategory.SCALE_NUMERIC, {"learning_rate"}, ActionRiskLevel.MODERATE),
        ("trigger_recovery", ActionCategory.TRIGGER_RECOVERY, set(), ActionRiskLevel.HIGH),
        ("trigger_coherence_injection", ActionCategory.ADJUST_RUNTIME_PARAM, {"routing_gain"}, ActionRiskLevel.MODERATE),
        ("toggle_counterfactual_sandbox", ActionCategory.TOGGLE_FLAG, {"counterfactual_sandbox_enabled"}, ActionRiskLevel.LOW),
        ("inject_neuron_energy", ActionCategory.ADJUST_RUNTIME_PARAM, {"learning_rate", "plasticity_rate"}, ActionRiskLevel.MODERATE),
        ("activate_stalled_neurons", ActionCategory.TRIGGER_RECOVERY, set(), ActionRiskLevel.HIGH),
        ("force_advance_tick", ActionCategory.TRIGGER_RECOVERY, set(), ActionRiskLevel.HIGH),
        ("reset_neuron_activations", ActionCategory.TRIGGER_SUBSYSTEM_RESTART, set(), ActionRiskLevel.CRITICAL),
        ("write_runtime_diagnostic", ActionCategory.WRITE_DATA_FILE, ALLOWED_DATA_PREFIXES, ActionRiskLevel.LOW),
        ("modify_homeostasis_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/regulation/homeostasis.yaml"}, ActionRiskLevel.HIGH),
        ("modify_emergent_dynamics_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/regulation/emergent_dynamics.yaml"}, ActionRiskLevel.HIGH),
        ("modify_monitoring_dashboard_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/monitoring_dashboard.yaml"}, ActionRiskLevel.HIGH),
        ("modify_runtime_module", ActionCategory.MODIFY_PY_FILE, {"speace_core/runtime/"}, ActionRiskLevel.CRITICAL),
    ],
    "defense_tech": [
        ("toggle_immune_system", ActionCategory.TOGGLE_FLAG, {"associative_memory_enabled"}, ActionRiskLevel.MODERATE),
        ("write_defense_diagnostic", ActionCategory.WRITE_DATA_FILE, ALLOWED_DATA_PREFIXES, ActionRiskLevel.LOW),
        ("modify_immune_rules_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/regulation/immune_rules.yaml"}, ActionRiskLevel.HIGH),
        ("modify_regulation_module", ActionCategory.MODIFY_PY_FILE, {"speace_core/cellular_brain/regulation/"}, ActionRiskLevel.HIGH),
    ],
    "memory_tech": [
        ("adjust_consolidation_threshold", ActionCategory.SCALE_NUMERIC, {"assembly_consolidation_threshold"}, ActionRiskLevel.LOW),
        ("toggle_semantic_memory", ActionCategory.TOGGLE_FLAG, {"semantic_memory_enabled"}, ActionRiskLevel.LOW),
        ("toggle_episodic_policy", ActionCategory.TOGGLE_FLAG, {"episodic_policy_enabled"}, ActionRiskLevel.LOW),
        ("write_memory_diagnostic", ActionCategory.WRITE_DATA_FILE, ALLOWED_DATA_PREFIXES, ActionRiskLevel.LOW),
        ("modify_memory_module", ActionCategory.MODIFY_PY_FILE, {"speace_core/cellular_brain/memory/"}, ActionRiskLevel.HIGH),
    ],
    "evolution_tech": [
        ("trigger_evolution_cycle", ActionCategory.TRIGGER_SELF_MOD, set(), ActionRiskLevel.HIGH),
        ("modify_evolution_params", ActionCategory.SCALE_NUMERIC, {"learning_rate", "plasticity_rate"}, ActionRiskLevel.MODERATE),
        ("toggle_brainstem_controller", ActionCategory.TOGGLE_FLAG, {"brainstem_controller_enabled"}, ActionRiskLevel.MODERATE),
        ("write_evolution_diagnostic", ActionCategory.WRITE_DATA_FILE, ALLOWED_DATA_PREFIXES, ActionRiskLevel.LOW),
        ("modify_edd_cvt_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/core/edd_cvt_principles.yaml"}, ActionRiskLevel.HIGH),
        ("modify_self_improvement_module", ActionCategory.MODIFY_PY_FILE, {"speace_core/cellular_brain/self_improvement/"}, ActionRiskLevel.CRITICAL),
    ],
    "network_tech": [
        ("modify_ecosystem_config", ActionCategory.MODIFY_YAML_FILE, ALLOWED_YAML_PATHS, ActionRiskLevel.HIGH),
        ("write_network_diagnostic", ActionCategory.WRITE_DATA_FILE, ALLOWED_DATA_PREFIXES, ActionRiskLevel.LOW),
        ("modify_social_cognition_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/morphology/social_cognition.yaml"}, ActionRiskLevel.HIGH),
        ("modify_distributed_module", ActionCategory.MODIFY_PY_FILE, {"speace_core/cellular_brain/distributed/"}, ActionRiskLevel.HIGH),
    ],
    "embodiment_tech": [
        ("modify_embodiment_config", ActionCategory.MODIFY_YAML_FILE, ALLOWED_YAML_PATHS, ActionRiskLevel.HIGH),
        ("trigger_parameter_reset", ActionCategory.ADJUST_RUNTIME_PARAM, {"decay_rate", "routing_gain"}, ActionRiskLevel.MODERATE),
        ("write_embodiment_diagnostic", ActionCategory.WRITE_DATA_FILE, ALLOWED_DATA_PREFIXES, ActionRiskLevel.LOW),
        ("modify_embodiment_substrate_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/morphology/embodiment_substrate.yaml"}, ActionRiskLevel.HIGH),
        ("modify_multi_body_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/morphology/multi_body_embodiment.yaml"}, ActionRiskLevel.HIGH),
        ("modify_embodiment_module", ActionCategory.MODIFY_PY_FILE, {"speace_core/cellular_brain/embodiment/"}, ActionRiskLevel.HIGH),
    ],
}

_SUPERVISOR_ACTIONS: Dict[str, List[tuple]] = {
    "chief_architect": [],  # Can propose ANY action (handled in is_authorized)
    "brain_supervisor": [
        ("toggle_brainstem_controller", ActionCategory.TOGGLE_FLAG, {"brainstem_controller_enabled"}, ActionRiskLevel.MODERATE),
        ("modify_brain_config_yaml", ActionCategory.MODIFY_YAML_FILE, ALLOWED_YAML_PATHS, ActionRiskLevel.HIGH),
        ("modify_allowed_cell_types_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/morphology/allowed_cell_types.yaml"}, ActionRiskLevel.HIGH),
        ("modify_dynamics_substrate_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/morphology/dynamics_substrate.yaml"}, ActionRiskLevel.HIGH),
        ("modify_cell_expression_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/differentiation/cell_expression_rules.yaml"}, ActionRiskLevel.HIGH),
        ("inject_neuron_energy", ActionCategory.ADJUST_RUNTIME_PARAM, {"plasticity_rate", "learning_rate"}, ActionRiskLevel.MODERATE),
        ("activate_stalled_neurons", ActionCategory.TRIGGER_RECOVERY, set(), ActionRiskLevel.HIGH),
        ("reset_neuron_activations", ActionCategory.TRIGGER_SUBSYSTEM_RESTART, set(), ActionRiskLevel.CRITICAL),
        ("modify_cell_module", ActionCategory.MODIFY_PY_FILE, {"speace_core/cellular_brain/cells/"}, ActionRiskLevel.HIGH),
        ("modify_region_module", ActionCategory.MODIFY_PY_FILE, {"speace_core/cellular_brain/regions/"}, ActionRiskLevel.HIGH),
        ("write_brain_diagnostic", ActionCategory.WRITE_DATA_FILE, ALLOWED_DATA_PREFIXES, ActionRiskLevel.LOW),
    ],
    "dna_supervisor": [
        ("modify_genome_yaml", ActionCategory.MODIFY_YAML_FILE, ALLOWED_YAML_PATHS, ActionRiskLevel.HIGH),
        ("modify_bootstrap_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/bootstrap.yaml"}, ActionRiskLevel.CRITICAL),
        ("modify_cell_expression_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/differentiation/cell_expression_rules.yaml"}, ActionRiskLevel.HIGH),
        ("modify_evolutionary_memory_module", ActionCategory.MODIFY_PY_FILE, {"speace_core/cellular_brain/evolutionary_memory/"}, ActionRiskLevel.CRITICAL),
        ("write_genome_diagnostic", ActionCategory.WRITE_DATA_FILE, ALLOWED_DATA_PREFIXES, ActionRiskLevel.LOW),
    ],
    "organism_supervisor": [
        ("modify_homeostasis_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/regulation/homeostasis.yaml"}, ActionRiskLevel.HIGH),
        ("modify_autonomous_drives_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/morphology/autonomous_drives.yaml"}, ActionRiskLevel.HIGH),
        ("trigger_subsystem_restart", ActionCategory.TRIGGER_SUBSYSTEM_RESTART, set(), ActionRiskLevel.CRITICAL),
        ("inject_neuron_energy", ActionCategory.ADJUST_RUNTIME_PARAM, {"learning_rate", "plasticity_rate"}, ActionRiskLevel.MODERATE),
        ("activate_stalled_neurons", ActionCategory.TRIGGER_RECOVERY, set(), ActionRiskLevel.HIGH),
        ("force_advance_tick", ActionCategory.TRIGGER_RECOVERY, set(), ActionRiskLevel.HIGH),
        ("reset_neuron_activations", ActionCategory.TRIGGER_SUBSYSTEM_RESTART, set(), ActionRiskLevel.CRITICAL),
        ("modify_regulation_module", ActionCategory.MODIFY_PY_FILE, {"speace_core/cellular_brain/regulation/"}, ActionRiskLevel.HIGH),
        ("modify_runtime_module", ActionCategory.MODIFY_PY_FILE, {"speace_core/runtime/"}, ActionRiskLevel.CRITICAL),
        ("write_organism_diagnostic", ActionCategory.WRITE_DATA_FILE, ALLOWED_DATA_PREFIXES, ActionRiskLevel.LOW),
    ],
    "memory_supervisor": [
        ("modify_curriculum_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/morphology/linguistic_curriculum.yaml"}, ActionRiskLevel.HIGH),
        ("modify_memory_module", ActionCategory.MODIFY_PY_FILE, {"speace_core/cellular_brain/memory/"}, ActionRiskLevel.HIGH),
        ("modify_cognition_module", ActionCategory.MODIFY_PY_FILE, {"speace_core/cellular_brain/cognition/"}, ActionRiskLevel.HIGH),
        ("write_memory_diagnostic", ActionCategory.WRITE_DATA_FILE, ALLOWED_DATA_PREFIXES, ActionRiskLevel.LOW),
    ],
    "selfimprovement_supervisor": [
        ("trigger_self_modification_cycle", ActionCategory.TRIGGER_SELF_MOD, set(), ActionRiskLevel.HIGH),
        ("modify_evolution_yaml", ActionCategory.MODIFY_YAML_FILE, ALLOWED_YAML_PATHS, ActionRiskLevel.HIGH),
        ("modify_edd_cvt_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/core/edd_cvt_principles.yaml"}, ActionRiskLevel.HIGH),
        ("modify_self_improvement_module", ActionCategory.MODIFY_PY_FILE, {"speace_core/cellular_brain/self_improvement/"}, ActionRiskLevel.CRITICAL),
        ("write_selfimprovement_diagnostic", ActionCategory.WRITE_DATA_FILE, ALLOWED_DATA_PREFIXES, ActionRiskLevel.LOW),
    ],
    "embodied_cognition_supervisor": [
        ("modify_embodiment_config", ActionCategory.MODIFY_YAML_FILE, ALLOWED_YAML_PATHS, ActionRiskLevel.HIGH),
        ("modify_embodiment_substrate_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/morphology/embodiment_substrate.yaml"}, ActionRiskLevel.HIGH),
        ("modify_multi_body_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/morphology/multi_body_embodiment.yaml"}, ActionRiskLevel.HIGH),
        ("modify_embodiment_module", ActionCategory.MODIFY_PY_FILE, {"speace_core/cellular_brain/embodiment/"}, ActionRiskLevel.HIGH),
        ("write_embodiment_diagnostic", ActionCategory.WRITE_DATA_FILE, ALLOWED_DATA_PREFIXES, ActionRiskLevel.LOW),
    ],
    "advanced_language_supervisor": [
        ("modify_curriculum_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/morphology/linguistic_curriculum.yaml"}, ActionRiskLevel.HIGH),
        ("modify_social_cognition_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/morphology/social_cognition.yaml"}, ActionRiskLevel.HIGH),
        ("modify_language_module", ActionCategory.MODIFY_PY_FILE, {"speace_core/cellular_brain/language/"}, ActionRiskLevel.HIGH),
        ("write_language_diagnostic", ActionCategory.WRITE_DATA_FILE, ALLOWED_DATA_PREFIXES, ActionRiskLevel.LOW),
    ],
    "longterm_planning_supervisor": [
        ("modify_species_orientation_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/core/species_orientation.yaml"}, ActionRiskLevel.HIGH),
        ("modify_ilf_principles_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/core/ilf_principles.yaml"}, ActionRiskLevel.HIGH),
        ("modify_monitoring_dashboard_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/monitoring_dashboard.yaml"}, ActionRiskLevel.HIGH),
        ("write_planning_diagnostic", ActionCategory.WRITE_DATA_FILE, ALLOWED_DATA_PREFIXES, ActionRiskLevel.LOW),
    ],
    "self_awareness_supervisor": [
        ("modify_bootstrap_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/bootstrap.yaml"}, ActionRiskLevel.CRITICAL),
        ("modify_identity_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/core/identity.yaml"}, ActionRiskLevel.CRITICAL),
        ("modify_distributed_identity_yaml", ActionCategory.MODIFY_YAML_FILE, {"speace_core/dna/genome/morphology/distributed_identity.yaml"}, ActionRiskLevel.HIGH),
        ("modify_identity_kernel_module", ActionCategory.MODIFY_PY_FILE, {"speace_core/cellular_brain/identity_kernel/"}, ActionRiskLevel.CRITICAL),
        ("modify_metacognition_module", ActionCategory.MODIFY_PY_FILE, {"speace_core/cellular_brain/metacognition/"}, ActionRiskLevel.HIGH),
        ("write_awareness_diagnostic", ActionCategory.WRITE_DATA_FILE, ALLOWED_DATA_PREFIXES, ActionRiskLevel.LOW),
    ],
}

# Supervisor → technician mapping (reuses Orchestrator._find_supervisor_for)
_SUPERVISOR_TECHNICIAN_MAP: Dict[str, List[str]] = {
    "chief_architect": [],
    "brain_supervisor": ["neuron_tech", "synapse_tech", "region_tech"],
    "dna_supervisor": ["genome_tech"],
    "organism_supervisor": ["runtime_tech", "defense_tech", "network_tech"],
    "memory_supervisor": ["memory_tech"],
    "selfimprovement_supervisor": ["evolution_tech"],
    "embodied_cognition_supervisor": ["embodiment_tech"],
    "advanced_language_supervisor": [],
    "longterm_planning_supervisor": [],
    "self_awareness_supervisor": [],
}


class ActionCatalog:
    """Manages agent-scoped action permissions.

    Each agent type can only propose actions within its catalog.
    The chief_architect can propose any action from any catalog.
    """

    @staticmethod
    def _all_actions() -> List[tuple]:
        """Flatten all actions from technician and supervisor catalogs."""
        actions = []
        for agent_id, agent_actions in _TECHNICIAN_ACTIONS.items():
            actions.extend(agent_actions)
        for agent_id, agent_actions in _SUPERVISOR_ACTIONS.items():
            actions.extend(agent_actions)
        return actions

    def is_authorized(self, agent_id: str, action_category: str, target: str) -> bool:
        """Check if an agent is authorized to propose a specific action.

        Rules:
        1. chief_architect can propose anything
        2. Supervisors can propose their own actions + their technicians' actions
        3. Technicians can only propose their own actions
        4. .py files are authorized ONLY under ALLOWED_PY_PATHS
        5. Absolutely blocked paths are never allowed
        6. Targets outside allowedlists are blocked
        """
        # Hard block: absolutely forbidden paths
        if self._is_absolutely_blocked(target):
            return False

        # .py files: special authorization via ALLOWED_PY_PATHS
        if target.endswith(".py") or action_category == ActionCategory.MODIFY_PY_FILE.value:
            return self._is_authorized_py(agent_id, target)

        # Hard block: remaining blocked patterns (.pyc, __pycache__)
        if self._is_blocked_path(target):
            return False

        # chief_architect can do anything (except .py, handled above)
        if agent_id == "chief_architect":
            return True

        # Gather all actions this agent can propose
        allowed_actions = self._get_agent_actions(agent_id)

        for action_type, cat, targets, risk in allowed_actions:
            if cat.value == action_category or cat == action_category:
                # Check target is in allowed set
                if not targets:
                    # Empty targets = any target allowed (e.g., trigger_recovery)
                    return True
                if target in targets:
                    return True
                # For data file writes, check prefix match
                if action_category == ActionCategory.WRITE_DATA_FILE.value:
                    for prefix in targets:
                        if target.startswith(prefix):
                            return True
        return False

    def get_risk_level(self, agent_id: str, action_category: str, target: str) -> ActionRiskLevel:
        """Get the risk level for a specific action."""
        if agent_id == "chief_architect":
            # chief_architect uses the risk level from the matching action definition
            pass

        allowed_actions = self._get_agent_actions(agent_id)
        for action_type, cat, targets, risk in allowed_actions:
            if cat.value == action_category or cat == action_category:
                if not targets or target in targets:
                    return risk
                if action_category == ActionCategory.WRITE_DATA_FILE.value:
                    for prefix in targets:
                        if target.startswith(prefix):
                            return risk
                # For MODIFY_PY_FILE, check path prefix match
                if action_category == ActionCategory.MODIFY_PY_FILE.value:
                    for allowed_path in targets:
                        if target.startswith(allowed_path):
                            return risk
        return ActionRiskLevel.CRITICAL  # Default to highest risk if not found

    def get_actions_for(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get all actions available to a specific agent."""
        actions = self._get_agent_actions(agent_id)
        return [
            {
                "action_type": at,
                "action_category": cat.value if isinstance(cat, ActionCategory) else cat,
                "targets": sorted(targets) if isinstance(targets, set) else sorted(list(targets)),
                "risk_level": risk.value if isinstance(risk, ActionRiskLevel) else risk,
            }
            for at, cat, targets, risk in actions
        ]

    def get_summary(self, agent_id: str) -> str:
        """Human-readable summary of an agent's action catalog."""
        actions = self.get_actions_for(agent_id)
        lines = [f"Azioni disponibili per {agent_id}:"]
        for a in actions:
            lines.append(
                f"  - {a['action_type']} [{a['action_category']}] "
                f"risk={a['risk_level']} targets={a['targets'][:3]}{'...' if len(a['targets']) > 3 else ''}"
            )
        return "\n".join(lines)

    def infer_category(self, action_type: str, target: str) -> str:
        """Infer the action category from action_type and target."""
        # .py files
        if target.endswith(".py"):
            return ActionCategory.MODIFY_PY_FILE.value
        # Runtime parameters
        if target in ALLOWED_FLAGS or target in ALLOWED_NUMERIC:
            return ActionCategory.ADJUST_RUNTIME_PARAM.value
        if target in ALLOWED_PROFILES:
            return ActionCategory.TOGGLE_FLAG.value
        # YAML files
        if target.endswith(".yaml") or target.endswith(".yml"):
            return ActionCategory.MODIFY_YAML_FILE.value
        # Data files
        if target.startswith("data/"):
            return ActionCategory.WRITE_DATA_FILE.value
        # External tasks
        if action_type.startswith("run_") or action_type in ALLOWED_EXTERNAL_TASKS:
            return ActionCategory.RUN_EXTERNAL_TASK.value
        # Triggers
        if "recovery" in action_type.lower():
            return ActionCategory.TRIGGER_RECOVERY.value
        if "self_mod" in action_type.lower() or "evolution" in action_type.lower():
            return ActionCategory.TRIGGER_SELF_MOD.value
        if "restart" in action_type.lower():
            return ActionCategory.TRIGGER_SUBSYSTEM_RESTART.value
        # Default
        return ActionCategory.ADJUST_RUNTIME_PARAM.value

    def _get_agent_actions(self, agent_id: str) -> List[tuple]:
        """Get all actions available to an agent, including inherited ones."""
        actions = list(_TECHNICIAN_ACTIONS.get(agent_id, []))
        actions.extend(_SUPERVISOR_ACTIONS.get(agent_id, []))

        # Supervisors also inherit their technicians' actions
        if agent_id in _SUPERVISOR_TECHNICIAN_MAP:
            for tech_id in _SUPERVISOR_TECHNICIAN_MAP[agent_id]:
                actions.extend(_TECHNICIAN_ACTIONS.get(tech_id, []))

        return actions

    def get_full_catalog(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get the complete catalog for all agents."""
        result = {}
        all_agents = set(_TECHNICIAN_ACTIONS.keys()) | set(_SUPERVISOR_ACTIONS.keys())
        for agent_id in sorted(all_agents):
            result[agent_id] = self.get_actions_for(agent_id)
        return result

    @staticmethod
    def _is_blocked_path(target: str) -> bool:
        """Check if a target path is blocked (e.g., .pyc, __pycache__)."""
        target_lower = target.lower()
        for pattern in BLOCKED_PATH_PATTERNS:
            if pattern in target_lower:
                return True
        # Block any path outside allowed directories
        if target.startswith("/") or ".." in target:
            return True
        return False

    @staticmethod
    def _is_absolutely_blocked(target: str) -> bool:
        """Check if a target path is absolutely forbidden for any agent."""
        target_lower = target.lower().replace("\\", "/")
        for blocked in ABSOLUTELY_BLOCKED_PATHS:
            if target_lower.startswith(blocked.lower()) or target_lower == blocked.lower():
                return True
        return False

    @staticmethod
    def _is_authorized_py(agent_id: str, target: str) -> bool:
        """Check if an agent is authorized for a .py file modification.

        Rules:
        1. Target must be under one of the ALLOWED_PY_PATHS
        2. Agent must have a MODIFY_PY_FILE action for that path
        3. chief_architect can modify any .py under ALLOWED_PY_PATHS
        """
        # Normalize path
        target_norm = target.lower().replace("\\", "/")

        # Must be under an allowed path
        path_allowed = False
        for allowed_path in ALLOWED_PY_PATHS:
            if target_norm.startswith(allowed_path.lower()):
                path_allowed = True
                break

        if not path_allowed:
            return False

        # chief_architect can modify any .py under allowed paths
        if agent_id == "chief_architect":
            return True

        # Check agent has MODIFY_PY_FILE action for this path
        catalog = ActionCatalog()
        actions = catalog._get_agent_actions(agent_id)
        for action_type, cat, targets, risk in actions:
            if cat == ActionCategory.MODIFY_PY_FILE:
                for allowed_target in targets:
                    if target_norm.startswith(allowed_target.lower()):
                        return True

        return False