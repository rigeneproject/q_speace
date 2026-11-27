"""q_speace.aacm — Alexander's Asymmetric Control Model for SPEACE.

Implements the engineering specification in ``docs/T-AACM-SPEC.md``.
The model extracts 9 strategic rules from the conquest patterns of
Alexander the Great and codifies them as: dataclass primitives,
numpy-only dynamics, JSON-validated checkpoints, and integration hooks
into the existing :class:`QuantumOrchestrator` and
:class:`EvolutionCouncil`.

Submodules are intentionally **numpy-only** — no scipy/torch — to
respect the AGENTS.md invariant. AACM is a control layer, not a model
fine-tune: it operates on the same substrate as the rest of q_speace.

BCEL: the AACM primitives are *functional*: each is a measurable
quantity or a deterministic operator. "Centrality" is a betweenness
score on a graph; "legitimacy" is a count of verified artefacts.
Neither is a metaphor for an agent's intent.
"""

from __future__ import annotations

from .checkpoint import (
    check_compatibility,
    load_checkpoint,
    write_checkpoint,
)
from .constants import (
    CENTRALITY_HIT_THRESHOLD,
    CHECKPOINT_INTERVAL_STEPS,
    DECAY_HALF_LIFE_S,
    FAIL_FAST_WINDOW,
    LEGITIMATION_K_MIN,
    OMEGA_MIN,
)
from .controller import AACMController, AACMStrategy, StepDecision
from .dynamics import (
    assert_resilience,
    collapse_probability,
    convert_opposition_to_capacity,
    dS_dt,
    infrastructure_self_sustaining,
    leverage_pre_existing_fractures,
    reputation_multiplier,
    resistance_decay,
    t_a_within_budget,
    value_integral,
)
from .exceptions import InvariantViolation
from .executor import ExecutionResult, WorktreeExecutor
from .loop import (
    LOOP_HARD_PROHIBITIONS,
    AACMLoop,
    FallbackEntry,
    FallbackRegistry,
    LoopIteration,
    LoopProhibited,
    LoopResult,
    LoopStop,
    ModuleReplacementProposal,
    ReputationEntry,
    ReputationRegistry,
    StopReason,
    ValidationSet,
    ValidationSetError,
    ValidationTask,
    adversarial_threshold,
    effective_min_evidence_kinds_for,
    evaluate_fallback_eligibility,
)
from .loop_constants import (
    ADVERSARIAL_THRESHOLD_BASE,
    ADVERSARIAL_THRESHOLD_HIGH_OMEGA,
    ADVERSARIAL_THRESHOLD_LOW_OMEGA,
    LOOP_CHECKPOINT_SCHEMA_VERSION,
    MAX_ITERATIONS,
    MAX_WALL_CLOCK_S,
    REPUTATION_HALF_LIFE_S,
)
from .plasticity import (
    EdgeGrowthProposal,
    EntropyBoundedUCB1Gating,
    GatingPolicy,
    GraphEdgePruner,
    ProposalOnlyEdgeGrower,
    shannon_entropy_bits,
)
from .pr_helper import PRResult, build_pr_body, create_pr
from .primitives import (
    CentralityGraph,
    FractureMap,
    LegitimationChannel,
    LegitimationChannelRegistry,
    ResilienceManifest,
)
from .resume import AACMResume
from .topology import (
    betweenness_centrality,
    edge_weights_from_observations,
    node_failure_streak,
)
from .typed_dag import (
    ContractSpec,
    DAGNodeSpec,
    EdgeKind,
    ExecutionTicket,
    FieldConstraint,
    PortEdge,
    TypedComputationalDAG,
)

__all__ = [
    # constants
    "OMEGA_MIN",
    "LEGITIMATION_K_MIN",
    "CHECKPOINT_INTERVAL_STEPS",
    "CENTRALITY_HIT_THRESHOLD",
    "FAIL_FAST_WINDOW",
    "DECAY_HALF_LIFE_S",
    # primitives
    "CentralityGraph",
    "FractureMap",
    "LegitimationChannel",
    "LegitimationChannelRegistry",
    "ResilienceManifest",
    # dynamics
    "dS_dt",
    "t_a_within_budget",
    "leverage_pre_existing_fractures",
    "convert_opposition_to_capacity",
    "reputation_multiplier",
    "resistance_decay",
    "infrastructure_self_sustaining",
    "collapse_probability",
    "assert_resilience",
    "value_integral",
    # topology
    "betweenness_centrality",
    "edge_weights_from_observations",
    "node_failure_streak",
    # controller
    "AACMController",
    "AACMStrategy",
    "StepDecision",
    # checkpoint
    "write_checkpoint",
    "load_checkpoint",
    "check_compatibility",
    # resume
    "AACMResume",
    # exceptions
    "InvariantViolation",
    # loop (T-AACM-LOOP_SPEC)
    "AACMLoop",
    "LoopIteration",
    "LoopResult",
    "LoopProhibited",
    "LoopStop",
    "StopReason",
    "ModuleReplacementProposal",
    "ReputationEntry",
    "ReputationRegistry",
    "ValidationSet",
    "ValidationSetError",
    "ValidationTask",
    "FallbackEntry",
    "FallbackRegistry",
    "LOOP_HARD_PROHIBITIONS",
    "adversarial_threshold",
    "effective_min_evidence_kinds_for",
    "evaluate_fallback_eligibility",
    "ADVERSARIAL_THRESHOLD_BASE",
    "ADVERSARIAL_THRESHOLD_HIGH_OMEGA",
    "ADVERSARIAL_THRESHOLD_LOW_OMEGA",
    "LOOP_CHECKPOINT_SCHEMA_VERSION",
    "MAX_ITERATIONS",
    "MAX_WALL_CLOCK_S",
    "MAX_DIFF_LINES",
    "REPUTATION_HALF_LIFE_S",
    # executor (T-AACM-LOOP_SPEC §C1)
    "ExecutionResult",
    "WorktreeExecutor",
    # pr helper (T-AACM-LOOP_SPEC §D4)
    "PRResult",
    "build_pr_body",
    "create_pr",
    # plasticity & UCB1 gating (T249-02)
    "EdgeGrowthProposal",
    "EntropyBoundedUCB1Gating",
    "GatingPolicy",
    "GraphEdgePruner",
    "ProposalOnlyEdgeGrower",
    "shannon_entropy_bits",
    # typed contract DAG (T256-02)
    "ContractSpec",
    "DAGNodeSpec",
    "EdgeKind",
    "ExecutionTicket",
    "FieldConstraint",
    "PortEdge",
    "TypedComputationalDAG",
]
