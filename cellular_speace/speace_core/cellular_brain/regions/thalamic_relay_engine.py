"""Thalamic Relay Engine — biologically-inspired thalamocortical hub
   with quantum resonance collapse for attention gating.

The thalamus is a central relay station that:
1. Receives sensory input (except olfaction) and relays it to cortex
2. Receives massive feedback from cortex (corticothalamic projections)
3. Gates information flow through burst vs tonic firing modes
4. Generates oscillatory rhythms through thalamocortical loops
5. Regulates attention via phase coherence collapse (quantum measurement analog)
"""

import math
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from speace_core.cellular_brain.memory.morphological_memory import MorphologicalMemory
from speace_core.cellular_brain.memory.morphology_events import MorphologyEventType


class ThalamicRelayMode(str, Enum):
    BURST = "burst"        # Sleep/inattention — hyperpolarized
    TONIC = "tonic"        # Wake/attention — depolarized, faithful relay
    GATED = "gated"        # Selective attention — some inputs relayed, some blocked
    COLLAPSED = "collapsed"  # Quantum measurement — attention locked to one coherent state


class ThalamicRelayState(BaseModel):
    mode: ThalamicRelayMode = ThalamicRelayMode.TONIC
    gating_level: Dict[str, float] = Field(default_factory=dict)
    cortical_feedback: Dict[str, float] = Field(default_factory=dict)
    relay_gain: float = 1.0
    oscillation_coupling: float = 0.0
    collapsed_loop: Optional[str] = None
    global_phase_coherence: float = 0.0

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ThalamocorticalLoopState(BaseModel):
    loop_id: str = ""
    thalamic_region: str = ""
    cortical_region: str = ""
    coherence: float = 0.0
    phase_difference: float = 0.0
    strength: float = 0.5
    resonance_frequency: float = 10.0
    phase: float = 0.0
    amplitude: float = 0.0

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ThalamicRelayEngine:
    """Thalamic relay hub with corticothalamic feedback loops
       and quantum resonance collapse for attention gating.

    Models the thalamus as a central relay that:
    - Receives and filters sensory/motor signals before cortical relay
    - Is modulated by corticothalamic feedback (top-down attention)
    - Switches between burst (relay-off) and tonic (relay-on) modes
    - Collapses attention when phase coherence exceeds threshold (quantum measurement)
    - Participates in thalamocortical oscillation loops
    """

    def __init__(
        self,
        default_gating: float = 0.8,
        burst_threshold: float = 0.3,
        tonic_threshold: float = 0.6,
        collapse_coherence_threshold: float = 0.7,
        feedback_gain: float = 0.5,
    ):
        self.default_gating = default_gating
        self.burst_threshold = burst_threshold
        self.tonic_threshold = tonic_threshold
        self.collapse_coherence_threshold = collapse_coherence_threshold
        self.feedback_gain = feedback_gain

        self.state = ThalamicRelayState()
        self.loops: Dict[str, ThalamocorticalLoopState] = {}

        self._input_buffer: Dict[str, List[float]] = {}
        self._output_buffer: Dict[str, List[float]] = {}

    # ------------------------------------------------------------------ #
    # Loop management
    # ------------------------------------------------------------------ #

    def register_thalamocortical_loop(
        self,
        loop_id: str,
        thalamic_region: str,
        cortical_region: str,
        resonance_frequency: float = 10.0,
        strength: float = 0.5,
    ) -> None:
        """Register a thalamocortical resonance loop."""
        self.loops[loop_id] = ThalamocorticalLoopState(
            loop_id=loop_id,
            thalamic_region=thalamic_region,
            cortical_region=cortical_region,
            resonance_frequency=resonance_frequency,
            strength=strength,
        )
        self._input_buffer[loop_id] = []
        self._output_buffer[loop_id] = []

    def unregister_loop(self, loop_id: str) -> None:
        self.loops.pop(loop_id, None)
        self._input_buffer.pop(loop_id, None)
        self._output_buffer.pop(loop_id, None)

    # ------------------------------------------------------------------ #
    # Signal I/O
    # ------------------------------------------------------------------ #

    def receive_signal(self, loop_id: str, signal: float) -> None:
        """Queue an incoming signal for a thalamocortical loop."""
        if loop_id in self._input_buffer:
            self._input_buffer[loop_id].append(signal)

    def receive_cortical_feedback(self, loop_id: str, feedback: float) -> None:
        """Receive top-down feedback from cortex for a loop."""
        if loop_id in self.loops:
            current = self.state.cortical_feedback.get(loop_id, 0.0)
            self.state.cortical_feedback[loop_id] = current * 0.7 + feedback * 0.3

    def emit_signal(self, loop_id: str) -> List[float]:
        """Retrieve and clear the output buffer for a loop."""
        output = self._output_buffer.get(loop_id, []).copy()
        self._output_buffer[loop_id] = []
        return output

    # ------------------------------------------------------------------ #
    # Main tick
    # ------------------------------------------------------------------ #

    def update_loop_phase(
        self, loop_id: str, phase: float, amplitude: float
    ) -> None:
        if loop_id in self.loops:
            self.loops[loop_id].phase = phase
            self.loops[loop_id].amplitude = amplitude

    def compute_global_phase_coherence(self) -> float:
        if not self.loops:
            return 0.0
        sin_sum = sum(math.sin(l.phase) * l.amplitude for l in self.loops.values())
        cos_sum = sum(math.cos(l.phase) * l.amplitude for l in self.loops.values())
        total_amp = sum(l.amplitude for l in self.loops.values()) + 1e-12
        return math.sqrt(sin_sum**2 + cos_sum**2) / total_amp

    def tick(
        self,
        global_arousal: float = 1.0,
        attention_focus: float = 0.5,
        cholinergic_level: float = 0.5,
        noradrenergic_level: float = 0.3,
        memory: Optional[MorphologicalMemory] = None,
    ) -> ThalamicRelayState:
        """Process one tick of thalamic relay and gating with quantum collapse.

        Determines relay mode based on arousal, attention, and phase coherence:
        - Low arousal + low attention → BURST mode (sleep-like)
        - Moderate arousal + moderate attention → TONIC mode
        - High arousal + focused attention → GATED mode
        - Very high phase coherence → COLLAPSED mode (quantum measurement analog)
        """
        arousal_attention = global_arousal * attention_focus

        self.state.global_phase_coherence = self.compute_global_phase_coherence()

        if self.state.global_phase_coherence > self.collapse_coherence_threshold and arousal_attention > self.tonic_threshold:
            self.state.mode = ThalamicRelayMode.COLLAPSED
            self.state.relay_gain = 1.0
            best_loop = max(
                self.loops.items(),
                key=lambda kv: kv[1].amplitude * kv[1].coherence,
            )[0] if self.loops else None
            self.state.collapsed_loop = best_loop
        elif arousal_attention < self.burst_threshold:
            self.state.mode = ThalamicRelayMode.BURST
            self.state.relay_gain = 0.2
            self.state.collapsed_loop = None
        elif arousal_attention < self.tonic_threshold:
            self.state.mode = ThalamicRelayMode.TONIC
            self.state.relay_gain = 0.8 + cholinergic_level * 0.2
            self.state.collapsed_loop = None
        else:
            self.state.mode = ThalamicRelayMode.GATED
            self.state.relay_gain = 0.5 + attention_focus * 0.5
            self.state.collapsed_loop = None

        # Process each thalamocortical loop
        for loop_id, loop in self.loops.items():
            inputs = self._input_buffer.get(loop_id, [])
            feedback = self.state.cortical_feedback.get(loop_id, 0.0)

            phase_diff = loop.phase_difference
            phase_modulator = max(0.0, 1.0 - phase_diff / math.pi)

            gating = self.default_gating - feedback * self.feedback_gain * attention_focus
            gating = gating * (0.5 + 0.5 * phase_modulator)
            gating = max(0.0, min(1.0, gating))
            self.state.gating_level[loop_id] = gating

            if self.state.mode == ThalamicRelayMode.BURST:
                outputs = [0.0] * len(inputs)
            elif self.state.mode == ThalamicRelayMode.COLLAPSED:
                if loop_id == self.state.collapsed_loop:
                    outputs = [inp * self.state.relay_gain * phase_modulator for inp in inputs]
                else:
                    outputs = [inp * 0.1 * phase_modulator for inp in inputs]
            elif self.state.mode == ThalamicRelayMode.GATED:
                outputs = [
                    inp * self.state.relay_gain * gating * phase_modulator
                    for inp in inputs
                ]
            else:
                outputs = [
                    inp * self.state.relay_gain * phase_modulator
                    for inp in inputs
                ]

            self._output_buffer[loop_id] = outputs
            self._input_buffer[loop_id] = []

            if outputs:
                mean_output = sum(abs(o) for o in outputs) / len(outputs) if outputs else 0.0
                loop.coherence = min(
                    1.0,
                    mean_output * (1.0 + feedback * 0.5) * (0.5 + 0.5 * phase_modulator)
                )

            loop.phase_difference = max(0.0, loop.phase_difference - 0.05 * (1.0 + feedback))

        self.state.oscillation_coupling = (
            cholinergic_level * 0.3 + noradrenergic_level * 0.2
        )

        if memory is not None:
            for loop_id in self.loops:
                loop = self.loops[loop_id]
                memory.create_event(
                    event_type=MorphologyEventType.THALAMIC_RELAY,
                    source_id=f"thalamus_{loop_id}",
                    target_id=f"cortex_{loop_id}",
                    metadata={
                        "mode": self.state.mode.value,
                        "relay_gain": self.state.relay_gain,
                        "gating": self.state.gating_level.get(loop_id, 0.0),
                        "coherence": loop.coherence,
                        "phase_diff": loop.phase_difference,
                        "collapsed": self.state.collapsed_loop == loop_id,
                    },
                )
            if self.state.mode == ThalamicRelayMode.GATED:
                for loop_id, gating in self.state.gating_level.items():
                    if gating < 0.5:
                        memory.create_event(
                            event_type=MorphologyEventType.THALAMIC_GATE,
                            source_id=f"thalamus_{loop_id}",
                            target_id=f"cortex_{loop_id}",
                            metadata={
                                "gating": gating,
                                "feedback": self.state.cortical_feedback.get(loop_id, 0.0),
                            },
                        )

        return self.state

    def get_state(self) -> ThalamicRelayState:
        return self.state

    def get_loop_coherence(self, loop_id: str) -> float:
        if loop_id in self.loops:
            return self.loops[loop_id].coherence
        return 0.0

    def reset(self) -> None:
        self.state = ThalamicRelayState()
        self._input_buffer = {lid: [] for lid in self.loops}
        self._output_buffer = {lid: [] for lid in self.loops}
