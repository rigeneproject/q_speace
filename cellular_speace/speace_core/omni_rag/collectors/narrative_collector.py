import structlog

from speace_core.omni_rag.models import CognitiveNode, NodeType, RelationType, CognitiveEdge
from speace_core.cognitive_observatory.narrative_memory import NarrativeMemory

logger = structlog.get_logger(__name__)


class NarrativeCollector:
    """Collects narrative events from NarrativeMemory into Omni-RAG."""

    def __init__(self, narrative_memory: NarrativeMemory) -> None:
        self._narrative = narrative_memory

    def collect(self) -> tuple[list[CognitiveNode], list[CognitiveEdge]]:
        nodes: list[CognitiveNode] = []
        edges: list[CognitiveEdge] = []

        events = self._narrative._store.get_all_narrative_events()
        for event in events:
            omni_node = CognitiveNode(
                id=f"nar:{event.id}",
                node_type=NodeType.NARRATIVE_EVENT,
                name=f"{event.event_type}: {event.description[:80]}",
                description=event.description,
                metadata={
                    "event_type": event.event_type,
                    "interpretation": event.interpretation,
                    "consequence": event.consequence,
                    "learning": event.learning,
                    "ilf_delta": event.ilf_delta,
                    "cci_delta": event.cci_delta,
                    "subsystem": event.subsystem,
                    "timestamp": event.timestamp,
                },
                tags=["narrative", event.event_type],
            )
            nodes.append(omni_node)

            # Link causal parents
            for parent_id in event.causal_parents:
                edges.append(CognitiveEdge(
                    source_id=f"nar:{parent_id}",
                    target_id=f"nar:{event.id}",
                    relation=RelationType.TRIGGERS,
                    metadata={"causal": True},
                ))

        logger.info("narrative_collector.done", nodes=len(nodes), edges=len(edges))
        return nodes, edges
