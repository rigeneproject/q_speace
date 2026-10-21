"""Classical, deterministic resilience metrics for six-node clusters."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import cos, isfinite
from typing import Literal


@dataclass(frozen=True)
class NodeState:
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
    node_ids: tuple[str, ...]
    resonance: float


@dataclass(frozen=True)
class SystemHealth:
    state: Literal["empty", "degraded", "stable"]
    average_entropy: float
    average_tension: float
    clusters: tuple[ClusterAssessment, ...]


@dataclass(frozen=True)
class FailureComparison:
    failed_node_ids: tuple[str, ...]
    redundant_capacity: float
    single_path_capacity: float


class ResonanceEngine:
    """Evaluate telemetry only; this class performs no I/O or actuation."""

    def __init__(self, resonance_threshold: float = 0.85, tension_threshold: float = 0.50) -> None:
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
        self._nodes[state.node_id] = state

    @staticmethod
    def pairwise_affinity(node_a: NodeState, node_b: NodeState) -> float:
        return ((cos(node_a.phase - node_b.phase) + 1.0) / 2.0) * (
            1.0 - (node_a.entropy + node_b.entropy) / 2.0
        )

    def find_hexagonal_clusters(self) -> tuple[ClusterAssessment, ...]:
        assessments = []
        for node_ids in combinations(sorted(self._nodes), 6):
            affinities = [
                self.pairwise_affinity(self._nodes[left], self._nodes[right])
                for left, right in combinations(node_ids, 2)
            ]
            resonance = sum(affinities) / len(affinities)
            if resonance >= self.resonance_threshold:
                assessments.append(ClusterAssessment(node_ids, resonance))
        return tuple(sorted(assessments, key=lambda item: (-item.resonance, item.node_ids)))

    def assess_health(self) -> SystemHealth:
        if not self._nodes:
            return SystemHealth("empty", 0.0, 0.0, ())
        nodes = tuple(self._nodes.values())
        entropy = sum(node.entropy for node in nodes) / len(nodes)
        tension = sum(node.tension for node in nodes) / len(nodes)
        clusters = self.find_hexagonal_clusters()
        state: Literal["degraded", "stable"] = (
            "stable" if clusters and tension <= self.tension_threshold else "degraded"
        )
        return SystemHealth(state, entropy, tension, clusters)

    def compare_controlled_failure(self, failed_node_ids: set[str]) -> FailureComparison:
        """Compare remaining redundant capacity with a single-path baseline."""
        unknown = failed_node_ids.difference(self._nodes)
        if unknown:
            raise ValueError(f"unknown node identifiers: {sorted(unknown)}")
        total = len(self._nodes)
        redundant_capacity = 0.0 if not total else (total - len(failed_node_ids)) / total
        single_path_capacity = 1.0 if not failed_node_ids else 0.0
        return FailureComparison(
            tuple(sorted(failed_node_ids)), redundant_capacity, single_path_capacity
        )
