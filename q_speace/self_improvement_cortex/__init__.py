"""Self-Improvement Cortex — SIA integration for SPEACE.

Provides the SelfImprovementCortex, EvolutionCouncil, OrganismObserver,
10-level adaptive hierarchy, epigenetic memory, neurogenesis, and the
Quantum Evolution Engine (QEE). See docs/progetto_q_speace_linee_guida.md §9.
"""

from __future__ import annotations

from .adaptive_levels import AdaptiveLevel, AdaptiveLevelRegistry, HarnessUpdate, WeightUpdate
from .cortex import PatchCycleResult, SandboxedPatchCycle, SelfImprovementCortex
from .dna_registry import DNAMutationRecord, MutationRegistry
from .epigenetics import EpigeneticEngine, EpigeneticMarker, EpigeneticState, EpigeneticTag
from .evolution_council import (
    AgentProposal,
    DigitalDNAAgent,
    EpistemicAuditResult,
    EpistemicProposalAuditor,
    EvolutionCouncil,
    EvolutionOrchestrator,
    ILFAgent,
    MemoryAgent,
    MutationAgent,
    NeuroscienceAgent,
    RLAgent,
    SafetyAgent,
    SoftwareArchitect,
)
from .evolutionary_memory import EvolutionaryMemory, MemoryEntry
from .ilf_regulator import ILFRegulator, MutationVerdict
from .macro_skills import (
    AnalogicalRoleMapper,
    AnalogyAuditTrace,
    EmpiricalOperatorModel,
    EpisodeExecutionReport,
    ExperientialCognitiveAgent,
    LiftedAtom,
    ParameterizedStep,
    RepairDecisionKind,
    RevisionExecutionReport,
    RoleParameterizedMacroSkill,
    RoleTopologyProfile,
    StatefulPlanningEnvironment,
    compute_regressed_kernels,
    extract_macro_skill,
    format_structured_atom,
    parse_structured_atom,
)
from .neurogenesis import NeurogenesisPipeline, NewModuleSpec
from .organism_observer import OrganismObserver, PhysiologicalProfile
from .quantum_engine import (
    QAOASelector,
    QuantumEvolutionEngine,
    QuantumKernelClassifier,
    QuantumOracle,
)
from .rollback import RollbackManager, RollbackPlan
from .skill_library import ReconsolidationWindow, ReusableSkill, SkillLibrary

__all__ = [
    "SelfImprovementCortex",
    "EvolutionCouncil",
    "EvolutionOrchestrator",
    "NeuroscienceAgent",
    "SoftwareArchitect",
    "RLAgent",
    "MemoryAgent",
    "SafetyAgent",
    "DigitalDNAAgent",
    "ILFAgent",
    "MutationAgent",
    "AgentProposal",
    "OrganismObserver",
    "PhysiologicalProfile",
    "AdaptiveLevel",
    "AdaptiveLevelRegistry",
    "HarnessUpdate",
    "WeightUpdate",
    "DNAMutationRecord",
    "MutationRegistry",
    "EpigeneticMarker",
    "EpigeneticTag",
    "EpigeneticState",
    "EpigeneticEngine",
    "EvolutionaryMemory",
    "MemoryEntry",
    "ILFRegulator",
    "MutationVerdict",
    "NeurogenesisPipeline",
    "NewModuleSpec",
    "RollbackManager",
    "RollbackPlan",
    "QuantumEvolutionEngine",
    "QuantumOracle",
    "QAOASelector",
    "QuantumKernelClassifier",
    "PatchCycleResult",
    "SandboxedPatchCycle",
    "EpistemicAuditResult",
    "EpistemicProposalAuditor",
    "ReusableSkill",
    "SkillLibrary",
    "ReconsolidationWindow",
    "AnalogicalRoleMapper",
    "AnalogyAuditTrace",
    "EmpiricalOperatorModel",
    "EpisodeExecutionReport",
    "ExperientialCognitiveAgent",
    "LiftedAtom",
    "ParameterizedStep",
    "RepairDecisionKind",
    "RevisionExecutionReport",
    "RoleParameterizedMacroSkill",
    "RoleTopologyProfile",
    "StatefulPlanningEnvironment",
    "compute_regressed_kernels",
    "extract_macro_skill",
    "format_structured_atom",
    "parse_structured_atom",
]
