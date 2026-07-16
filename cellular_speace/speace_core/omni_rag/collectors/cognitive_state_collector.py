import structlog

from speace_core.omni_rag.models import CognitiveNode, NodeType, RelationType, CognitiveEdge
from speace_core.cognitive_observatory.cognitive_state_graph import CognitiveStateGraph
from speace_core.cognitive_observatory.models import NodeTypeObs

logger = structlog.get_logger(__name__)

_NODE_TYPE_MAP = {
    NodeTypeObs.THOUGHT: NodeType.THOUGHT,
    NodeTypeObs.DECISION: NodeType.DECISION,
    NodeTypeObs.GOAL: NodeType.GOAL,
    NodeTypeObs.BELIEF: NodeType.BELIEF,
    NodeTypeObs.HYPOTHESIS: NodeType.HYPOTHESIS,
    NodeTypeObs.ERROR: NodeType.ERROR,
    NodeTypeObs.LEARNING_EVENT: NodeType.LEARNING_EVENT,
    NodeTypeObs.NARRATIVE_EVENT: NodeType.NARRATIVE_EVENT,
    NodeTypeObs.MUTATION_EVENT: NodeType.MUTATION,
    NodeTypeObs.ACTION: NodeType.AGENT,
    NodeTypeObs.MEMORY_STATE: NodeType.MEMORY,
}

_RELATION_MAP = {
    "generated": RelationType.GENERATES,
    "caused": RelationType.TRIGGERS,
    "influenced": RelationType.AFFECTS,
    "contradicted": RelationType.CHANGES,
    "supported": RelationType.VALIDATES,
    "corrected": RelationType.AUDITS,
    "learned_from": RelationType.REFERENCES,
    "preceded": RelationType.DEPENDS_ON,
    "expressed_as": RelationType.EXPRESSES,
    "led_to": RelationType.PRODUCES,
    "produced": RelationType.PRODUCES,
    "changed_ilf": RelationType.AFFECTS,
    "triggered_learning": RelationType.GENERATES,
    "resulted_in_mutation": RelationType.MUTATES,
}


class CognitiveStateCollector:
    """Collects cognitive state nodes from CognitiveStateGraph into Omni-RAG."""

    def __init__(self, state_graph: CognitiveStateGraph) -> None:
        self._state = state_graph

    def collect(self) -> tuple[list[CognitiveNode], list[CognitiveEdge]]:
        nodes: list[CognitiveNode] = []
        edges: list[CognitiveEdge] = []

        for obs_node in self._state._nodes.values():
            omni_type = _NODE_TYPE_MAP.get(obs_node.node_type, NodeType.UNKNOWN)
            omni_node = CognitiveNode(
                id=f"obs:{obs_node.id}",
                node_type=omni_type,
                name=obs_node.name,
                description=obs_node.description,
                metadata={
                    **obs_node.metadata,
                    "source_subsystem": obs_node.source_subsystem,
                    "timestamp": obs_node.timestamp,
                },
                tags=["cognitive_observatory", obs_node.node_type.value],
            )
            nodes.append(omni_node)

        for edges_out in self._state._edges_out.values():
            for obs_edge in edges_out:
                omni_rel = _RELATION_MAP.get(obs_edge.relation.value, RelationType.REFERENCES)
                omni_edge = CognitiveEdge(
                    source_id=f"obs:{obs_edge.source_id}",
                    target_id=f"obs:{obs_edge.target_id}",
                    relation=omni_rel,
                    weight=obs_edge.weight,
                    metadata={
                        **obs_edge.metadata,
                        "timestamp": obs_edge.timestamp,
                    },
                )
                edges.append(omni_edge)

        logger.info("cognitive_state_collector.done", nodes=len(nodes), edges=len(edges))
        return nodes, edges
