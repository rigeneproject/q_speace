import time
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    GENE = "gene"
    RNA = "rna"
    CIRCUIT = "circuit"
    MEMORY = "memory"
    AGENT = "agent"
    CONSTRAINT = "constraint"
    BCEL_MAPPING = "bcel_mapping"
    ILF_METRIC = "ilf_metric"
    MUTATION = "mutation"
    TEST = "test"
    RUNTIME_EVENT = "runtime_event"
    DOCUMENT = "document"
    CONFIG = "config"
    PRINCIPLE = "principle"
    BEHAVIOR = "behavior"
    METRIC = "metric"
    PHENOTYPE = "phenotype"
    BIOLOGICAL_PRINCIPLE = "biological_principle"
    DIGITAL_MECHANISM = "digital_mechanism"
    THOUGHT = "thought"
    DECISION = "decision"
    GOAL = "goal"
    BELIEF = "belief"
    HYPOTHESIS = "hypothesis"
    ERROR = "error"
    LEARNING_EVENT = "learning_event"
    NARRATIVE_EVENT = "narrative_event"
    UNKNOWN = "unknown"


class RelationType(str, Enum):
    IMPORTS = "imports"
    DEPENDS_ON = "depends_on"
    IMPLEMENTS = "implements"
    EXTENDS = "extends"
    USES = "uses"
    GENERATES = "generates"
    VALIDATES = "validates"
    MUTATES = "mutates"
    EXPRESSES = "expresses"
    REGULATES = "regulates"
    DEFINES = "defines"
    REFERENCES = "references"
    CONTAINS = "contains"
    TRIGGERS = "triggers"
    CORRELATES_WITH = "correlates_with"
    TRANSLATED_TO = "translated_to"
    BELONGS_TO = "belongs_to"
    AUDITS = "audits"
    PRODUCES = "produces"
    CHANGES = "changes"
    AFFECTS = "affects"
    VALIDATED_BY = "validated_by"
    ACTIVATED_BY = "activated_by"
    CONSTRAINS = "constrains"
    MAPS_TO = "maps_to"


class LayerFilter(str, Enum):
    SEMANTIC = "semantic"
    ARCH = "arch"
    DNA = "dna"
    BCEL = "bcel"
    RUNTIME = "runtime"


class AuditType(str, Enum):
    ARCH = "arch"
    BCEL = "bcel"
    DNA = "dna"
    RUNTIME = "runtime"
    COGNITIVE_FACTORS = "cognitive_factors"
    ALL = "all"


class CognitiveNode(BaseModel):
    id: str
    node_type: NodeType = NodeType.UNKNOWN
    name: str
    description: str = ""
    source_path: str = ""
    source_line: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.tags.append(tag)


class CognitiveEdge(BaseModel):
    source_id: str
    target_id: str
    relation: RelationType
    metadata: Dict[str, Any] = Field(default_factory=dict)
    weight: float = 1.0


class OmniQuery(BaseModel):
    text: str = ""
    layers: List[LayerFilter] = Field(default_factory=lambda: list(LayerFilter))
    node_types: List[NodeType] = Field(default_factory=list)
    node_ids: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    relations: List[RelationType] = Field(default_factory=list)
    max_depth: int = 3
    limit: int = 50
    semantic_weight: float = 0.3
    graph_weight: float = 0.5
    runtime_weight: float = 0.2


class OmniResult(BaseModel):
    query: OmniQuery
    nodes: List[CognitiveNode] = Field(default_factory=list)
    edges: List[CognitiveEdge] = Field(default_factory=list)
    paths: List[List[CognitiveEdge]] = Field(default_factory=list)
    semantic_scores: Dict[str, float] = Field(default_factory=dict)
    graph_scores: Dict[str, float] = Field(default_factory=dict)
    runtime_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    audit_summary: Optional[Dict[str, Any]] = None
    explanation: str = ""
    total_count: int = 0
    latency_ms: float = 0.0


class AuditFinding(BaseModel):
    severity: str  # "critical", "warning", "info"
    category: str
    message: str
    node_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class AuditResult(BaseModel):
    audit_type: AuditType
    findings: List[AuditFinding] = Field(default_factory=list)
    summary: Dict[str, int] = Field(default_factory=lambda: {"critical": 0, "warning": 0, "info": 0})
    passed: bool = True
    duration_ms: float = 0.0
