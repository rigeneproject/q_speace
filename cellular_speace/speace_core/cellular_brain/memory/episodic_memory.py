import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from speace_core.cellular_brain.memory.morphology_events import MorphologyEvent, MorphologyEventType


class EpisodeEvent(BaseModel):
    event_id: str
    timestamp: str
    tick_id: int = 0
    event_type: str
    source_module: str
    region: Optional[str] = None
    metrics: Dict[str, float] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Episode(BaseModel):
    episode_id: str
    start_time: str
    end_time: Optional[str] = None
    trigger: str
    events: List[EpisodeEvent] = Field(default_factory=list)
    initial_metrics: Dict[str, float] = Field(default_factory=dict)
    final_metrics: Dict[str, float] = Field(default_factory=dict)
    outcome: str = "unknown"
    cognitive_delta: float = 0.0
    phi_delta: float = 0.0
    energy_delta: float = 0.0
    semantic_tags: List[str] = Field(default_factory=list)
    linked_assemblies: List[str] = Field(default_factory=list)
    linked_proposals: List[str] = Field(default_factory=list)


class EpisodicMemory:
    """T47 — Episodic Memory & Temporal Experience Layer."""

    def __init__(
        self,
        storage_path: str = "data/episodic_memory/episodes.jsonl",
        memory=None,
    ):
        self._storage_path = Path(storage_path)
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory = memory
        self._episodes: Dict[str, Episode] = {}
        self._load()

    # ------------------------------------------------------------------ #
    # Episode lifecycle
    # ------------------------------------------------------------------ #

    def start_episode(
        self,
        trigger: str,
        initial_metrics: Optional[Dict[str, float]] = None,
        tick_id: int = 0,
    ) -> Episode:
        now = datetime.now(timezone.utc).isoformat()
        episode = Episode(
            episode_id=f"ep-{uuid.uuid4().hex[:8]}",
            start_time=now,
            trigger=trigger,
            initial_metrics=initial_metrics or {},
        )
        self._episodes[episode.episode_id] = episode
        self._persist()
        self._log_event(
            MorphologyEventType.EPISODE_STARTED,
            {
                "episode_id": episode.episode_id,
                "trigger": trigger,
                "tick_id": tick_id,
            },
        )
        return episode

    def record_event(
        self,
        episode_id: str,
        event_type: str,
        source_module: str,
        metrics: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tick_id: int = 0,
        region: Optional[str] = None,
    ) -> Optional[EpisodeEvent]:
        episode = self._episodes.get(episode_id)
        if episode is None:
            return None

        event = EpisodeEvent(
            event_id=f"evt-{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            tick_id=tick_id,
            event_type=event_type,
            source_module=source_module,
            region=region,
            metrics=metrics or {},
            metadata=metadata or {},
        )
        episode.events.append(event)
        self._persist()
        self._log_event(
            MorphologyEventType.EPISODE_EVENT_RECORDED,
            {
                "episode_id": episode_id,
                "event_id": event.event_id,
                "event_type": event_type,
                "source_module": source_module,
            },
        )
        return event

    def close_episode(
        self,
        episode_id: str,
        final_metrics: Optional[Dict[str, float]] = None,
        outcome: str = "unknown",
    ) -> Optional[Episode]:
        episode = self._episodes.get(episode_id)
        if episode is None:
            return None

        now = datetime.now(timezone.utc).isoformat()
        episode.end_time = now
        episode.final_metrics = final_metrics or {}
        episode.outcome = outcome

        # Compute deltas
        init = episode.initial_metrics
        fin = episode.final_metrics
        episode.cognitive_delta = fin.get("cognitive_score", 0.0) - init.get("cognitive_score", 0.0)
        episode.phi_delta = fin.get("coherence_phi", 0.0) - init.get("coherence_phi", 0.0)
        episode.energy_delta = fin.get("energy_efficiency", 0.0) - init.get("energy_efficiency", 0.0)

        self._persist()
        self._log_event(
            MorphologyEventType.EPISODE_CLOSED,
            {
                "episode_id": episode_id,
                "outcome": outcome,
                "event_count": len(episode.events),
                "cognitive_delta": round(episode.cognitive_delta, 4),
                "phi_delta": round(episode.phi_delta, 4),
                "energy_delta": round(episode.energy_delta, 4),
            },
        )
        return episode

    def link_assembly(self, episode_id: str, assembly_id: str) -> bool:
        episode = self._episodes.get(episode_id)
        if episode is None:
            return False
        if assembly_id not in episode.linked_assemblies:
            episode.linked_assemblies.append(assembly_id)
            self._persist()
        return True

    def link_proposal(self, episode_id: str, proposal_id: str) -> bool:
        episode = self._episodes.get(episode_id)
        if episode is None:
            return False
        if proposal_id not in episode.linked_proposals:
            episode.linked_proposals.append(proposal_id)
            self._persist()
        return True

    # ------------------------------------------------------------------ #
    # Retrieval
    # ------------------------------------------------------------------ #

    def load_episodes(self) -> List[Episode]:
        return list(self._episodes.values())

    def get_recent_episodes(self, limit: int = 10) -> List[Episode]:
        episodes = sorted(
            self._episodes.values(),
            key=lambda e: e.start_time,
            reverse=True,
        )
        return episodes[:limit]

    def get_episode(self, episode_id: str) -> Optional[Episode]:
        return self._episodes.get(episode_id)

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #

    def _persist(self) -> None:
        lines = []
        for episode in self._episodes.values():
            lines.append(episode.model_dump_json())
        self._storage_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _load(self) -> None:
        if not self._storage_path.exists():
            return
        for line in self._storage_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                episode = Episode(**data)
                self._episodes[episode.episode_id] = episode
            except Exception:
                continue

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _log_event(
        self,
        event_type: MorphologyEventType,
        metadata: Dict[str, Any],
    ) -> None:
        if self.memory is None or not hasattr(self.memory, "log_event"):
            return
        try:
            event = MorphologyEvent(
                event_id=f"evt-{uuid.uuid4().hex[:8]}",
                event_type=event_type,
                timestamp=datetime.now(timezone.utc).timestamp(),
                metadata=metadata,
            )
            self.memory.log_event(event)
        except Exception:
            pass
