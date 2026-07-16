import structlog

from speace_core.omni_rag.models import CognitiveNode, NodeType, RelationType, CognitiveEdge
from speace_core.cognitive_observatory.self_model import SelfModelEngine

logger = structlog.get_logger(__name__)


class SelfModelCollector:
    """Collects self-model state from SelfModelEngine into Omni-RAG."""

    def __init__(self, self_model: SelfModelEngine) -> None:
        self._self_model = self_model

    def collect(self) -> tuple[list[CognitiveNode], list[CognitiveEdge]]:
        nodes: list[CognitiveNode] = []
        edges: list[CognitiveEdge] = []
        model = self._self_model.model

        # Identity node
        identity_node = CognitiveNode(
            id="self:identity",
            node_type=NodeType.PRINCIPLE,
            name=model.identity.get("entity_name", "SPEACE"),
            description=f"Self identity: {model.identity}",
            metadata={
                "entity_name": model.identity.get("entity_name", ""),
                "nature": model.identity.get("nature", ""),
                "invariants": model.identity.get("invariants", []),
                "last_updated": model.last_updated,
            },
            tags=["self_model", "identity"],
        )
        nodes.append(identity_node)

        # Goal nodes
        for goal in model.active_goals:
            goal_id = f"self:goal:{hash(goal.get('name', '')) % 100000}"
            goal_node = CognitiveNode(
                id=goal_id,
                node_type=NodeType.GOAL,
                name=goal.get("name", "unnamed_goal"),
                description=str(goal),
                metadata=goal,
                tags=["self_model", "goal"],
            )
            nodes.append(goal_node)
            edges.append(CognitiveEdge(
                source_id="self:identity",
                target_id=goal_id,
                relation=RelationType.DEFINES,
            ))

        # Capability nodes
        for cap_name, confidence in model.capabilities.items():
            cap_id = f"self:cap:{hash(cap_name) % 100000}"
            cap_node = CognitiveNode(
                id=cap_id,
                node_type=NodeType.METRIC,
                name=f"capability:{cap_name}",
                description=f"Capability {cap_name} with confidence {confidence:.3f}",
                metadata={"name": cap_name, "confidence": confidence},
                tags=["self_model", "capability"],
            )
            nodes.append(cap_node)
            edges.append(CognitiveEdge(
                source_id="self:identity",
                target_id=cap_id,
                relation=RelationType.DEFINES,
            ))

        # Constraint nodes
        for constraint in model.active_constraints:
            constraint_id = f"self:constraint:{hash(constraint) % 100000}"
            constraint_node = CognitiveNode(
                id=constraint_id,
                node_type=NodeType.CONSTRAINT,
                name=constraint,
                description=f"Active constraint: {constraint}",
                tags=["self_model", "constraint"],
            )
            nodes.append(constraint_node)
            edges.append(CognitiveEdge(
                source_id="self:identity",
                target_id=constraint_id,
                relation=RelationType.REGULATES,
            ))

        # Weakness nodes
        for weakness in model.known_weaknesses:
            weak_id = f"self:weakness:{hash(weakness) % 100000}"
            weak_node = CognitiveNode(
                id=weak_id,
                node_type=NodeType.CONSTRAINT,
                name=f"weakness:{weakness}",
                description=weakness,
                tags=["self_model", "weakness"],
            )
            nodes.append(weak_node)
            edges.append(CognitiveEdge(
                source_id="self:identity",
                target_id=weak_id,
                relation=RelationType.CHANGES,
            ))

        # Blind spot nodes
        for spot in model.blind_spots:
            spot_id = f"self:blind_spot:{hash(spot) % 100000}"
            spot_node = CognitiveNode(
                id=spot_id,
                node_type=NodeType.CONSTRAINT,
                name=f"blind_spot:{spot}",
                description=f"Known blind spot: {spot}",
                tags=["self_model", "blind_spot"],
            )
            nodes.append(spot_node)
            edges.append(CognitiveEdge(
                source_id="self:identity",
                target_id=spot_id,
                relation=RelationType.REGULATES,
            ))

        # Genome state node
        if model.genome_state:
            genome_node = CognitiveNode(
                id="self:genome_state",
                node_type=NodeType.GENE,
                name="genome_state",
                description=str(model.genome_state),
                metadata=model.genome_state,
                tags=["self_model", "genome"],
            )
            nodes.append(genome_node)
            edges.append(CognitiveEdge(
                source_id="self:identity",
                target_id="self:genome_state",
                relation=RelationType.EXPRESSES,
            ))

        # ILF state node
        if model.ilf_state:
            ilf_node = CognitiveNode(
                id="self:ilf_state",
                node_type=NodeType.ILF_METRIC,
                name="ilf_state",
                description=str(model.ilf_state),
                metadata=model.ilf_state,
                tags=["self_model", "ilf"],
            )
            nodes.append(ilf_node)
            edges.append(CognitiveEdge(
                source_id="self:identity",
                target_id="self:ilf_state",
                relation=RelationType.AFFECTS,
            ))

        # BCEL coverage node
        if model.bcel_coverage:
            bcel_node = CognitiveNode(
                id="self:bcel_coverage",
                node_type=NodeType.BCEL_MAPPING,
                name="bcel_coverage",
                description=str(model.bcel_coverage),
                metadata=model.bcel_coverage,
                tags=["self_model", "bcel"],
            )
            nodes.append(bcel_node)
            edges.append(CognitiveEdge(
                source_id="self:identity",
                target_id="self:bcel_coverage",
                relation=RelationType.VALIDATES,
            ))

        logger.info("self_model_collector.done", nodes=len(nodes), edges=len(edges))
        return nodes, edges
