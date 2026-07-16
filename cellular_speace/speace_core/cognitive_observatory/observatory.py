"""CognitiveObservatory — ties all 8 levels together."""

import time
from typing import Any, Dict, List, Optional

import structlog

from speace_core.cognitive_observatory.cognitive_state_graph import CognitiveStateGraph
from speace_core.cognitive_observatory.self_model import SelfModelEngine
from speace_core.cognitive_observatory.narrative_memory import NarrativeMemory
from speace_core.cognitive_observatory.coherence_engine import CoherenceEngine
from speace_core.cognitive_observatory.metacognitive_engine import MetacognitiveEngine
from speace_core.cognitive_observatory.causal_evolution_graph import CausalEvolutionGraph
from speace_core.cognitive_observatory.self_interpretation_engine import SelfInterpretationEngine
from speace_core.cognitive_observatory.persistence.observatory_store import ObservatoryStore

try:
    from speace_core.cellular_brain.psn.physiological_signal_bus import PhysiologicalSignalBus
    from speace_core.cognitive_observatory.occap.occap_calculator import OCCapCalculator
    _HAS_OCCAP = True
except ImportError:
    _HAS_OCCAP = False

logger = structlog.get_logger(__name__)


class CognitiveObservatory:
    """The Cognitive Self Observatory organ.

    Orchestrates all 8 levels into a unified self-observation system.
    Designed to integrate with the orchestrator's tick loop.
    """

    def __init__(
        self,
        store: Optional[ObservatoryStore] = None,
        psn: Optional["PhysiologicalSignalBus"] = None,
    ) -> None:
        self._store = store or ObservatoryStore()

        # L1
        self.state_graph = CognitiveStateGraph(store=self._store)

        # L2
        self.self_model = SelfModelEngine(store=self._store)

        # L3
        self.narrative = NarrativeMemory(store=self._store)

        # L5
        self.metacognitive = MetacognitiveEngine(store=self._store)

        # L4 (depends on L2, L3, L5)
        self.coherence = CoherenceEngine(
            store=self._store,
            self_model=self.self_model,
            narrative_memory=self.narrative,
            metacognitive=self.metacognitive,
        )

        # L6 (depends on L1)
        self.causal_evolution = CausalEvolutionGraph(
            state_graph=self.state_graph,
        )

        # L7 (depends on L1, L3)
        self.interpretation = SelfInterpretationEngine(
            store=self._store,
            state_graph=self.state_graph,
            narrative=self.narrative,
        )

        # OCCap (T178) — optional PSN-based organismic cognitive capacity
        self._psn = psn
        self._occap: Optional["OCCapCalculator"] = None
        if _HAS_OCCAP and psn is not None:
            try:
                self._occap = OCCapCalculator(psn)
            except Exception as exc:
                logger.warning("occap_calculator_init_failed", error=str(exc))

    # ------------------------------------------------------------------ #
    # Integration with orchestrator tick
    # ------------------------------------------------------------------ #

    def on_tick(self, orchestrator_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Called every orchestration tick to update self-observation."""
        start = time.perf_counter()

        if orchestrator_state:
            self.self_model.update_from_orchestrator(orchestrator_state)

        cci = self.coherence.compute_cci()

        occap_state = None
        if self._occap is not None:
            tick = orchestrator_state.get("metrics", {}).get("tick", 0) if orchestrator_state else 0
            try:
                occap_state = self._occap.compute(tick)
            except Exception as exc:
                logger.warning("occap_compute_failed", error=str(exc))

        elapsed = time.perf_counter() - start
        result = {
            "cci": cci.compute(),
            "cci_components": cci.model_dump(),
            "state_graph_size": self.state_graph.node_count(),
            "narrative_count": len(self.narrative.get_timeline(limit=1000)),
            "elapsed_ms": round(elapsed * 1000, 2),
        }
        if occap_state is not None:
            result["occap"] = occap_state.as_dict()
        return result

    # ------------------------------------------------------------------ #
    # High-level queries
    # ------------------------------------------------------------------ #

    def get_full_cognitive_audit(self) -> Dict[str, Any]:
        """Comprehensive cognitive audit across all levels."""
        cci = self.coherence.get_current_cci()
        cci_components = self.coherence.get_cci_history(limit=1)
        cci_data = cci_components[0] if cci_components else None

        return {
            "cci": cci,
            "cci_components": cci_data.model_dump() if cci_data else {},
            "cci_trend": self.coherence.get_cci_trend(window=20),
            "self_summary": self.self_model.get_self_summary(),
            "metacognitive": self.metacognitive.get_comprehensive_metacognitive_report(),
            "narrative_events": self.narrative.get_event_count_by_type(),
            "state_graph": {
                "nodes": self.state_graph.node_count(),
                "edges": self.state_graph.edge_count(),
                "error_rate": self.state_graph.get_error_rate(),
            },
            "self_understanding": self.interpretation.summarize_self_understanding(),
        }

    def get_coherence_report(self) -> Dict[str, Any]:
        """Detailed coherence report with time series."""
        cci_history = self.coherence.get_cci_history(limit=100)
        return {
            "current_cci": self.coherence.get_current_cci(),
            "cci_trend_20": self.coherence.get_cci_trend(window=20),
            "cci_trend_50": self.coherence.get_cci_trend(window=50),
            "cci_history": [
                {
                    "timestamp": c.timestamp,
                    "value": c.compute(),
                    "components": {
                        "memory": c.c_memory,
                        "identity": c.c_identity,
                        "reasoning": c.c_reasoning,
                        "learning": c.c_learning,
                        "prediction": c.c_prediction,
                        "traceability": c.c_traceability,
                    },
                }
                for c in cci_history[-50:]
            ],
        }

    def get_narrative_timeline(
        self, limit: int = 100, event_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        events = self.narrative.get_timeline(limit=limit, event_type=event_type)
        return [
            {
                "id": e.id,
                "timestamp": e.timestamp,
                "type": e.event_type,
                "description": e.description,
                "interpretation": e.interpretation,
                "consequence": e.consequence,
                "learning": e.learning,
                "ilf_delta": e.ilf_delta,
                "cci_delta": e.cci_delta,
            }
            for e in events
        ]

    def causal_trace(self, node_id: str, direction: str = "upstream", depth: int = 5) -> Dict[str, Any]:
        if direction == "downstream":
            path = self.state_graph.trace_downstream(node_id, max_depth=depth)
        else:
            path = self.state_graph.trace_upstream(node_id, max_depth=depth)
        return {
            "start_id": node_id,
            "direction": direction,
            "depth": depth,
            "nodes": [
                {"id": n.id, "type": n.node_type.value, "name": n.name}
                for n in path.nodes
            ],
            "edges": [
                {
                    "source": e.source_id,
                    "target": e.target_id,
                    "relation": e.relation.value,
                }
                for e in path.edges
            ],
            "description": path.description,
        }

    def clear(self) -> None:
        self._store.clear()
        self.state_graph.clear()
        self.self_model.clear()
        logger.info("cognitive_observatory.cleared")
