"""Cholinergic Drive Circuit — biologically-inspired attention/learning.

Provides:
- CholinergicModulator: models basal forebrain (nBM) and
  pedunculopontine nucleus (PPN) acetylcholine release, and its
  effects on attention, learning rate, and memory encoding.
- Integration with plasticity, global workspace attention, and
  cortical activation.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from speace_core.cellular_brain.memory.morphological_memory import MorphologicalMemory
from speace_core.cellular_brain.memory.morphology_events import MorphologyEventType


class AcetylcholineState(BaseModel):
    acetylcholine_level: float = 0.5
    basal_forebrain_firing: float = 0.0
    ppn_firing_rate: float = 0.0
    novelty_signal: float = 0.0
    burst_count: int = 0
    dip_count: int = 0

    model_config = ConfigDict(arbitrary_types_allowed=True)


class CholinergicModulator:
    """Biologically-inspired cholinergic modulator.

    The basal forebrain (nucleus basalis of Meynert) releases
    acetylcholine (ACh) widely to the cortex, modulating:

    - Attention: ACh enhances signal-to-noise ratio in cortical
      processing by strengthening strong inputs and suppressing weak ones
    - Learning rate: ACh gates plasticity, enabling encoding of new
      memories
    - Cortical activation: ACh promotes desynchronized EEG (awake,
      attentive state)

    The pedunculopontine nucleus (PPN) provides additional ACh to
    the thalamus and basal ganglia, modulating arousal and
    action selection.
    """

    def __init__(
        self,
        alpha: float = 0.2,
        baseline_acetylcholine: float = 0.5,
        novelty_gain: float = 1.0,
        attention_gain: float = 1.0,
        decay_rate: float = 0.03,
    ):
        self.alpha = alpha
        self.baseline_acetylcholine = baseline_acetylcholine
        self.novelty_gain = novelty_gain
        self.attention_gain = attention_gain
        self.decay_rate = decay_rate

        self.state = AcetylcholineState(
            acetylcholine_level=baseline_acetylcholine,
        )

    def tick(
        self,
        novelty_signal: float = 0.0,
        attention_demand: float = 0.0,
        memory: Optional[MorphologicalMemory] = None,
        source_id: str = "cholinergic_modulator",
        target_id: str = "cortical_attention",
    ) -> AcetylcholineState:
        """Process novelty and attention signals, update ACh level.

        ACh rises with novelty and attention demand, then decays
        back to baseline when stimuli are familiar or ignored.
        """
        novelty = novelty_signal * self.novelty_gain
        attention = attention_demand * self.attention_gain

        # Basal forebrain firing tracks the combined signal
        combined = novelty + attention
        self.state.basal_forebrain_firing = combined
        self.state.ppn_firing_rate = attention * 0.5

        # Update ACh level: rise with input, decay toward baseline
        delta = combined * (1.0 - self.state.acetylcholine_level) - self.decay_rate * (
            self.state.acetylcholine_level - self.baseline_acetylcholine
        )
        self.state.acetylcholine_level = max(
            0.0,
            min(1.0, self.state.acetylcholine_level + delta),
        )
        self.state.novelty_signal = novelty

        if novelty > 0.05:
            self.state.burst_count += 1
        elif novelty < -0.05:
            self.state.dip_count += 1

        if memory is not None:
            if novelty > 0.05:
                memory.create_event(
                    event_type=MorphologyEventType.ACETYLCHOLINE_RELEASED,
                    source_id=source_id,
                    target_id=target_id,
                    metadata={
                        "acetylcholine_level": self.state.acetylcholine_level,
                        "basal_forebrain_firing": self.state.basal_forebrain_firing,
                        "novelty": novelty,
                        "attention": attention,
                    },
                )
            elif novelty < -0.05:
                memory.create_event(
                    event_type=MorphologyEventType.ACETYLCHOLINE_DIP,
                    source_id=source_id,
                    target_id=target_id,
                    metadata={
                        "acetylcholine_level": self.state.acetylcholine_level,
                        "basal_forebrain_firing": self.state.basal_forebrain_firing,
                    },
                )

        return self.state

    def get_attention_modulation(self) -> float:
        """Return attention/signal-to-noise multiplier.

        High ACh → sharpened attention, higher contrast
        Low ACh → diffuse attention, lower contrast
        """
        return 0.5 + self.state.acetylcholine_level

    def get_plasticity_gate(self) -> tuple[bool, str]:
        """Return whether learning should be enabled.

        ACh gates hippocampal and cortical plasticity.
        Moderate-to-high ACh enables learning.
        """
        if self.state.acetylcholine_level > 0.55:
            return True, "high_ach_enables_plasticity"
        if self.state.acetylcholine_level > 0.35:
            return True, "moderate_ach_allows_plasticity"
        return False, "low_ach_suppresses_plasticity"

    def get_cortical_activation_modulation(self) -> float:
        """Return cortical activation/arousal multiplier.

        High ACh → high cortical activation (desynchronized)
        Low ACh → low cortical activation (synchronized/sleepy)
        """
        return self.state.acetylcholine_level * 1.2 + 0.3

    def get_state(self) -> AcetylcholineState:
        return self.state

    def reset(self) -> None:
        self.state = AcetylcholineState(acetylcholine_level=self.baseline_acetylcholine)
