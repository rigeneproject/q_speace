"""GABAergic Modulator — biologically-inspired diffuse inhibition.

Provides:
- GABAergicModulator: models the diffuse GABAergic inhibitory system
  that regulates neural synchrony, oscillation gating, and noise
  suppression through tonic and phasic inhibition.
- Integration with oscillation phase coupling, noise suppression,
  and seizure prevention.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from speace_core.cellular_brain.memory.morphological_memory import MorphologicalMemory
from speace_core.cellular_brain.memory.morphology_events import MorphologyEventType


class GABAState(BaseModel):
    gaba_level: float = 0.5
    tonic_inhibition: float = 0.3
    phasic_inhibition: float = 0.0
    interneuron_activity: float = 0.0
    oscillation_gating: float = 0.5
    burst_count: int = 0

    model_config = ConfigDict(arbitrary_types_allowed=True)


class GABAergicModulator:
    """Biologically-inspired GABAergic modulator.

    GABA (gamma-aminobutyric acid) is the primary inhibitory
    neurotransmitter in the brain. It acts through:

    1. **Tonic inhibition**: sustained, low-level inhibition that
       sets the baseline excitability of neural circuits
    2. **Phasic inhibition**: transient, synapse-specific inhibition
       that follows excitatory input, providing feedback control
    3. **Oscillation gating**: GABAergic interneurons pace network
       oscillations by rhythmically inhibiting principal cells,
       creating temporal windows for synchrony

    Key effects:
    - Prevents runaway excitation (seizure prevention)
    - Shapes oscillatory rhythms (theta, gamma)
    - Controls gain of cortical processing
    - Regulates signal-to-noise ratio
    """

    def __init__(
        self,
        baseline_gaba: float = 0.5,
        tonic_level: float = 0.3,
        interneuron_gain: float = 1.0,
        recovery_rate: float = 0.05,
        excitation_threshold: float = 0.6,
    ):
        self.baseline_gaba = baseline_gaba
        self.tonic_level = tonic_level
        self.interneuron_gain = interneuron_gain
        self.recovery_rate = recovery_rate
        self.excitation_threshold = excitation_threshold

        self.state = GABAState(
            gaba_level=baseline_gaba,
            tonic_inhibition=tonic_level,
        )

    def tick(
        self,
        mean_excitation: float = 0.0,
        oscillation_energy: float = 0.0,
        seizure_risk: float = 0.0,
        memory: Optional[MorphologicalMemory] = None,
        source_id: str = "gabaergic_modulator",
        target_id: str = "global_inhibition",
    ) -> GABAState:
        """Update GABA levels based on excitation and oscillation energy.

        High excitation → increased phasic GABA (negative feedback).
        High oscillation energy → phase-locked GABA gating.
        Seizure risk → emergency GABA boost.
        """
        if mean_excitation > self.excitation_threshold:
            phasic = (mean_excitation - self.excitation_threshold) * self.interneuron_gain
        else:
            phasic = 0.0

        self.state.phasic_inhibition = phasic
        self.state.interneuron_activity = phasic + self.tonic_level

        gaba_increase = phasic * 0.3 + seizure_risk * 0.5
        gaba_decay = self.recovery_rate * (self.state.gaba_level - self.baseline_gaba)

        self.state.gaba_level = max(
            0.0,
            min(1.0, self.state.gaba_level + gaba_increase - gaba_decay),
        )

        self.state.oscillation_gating = max(
            0.0, min(1.0, 0.5 + oscillation_energy * 0.3 - self.state.gaba_level * 0.2)
        )

        if phasic > 0.1:
            self.state.burst_count += 1

        if memory is not None:
            if seizure_risk > 0.5:
                memory.create_event(
                    event_type=MorphologyEventType.GABA_RELEASED,
                    source_id=source_id,
                    target_id=target_id,
                    metadata={
                        "gaba_level": self.state.gaba_level,
                        "seizure_risk": seizure_risk,
                        "phasic_inhibition": self.state.phasic_inhibition,
                    },
                )
            elif phasic > 0.05:
                memory.create_event(
                    event_type=MorphologyEventType.GABA_RELEASED,
                    source_id=source_id,
                    target_id=target_id,
                    metadata={
                        "gaba_level": self.state.gaba_level,
                        "tonic_inhibition": self.state.tonic_inhibition,
                        "phasic_inhibition": self.state.phasic_inhibition,
                    },
                )
            elif self.state.gaba_level < self.baseline_gaba * 0.7:
                memory.create_event(
                    event_type=MorphologyEventType.GABA_SUPPRESSED,
                    source_id=source_id,
                    target_id=target_id,
                    metadata={
                        "gaba_level": self.state.gaba_level,
                        "mean_excitation": mean_excitation,
                    },
                )

        return self.state

    def get_inhibition_multiplier(self) -> float:
        """Return global inhibition multiplier.

        Higher GABA → stronger inhibition across all synapses.
        """
        return 0.5 + self.state.gaba_level * 0.5

    def get_noise_suppression(self) -> float:
        """Return noise suppression factor.

        Higher GABA → more noise suppression (cleaner signal).
        """
        return 0.3 + self.state.gaba_level * 0.7

    def get_oscillation_gating(self) -> float:
        """Return oscillation gating factor.

        Determines how strongly GABA shapes oscillatory rhythms.
        """
        return self.state.oscillation_gating

    def get_excitability_modulation(self) -> float:
        """Return neuronal excitability multiplier.

        Higher GABA → lower excitability.
        """
        return 1.0 - self.state.gaba_level * 0.5

    def get_state(self) -> GABAState:
        return self.state

    def reset(self) -> None:
        self.state = GABAState(gaba_level=self.baseline_gaba)
