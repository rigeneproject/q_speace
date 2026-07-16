"""Serotonergic Drive Circuit — biologically-inspired mood/behavioral inhibition.

Provides:
- SerotonergicModulator: models dorsal raphe nucleus (DRN) firing,
  5-HT release, and its effects on inhibition, cognitive flexibility,
  and mood regulation.
- Integration with inhibition engine, exploration drives, and
  long-term stability.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from speace_core.cellular_brain.memory.morphological_memory import MorphologicalMemory
from speace_core.cellular_brain.memory.morphology_events import MorphologyEventType


class SerotoninState(BaseModel):
    serotonin_level: float = 0.5
    drn_firing_rate: float = 0.0
    median_raphe_firing_rate: float = 0.0
    last_rpe_signal: float = 0.0
    burst_count: int = 0
    dip_count: int = 0

    model_config = ConfigDict(arbitrary_types_allowed=True)


class SerotonergicModulator:
    """Biologically-inspired serotonergic modulator.

    The dorsal raphe nucleus (DRN) fires in response to reward/punishment
    outcomes and modulates behavioral inhibition, cognitive flexibility,
    and long-term stability.

    Key effects:
    - High 5-HT → increased behavioral inhibition, reduced impulsivity,
      cognitive persistence
    - Low 5-HT → reduced inhibition, increased impulsivity,
      cognitive flexibility (exploration)
    - Interacts with dopamine: 5-HT / DA balance controls
      exploration/exploitation trade-off
    """

    def __init__(
        self,
        alpha: float = 0.15,
        baseline_serotonin: float = 0.5,
        burst_gain: float = 0.8,
        dip_gain: float = 0.6,
        drn_recovery_rate: float = 0.05,
    ):
        self.alpha = alpha
        self.baseline_serotonin = baseline_serotonin
        self.burst_gain = burst_gain
        self.dip_gain = dip_gain
        self.drn_recovery_rate = drn_recovery_rate

        self.state = SerotoninState(
            serotonin_level=baseline_serotonin,
        )

    def tick(
        self,
        reward_signal: float = 0.0,
        punishment_signal: float = 0.0,
        memory: Optional[MorphologicalMemory] = None,
        source_id: str = "serotonergic_modulator",
        target_id: str = "global_inhibition",
        gut_serotonin: float = 0.0,
    ) -> SerotoninState:
        """Process reward/punishment signals and update serotonin level.

        Serotonin responds primarily to long-term average reward rates
        and punishment signals (opponent to dopamine's short-term RPE).
        ``gut_serotonin`` provides a tonic baseline elevation from the
        gut-brain axis (microbiome-derived 5-HT precursor).
        """
        tonic_floor = max(0.0, gut_serotonin * 0.3)
        net_signal = reward_signal - punishment_signal
        current = self.state.serotonin_level

        smoothed = self.alpha * net_signal + (1.0 - self.alpha) * self.state.last_rpe_signal
        self.state.last_rpe_signal = smoothed

        burst = max(0.0, smoothed) * self.burst_gain
        dip = min(0.0, smoothed) * self.dip_gain

        self.state.drn_firing_rate = burst

        self.state.serotonin_level = max(
            tonic_floor,
            min(1.0, current + burst + dip),
        )

        if burst > 0:
            self.state.burst_count += 1
        elif dip < 0:
            self.state.dip_count += 1

        if memory is not None:
            if burst > 0:
                memory.create_event(
                    event_type=MorphologyEventType.SEROTONIN_BURST,
                    source_id=source_id,
                    target_id=target_id,
                    metadata={
                        "serotonin_level": self.state.serotonin_level,
                        "drn_firing_rate": self.state.drn_firing_rate,
                        "signal": net_signal,
                    },
                )
            elif dip < 0:
                memory.create_event(
                    event_type=MorphologyEventType.SEROTONIN_DIP,
                    source_id=source_id,
                    target_id=target_id,
                    metadata={
                        "serotonin_level": self.state.serotonin_level,
                        "drn_firing_rate": self.state.drn_firing_rate,
                        "signal": net_signal,
                    },
                )

        return self.state

    def get_inhibition_modulation(self) -> float:
        """Return inhibition multiplier based on serotonin level.

        High serotonin → stronger inhibition (multiplier > 1.0)
        Low serotonin → weaker inhibition (multiplier < 1.0)
        """
        return 0.5 + self.state.serotonin_level

    def get_flexibility_modulation(self) -> float:
        """Return cognitive flexibility multiplier.

        High serotonin → lower flexibility (persistence, multiplier < 1.0)
        Low serotonin → higher flexibility (exploration, multiplier > 1.0)
        """
        return 1.5 - self.state.serotonin_level

    def get_persistence_modulation(self) -> float:
        """Return persistence/grit multiplier.

        High serotonin → more persistence (stay on task)
        Low serotonin → less persistence (switch tasks easily)
        """
        return self.state.serotonin_level * 1.5 + 0.25

    def get_state(self) -> SerotoninState:
        return self.state

    def reset(self) -> None:
        self.state = SerotoninState(serotonin_level=self.baseline_serotonin)
