"""T221-13 (I2): Hash-chained, append-only, externally replicated audit log."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AuditEntry:
    """One hash-chained entry in the PTAA audit log."""

    seq: int
    timestamp: float
    agent_id: str
    event_type: str
    payload: dict[str, Any]
    prev_hash: str
    entry_hash: str


class ExternalAuditReplica:
    """Independent append-only replica sink verifying incoming hash links."""

    def __init__(self, replica_id: str) -> None:
        self.replica_id = replica_id
        self._entries: list[AuditEntry] = []

    @property
    def entries(self) -> tuple[AuditEntry, ...]:
        return tuple(self._entries)

    def receive(self, entry: AuditEntry) -> None:
        expected_prev = self._entries[-1].entry_hash if self._entries else "GENESIS"
        if entry.prev_hash != expected_prev:
            raise ValueError(f"replica {self.replica_id!r} chain discontinuity")
        self._entries.append(entry)


class PTAAAuditLog:
    """Append-only hash-chained audit log replicated to external sinks (Annex T1 §5.1)."""

    def __init__(self, replicas: tuple[ExternalAuditReplica, ...] = ()) -> None:
        if not replicas:
            raise ValueError("I2 requires at least one external audit replica")
        self._replicas = tuple(replicas)
        self._entries: list[AuditEntry] = []

    @property
    def entries(self) -> tuple[AuditEntry, ...]:
        return tuple(self._entries)

    def append(
        self, *, agent_id: str, event_type: str, payload: dict[str, Any] | None = None
    ) -> AuditEntry:
        seq = len(self._entries) + 1
        ts = time.time()
        prev_hash = self._entries[-1].entry_hash if self._entries else "GENESIS"
        clean_payload = dict(payload or {})
        body = json.dumps(
            {
                "seq": seq,
                "timestamp": ts,
                "agent_id": agent_id,
                "event_type": event_type,
                "payload": clean_payload,
                "prev_hash": prev_hash,
            },
            sort_keys=True,
            allow_nan=False,
        )
        entry_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        entry = AuditEntry(
            seq=seq,
            timestamp=ts,
            agent_id=agent_id,
            event_type=event_type,
            payload=clean_payload,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
        )
        self._entries.append(entry)
        for rep in self._replicas:
            rep.receive(entry)
        return entry

    def verify_integrity(self) -> bool:
        """Verify primary hash chain AND exact parity with every external replica."""
        prev = "GENESIS"
        for idx, entry in enumerate(self._entries, start=1):
            if entry.seq != idx or entry.prev_hash != prev:
                return False
            data = asdict(entry)
            claimed = data.pop("entry_hash")
            recomputed = hashlib.sha256(
                json.dumps(data, sort_keys=True, allow_nan=False).encode("utf-8")
            ).hexdigest()
            if claimed != recomputed:
                return False
            prev = claimed
        return all(rep.entries == tuple(self._entries) for rep in self._replicas)
