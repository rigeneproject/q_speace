"""EventCollector — intercetta i messaggi tra sottosistemi.

Avvolge l'OrganismBus e registra ogni publish/broadcast in un buffer
temporale per costruire l'Operational Functional Graph (OFG).
"""

from __future__ import annotations

import json
import pathlib
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class RecordedEvent:
    source: str
    target: Optional[str]
    message_type: str
    priority: float
    timestamp: float
    latency_ms: float = 0.0
    success: bool = True


class EventCollector:
    """Cattura e bufferizza gli eventi di comunicazione tra sottosistemi.

    Può operare in due modalità:
      1. **Wrap mode**: avvolge un OrganismBus esistente intercettando
         publish/broadcast senza modificare il bus originale.
      2. **Direct mode**: chiamate manuali a ``record()`` da qualsiasi punto.
    """

    def __init__(
        self,
        buffer_size: int = 100_000,
        persist_path: str = "data/organism_observer/events.jsonl",
    ) -> None:
        self.buffer_size = buffer_size
        self.persist_path = pathlib.Path(persist_path)
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        self._events: List[RecordedEvent] = []
        self._wrapped_bus: Any = None
        self._original_publish = None
        self._original_broadcast = None
        self._session_id = uuid.uuid4().hex[:12]

    # ------------------------------------------------------------------ #
    # Wrap / Unwrap
    # ------------------------------------------------------------------ #

    def wrap(self, bus: Any) -> Any:
        """Avvolge un OrganismBus: intercetta publish/broadcast.

        Restituisce lo stesso bus con i metodi sostituiti.
        Chiamare una sola volta all'avvio.
        """
        self._wrapped_bus = bus
        self._original_publish = bus.publish
        self._original_broadcast = bus.broadcast

        def _wrapped_publish(message: Any) -> bool:
            start = time.perf_counter()
            result = self._original_publish(message)
            elapsed = (time.perf_counter() - start) * 1000
            self.record(
                source=message.source,
                target=message.target,
                message_type=message.message_type,
                priority=message.priority,
                latency_ms=elapsed,
                success=result,
            )
            return result

        def _wrapped_broadcast(message: Any) -> bool:
            start = time.perf_counter()
            result = self._original_broadcast(message)
            elapsed = (time.perf_counter() - start) * 1000
            self.record(
                source=message.source,
                target="*broadcast*",
                message_type=message.message_type,
                priority=message.priority,
                latency_ms=elapsed,
                success=result,
            )
            return result

        bus.publish = _wrapped_publish
        bus.broadcast = _wrapped_broadcast
        return bus

    def unwrap(self) -> None:
        """Ripristina i metodi originali del bus."""
        if self._wrapped_bus is not None:
            if self._original_publish is not None:
                self._wrapped_bus.publish = self._original_publish
            if self._original_broadcast is not None:
                self._wrapped_bus.broadcast = self._original_broadcast
        self._wrapped_bus = None

    # ------------------------------------------------------------------ #
    # Recording
    # ------------------------------------------------------------------ #

    def record(
        self,
        source: str,
        target: Optional[str] = None,
        message_type: str = "unknown",
        priority: float = 0.5,
        latency_ms: float = 0.0,
        success: bool = True,
    ) -> None:
        """Aggiunge un evento al buffer."""
        event = RecordedEvent(
            source=source,
            target=target,
            message_type=message_type,
            priority=priority,
            timestamp=time.time(),
            latency_ms=latency_ms,
            success=success,
        )
        self._events.append(event)
        if len(self._events) >= self.buffer_size:
            self._trim()

    # ------------------------------------------------------------------ #
    # Buffer management
    # ------------------------------------------------------------------ #

    def _trim(self) -> None:
        """Mantiene il buffer entro buffer_size, rimuovendo i più vecchi."""
        overflow = len(self._events) - self.buffer_size
        if overflow > 0:
            self._events = self._events[overflow:]

    def flush(self) -> int:
        """Scrive il buffer su JSONL e lo svuota. Restituisce il numero di eventi scritti."""
        if not self._events:
            return 0
        count = len(self._events)
        try:
            with self.persist_path.open("a", encoding="utf-8") as f:
                for ev in self._events:
                    line = {
                        "session_id": self._session_id,
                        **asdict(ev),
                    }
                    f.write(json.dumps(line) + "\n")
            self._events.clear()
        except OSError:
            pass
        return count

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #

    def events(self, since: Optional[float] = None) -> List[RecordedEvent]:
        """Restituisce gli eventi nel buffer, opzionalmente filtrati per timestamp."""
        if since is None:
            return list(self._events)
        return [e for e in self._events if e.timestamp >= since]

    def count(self) -> int:
        return len(self._events)

    def sources(self) -> List[str]:
        return list({e.source for e in self._events})

    def targets(self) -> List[str]:
        return list({e.target for e in self._events if e.target})

    def message_types(self) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for e in self._events:
            counts[e.message_type] += 1
        return dict(counts)

    def summary(self) -> Dict[str, Any]:
        return {
            "session_id": self._session_id,
            "buffer_events": len(self._events),
            "unique_sources": len(self.sources()),
            "unique_targets": len(self.targets()),
            "message_types": self.message_types(),
            "persist_path": str(self.persist_path),
        }

    def load_history(self, path: Optional[str] = None) -> int:
        """Carica eventi da un file JSONL esistente. Restituisce il numero caricato."""
        src = pathlib.Path(path) if path else self.persist_path
        if not src.exists():
            return 0
        count = 0
        try:
            with src.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    self._events.append(RecordedEvent(
                        source=data.get("source", "unknown"),
                        target=data.get("target"),
                        message_type=data.get("message_type", "unknown"),
                        priority=data.get("priority", 0.5),
                        timestamp=data.get("timestamp", time.time()),
                        latency_ms=data.get("latency_ms", 0.0),
                        success=data.get("success", True),
                    ))
                    count += 1
        except OSError:
            pass
        return count
