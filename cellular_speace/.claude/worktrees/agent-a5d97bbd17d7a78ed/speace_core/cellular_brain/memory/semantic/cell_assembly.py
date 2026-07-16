from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CellAssembly(BaseModel):
    """A cell assembly is a recurrent co-activation pattern representing
    a distributed semantic memory trace."""

    assembly_id: str
    created_tick: int = 0
    last_activated_tick: int = 0
    neuron_ids: List[str] = Field(default_factory=list)
    region_ids: List[str] = Field(default_factory=list)
    activation_signature: List[float] = Field(default_factory=list)
    semantic_pointer: str = ""
    strength: float = 0.0
    stability: float = 0.0
    recurrence_count: int = 0
    utility_score: float = 0.0
    coherence_phi_at_creation: float = 0.0
    mean_energy_at_creation: float = 0.0
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    consolidated: bool = False
    active: bool = True


class AssemblyActivationTrace(BaseModel):
    """Snapshot of active neurons/regions at a given tick."""

    tick_id: int = 0
    active_neuron_ids: List[str] = Field(default_factory=list)
    active_region_ids: List[str] = Field(default_factory=list)
    activation_vector: List[float] = Field(default_factory=list)
    mean_activation: float = 0.0
    coherence_phi: float = 0.0
    mean_energy: float = 0.0
    confidence_score: float = 0.0


class SemanticRecallResult(BaseModel):
    """Result of a semantic recall query."""

    query_signature: List[float] = Field(default_factory=list)
    matched_assemblies: List[str] = Field(default_factory=list)
    best_match_id: Optional[str] = None
    similarity_score: float = 0.0
    recalled_activation_pattern: List[float] = Field(default_factory=list)
    recall_confidence: float = 0.0
    recall_success: bool = False


class SemanticMemoryMetrics(BaseModel):
    """Aggregate metrics for the semantic memory layer."""

    assembly_count: int = 0
    active_assembly_count: int = 0
    mean_assembly_strength: float = 0.0
    mean_assembly_stability: float = 0.0
    semantic_recall_success_rate: float = 0.0
    semantic_memory_density: float = 0.0
    semantic_memory_utility: float = 0.0
    semantic_consolidation_rate: float = 0.0
    semantic_decay_rate: float = 0.0
