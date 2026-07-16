import structlog

from speace_core.omni_rag.models import CognitiveNode, NodeType, RelationType, CognitiveEdge
from speace_core.cognitive_observatory.metacognitive_engine import MetacognitiveEngine

logger = structlog.get_logger(__name__)


class MetacognitiveCollector:
    """Collects metacognitive scores from MetacognitiveEngine into Omni-RAG."""

    def __init__(self, metacognitive: MetacognitiveEngine) -> None:
        self._metacognitive = metacognitive

    def collect(self) -> tuple[list[CognitiveNode], list[CognitiveEdge]]:
        nodes: list[CognitiveNode] = []
        edges: list[CognitiveEdge] = []

        scores = self._metacognitive._store.get_recent_metacognitive_scores(limit=1000)
        for score in scores:
            score_node = CognitiveNode(
                id=f"meta:decision:{score.decision_id}",
                node_type=NodeType.METRIC,
                name=f"decision_quality:{score.decision_id[:40]}",
                description=(
                    f"Confidence={score.confidence:.3f}, "
                    f"Accuracy={score.accuracy:.3f}, "
                    f"Context={score.context_completeness:.3f}, "
                    f"Evidence={score.evidence_quality:.3f}"
                ),
                metadata={
                    "decision_id": score.decision_id,
                    "confidence": score.confidence,
                    "accuracy": score.accuracy,
                    "context_completeness": score.context_completeness,
                    "evidence_quality": score.evidence_quality,
                    "hypotheses_considered": score.hypotheses_considered,
                    "subsequent_errors": score.subsequent_errors,
                    "prediction_outcome_diff": score.prediction_outcome_diff,
                    "subsystem": score.subsystem,
                    "timestamp": score.timestamp,
                },
                tags=["metacognitive", "decision_quality"],
            )
            nodes.append(score_node)

        # Calibration summary node
        recent = scores[-50:] if len(scores) >= 50 else scores
        if recent:
            cal_error = self._metacognitive.get_calibration_error(window=50)
            avg_conf = self._metacognitive.get_average_confidence(window=50)
            avg_acc = self._metacognitive.get_average_accuracy(window=50)

            cal_node = CognitiveNode(
                id="meta:calibration_summary",
                node_type=NodeType.METRIC,
                name="metacognitive_calibration",
                description=(
                    f"Calibration error={cal_error:.4f}, "
                    f"Avg confidence={avg_conf:.4f}, "
                    f"Avg accuracy={avg_acc:.4f}"
                ),
                metadata={
                    "calibration_error": cal_error,
                    "average_confidence": avg_conf,
                    "average_accuracy": avg_acc,
                    "sample_size": len(recent),
                },
                tags=["metacognitive", "calibration"],
            )
            nodes.append(cal_node)

        logger.info("metacognitive_collector.done", nodes=len(nodes), edges=len(edges))
        return nodes, edges
