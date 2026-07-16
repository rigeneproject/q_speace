"""Functional Resonance Layer (FRL) — Communication Through Coherence.

Implements the biological principle that oscillatory phase alignment
between neural populations gates communication efficiency:

  Communication Through Coherence (Fries, 2005, 2015)

Key concepts:
1. Phase Coherence Matrix: pairwise phase alignment between all
   brain regions on multiple oscillatory bands
2. Functional Assemblies: temporary coalitions of phase-locked regions
3. Coherence-Gated Routing: signal routing modulated by real-time
   phase alignment (not just structural connectivity)
4. Multi-Scale Global Resonance: coherence measured across local
   pairwise, global Kuramoto, and cross-frequency dimensions
5. Temporary Assembly Lifecycle: assemblies form, stabilize, and
   dissolve based on coherence dynamics
"""

import cmath
import math
from collections import deque
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from pydantic import BaseModel, ConfigDict, Field

from speace_core.cellular_brain.memory.morphological_memory import MorphologicalMemory
from speace_core.cellular_brain.memory.morphology_events import MorphologyEventType


class AssemblyStatus(str, Enum):
    FORMING = "forming"
    STABLE = "stable"
    DISSOLVING = "dissolving"
    DISSOLVED = "dissolved"


class GlobalResonanceMetrics(BaseModel):
    global_coherence: float = 0.0
    mean_pairwise_coherence: float = 0.0
    assembly_count: int = 0
    largest_assembly_size: int = 0
    cross_frequency_coupling: float = 0.0
    temporal_binding_index: float = 0.0
    functional_flexibility: float = 0.0
    metastability: float = 0.0

    model_config = ConfigDict(arbitrary_types_allowed=True)


class FunctionalAssembly:
    """A temporary coalition of regions phase-locked together."""

    def __init__(
        self,
        assembly_id: str,
        region_ids: List[str],
        band: str = "gamma",
        coherence_threshold: float = 0.6,
    ):
        self.assembly_id = assembly_id
        self.region_ids: List[str] = region_ids
        self.band = band
        self.coherence_threshold = coherence_threshold
        self.status = AssemblyStatus.FORMING
        self.mean_coherence: float = 0.0
        self.age_ticks: int = 0
        self.stability_ticks: int = 0
        self.dissolve_age: int = 0
        self.birth_tick: int = 0

    def update(self, phase_coherence_matrix: Dict[str, float]) -> None:
        self.age_ticks += 1
        intra_coherences = []
        for i, r1 in enumerate(self.region_ids):
            for j, r2 in enumerate(self.region_ids):
                if i < j:
                    key = f"{r1}->{r2}"
                    coh = phase_coherence_matrix.get(key, 0.0)
                    intra_coherences.append(coh)
                    key_rev = f"{r2}->{r1}"
                    coh_rev = phase_coherence_matrix.get(key_rev, 0.0)
                    intra_coherences.append(coh_rev)

        if intra_coherences:
            self.mean_coherence = sum(intra_coherences) / len(intra_coherences)
        else:
            self.mean_coherence = 0.0

        if self.mean_coherence >= self.coherence_threshold:
            self.stability_ticks += 1
        else:
            self.stability_ticks = max(0, self.stability_ticks - 1)

        if self.status == AssemblyStatus.FORMING and self.stability_ticks >= 3:
            self.status = AssemblyStatus.STABLE
        elif self.status == AssemblyStatus.STABLE and self.stability_ticks == 0:
            self.dissolve_age = self.age_ticks
            self.status = AssemblyStatus.DISSOLVING
        elif self.status == AssemblyStatus.DISSOLVING and self.stability_ticks == 0:
            self.status = AssemblyStatus.DISSOLVED

    def is_active(self) -> bool:
        return self.status not in (AssemblyStatus.DISSOLVED,)

    def get_core_regions(self, min_coherence: float = 0.7) -> List[str]:
        return [r for r in self.region_ids if self.mean_coherence >= min_coherence]


