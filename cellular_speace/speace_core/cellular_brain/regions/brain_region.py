from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from speace_core.cellular_brain.resonance.frequency_oscillator import (
    FrequencyOscillator,
    FrequencyBand,
    default_oscillators_for_region,
)
from speace_core.cellular_brain.resonance.resonance_field import WaveState


class BrainRegionProfile(BaseModel):
    region_id: str
    name: str
    region_type: str
    neuron_ids: List[str] = Field(default_factory=list)
    synapse_ids: List[str] = Field(default_factory=list)
    dominant_cell_types: List[str] = Field(default_factory=list)
    mean_energy: float = 0.0
    local_phi: float = 0.0
    local_confidence: Optional[float] = None
    community_count: int = 0
    role_description: Optional[str] = None
    dominant_frequency: float = 10.0
    phase_coherence: float = 0.0
    resonance_amplitude: float = 0.0
    active_bands: List[str] = []


class BrainRegion:
    """Functional neurocellular region in SPEACE with quantum resonance."""

    def __init__(
        self,
        region_id: str,
        region_type: str,
        neuron_ids: Optional[List[str]] = None,
        dominant_cell_types: Optional[List[str]] = None,
        role_description: Optional[str] = None,
    ):
        self.region_id = region_id
        self.region_type = region_type
        self.neuron_ids = neuron_ids or []
        self.synapse_ids: List[str] = []
        self.dominant_cell_types = dominant_cell_types or []
        self.role_description = role_description or ""
        self._input_buffer: List[float] = []
        self._output_buffer: List[float] = []

        self.oscillators: Dict[str, FrequencyOscillator] = {
            o.oscillator_id: o
            for o in default_oscillators_for_region(region_type, region_id)
        }
        self.current_phase: float = 0.0
        self.current_amplitude: float = 0.0
        self.phase_coherence: float = 0.0
        self.dominant_frequency: float = 10.0

    # ------------------------------------------------------------------ #
    # Local metrics
    # ------------------------------------------------------------------ #

    def compute_local_metrics(self, circuit) -> BrainRegionProfile:
        """Compute energy, phi, and community proxy for this region."""
        from speace_core.cellular_brain.circuits.neural_circuit import NeuralCircuit

        if not isinstance(circuit, NeuralCircuit):
            return self.to_profile()

        all_neurons = circuit.input_neurons + circuit.hidden_neurons + circuit.output_neurons
        region_neurons = [
            n for n in all_neurons if n.cell_id in self.neuron_ids
        ]
        region_synapses = [
            s for s in circuit.synapses
            if s.source in self.neuron_ids and s.target in self.neuron_ids
        ]

        mean_energy = (
            sum(n.energy for n in region_neurons) / len(region_neurons)
            if region_neurons
            else 0.0
        )

        # Local phi proxy: ratio of internal vs total synaptic weight
        internal_weight = sum(s.weight for s in region_synapses if s.state != "pruned")
        all_weight = sum(
            s.weight
            for s in circuit.synapses
            if s.source in self.neuron_ids or s.target in self.neuron_ids
            if s.state != "pruned"
        )
        local_phi = internal_weight / (all_weight + 1e-12) if all_weight > 0 else 0.0

        return BrainRegionProfile(
            region_id=self.region_id,
            name=self.region_type,
            region_type=self.region_type,
            neuron_ids=self.neuron_ids,
            synapse_ids=[s.cell_id for s in region_synapses],
            dominant_cell_types=self.dominant_cell_types,
            mean_energy=mean_energy,
            local_phi=local_phi,
            role_description=self.role_description,
            dominant_frequency=self.dominant_frequency,
            phase_coherence=self.phase_coherence,
            resonance_amplitude=self.current_amplitude,
            active_bands=[osc.band.value for osc in self.oscillators.values()],
        )

    def to_profile(self) -> BrainRegionProfile:
        return BrainRegionProfile(
            region_id=self.region_id,
            name=self.region_type,
            region_type=self.region_type,
            neuron_ids=self.neuron_ids,
            synapse_ids=self.synapse_ids,
            dominant_cell_types=self.dominant_cell_types,
            role_description=self.role_description,
            dominant_frequency=self.dominant_frequency,
            phase_coherence=self.phase_coherence,
            resonance_amplitude=self.current_amplitude,
            active_bands=[osc.band.value for osc in self.oscillators.values()],
        )

    # ------------------------------------------------------------------ #
    # Signal I/O
    # ------------------------------------------------------------------ #

    def receive_signal(self, signal: List[float]) -> None:
        self._input_buffer.extend(signal)

    def emit_signal(self) -> List[float]:
        output = self._output_buffer.copy()
        self._output_buffer.clear()
        return output

    def flush_buffers(self) -> None:
        self._input_buffer.clear()
        self._output_buffer.clear()

    # ------------------------------------------------------------------ #
    # Resonance / Oscillation
    # ------------------------------------------------------------------ #

    def tick_oscillators(self, dt: float = 1.0) -> Dict[str, float]:
        outputs: Dict[str, float] = {}
        for oid, osc in self.oscillators.items():
            outputs[oid] = osc.tick(dt)

        if self.oscillators:
            import math
            sin_sum = sum(math.sin(o.phase) for o in self.oscillators.values())
            cos_sum = sum(math.cos(o.phase) for o in self.oscillators.values())
            n = len(self.oscillators)
            self.current_phase = math.atan2(sin_sum / n, cos_sum / n) if n > 0 else 0.0
            self.current_amplitude = sum(o.amplitude for o in self.oscillators.values()) / n
            self.phase_coherence = math.sqrt(sin_sum**2 + cos_sum**2) / (n + 1e-12)

            best = max(self.oscillators.values(), key=lambda o: o.amplitude)
            self.dominant_frequency = best.frequency

        return outputs

    def get_field_state(self) -> Dict[str, float]:
        return {
            "phase": self.current_phase,
            "amplitude": self.current_amplitude,
            "coherence": self.phase_coherence,
            "frequency": self.dominant_frequency,
        }

    def phase_lock_to(self, target_phase: float, strength: float = 0.1) -> None:
        for osc in self.oscillators.values():
            osc.phase_lock_to(target_phase, strength)

    def release_phase_lock(self) -> None:
        for osc in self.oscillators.values():
            osc.release_phase_lock()

    def get_oscillator_list(self) -> List[FrequencyOscillator]:
        return list(self.oscillators.values())

    # ------------------------------------------------------------------ #
    # Regulation
    # ------------------------------------------------------------------ #

    def regulate_region(self, circuit) -> None:
        """Apply region-specific regulation (e.g., energy normalization)."""
        all_neurons = circuit.input_neurons + circuit.hidden_neurons + circuit.output_neurons
        region_neurons = [
            n for n in all_neurons if n.cell_id in self.neuron_ids
        ]
        if not region_neurons:
            return
        mean_energy = sum(n.energy for n in region_neurons) / len(region_neurons)
        if mean_energy > 0.9:
            for n in region_neurons:
                n.energy *= 0.98
        elif mean_energy < 0.3:
            for n in region_neurons:
                n.energy = min(1.0, n.energy + 0.02)
