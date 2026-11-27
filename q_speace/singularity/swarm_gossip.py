"""Bounded-TTL SWIM-like Swarm Gossip & Advisory Self-Healing Coordinator (T256-05).

Synthesized via BCEL from ``SPEACE PROTOTIPO CLAUDE`` (``SPEACE_Cortex/swarm/swarm_node.py``):
- Fast-plane epidemic peer liveness / capability dissemination complementing slow-plane
  ``DLTSwarmLedger`` (``T236``).
- Enforces bounded ``ttl``, ``(sender_id, msg_id)`` ring-buffer deduplication, explicit
  monotonic timestamp evaluation (zero wall-clock flakiness), and advisory ``RepairPlan``
  generation (``replace``, ``reroute``, ``rebalance``).
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import numpy as np


class PeerState(StrEnum):
    """Liveness state of a swarm peer."""

    ACTIVE = "active"
    STALE = "stale"
    FAILED = "failed"
    RECOVERING = "recovering"


@dataclass
class PeerNodeRecord:
    """Tracked telemetry and liveness state for one swarm peer."""

    node_id: str
    role: str = "edge"
    state: PeerState = PeerState.ACTIVE
    last_heartbeat_s: float = 0.0
    phi: float = 0.70
    load: float = 0.20
    consecutive_misses: int = 0
    capabilities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.node_id or not self.role:
            raise ValueError("node_id and role must be non-empty")
        for name, val in (("phi", self.phi), ("load", self.load)):
            if not math.isfinite(val) or not (0.0 <= val <= 1.0):
                raise ValueError(f"{name} must be finite and in [0, 1]")
        if not math.isfinite(self.last_heartbeat_s) or self.last_heartbeat_s < 0.0:
            raise ValueError("last_heartbeat_s must be finite and >= 0")


@dataclass(frozen=True)
class GossipEnvelope:
    """Immutable bounded-TTL gossip message."""

    msg_id: str
    kind: str  # "heartbeat" | "resource_update" | "repair_notice"
    sender_id: str
    created_at_s: float
    ttl: int = 3
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.msg_id or not self.sender_id or not self.kind:
            raise ValueError("msg_id, kind, and sender_id must be non-empty")
        if self.ttl < 0 or self.ttl > 8:
            raise ValueError("ttl must be in [0, 8]")
        if not math.isfinite(self.created_at_s) or self.created_at_s < 0.0:
            raise ValueError("created_at_s must be finite and >= 0")


@dataclass(frozen=True)
class RepairPlan:
    """Advisory self-healing plan emitted when a peer transitions to ``FAILED``."""

    failed_node_id: str
    strategy: str  # "replace" | "reroute" | "rebalance"
    selected_targets: tuple[str, ...]
    reason: str


class BoundedGossipProtocol:
    """Seeded epidemic gossip disseminator with TTL decrement and deduplication (T256-05)."""

    def __init__(
        self,
        local_node_id: str,
        *,
        fanout: int = 2,
        dedup_capacity: int = 256,
        seed: int = 42,
    ) -> None:
        if not local_node_id:
            raise ValueError("local_node_id must be non-empty")
        if fanout < 1:
            raise ValueError("fanout must be >= 1")
        if dedup_capacity < 8:
            raise ValueError("dedup_capacity must be >= 8")

        self.local_node_id = local_node_id
        self.fanout = int(fanout)
        self._seen: deque[tuple[str, str]] = deque(maxlen=dedup_capacity)
        self._rng = np.random.default_rng(seed)

    def has_seen(self, envelope: GossipEnvelope) -> bool:
        return (envelope.sender_id, envelope.msg_id) in self._seen

    def prepare_forward(
        self,
        envelope: GossipEnvelope,
        candidate_peers: Sequence[str],
    ) -> tuple[GossipEnvelope | None, tuple[str, ...]]:
        """Deduplicate, decrement TTL, and select up to ``fanout`` downstream peers."""
        key = (envelope.sender_id, envelope.msg_id)
        if key in self._seen:
            return (None, ())
        self._seen.append(key)

        if envelope.ttl <= 0:
            return (None, ())

        eligible = [
            p for p in candidate_peers if p and p not in {self.local_node_id, envelope.sender_id}
        ]
        if not eligible:
            return (None, ())

        if len(eligible) <= self.fanout:
            targets = tuple(eligible)
        else:
            idxs = self._rng.choice(len(eligible), size=self.fanout, replace=False)
            targets = tuple(eligible[int(i)] for i in sorted(idxs))

        forwarded = GossipEnvelope(
            msg_id=envelope.msg_id,
            kind=envelope.kind,
            sender_id=envelope.sender_id,
            created_at_s=envelope.created_at_s,
            ttl=envelope.ttl - 1,
            payload=dict(envelope.payload),
        )
        return (forwarded, targets)


class SwarmSelfHealer:
    """Deterministic SWIM-like peer liveness detector and advisory repair planner (T256-05)."""

    def __init__(
        self,
        *,
        stale_timeout_s: float = 30.0,
        failure_misses: int = 3,
    ) -> None:
        if not math.isfinite(stale_timeout_s) or stale_timeout_s <= 0.0:
            raise ValueError("stale_timeout_s must be finite and > 0")
        if failure_misses < 1:
            raise ValueError("failure_misses must be >= 1")
        self.stale_timeout_s = float(stale_timeout_s)
        self.failure_misses = int(failure_misses)
        self._peers: dict[str, PeerNodeRecord] = {}
        self._standbys: dict[str, str] = {}

    @property
    def peers(self) -> Mapping[str, PeerNodeRecord]:
        return self._peers

    def register_peer(
        self,
        peer: PeerNodeRecord,
        *,
        standby_node_id: str | None = None,
    ) -> None:
        self._peers[peer.node_id] = peer
        if standby_node_id:
            self._standbys[peer.node_id] = standby_node_id

    def record_heartbeat(
        self,
        node_id: str,
        *,
        now_s: float,
        phi: float | None = None,
        load: float | None = None,
    ) -> None:
        if node_id not in self._peers:
            raise KeyError(f"Unknown peer: {node_id!r}")
        if not math.isfinite(now_s) or now_s < 0.0:
            raise ValueError("now_s must be finite and >= 0")
        rec = self._peers[node_id]
        rec.last_heartbeat_s = float(now_s)
        rec.consecutive_misses = 0
        rec.state = PeerState.ACTIVE
        if phi is not None:
            if not math.isfinite(phi) or not (0.0 <= phi <= 1.0):
                raise ValueError("phi must be in [0, 1]")
            rec.phi = float(phi)
        if load is not None:
            if not math.isfinite(load) or not (0.0 <= load <= 1.0):
                raise ValueError("load must be in [0, 1]")
            rec.load = float(load)

    def audit_liveness(self, now_s: float) -> tuple[RepairPlan, ...]:
        """Advance peer liveness at monotonic ``now_s`` and emit advisory ``RepairPlan``s."""
        if not math.isfinite(now_s) or now_s < 0.0:
            raise ValueError("now_s must be finite and >= 0")

        newly_failed: list[PeerNodeRecord] = []
        for rec in self._peers.values():
            if rec.state == PeerState.FAILED:
                continue
            silence_s = now_s - rec.last_heartbeat_s
            if silence_s > self.stale_timeout_s:
                rec.consecutive_misses += 1
                if rec.consecutive_misses >= self.failure_misses:
                    rec.state = PeerState.FAILED
                    newly_failed.append(rec)
                else:
                    rec.state = PeerState.STALE

        healthy = [
            p
            for p in sorted(self._peers.values(), key=lambda x: (x.load, x.node_id))
            if p.state == PeerState.ACTIVE and p.load < 0.85
        ]

        plans: list[RepairPlan] = []
        for failed in newly_failed:
            standby_id = self._standbys.get(failed.node_id)
            standby = self._peers.get(standby_id) if standby_id else None
            if standby is not None and standby.state == PeerState.ACTIVE and standby.load < 0.85:
                plans.append(
                    RepairPlan(
                        failed_node_id=failed.node_id,
                        strategy="replace",
                        selected_targets=(standby.node_id,),
                        reason=f"Designated standby {standby.node_id} healthy (load={standby.load:.2f})",
                    )
                )
            elif failed.role in {"relay", "edge"} and healthy:
                plans.append(
                    RepairPlan(
                        failed_node_id=failed.node_id,
                        strategy="reroute",
                        selected_targets=(healthy[0].node_id,),
                        reason=f"Bypass {failed.role} via lowest-load peer {healthy[0].node_id}",
                    )
                )
            else:
                targets = tuple(p.node_id for p in healthy[:2])
                plans.append(
                    RepairPlan(
                        failed_node_id=failed.node_id,
                        strategy="rebalance",
                        selected_targets=targets,
                        reason="Redistribute workload across remaining active peers",
                    )
                )

        return tuple(plans)