class FunctionalResonanceLayer:
    """Multi-scale functional resonance tracking for Communication Through Coherence.

    Measures real-time phase alignment between brain regions and uses it to:
    - Form temporary functional assemblies (coalitions of phase-locked regions)
    - Modulate inter-region signal routing (coherence-gated routing)
    - Compute global resonance metrics for system-level feedback
    """

    def __init__(
        self,
        n_regions: int = 8,
        phase_history_window: int = 20,
        coherence_threshold: float = 0.5,
        assembly_coherence_threshold: float = 0.6,
        metastability_window: int = 50,
        default_band: str = "gamma",
        bands: Optional[Dict[str, float]] = None,
    ):
        self.n_regions = n_regions
        self.phase_history_window = phase_history_window
        self.coherence_threshold = coherence_threshold
        self.assembly_coherence_threshold = assembly_coherence_threshold
        self.metastability_window = metastability_window
        self.default_band = default_band
        self.bands = bands or {
            "theta": 5.0,
            "alpha": 10.0,
            "beta": 20.0,
            "gamma": 40.0,
        }

        self.region_ids: List[str] = []
        self.region_id_to_idx: Dict[str, int] = {}

        # Activation history per region (for phase extraction)
        self._activation_history: Dict[str, deque] = {}
        # Phase per region (current, from Hilbert transform)
        self._phases: Dict[str, Dict[str, float]] = {}
        # Phase coherence matrix: (src, tgt, band) -> coherence [0,1]
        self._coherence_matrix: Dict[Tuple[str, str, str], float] = {}
        # Signal coherence for routing: (src, tgt) -> multiplier
        self._routing_multipliers: Dict[Tuple[str, str], float] = {}
        # Functional assemblies
        self._assemblies: Dict[str, FunctionalAssembly] = {}
        self._next_assembly_id: int = 0
        # History for metastability
        self._global_coherence_history: deque = deque(maxlen=metastability_window)

        self.current_metrics: "GlobalResonanceMetrics | None" = None
        self._tick_count: int = 0

    # ------------------------------------------------------------------ #
    # Region registration
    # ------------------------------------------------------------------ #

    def register_region(self, region_id: str) -> None:
        if region_id not in self.region_ids:
            idx = len(self.region_ids)
            self.region_ids.append(region_id)
            self.region_id_to_idx[region_id] = idx
            self._activation_history[region_id] = deque(maxlen=self.phase_history_window)
            self._phases[region_id] = {band: 0.0 for band in self.bands}

    def unregister_region(self, region_id: str) -> None:
        if region_id in self.region_ids:
            idx = self.region_id_to_idx.pop(region_id, None)
            self.region_ids.remove(region_id)
            self._activation_history.pop(region_id, None)
            self._phases.pop(region_id, None)
            self.n_regions = len(self.region_ids)

    # ------------------------------------------------------------------ #
    # Phase extraction from activation traces
    # ------------------------------------------------------------------ #

    def record_activation(self, region_id: str, activation: float) -> None:
        if region_id in self._activation_history:
            self._activation_history[region_id].append(activation)

    def _compute_phases(self) -> None:
        for region_id in self.region_ids:
            history = list(self._activation_history.get(region_id, []))
            if len(history) < 4:
                for band in self.bands:
                    self._phases[region_id][band] = 0.0
                continue

            arr = np.array(history)
            mean = np.mean(arr)
            std = np.std(arr) + 1e-10
            normalized = (arr - mean) / std

            for band, freq in self.bands.items():
                window = min(len(normalized), max(4, int(self.phase_history_window * freq / 40.0)))
                if window < 4:
                    self._phases[region_id][band] = 0.0
                    continue

                segment = normalized[-window:]
                # Hilbert transform for instantaneous phase
                analytic = np.fft.fft(segment)
                n = len(segment)
                analytic[1:n//2] *= 2.0
                if n % 2 == 0:
                    analytic[n//2] = 0.0
                analytic[n//2 + 1:] = 0.0
                analytic_signal = np.fft.ifft(analytic)
                phase = np.angle(analytic_signal)[-1] if len(analytic_signal) > 0 else 0.0
                self._phases[region_id][band] = phase

    # ------------------------------------------------------------------ #
    # Coherence computation
    # ------------------------------------------------------------------ #

    def _compute_pairwise_coherence(self) -> None:
        self._coherence_matrix.clear()
        for i, r1 in enumerate(self.region_ids):
            for j, r2 in enumerate(self.region_ids):
                if i == j:
                    continue
                for band in self.bands:
                    p1 = self._phases.get(r1, {}).get(band, 0.0)
                    p2 = self._phases.get(r2, {}).get(band, 0.0)
                    delta = abs(p1 - p2)
                    delta = min(delta, 2.0 * math.pi - delta)
                    coherence = math.cos(delta)
                    coherence = max(0.0, (coherence + 1.0) / 2.0)
                    self._coherence_matrix[(r1, r2, band)] = coherence

    def _compute_routing_multipliers(self) -> None:
        self._routing_multipliers.clear()
        for i, r1 in enumerate(self.region_ids):
            for j, r2 in enumerate(self.region_ids):
                if i == j:
                    continue
                key = (r1, r2)
                gamma_coh = self._coherence_matrix.get((r1, r2, "gamma"), 0.0)
                beta_coh = self._coherence_matrix.get((r1, r2, "beta"), 0.0)
                theta_coh = self._coherence_matrix.get((r1, r2, "theta"), 0.0)
                # Weighted combination: gamma for attention, beta for cognition,
                # theta for memory
                multiplier = 0.5 * gamma_coh + 0.3 * beta_coh + 0.2 * theta_coh
                multiplier = max(0.1, min(1.0, multiplier))
                self._routing_multipliers[key] = multiplier

    # ------------------------------------------------------------------ #
    # Functional assembly management
    # ------------------------------------------------------------------ #

    def _update_assemblies(self) -> None:
        # Collect coherence matrix as flat dict for assembly update
        flat_matrix: Dict[str, float] = {}
        for (r1, r2, band), coh in self._coherence_matrix.items():
            if band == self.default_band:
                flat_matrix[f"{r1}->{r2}"] = coh

        # Find connected components above threshold (functional assemblies)
        current_active: set = set()
        visited: set = set()
        components: List[List[str]] = []

        for r in self.region_ids:
            if r in visited:
                continue
            component = []
            stack = [r]
            while stack:
                node = stack.pop()
                if node in visited:
                    continue
                visited.add(node)
                component.append(node)
                for other in self.region_ids:
                    if other == node or other in visited:
                        continue
                    key_fwd = f"{node}->{other}"
                    key_rev = f"{other}->{node}"
                    coh = max(
                        flat_matrix.get(key_fwd, 0.0),
                        flat_matrix.get(key_rev, 0.0),
                    )
                    if coh >= self.coherence_threshold:
                        stack.append(other)
            if len(component) >= 2:
                components.append(component)

        all_component_regions: set = set()
        for comp in components:
            all_component_regions.update(comp)
            current_active.update(comp)

        # Match existing assemblies to components or create new ones
        matched_assemblies: set = set()
        for comp in components:
            comp_set = set(comp)
            found = False
            for aid, assembly in list(self._assemblies.items()):
                if not assembly.is_active():
                    continue
                asm_set = set(assembly.region_ids)
                overlap = len(comp_set & asm_set)
                if overlap >= len(comp_set) * 0.6 or overlap >= len(asm_set) * 0.6:
                    assembly.region_ids = list(comp_set)
                    assembly.update(flat_matrix)
                    matched_assemblies.add(aid)
                    found = True
                    break
            if not found:
                aid = f"assembly_{self._next_assembly_id}"
                self._next_assembly_id += 1
                assembly = FunctionalAssembly(
                    assembly_id=aid,
                    region_ids=list(comp_set),
                    band=self.default_band,
                    coherence_threshold=self.assembly_coherence_threshold,
                )
                assembly.birth_tick = self._tick_count
                assembly.update(flat_matrix)
                self._assemblies[aid] = assembly
                matched_assemblies.add(aid)

        # Mark unmatched assemblies as dissolving
        for aid, assembly in self._assemblies.items():
            if aid not in matched_assemblies and assembly.is_active():
                if assembly.status == AssemblyStatus.STABLE:
                    assembly.status = AssemblyStatus.DISSOLVING
                elif assembly.status == AssemblyStatus.DISSOLVING:
                    assembly.status = AssemblyStatus.DISSOLVED

        # Clean up fully dissolved
        self._assemblies = {
            aid: asm for aid, asm in self._assemblies.items()
            if asm.is_active() or asm.age_ticks < 100
        }

    # ------------------------------------------------------------------ #
    # Global resonance metrics
    # ------------------------------------------------------------------ #

    def _compute_global_metrics(self) -> "GlobalResonanceMetrics":
        if not self.region_ids:
            return GlobalResonanceMetrics(
                global_coherence=0.0,
                mean_pairwise_coherence=0.0,
                assembly_count=0,
                largest_assembly_size=0,
                cross_frequency_coupling=0.0,
                temporal_binding_index=0.0,
                functional_flexibility=0.0,
                metastability=0.0,
            )

        n = len(self.region_ids)
        total_pairs = n * (n - 1)
        mean_pairwise = 0.0
        if total_pairs > 0:
            gamma_sum = 0.0
            count = 0
            for i, r1 in enumerate(self.region_ids):
                for j, r2 in enumerate(self.region_ids):
                    if i != j:
                        coh = self._coherence_matrix.get((r1, r2, "gamma"), 0.0)
                        gamma_sum += coh
                        count += 1
            mean_pairwise = gamma_sum / max(1, count)

        # Global Kuramoto-like coherence from phases
        if n >= 2:
            gamma_phases = [
                self._phases.get(rid, {}).get("gamma", 0.0)
                for rid in self.region_ids
            ]
            complex_sum = sum(cmath.exp(1j * p) for p in gamma_phases)
            global_coherence = abs(complex_sum) / n
        else:
            global_coherence = 0.0

        # Cross-frequency coupling (gamma-theta)
        cfc = 0.0
        if n >= 2:
            gamma_phases = [
                self._phases.get(rid, {}).get("gamma", 0.0)
                for rid in self.region_ids
            ]
            theta_phases = [
                self._phases.get(rid, {}).get("theta", 0.0)
                for rid in self.region_ids
            ]
            gamma_mean = math.atan2(
                sum(math.sin(p) for p in gamma_phases),
                sum(math.cos(p) for p in gamma_phases),
            )
            theta_mean = math.atan2(
                sum(math.sin(p) for p in theta_phases),
                sum(math.cos(p) for p in theta_phases),
            )
            cfc = abs(math.cos(gamma_mean - theta_mean))

        # Temporal binding index: fraction of regions in assemblies
        in_assembly: set = set()
        for asm in self._assemblies.values():
            if asm.is_active():
                in_assembly.update(asm.region_ids)
        tbi = len(in_assembly) / max(1, n)

        # Functional flexibility: how often assemblies change
        self._global_coherence_history.append(global_coherence)
        metastability = 0.0
        flexibility = 0.0
        if len(self._global_coherence_history) >= 10:
            coh_series = list(self._global_coherence_history)
            metastability = float(np.std(coh_series))
            # Flexibility = rate of significant coherence changes
            changes = sum(
                1 for i in range(1, len(coh_series))
                if abs(coh_series[i] - coh_series[i-1]) > 0.1
            )
            flexibility = changes / max(1, len(coh_series) - 1)

        active_assemblies = [a for a in self._assemblies.values() if a.is_active()]
        largest = max((len(a.region_ids) for a in active_assemblies), default=0)

        metrics = GlobalResonanceMetrics(
            global_coherence=round(global_coherence, 4),
            mean_pairwise_coherence=round(mean_pairwise, 4),
            assembly_count=len(active_assemblies),
            largest_assembly_size=largest,
            cross_frequency_coupling=round(cfc, 4),
            temporal_binding_index=round(tbi, 4),
            functional_flexibility=round(flexibility, 4),
            metastability=round(metastability, 4),
        )
        return metrics

    # ------------------------------------------------------------------ #
    # Main tick
    # ------------------------------------------------------------------ #

    def tick(
        self,
        memory: Optional[MorphologicalMemory] = None,
    ) -> "GlobalResonanceMetrics":
        """Compute phase coherence, update assemblies, and return metrics."""
        self._tick_count += 1

        self._compute_phases()
        self._compute_pairwise_coherence()
        self._compute_routing_multipliers()
        self._update_assemblies()
        self.current_metrics = self._compute_global_metrics()

        if memory is not None and self.current_metrics is not None:
            for asm in self._assemblies.values():
                if asm.status == AssemblyStatus.STABLE and asm.age_ticks == asm.stability_ticks:
                    memory.create_event(
                        event_type=MorphologyEventType.FUNCTIONAL_ASSEMBLY_FORMED,
                        source_id="functional_resonance_layer",
                        metadata={
                            "assembly_id": asm.assembly_id,
                            "region_ids": asm.region_ids,
                            "band": asm.band,
                            "mean_coherence": round(asm.mean_coherence, 4),
                        },
                    )
                elif asm.status == AssemblyStatus.DISSOLVED and asm.age_ticks == asm.dissolve_age + 1:
                    memory.create_event(
                        event_type=MorphologyEventType.FUNCTIONAL_ASSEMBLY_DISSOLVED,
                        source_id="functional_resonance_layer",
                        metadata={
                            "assembly_id": asm.assembly_id,
                            "age_ticks": asm.dissolve_age,
                            "mean_coherence": round(asm.mean_coherence, 4),
                        },
                    )

        return self.current_metrics

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def get_routing_multiplier(self, source_region: str, target_region: str) -> float:
        """Return Communication-Through-Coherence multiplier [0.1, 1.0].

        Used to modulate inter-region signal strength based on
        real-time phase alignment between source and target regions.
        """
        return self._routing_multipliers.get((source_region, target_region), 0.5)

    def get_assembly_for_region(self, region_id: str) -> Optional[FunctionalAssembly]:
        """Return the functional assembly containing a region, if any."""
        for asm in self._assemblies.values():
            if asm.is_active() and region_id in asm.region_ids:
                return asm
        return None

    def get_routing_multipliers_map(self) -> Dict[Tuple[str, str], float]:
        """Return all per-pair routing multipliers (copy of internal map)."""
        return dict(self._routing_multipliers)

    def get_active_assemblies(self) -> List[FunctionalAssembly]:
        return [a for a in self._assemblies.values() if a.is_active()]

    def get_phase_coherence(self, r1: str, r2: str, band: str = "gamma") -> float:
        """Return pairwise phase coherence [0,1] between two regions."""
        return self._coherence_matrix.get((r1, r2, band), 0.0)

    def get_phase(self, region_id: str, band: str = "gamma") -> float:
        """Return current oscillatory phase for a region."""
        return self._phases.get(region_id, {}).get(band, 0.0)

    def get_global_metrics(self) -> "GlobalResonanceMetrics":
        if self.current_metrics is not None:
            return self.current_metrics
        return GlobalResonanceMetrics()

    def reset(self) -> None:
        self._activation_history.clear()
        self._phases.clear()
        self._coherence_matrix.clear()
        self._routing_multipliers.clear()
        self._assemblies.clear()
        self._global_coherence_history.clear()
        self._tick_count = 0
        self.current_metrics = None

    def get_state_summary(self) -> Dict[str, Any]:
        metrics = self.get_global_metrics()
        active = self.get_active_assemblies()
        return {
            "global_coherence": metrics.global_coherence,
            "mean_pairwise_coherence": metrics.mean_pairwise_coherence,
            "assembly_count": metrics.assembly_count,
            "largest_assembly_size": metrics.largest_assembly_size,
            "cross_frequency_coupling": metrics.cross_frequency_coupling,
            "temporal_binding_index": metrics.temporal_binding_index,
            "functional_flexibility": metrics.functional_flexibility,
            "metastability": metrics.metastability,
            "assemblies": [
                {
                    "id": a.assembly_id,
                    "regions": a.region_ids,
                    "status": a.status.value,
                    "mean_coherence": round(a.mean_coherence, 4),
                    "age": a.age_ticks,
                }
                for a in active
            ],
        }
