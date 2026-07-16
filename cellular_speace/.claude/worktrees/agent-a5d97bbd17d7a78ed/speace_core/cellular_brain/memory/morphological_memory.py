import json
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from speace_core.cellular_brain.memory.morphology_events import MorphologyEvent, MorphologyEventType
from speace_core.cellular_brain.memory.morphology_snapshot import MorphologySnapshot


class MorphologicalMemory:
    def __init__(self, storage_path: str = "data/morphological_memory"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.events: List[MorphologyEvent] = []
        self.snapshots: List[MorphologySnapshot] = []

    def record_event(self, event: MorphologyEvent) -> None:
        self.events.append(event)

    def record_snapshot(self, snapshot: MorphologySnapshot) -> None:
        self.snapshots.append(snapshot)

    def create_event(self, event_type: MorphologyEventType, **kwargs: object) -> MorphologyEvent:
        event = MorphologyEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            **kwargs,
        )
        self.record_event(event)
        return event

    def save(self) -> None:
        events_path = self.storage_path / "events.jsonl"
        snapshots_path = self.storage_path / "snapshots.jsonl"

        with events_path.open("w", encoding="utf-8") as f:
            for event in self.events:
                f.write(event.model_dump_json() + "\n")

        with snapshots_path.open("w", encoding="utf-8") as f:
            for snapshot in self.snapshots:
                f.write(snapshot.model_dump_json() + "\n")

    def load(self) -> None:
        events_path = self.storage_path / "events.jsonl"
        snapshots_path = self.storage_path / "snapshots.jsonl"

        if events_path.exists():
            self.events = [
                MorphologyEvent.model_validate_json(line)
                for line in events_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        if snapshots_path.exists():
            self.snapshots = [
                MorphologySnapshot.model_validate_json(line)
                for line in snapshots_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

    def latest_phi(self) -> Optional[float]:
        if not self.snapshots:
            return None
        return self.snapshots[-1].coherence_phi

    def phi_trend(self) -> float:
        if len(self.snapshots) < 2:
            return 0.0
        return self.snapshots[-1].coherence_phi - self.snapshots[0].coherence_phi

    def count_events(self, event_type: MorphologyEventType) -> int:
        return sum(1 for e in self.events if e.event_type == event_type)
