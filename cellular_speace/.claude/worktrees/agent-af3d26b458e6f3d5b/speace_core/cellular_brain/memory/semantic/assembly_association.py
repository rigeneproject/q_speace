from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AssemblyAssociation(BaseModel):
    """Represents an associative link between two cell assemblies."""

    id: str
    source_assembly_id: str
    target_assembly_id: str
    association_type: str = "temporal"
    strength: float = 0.1
    confidence: float = 0.0
    coactivation_count: int = 0
    recall_success_count: int = 0
    recall_failure_count: int = 0
    last_reinforced_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AssociativeLearningResult(BaseModel):
    """Aggregate result of an associative learning cycle."""

    created_associations: int = 0
    reinforced_associations: int = 0
    weakened_associations: int = 0
    pruned_associations: int = 0
    mean_association_strength: float = 0.0
    max_association_strength: float = 0.0
    association_density: float = 0.0
    events_logged: int = 0


class AssociativeRecallResult(BaseModel):
    """Result of an associative recall query."""

    cue_assembly_id: str = ""
    recalled_assembly_ids: List[str] = Field(default_factory=list)
    recall_scores: Dict[str, float] = Field(default_factory=dict)
    best_match_id: Optional[str] = None
    best_match_score: float = 0.0
    success: bool = False
    partial_success: bool = False
