"""Noradrenergic Drive Circuit — biologically-inspired arousal/vigilance.

Provides:
- NoradrenergicModulator: models locus coeruleus (LC) firing modes
  (phasic vs tonic) and norepinephrine (NE) effects on arousal,
  vigilance, attention focus, and stress response.
- Three modes: phasic (focused attention), tonic (distracted scanning),
  hyper (stress/fight-or-flight).
"""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from speace_core.cellular_brain.memory.morphological_memory import MorphologicalMemory
from speace_core.cellular_brain.memory.morphology_events import MorphologyEventType


class LCMode(str, Enum):
    PHASIC = "phasic"
    TONIC = "tonic"
    HYPER = "hyper"


class NoradrenalineState(BaseModel):
    noradrenaline_level: float = 0.3
    lc_firing_rate: float = 0.0
    lc_mode: LCMode = LCMode.TONIC
    arousal_level: float = 0.3
    stress_level: float = 0.0
    burst_count: int = 0
    dip_count: int = 0

    model_config = ConfigDict(arbitrary_types_allowed=True)


class NoradrenergicModulator:
    """Biologically-inspired noradrenergic modulator.

    The locus coeruleus (LC) is the primary source of norepinephrine (NE)
    in the brain. It operates in three modes:

    1. **Phasic mode**: LC fires in bursts to salient stimuli → focused
       attention, optimal performance (Yerkes-Dodson peak)
    2. **Tonic mode**: LC fires at moderate baseline → scanning,
       distractible, exploratory
    3. **Hyper mode**: LC fires at very high rate → stress, hypervigilance,
       impaired cognition (Yerkes-Dodson decline)

    NE effects:
    - Modulates signal-to-noise ratio in cortex
    - Regulates arousal and vigilance
    - Gates attention focus (phasic) vs exploration (tonic)
    - Triggers stress responses at high levels
    """

    def __init__(
        self,
        alpha: float = 0.3,
        baseline_noradrenaline: float = 0.3,
        phasic_gain: float = 1.5,
        tonic_gain: float = 0.6,
        stress_threshold: float = 0.7,
        recovery_rate: float = 0.04,
    ):
        self.alpha = alpha
        self.baseline_noradrenaline = baseline_noradrenaline
        self.phasic_gain = phasic_gain
        self.tonic_gain = tonic_gain
        self.stress_threshold = stress_threshold
        self.recovery_rate = recovery_rate

        self.state = NoradrenalineState(
            noradrenaline_level=baseline_noradrenaline,
        )

    def tick(
        self,
        salient_stimulus: float = 0.0,
        unexpected_event: float = 0.0,
        cognitive_load: float = 0.0,
        memory: Optional[MorphologicalMemory] = None,
        source_id: str = "noradrenergic_modulator",
        target_id: str = "cortical_arousal",
    ) -> NoradrenalineState:
        """Update LC firing mode and NE level based on inputs.

        Salient/unexpected events trigger phasic bursts.
        Sustained cognitive load without salient events maintains
        tonic mode. High stress pushes to hyper mode.
        """
        total_input = salient_stimulus + unexpected_event

        self.state.stress_level = max(
            0.0, min(1.0, self.state.stress_level + cognitive_load * 0.1 - self.recovery_rate)
        )

        if self.state.stress_level > self.stress_threshold:
            self.state.lc_mode = LCMode.HYPER
            lc_firing = self.state.stress_level * 2.0
        elif total_input > 0.3:
            self.state.lc_mode = LCMode.PHASIC
            lc_firing = total_input * self.phasic_gain
        else:
            self.state.lc_mode = LCMode.TONIC
            lc_firing = self.tonic_gain * (0.3 + cognitive_load * 0.3)

        self.state.lc_firing_rate = lc_firing

        delta = lc_firing * 0.2 - self.recovery_rate * (
            self.state.noradrenaline_level - self.baseline_noradrenaline
        )
        self.state.noradrenaline_level = max(
            0.0,
            min(1.0, self.state.noradrenaline_level + delta),
        )

        self.state.arousal_level = self.state.noradrenaline_level

        if total_input > 0.3:
            self.state.burst_count += 1
        elif total_input < 0.0:
            self.state.dip_count += 1

        if memory is not None:
            if self.state.lc_mode == LCMode.HYPER:
                memory.create_event(
                    event_type=MorphologyEventType.NORADRENALINE_BURST,
                    source_id=source_id,
                    target_id=target_id,
                    metadata={
                        "noradrenaline_level": self.state.noradrenaline_level,
                        "lc_mode": self.state.lc_mode.value,
                        "stress_level": self.state.stress_level,
                        "lc_firing_rate": self.state.lc_firing_rate,
                    },
                )
            elif self.state.lc_mode == LCMode.PHASIC:
                memory.create_event(
                    event_type=MorphologyEventType.NORADRENALINE_BURST,
                    source_id=source_id,
                    target_id=target_id,
                    metadata={
                        "noradrenaline_level": self.state.noradrenaline_level,
                        "lc_mode": self.state.lc_mode.value,
                        "salient_stimulus": salient_stimulus,
                    },
                )
            elif self.state.noradrenaline_level < self.baseline_noradrenaline * 0.8:
                memory.create_event(
                    event_type=MorphologyEventType.NORADRENALINE_DIP,
                    source_id=source_id,
                    target_id=target_id,
                    metadata={
                        "noradrenaline_level": self.state.noradrenaline_level,
                        "lc_mode": self.state.lc_mode.value,
                    },
                )

        return self.state

    def get_arousal_modulation(self) -> float:
        """Return arousal multiplier based on Yerkes-Dodson curve.

        Optimal performance at moderate NE (phasic mode).
        Impaired at very low (tonic) and very high (hyper).
        """
        ne = self.state.noradrenaline_level
        return max(0.0, 4.0 * ne * (1.0 - ne))

    def get_focus_modulation(self) -> float:
        """Return attention focus multiplier.

        Phasic mode → high focus
        Tonic mode → low focus (distractible)
        Hyper mode → very low focus (hypervigilant, scattered)
        """
        if self.state.lc_mode == LCMode.PHASIC:
            return 1.0 + self.state.noradrenaline_level * 0.5
        if self.state.lc_mode == LCMode.HYPER:
            return max(0.2, 1.0 - self.state.noradrenaline_level * 0.8)
        return 0.5 + self.state.noradrenaline_level * 0.3

    def get_exploration_modulation(self) -> float:
        """Return exploration drive multiplier.

        Tonic mode → high exploration
        Phasic mode → low exploration (exploit)
        Hyper mode → very low exploration
        """
        if self.state.lc_mode == LCMode.TONIC:
            return 1.5 - self.state.noradrenaline_level
        if self.state.lc_mode == LCMode.HYPER:
            return max(0.1, 0.5 - self.state.stress_level * 0.5)
        return max(0.2, 1.0 - self.state.noradrenaline_level)

    def get_plasticity_gate(self) -> tuple[bool, str]:
        """Return whether plasticity should be enabled.

        Moderate NE enables plasticity (optimal learning).
        Very low or very high NE suppresses plasticity.
        """
        ne = self.state.noradrenaline_level
        if 0.25 <= ne <= 0.75:
            return True, "moderate_ne_enables_plasticity"
        if ne > 0.75:
            return False, "high_ne_stress_suppresses_plasticity"
        return False, "low_ne_suppresses_plasticity"

    def get_state(self) -> NoradrenalineState:
        return self.state

    def reset(self) -> None:
        self.state = NoradrenalineState(noradrenaline_level=self.baseline_noradrenaline)
