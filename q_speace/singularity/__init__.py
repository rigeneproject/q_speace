"""T234: Singularity phase-transition evaluator, genetic-epigenetic codec, MCP tools & drills."""

from __future__ import annotations

from .codec import (
    EpigeneticRegulator,
    EvolutionaryGenomeCodec,
    HiddenCausalEvaluator,
    SelfEvolvingEpigeneticEngine,
)
from .drills import DrillOutcome, DrillSuiteReport, run_t234_verification_drills
from .evaluator import (
    PhaseTransitionEvaluator,
    assess_phase_transition,
    compute_energy_weighted_sevo,
)
from .mcp_tools import (
    VALID_MANIFEST_SECTIONS,
    build_singularity_framework_manifest,
    handle_epigenetic_step_evaluate,
    handle_phase_transition_assess,
    handle_singularity_framework_manifest,
)
from .schema import (
    DEFAULT_LOCI,
    DEFAULT_RUNTIME_BINDINGS,
    LOCUS_REGISTRY,
    BottleneckKind,
    CausalFeedback,
    ConstitutionalGenome,
    EpigeneticAuditEntry,
    EpigeneticFaultError,
    EpigeneticLocus,
    EpigeneticProfile,
    EpigeneticProposal,
    EpigeneticStepResult,
    PhaseTelemetry,
    PhaseTransitionAssessment,
    PhaseTransitionTelemetry,
    PhaseTransitionThresholds,
    RuntimeBinding,
    SingularityStage,
    TransitionVerdict,
)

__all__ = [
    "BottleneckKind",
    "CausalFeedback",
    "ConstitutionalGenome",
    "DEFAULT_LOCI",
    "DEFAULT_RUNTIME_BINDINGS",
    "DrillOutcome",
    "DrillSuiteReport",
    "EpigeneticAuditEntry",
    "EpigeneticFaultError",
    "EpigeneticLocus",
    "EpigeneticProfile",
    "EpigeneticProposal",
    "EpigeneticRegulator",
    "EpigeneticStepResult",
    "EvolutionaryGenomeCodec",
    "HiddenCausalEvaluator",
    "LOCUS_REGISTRY",
    "PhaseTelemetry",
    "PhaseTransitionAssessment",
    "PhaseTransitionEvaluator",
    "PhaseTransitionTelemetry",
    "PhaseTransitionThresholds",
    "RuntimeBinding",
    "SelfEvolvingEpigeneticEngine",
    "SingularityStage",
    "TransitionVerdict",
    "VALID_MANIFEST_SECTIONS",
    "assess_phase_transition",
    "build_singularity_framework_manifest",
    "compute_energy_weighted_sevo",
    "handle_epigenetic_step_evaluate",
    "handle_phase_transition_assess",
    "handle_singularity_framework_manifest",
    "run_t234_verification_drills",
]
