"""Deterministic, classical resilience metrics for six-node clusters.

This module models observable system state only.  It performs no I/O,
actuation, quantum-backend access, or implied communication between nodes.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import cos, isfinite
from typing import Literal


@dataclass(frozen=True)
class NodeState:
    """Finite telemetry used by the resilience calculation."""

    node_id: str
    load: float
    entropy: float
    tension: float
    phase: float

    def __post_init__(self) -> None:
        if not self.node_id:
            raise ValueError("node_id must not be empty")
        for name, value in (
            ("load", self.load),
            ("entropy", self.entropy),
            ("tension", self.tension),
        ):
            if not isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be finite and in [0, 1]")
        if not isfinite(self.phase):
            raise ValueError("phase must be finite")


@dataclass(frozen=True)
class ClusterAssessment:
    """A six-node cluster and its deterministic affinity score."""

    node_ids: tuple[str, ...]
    resonance: float


@dataclass(frozen=True)
class SystemHealth:
    """Read-only health report suitable for a dashboard or simulation."""

    state: Literal["empty", "degraded", "stable"]
    average_entropy: float
    average_tension: float
    clusters: tuple[ClusterAssessment, ...]


class ResonanceEngine:
    """Evaluate fixed-cardinality redundancy clusters without side effects."""

    def __init__(
        self,
        resonance_threshold: float = 0.85,
        tension_threshold: float = 0.50,
    ) -> None:
        for name, value in (
            ("resonance_threshold", resonance_threshold),
            ("tension_threshold", tension_threshold),
        ):
            if not isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be finite and in [0, 1]")
        self._nodes: dict[str, NodeState] = {}
        self.resonance_threshold = resonance_threshold
        self.tension_threshold = tension_threshold

    def update_node_state(self, state: NodeState) -> None:
        """Store the latest telemetry for one logical node."""
        self._nodes[state.node_id] = state

    @staticmethod
    def pairwise_affinity(node_a: NodeState, node_b: NodeState) -> float:
        """Return a phase-alignment score penalized by average entropy."""
        phase_alignment = (cos(node_a.phase - node_b.phase) + 1.0) / 2.0
        entropy_penalty = 1.0 - ((node_a.entropy + node_b.entropy) / 2.0)
        return phase_alignment * entropy_penalty

    def find_hexagonal_clusters(self) -> tuple[ClusterAssessment, ...]:
        """Return qualifying groups of exactly six nodes in stable order."""
        node_ids = sorted(self._nodes)
        assessments: list[ClusterAssessment] = []
        for cluster_ids in combinations(node_ids, 6):
            affinities = [
                self.pairwise_affinity(self._nodes[left], self._nodes[right])
                for left, right in combinations(cluster_ids, 2)
            ]
            resonance = sum(affinities) / len(affinities)
            if resonance >= self.resonance_threshold:
                assessments.append(ClusterAssessment(cluster_ids, resonance))
        return tuple(sorted(assessments, key=lambda item: (-item.resonance, item.node_ids)))

    def assess_health(self) -> SystemHealth:
        """Summarize current telemetry without commanding any action."""
        if not self._nodes:
            return SystemHealth("empty", 0.0, 0.0, ())
        nodes = tuple(self._nodes.values())
        average_entropy = sum(node.entropy for node in nodes) / len(nodes)
        average_tension = sum(node.tension for node in nodes) / len(nodes)
        clusters = self.find_hexagonal_clusters()
        state: Literal["degraded", "stable"] = "stable"
        if not clusters or average_tension > self.tension_threshold:
            state = "degraded"
        return SystemHealth(state, average_entropy, average_tension, clusters)
