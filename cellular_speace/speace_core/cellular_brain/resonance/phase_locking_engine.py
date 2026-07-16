from __future__ import annotations

import math
from enum import Enum
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from speace_core.cellular_brain.resonance.frequency_oscillator import FrequencyOscillator


class CouplingTopology(str, Enum):
    GLOBAL = "global"
    NEAREST_NEIGHBOR = "nearest_neighbor"
    TARGETED = "targeted"


class PhaseLockingConfig(BaseModel):
    coupling_strength: float = 0.1
    coupling_topology: CouplingTopology = CouplingTopology.GLOBAL
    natural_frequency_weight: float = 0.3
    phase_tolerance: float = 0.1
    max_coupled_oscillators: int = 0
    enable_adaptive_coupling: bool = True

    model_config = ConfigDict(arbitrary_types_allowed=True)


class PhaseLockingEngine(BaseModel):
    config: PhaseLockingConfig = Field(default_factory=PhaseLockingConfig)
    oscillators: Dict[str, FrequencyOscillator] = Field(default_factory=dict)
    coupling_matrix: Dict[str, List[str]] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def register_oscillator(self, oscillator: FrequencyOscillator) -> None:
        self.oscillators[oscillator.oscillator_id] = oscillator
        self.coupling_matrix[oscillator.oscillator_id] = []

    def unregister_oscillator(self, oscillator_id: str) -> None:
        self.oscillators.pop(oscillator_id, None)
        self.coupling_matrix.pop(oscillator_id, None)
        for source_id in list(self.coupling_matrix.keys()):
            if oscillator_id in self.coupling_matrix[source_id]:
                self.coupling_matrix[source_id].remove(oscillator_id)

    def couple_oscillators(
        self, source_id: str, target_id: str, strength: Optional[float] = None
    ) -> None:
        if source_id not in self.coupling_matrix:
            self.coupling_matrix[source_id] = []
        if target_id not in self.coupling_matrix[source_id]:
            self.coupling_matrix[source_id].append(target_id)

    def uncouple_oscillators(self, source_id: str, target_id: str) -> None:
        if source_id in self.coupling_matrix:
            if target_id in self.coupling_matrix[source_id]:
                self.coupling_matrix[source_id].remove(target_id)

    def tick(self, dt: float = 1.0) -> Dict[str, float]:
        if not self.oscillators:
            return {}

        coupling_map = self._build_coupling_map()

        phase_updates: Dict[str, float] = {}
        for oid, osc in self.oscillators.items():
            coupled = coupling_map.get(oid, [])
            if not coupled:
                phase_updates[oid] = osc.phase
                continue

            mean_sin = sum(math.sin(self.oscillators[c].phase) for c in coupled)
            mean_cos = sum(math.cos(self.oscillators[c].phase) for c in coupled)
            n = len(coupled)
            mean_phase = math.atan2(mean_sin / n, mean_cos / n) if n > 0 else osc.phase

            diff = mean_phase - osc.phase
            coupling = self.config.coupling_strength / max(1, len(self.coupling_matrix.get(oid, [])))
            phase_updates[oid] = osc.phase + diff * coupling * 0.1

        for oid, new_phase in phase_updates.items():
            if oid in self.oscillators:
                self.oscillators[oid].phase = new_phase % (2.0 * math.pi)

        return phase_updates

    def _build_coupling_map(self) -> Dict[str, List[str]]:
        topology = self.config.coupling_topology
        if topology == CouplingTopology.GLOBAL:
            all_ids = list(self.oscillators.keys())
            return {oid: [x for x in all_ids if x != oid] for oid in all_ids}
        elif topology == CouplingTopology.NEAREST_NEIGHBOR:
            return self._build_nearest_neighbor_map()
        else:
            return {
                oid: list(targets) for oid, targets in self.coupling_matrix.items()
            }

    def _build_nearest_neighbor_map(self) -> Dict[str, List[str]]:
        sorted_ids = sorted(self.oscillators.keys())
        result: Dict[str, List[str]] = {}
        for i, oid in enumerate(sorted_ids):
            neighbors = []
            if i > 0:
                neighbors.append(sorted_ids[i - 1])
            if i < len(sorted_ids) - 1:
                neighbors.append(sorted_ids[i + 1])
            result[oid] = neighbors
        return result

    def compute_order_parameter(self) -> float:
        if not self.oscillators:
            return 0.0
        sin_sum = sum(math.sin(o.phase) for o in self.oscillators.values())
        cos_sum = sum(math.cos(o.phase) for o in self.oscillators.values())
        n = len(self.oscillators)
        return math.sqrt(sin_sum**2 + cos_sum**2) / (n + 1e-12)

    def compute_phase_locking_value(self, oscillator_ids: List[str]) -> float:
        oscs = [self.oscillators[oid] for oid in oscillator_ids if oid in self.oscillators]
        if len(oscs) < 2:
            return 1.0
        sin_sum = sum(math.sin(o.phase) for o in oscs)
        cos_sum = sum(math.cos(o.phase) for o in oscs)
        n = len(oscs)
        return math.sqrt(sin_sum**2 + cos_sum**2) / (n + 1e-12)

    def detect_phase_clusters(self, tolerance: Optional[float] = None) -> List[List[str]]:
        tol = tolerance or self.config.phase_tolerance
        osc_list = list(self.oscillators.keys())
        clusters: List[List[str]] = []
        assigned: set = set()

        for oid in osc_list:
            if oid in assigned:
                continue
            cluster = [oid]
            phase_i = self.oscillators[oid].phase
            for other in osc_list:
                if other in assigned or other == oid:
                    continue
                diff = abs(self.oscillators[other].phase - phase_i) % (2.0 * math.pi)
                diff = min(diff, 2.0 * math.pi - diff)
                if diff < tol:
                    cluster.append(other)
                    assigned.add(other)
            assigned.add(oid)
            if len(cluster) > 1:
                clusters.append(cluster)

        return clusters
