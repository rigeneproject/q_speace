import json
import time
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

import structlog

from speace_core.cognitive_observatory.models import (
    CognitiveNodeObs,
    CognitiveEdgeObs,
    NarrativeEvent,
    MetacognitiveScore,
    CCIComponents,
    SelfInterpretation,
)

logger = structlog.get_logger(__name__)


class ObservatoryStore:
    """JSONL-backed persistence for the Cognitive Self Observatory.

    Stores cognitive graph nodes/edges, narrative events, metacognitive
    scores, CCI history, and self interpretations in separate files.
    """

    def __init__(self, data_dir: str = "data/cognitive_observatory") -> None:
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._nodes_path = self._data_dir / "cognitive_nodes.jsonl"
        self._edges_path = self._data_dir / "cognitive_edges.jsonl"
        self._narrative_path = self._data_dir / "narrative_events.jsonl"
        self._metacognitive_path = self._data_dir / "metacognitive_scores.jsonl"
        self._cci_path = self._data_dir / "cci_history.jsonl"
        self._interpretations_path = self._data_dir / "interpretations.jsonl"

        self._lock = Lock()

        self._nodes: Dict[str, CognitiveNodeObs] = {}
        self._edges_out: Dict[str, List[CognitiveEdgeObs]] = {}
        self._edges_in: Dict[str, List[CognitiveEdgeObs]] = {}
        self._narrative_events: Dict[str, NarrativeEvent] = {}
        self._metacognitive_scores: List[MetacognitiveScore] = []
        self._cci_history: List[CCIComponents] = []
        self._interpretations: Dict[str, SelfInterpretation] = {}

        self._load_all()

    # ------------------------------------------------------------------ #
    # Cognitive Graph
    # ------------------------------------------------------------------ #

    def put_node(self, node: CognitiveNodeObs) -> None:
        with self._lock:
            self._nodes[node.id] = node
            self._append_jsonl(self._nodes_path, node.model_dump())

    def put_edge(self, edge: CognitiveEdgeObs) -> None:
        with self._lock:
            self._edges_out.setdefault(edge.source_id, []).append(edge)
            self._edges_in.setdefault(edge.target_id, []).append(edge)
            self._append_jsonl(self._edges_path, edge.model_dump())

    def get_node(self, node_id: str) -> Optional[CognitiveNodeObs]:
        with self._lock:
            return self._nodes.get(node_id)

    def get_edges_out(self, node_id: str) -> List[CognitiveEdgeObs]:
        with self._lock:
            return list(self._edges_out.get(node_id, []))

    def get_edges_in(self, node_id: str) -> List[CognitiveEdgeObs]:
        with self._lock:
            return list(self._edges_in.get(node_id, []))

    def get_all_nodes(self) -> List[CognitiveNodeObs]:
        with self._lock:
            return list(self._nodes.values())

    def get_all_edges(self) -> List[CognitiveEdgeObs]:
        with self._lock:
            result = []
            for edges in self._edges_out.values():
                result.extend(edges)
            return result

    def query_nodes(
        self,
        *,
        node_type: Optional[str] = None,
        subsystem: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 100,
    ) -> List[CognitiveNodeObs]:
        with self._lock:
            results = []
            for node in self._nodes.values():
                if node_type and node.node_type.value != node_type:
                    continue
                if subsystem and node.source_subsystem != subsystem:
                    continue
                if tag and tag not in node.tags:
                    continue
                results.append(node)
                if len(results) >= limit:
                    break
            return results

    # ------------------------------------------------------------------ #
    # Narrative Events
    # ------------------------------------------------------------------ #

    def put_narrative_event(self, event: NarrativeEvent) -> None:
        with self._lock:
            self._narrative_events[event.id] = event
            self._append_jsonl(self._narrative_path, event.model_dump())

    def get_narrative_event(self, event_id: str) -> Optional[NarrativeEvent]:
        with self._lock:
            return self._narrative_events.get(event_id)

    def get_all_narrative_events(self) -> List[NarrativeEvent]:
        with self._lock:
            return list(self._narrative_events.values())

    def get_narrative_timeline(
        self, limit: int = 100, event_type: Optional[str] = None
    ) -> List[NarrativeEvent]:
        with self._lock:
            events = sorted(
                self._narrative_events.values(),
                key=lambda e: e.timestamp,
                reverse=True,
            )
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            return events[:limit]

    # ------------------------------------------------------------------ #
    # Metacognitive Scores
    # ------------------------------------------------------------------ #

    def put_metacognitive_score(self, score: MetacognitiveScore) -> None:
        with self._lock:
            self._metacognitive_scores.append(score)
            self._append_jsonl(self._metacognitive_path, score.model_dump())

    def get_recent_metacognitive_scores(self, limit: int = 50) -> List[MetacognitiveScore]:
        with self._lock:
            return sorted(
                self._metacognitive_scores, key=lambda s: s.timestamp, reverse=True
            )[:limit]

    # ------------------------------------------------------------------ #
    # CCI History
    # ------------------------------------------------------------------ #

    def put_cci_snapshot(self, cci: CCIComponents) -> None:
        with self._lock:
            self._cci_history.append(cci)
            self._append_jsonl(self._cci_path, cci.model_dump())

    def get_cci_history(self, limit: int = 100) -> List[CCIComponents]:
        with self._lock:
            return sorted(self._cci_history, key=lambda c: c.timestamp, reverse=True)[:limit]

    def get_cci_trend(self, window: int = 10) -> float:
        with self._lock:
            recent = self._cci_history[-window:]
            if len(recent) < 2:
                return 0.0
            first = recent[0].compute()
            last = recent[-1].compute()
            return last - first

    # ------------------------------------------------------------------ #
    # Self Interpretations
    # ------------------------------------------------------------------ #

    def put_interpretation(self, interp: SelfInterpretation) -> None:
        with self._lock:
            self._interpretations[interp.event_id] = interp
            self._append_jsonl(self._interpretations_path, interp.model_dump())

    def get_interpretation(self, event_id: str) -> Optional[SelfInterpretation]:
        with self._lock:
            return self._interpretations.get(event_id)

    def get_all_interpretations(self) -> List[SelfInterpretation]:
        with self._lock:
            return list(self._interpretations.values())

    # ------------------------------------------------------------------ #
    # Maintenance
    # ------------------------------------------------------------------ #

    def clear(self) -> None:
        with self._lock:
            self._nodes.clear()
            self._edges_out.clear()
            self._edges_in.clear()
            self._narrative_events.clear()
            self._metacognitive_scores.clear()
            self._cci_history.clear()
            self._interpretations.clear()
            for p in [
                self._nodes_path, self._edges_path, self._narrative_path,
                self._metacognitive_path, self._cci_path, self._interpretations_path,
            ]:
                p.write_text("", encoding="utf-8")

    def compact(self) -> None:
        with self._lock:
            for path, data in [
                (self._nodes_path, [n.model_dump() for n in self._nodes.values()]),
                (self._edges_path, [e.model_dump() for e in self.get_all_edges()]),
                (self._narrative_path, [e.model_dump() for e in self._narrative_events.values()]),
                (self._metacognitive_path, [s.model_dump() for s in self._metacognitive_scores]),
                (self._cci_path, [c.model_dump() for c in self._cci_history]),
                (self._interpretations_path, [i.model_dump() for i in self._interpretations.values()]),
            ]:
                with open(path, "w", encoding="utf-8") as f:
                    for entry in data:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            logger.info("observatory_store.compacted")

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _append_jsonl(self, path: Path, data: dict) -> None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    def _load_all(self) -> None:
        self._load_jsonl(self._nodes_path, self._nodes, CognitiveNodeObs, "nodes")
        self._load_edges()
        self._load_jsonl(self._narrative_path, self._narrative_events, NarrativeEvent, "narrative")
        self._load_jsonl_array(self._metacognitive_path, self._metacognitive_scores, MetacognitiveScore, "metacognitive")
        self._load_jsonl_array(self._cci_path, self._cci_history, CCIComponents, "cci")
        self._load_jsonl(self._interpretations_path, self._interpretations, SelfInterpretation, "interpretations")

    def _load_jsonl(self, path: Path, target: dict, model_class, label: str) -> None:
        if not path.exists():
            return
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    obj_id = data.get("id") or data.get("event_id") or str(count)
                    target[obj_id] = model_class(**data)
                    count += 1
                except Exception as exc:
                    logger.warning("observatory_store.load_skipped", label=label, error=str(exc))
        logger.info("observatory_store.loaded", label=label, count=count)

    def _load_jsonl_array(self, path: Path, target: list, model_class, label: str) -> None:
        if not path.exists():
            return
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    target.append(model_class(**data))
                    count += 1
                except Exception as exc:
                    logger.warning("observatory_store.load_skipped", label=label, error=str(exc))
        logger.info("observatory_store.loaded", label=label, count=count)

    def _load_edges(self) -> None:
        if not self._edges_path.exists():
            return
        count = 0
        with open(self._edges_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    edge = CognitiveEdgeObs(**data)
                    self._edges_out.setdefault(edge.source_id, []).append(edge)
                    self._edges_in.setdefault(edge.target_id, []).append(edge)
                    count += 1
                except Exception as exc:
                    logger.warning("observatory_store.load_edge_skipped", error=str(exc))
        logger.info("observatory_store.edges_loaded", count=count)
