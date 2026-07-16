import math
from typing import Dict, List, Optional

from speace_core.cellular_brain.base.digital_cell import DigitalCell
from pydantic import Field
from speace_core.cellular_brain.base.digital_signal import DigitalSignal
from speace_core.cellular_brain.cells.functional_activation_gate import (
    FunctionalActivationGate,
)
from speace_core.cellular_brain.base.receptor_profile import (
    ReceptorProfile,
    ReceptorType,
    default_excitatory_neuron_profile,
    default_inhibitory_neuron_profile,
)


class DigitalNeuron(DigitalCell):
    threshold: float = 0.5
    activation: float = 0.0
    plasticity_rate: float = 0.05
    targets: List[str] = []
    error_history: List[float] = []

    # Quantum wave-particle duality field
    wave_phase: float = 0.0
    wave_amplitude: float = 0.3
    wave_frequency: float = 10.0
    wave_damping: float = 0.02
    emit_wave: bool = True

    # T9 — ApoptosisEngine fields
    neuron_role: str = "excitatory"
    is_critical: bool = False
    snooze_counter: int = 0
    refractory_counter: int = 0
    refractory_period: int = 0
    consecutive_fires: int = 0
    last_fired_tick: int | None = None
    utility_score: float = 0.0
    apoptosis_risk: float = 0.0

    # T12 — EventDrivenBurstEngine fields
    last_fired_burst: int = 0

    # T14 — InhibitoryNeuron & Snooze fields
    inhibitory: bool = False
    inhibition_strength: float = 1.0
    max_consecutive_fires: int = 5

    # T10 — CellDifferentiationEngine fields
    cell_type: str = "generic_neuron"
    region: str | None = None
    layer: str | None = None
    differentiation_state: str = "undifferentiated"
    differentiation_score: float = 0.0
    gene_expression: dict = {}
    epigenetic_marks: dict = {}

    # T132 — Linguistic phenotype fields
    phoneme_sensitivity: float = 0.0
    grammatical_role: str = ""
    sequence_buffer: list = []
    comprehension_strength: float = 0.0
    context_window: list = []
    symbol: str | None = None
    assembly_id: str | None = None
    binding_strength: float = 0.0

    # T184 — Periodic table element identifier
    periodic_element_id: Optional[int] = None
    periodic_symbol: Optional[str] = None

    receptor_profile: Optional[ReceptorProfile] = None

    # T-FAG — Functional Activation Gate (lazy on-demand sub-functions)
    functional_activation_gate: FunctionalActivationGate = Field(
        default_factory=FunctionalActivationGate
    )

    # T-COR — Cognitive Objective Reduction microstates
    latent_states: Dict[str, float] = {}
    cor_pressure: float = 0.0
    cor_capacity: float = 0.0
    last_collapse_tick: int = 0

    def get_periodic_element(self):
        """Get the NeuralElement for this neuron's type."""
        from speace_core.cellular_brain.neuroperiodic.neural_element import (
            get_element_by_cell_type,
        )
        if self.periodic_element_id is not None:
            from speace_core.cellular_brain.neuroperiodic.neural_element import (
                build_element,
            )
            return build_element(self.periodic_element_id)
        return get_element_by_cell_type(self.cell_type)

    def predict_synapse_with(self, target: "DigitalNeuron") -> dict:
        """Predict synaptic properties with another neuron."""
        from speace_core.cellular_brain.neuroperiodic.neuroperiodic_integrator import (
            NeuroPeriodicIntegrator,
        )
        integrator = NeuroPeriodicIntegrator()
        return integrator.predict_synapse(self.cell_type, target.cell_type)

    def periodic_classification(self) -> dict:
        """Full periodic classification of this neuron."""
        from speace_core.cellular_brain.neuroperiodic.neuroperiodic_integrator import (
            NeuroPeriodicIntegrator,
        )
        integrator = NeuroPeriodicIntegrator()
        return integrator.classify_cell_type(self.cell_type)

    # T-COR helpers
    def update_latent_states(self, states: Dict[str, float]) -> None:
        """Replace or seed the latent-state superposition for this neuron."""
        if not states:
            return
        total = sum(states.values())
        if total > 0:
            self.latent_states = {k: v / total for k, v in states.items()}
        else:
            self.latent_states = dict(states)

    def add_latent_state(self, label: str, weight: float) -> None:
        """Add or update one latent hypothesis weight, then re-normalise."""
        self.latent_states[label] = max(0.0, min(1.0, weight))
        total = sum(self.latent_states.values())
        if total > 0:
            self.latent_states = {k: v / total for k, v in self.latent_states.items()}

    def dominant_latent_state(self) -> Optional[str]:
        """Return the label with the highest latent weight."""
        if not self.latent_states:
            return None
        return max(self.latent_states, key=self.latent_states.get)

    def latent_entropy(self) -> float:
        """Shannon entropy of the latent-state distribution."""
        import math
        values = list(self.latent_states.values())
        if len(values) < 2:
            return 0.0
        total = sum(values)
        if total <= 0:
            return 0.0
        probs = [v / total for v in values]
        entropy = -sum(p * math.log2(p + 1e-12) for p in probs)
        return entropy / math.log2(len(probs)) if entropy > 0 else 0.0

    def init_receptor_profile(self, profile_type: str = "excitatory") -> None:
        if profile_type == "inhibitory":
            self.receptor_profile = default_inhibitory_neuron_profile(self.cell_id)
        else:
            self.receptor_profile = default_excitatory_neuron_profile(self.cell_id)

    async def receive(self, signal: DigitalSignal) -> None:
        # T-FAG — lazy functional activation on-demand
        self.functional_activation_gate.apply(signal, self)

        if self.receptor_profile is not None and signal.meaning:
            try:
                rt = ReceptorType(signal.meaning)
                mod = self.receptor_profile.bind(rt, signal.strength)
                self.activation += mod
            except (ValueError, KeyError):
                self.activation += signal.strength
        else:
            self.activation += signal.strength

    def tick_wave(self, dt: float = 1.0) -> float:
        """Aggiorna il contributo d'onda del neurone (dualità onda-particella).

        Returns: valore dell'onda in questo tick (usato dal ResonanceField).
        """
        if not self.emit_wave:
            return 0.0

        phase_increment = 2.0 * math.pi * self.wave_frequency * dt / 100.0
        self.wave_phase = (self.wave_phase + phase_increment) % (2.0 * math.pi)
        self.wave_amplitude = max(0.0, self.wave_amplitude - self.wave_damping * dt)

        if self.activation >= self.threshold * 0.7:
            self.wave_amplitude = min(1.0, self.wave_amplitude + 0.1)

        return self.wave_amplitude * math.sin(self.wave_phase)

    def get_wave_state(self) -> dict:
        return {
            "phase": self.wave_phase,
            "amplitude": self.wave_amplitude,
            "frequency": self.wave_frequency,
        }

    async def tick(self) -> List[DigitalSignal]:
        # T9 — handle snooze and refractory
        if self.snooze_counter > 0:
            self.snooze_counter -= 1
            self.activation *= 0.5
            return []
        if self.refractory_counter > 0:
            self.refractory_counter -= 1
            self.activation *= 0.5
            return []

        signals: List[DigitalSignal] = []
        if self.activation >= self.threshold and self.energy > 0.1:
            self.energy = max(0.0, self.energy - 0.05)
            for target_id in self.targets:
                signals.append(
                    DigitalSignal(
                        source=self.cell_id,
                        target=target_id,
                        strength=self.activation,
                    )
                )
            self.activation = 0.0
            self.consecutive_fires += 1
            if self.refractory_period > 0:
                self.refractory_counter = self.refractory_period
        else:
            self.activation *= 0.5
            self.consecutive_fires = 0
        return signals

    def adapt(self, feedback_score: float) -> None:
        self.threshold -= self.plasticity_rate * feedback_score
        self.threshold = max(0.1, min(1.0, self.threshold))
        self.local_memory.append(feedback_score)
        if feedback_score < 0:
            self.error_history.append(feedback_score)






