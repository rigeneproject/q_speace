"""DMN Switching Engine — Default Mode Network ↔ Task-Positive switching.

Implements the competitive dynamics between:
1. Default Mode Network (DMN): introspection, autobiographical memory,
   future planning, mind-wandering, social cognition
2. Task-Positive Network (TPN): externally-focused attention,
   executive control, working memory, goal-directed behavior

Switching is controlled by:
- Noradrenergic tone (LC phasic → TPN, LC tonic → DMN)
- Cholinergic tone (high ACh → TPN, low ACh → DMN)
- Cognitive demand
- Salience network detection of important stimuli
"""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from speace_core.cellular_brain.memory.morphological_memory import MorphologicalMemory
from speace_core.cellular_brain.memory.morphology_events import MorphologyEventType


class ActiveNetwork(str, Enum):
    DMN = "dmn"
    TPN = "tpn"
    TRANSITIONING = "transitioning"
    COACTIVATED = "coactivated"


class DMNSwitchingState(BaseModel):
    active_network: ActiveNetwork = ActiveNetwork.DMN
    dmn_activation: float = 0.5
    tpn_activation: float = 0.3
    switching_progress: float = 0.0
    cognitive_demand: float = 0.0
    salience_signal: float = 0.0
    switch_count: int = 0
    model_config = ConfigDict(arbitrary_types_allowed=True)


class DMNSwitchingEngine:
    """Controls the competitive switching between DMN and TPN networks.

    The DMN and TPN are mutually inhibitory: when one is active,
    the other is suppressed. The salience network detects important
    stimuli and triggers switching between them.

    Switching dynamics:
    - Low cognitive demand + low salience → DMN active
    - High cognitive demand + high salience → TPN active
    - Sustained attention demand → gradual shift to TPN
    - Rest/boredom → gradual shift to DMN
    """

    def __init__(
        self,
        switch_rate: float = 0.05,
        dmn_baseline: float = 0.5,
        tpn_baseline: float = 0.3,
        cognitive_threshold: float = 0.4,
        salience_threshold: float = 0.3,
        mutual_inhibition_strength: float = 0.6,
    ):
        self.switch_rate = switch_rate
        self.dmn_baseline = dmn_baseline
        self.tpn_baseline = tpn_baseline
        self.cognitive_threshold = cognitive_threshold
        self.salience_threshold = salience_threshold
        self.mutual_inhibition_strength = mutual_inhibition_strength

        self.state = DMNSwitchingState()

    def tick(
        self,
        cognitive_demand: float = 0.0,
        salience_signal: float = 0.0,
        noradrenaline_level: float = 0.3,
        acetylcholine_level: float = 0.5,
        memory: Optional[MorphologicalMemory] = None,
    ) -> DMNSwitchingState:
        """Update DMN/TPN activation levels and determine active network.

        DMN activation increases with:
        - Low cognitive demand
        - Low salience
        - Tonic LC mode (low NE)
        - Low ACh

        TPN activation increases with:
        - High cognitive demand
        - High salience
        - Phasic LC mode (moderate NE)
        - High ACh
        """
        self.state.cognitive_demand = cognitive_demand
        self.state.salience_signal = salience_signal

        ne_drive = noradrenaline_level
        ach_drive = acetylcholine_level

        dmn_input = (
            (1.0 - cognitive_demand) * 0.4
            + (1.0 - salience_signal) * 0.3
            + (1.0 - ne_drive) * 0.15
            + (1.0 - ach_drive) * 0.15
        )

        tpn_input = (
            cognitive_demand * 0.3
            + salience_signal * 0.3
            + ne_drive * 0.2
            + ach_drive * 0.2
        )

        # Mutual inhibition
        dmn_net = dmn_input - self.state.tpn_activation * self.mutual_inhibition_strength
        tpn_net = tpn_input - self.state.dmn_activation * self.mutual_inhibition_strength

        # Smooth integration
        self.state.dmn_activation = max(
            0.0, min(1.0, self.state.dmn_activation + dmn_net * self.switch_rate)
        )
        self.state.tpn_activation = max(
            0.0, min(1.0, self.state.tpn_activation + tpn_net * self.switch_rate)
        )

        previous = self.state.active_network

        # Determine dominant network
        if abs(self.state.dmn_activation - self.state.tpn_activation) < 0.15:
            self.state.active_network = ActiveNetwork.COACTIVATED
            self.state.switching_progress = 0.5
        elif self.state.dmn_activation > self.state.tpn_activation:
            if previous != ActiveNetwork.DMN:
                self.state.switch_count += 1
            self.state.active_network = ActiveNetwork.DMN
            self.state.switching_progress = 0.0
        else:
            if previous != ActiveNetwork.TPN:
                self.state.switch_count += 1
            self.state.active_network = ActiveNetwork.TPN
            self.state.switching_progress = 1.0

        if memory is not None:
            if self.state.active_network == ActiveNetwork.DMN and previous != ActiveNetwork.DMN:
                memory.create_event(
                    event_type=MorphologyEventType.DMN_ACTIVATED,
                    source_id="dmn_switching_engine",
                    target_id="default_mode",
                    metadata={
                        "dmn_activation": self.state.dmn_activation,
                        "tpn_activation": self.state.tpn_activation,
                        "cognitive_demand": cognitive_demand,
                        "salience_signal": salience_signal,
                    },
                )
            elif self.state.active_network == ActiveNetwork.TPN and previous != ActiveNetwork.TPN:
                memory.create_event(
                    event_type=MorphologyEventType.TASK_POSITIVE_NETWORK_ACTIVATED,
                    source_id="dmn_switching_engine",
                    target_id="prefrontal",
                    metadata={
                        "dmn_activation": self.state.dmn_activation,
                        "tpn_activation": self.state.tpn_activation,
                        "cognitive_demand": cognitive_demand,
                        "salience_signal": salience_signal,
                    },
                )

        return self.state

    def get_network_ratio(self) -> float:
        """Return the DMN/TPN activation ratio.

        > 1.0 → DMN dominant
        < 1.0 → TPN dominant
        """
        tpn = max(0.001, self.state.tpn_activation)
        return self.state.dmn_activation / tpn

    def get_dmn_modulation(self) -> float:
        """Return DMN activity as a modulation factor for introspection/consolidation."""
        return self.state.dmn_activation

    def get_tpn_modulation(self) -> float:
        """Return TPN activity as a modulation factor for executive function."""
        return self.state.tpn_activation

    def is_dmn_active(self) -> bool:
        return self.state.active_network in (ActiveNetwork.DMN, ActiveNetwork.COACTIVATED)

    def is_tpn_active(self) -> bool:
        return self.state.active_network in (ActiveNetwork.TPN, ActiveNetwork.COACTIVATED)

    def get_state(self) -> DMNSwitchingState:
        return self.state

    def reset(self) -> None:
        self.state = DMNSwitchingState()
