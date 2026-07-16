import time
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NodeTypeObs(str, Enum):
    THOUGHT = "thought"
    DECISION = "decision"
    GOAL = "goal"
    MEMORY_STATE = "memory_state"
    BELIEF = "belief"
    HYPOTHESIS = "hypothesis"
    MUTATION_EVENT = "mutation_event"
    ACTION = "action"
    ERROR = "error"
    LEARNING_EVENT = "learning_event"
    NARRATIVE_EVENT = "narrative_event"


class RelationTypeObs(str, Enum):
    GENERATED = "generated"
    CAUSED = "caused"
    INFLUENCED = "influenced"
    CONTRADICTED = "contradicted"
    SUPPORTED = "supported"
    CORRECTED = "corrected"
    LEARNED_FROM = "learned_from"
    PRECEDED = "preceded"
    EXPRESSED_AS = "expressed_as"
    LED_TO = "led_to"
    PRODUCED = "produced"
    CHANGED_ILF = "changed_ilf"
    TRIGGERED_LEARNING = "triggered_learning"
    RESULTED_IN_MUTATION = "resulted_in_mutation"


class CognitiveNodeObs(BaseModel):
    id: str
    node_type: NodeTypeObs
    name: str
    description: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)
    source_subsystem: str = ""


class CognitiveEdgeObs(BaseModel):
    source_id: str
    target_id: str
    relation: RelationTypeObs
    weight: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class SelfModel(BaseModel):
    identity: Dict[str, Any] = Field(default_factory=dict)
    active_goals: List[Dict[str, Any]] = Field(default_factory=list)
    active_constraints: List[str] = Field(default_factory=list)
    capabilities: Dict[str, float] = Field(default_factory=dict)
    known_weaknesses: List[str] = Field(default_factory=list)
    known_errors: List[Dict[str, Any]] = Field(default_factory=list)
    blind_spots: List[str] = Field(default_factory=list)
    genome_state: Dict[str, Any] = Field(default_factory=dict)
    ilf_state: Dict[str, float] = Field(default_factory=dict)
    bcel_coverage: Dict[str, Any] = Field(default_factory=dict)
    last_updated: float = Field(default_factory=time.time)


class NarrativeEvent(BaseModel):
    id: str
    timestamp: float = Field(default_factory=time.time)
    event_type: str = ""
    description: str = ""
    interpretation: str = ""
    consequence: str = ""
    learning: str = ""
    causal_parents: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    ilf_delta: float = 0.0
    cci_delta: float = 0.0
    subsystem: str = ""


class CCIComponents(BaseModel):
    c_memory: float = 0.5
    c_identity: float = 0.5
    c_reasoning: float = 0.5
    c_learning: float = 0.5
    c_prediction: float = 0.5
    c_traceability: float = 0.5
    timestamp: float = Field(default_factory=time.time)
    weights: Dict[str, float] = Field(default_factory=lambda: {
        "c_memory": 0.2,
        "c_identity": 0.2,
        "c_reasoning": 0.2,
        "c_learning": 0.15,
        "c_prediction": 0.15,
        "c_traceability": 0.1,
    })

    def compute(self) -> float:
        total = (
            self.weights.get("c_memory", 0.2) * self.c_memory
            + self.weights.get("c_identity", 0.2) * self.c_identity
            + self.weights.get("c_reasoning", 0.2) * self.c_reasoning
            + self.weights.get("c_learning", 0.15) * self.c_learning
            + self.weights.get("c_prediction", 0.15) * self.c_prediction
            + self.weights.get("c_traceability", 0.1) * self.c_traceability
        )
        return max(0.0, min(1.0, total))


class MetacognitiveScore(BaseModel):
    decision_id: str = ""
    confidence: float = 0.0
    accuracy: float = 0.0
    context_completeness: float = 0.0
    evidence_quality: float = 0.0
    hypotheses_considered: int = 0
    subsequent_errors: int = 0
    prediction_outcome_diff: float = 0.0
    timestamp: float = Field(default_factory=time.time)
    subsystem: str = ""


class SelfInterpretation(BaseModel):
    event_id: str = ""
    what: str = ""
    why: str = ""
    contributing_factors: List[str] = Field(default_factory=list)
    supporting_evidence: List[str] = Field(default_factory=list)
    learning: str = ""
    coherence_impact: float = 0.0
    recommendation: str = ""
    timestamp: float = Field(default_factory=time.time)


class CausalPath(BaseModel):
    nodes: List[CognitiveNodeObs] = Field(default_factory=list)
    edges: List[CognitiveEdgeObs] = Field(default_factory=list)
    start_id: str = ""
    end_id: str = ""
    depth: int = 0
    description: str = ""
