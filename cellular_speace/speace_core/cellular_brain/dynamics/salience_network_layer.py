"""Salience Network Layer — biologically-inspired attention arbitration.

Aggregates multiple salience sources into a single scalar that drives
downstream switching (DMN ↔ TPN), thalamic gating and global-workspace
attention. This is the SPEACE analog of the brain's salience / ventral
attention network.

Channels:
- interoceptive_salience: internal bodily alarm (energy, stress, damage)
- prediction_error: mismatch between predicted and actual states
- novelty_signal: change in global coherence / dynamics
- neuromodulator_arousal: noradrenergic arousal proxy
- unexpected_event: external salient surprise
"""

from pydantic import BaseModel, ConfigDict, Field

from speace_core.cellular_brain.memory.morphological_memory import MorphologicalMemory
from speace_core.cellular_brain.memory.morphology_events import MorphologyEventType


class SalienceState(BaseModel):
    """Observable state of the salience network."""

    global_salience: float = 0.0
    smoothed_salience: float = 0.0
    dominant_source: str = "none"
    salience_vector: dict[str, float] = Field(default_factory=dict)
    tick: int = 0

    model_config = ConfigDict(arbitrary_types_allowed=True)


class SalienceNetworkLayer:
    """Multi-channel salience integration for SPEACE.

    Combines weighted input channels, applies exponential smoothing, and
    emits a normalized global salience signal in [0, 1]. The signal is
    designed to be consumed by:

    - DMNSwitchingEngine (salience_signal)
    - ThalamicRelayEngine (attention_focus)
    - GlobalWorkspace (attention modulation)
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        ema_alpha: float = 0.3,
        burst_threshold: float = 0.6,
        dip_threshold: float = 0.2,
    ):
        self.weights = weights or {
            "interoceptive_salience": 0.15,
            "prediction_error": 0.40,
            "novelty_signal": 0.15,
            "neuromodulator_arousal": 0.30,
            "unexpected_event": 0.10,
        }
        self.ema_alpha = ema_alpha
        self.burst_threshold = burst_threshold
        self.dip_threshold = dip_threshold

        self.state = SalienceState()
        self._history: list[float] = []

    def tick(
        self,
        interoceptive_salience: float = 0.0,
        prediction_error: float = 0.0,
        novelty_signal: float = 0.0,
        neuromodulator_arousal: float = 0.0,
        unexpected_event: float = 0.0,
        memory: MorphologicalMemory | None = None,
    ) -> SalienceState:
        """Update global salience from multi-channel inputs."""
        raw_vector = {
            "interoceptive_salience": float(interoceptive_salience),
            "prediction_error": float(prediction_error),
            "novelty_signal": float(novelty_signal),
            "neuromodulator_arousal": float(neuromodulator_arousal),
            "unexpected_event": float(unexpected_event),
        }

        # Weighted aggregation, clamped to [0, 1]
        total_weight = sum(self.weights.values())
        weighted_sum = sum(
            self.weights.get(k, 0.0) * max(0.0, v)
            for k, v in raw_vector.items()
        )
        raw_salience = (
            min(1.0, weighted_sum / total_weight) if total_weight > 0.0 else 0.0
        )

        # EMA smoothing to avoid abrupt jumps
        smoothed = (
            self.ema_alpha * raw_salience
            + (1.0 - self.ema_alpha) * self.state.smoothed_salience
        )

        # Identify dominant source by weighted contribution
        contributions = {
            k: self.weights.get(k, 0.0) * max(0.0, v)
            for k, v in raw_vector.items()
        }
        dominant = (
            max(contributions, key=contributions.get)
            if any(v > 0.0 for v in contributions.values())
            else "none"
        )

        previous_smoothed = self.state.smoothed_salience
        self.state.global_salience = round(raw_salience, 6)
        self.state.smoothed_salience = round(smoothed, 6)
        self.state.salience_vector = {
            k: round(v, 6) for k, v in raw_vector.items()
        }
        self.state.dominant_source = dominant
        self.state.tick += 1
        self._history.append(smoothed)

        if memory is not None:
            self._log_salience_events(
                memory, raw_salience, smoothed, previous_smoothed, dominant
            )

        # Return a copy so callers cannot mutate the live internal state
        # and historical snapshots remain valid.
        return self.state.model_copy()

    def _log_salience_events(
        self,
        memory: MorphologicalMemory,
        raw_salience: float,
        smoothed: float,
        previous_smoothed: float,
        dominant: str,
    ) -> None:
        """Log burst/dip/updated events to morphological memory."""
        metadata = {
            "global_salience": round(raw_salience, 6),
            "smoothed_salience": round(smoothed, 6),
            "dominant_source": dominant,
            "salience_vector": dict(self.state.salience_vector),
        }

        if raw_salience >= self.burst_threshold and previous_smoothed < self.burst_threshold:
            memory.create_event(
                event_type=MorphologyEventType.SALIENCE_BURST,
                source_id="salience_network_layer",
                metadata=metadata,
            )
        elif raw_salience <= self.dip_threshold and previous_smoothed > self.dip_threshold:
            memory.create_event(
                event_type=MorphologyEventType.SALIENCE_DIP,
                source_id="salience_network_layer",
                metadata={
                    "global_salience": round(raw_salience, 6),
                    "smoothed_salience": round(smoothed, 6),
                    "dominant_source": dominant,
                },
            )

        if self.state.tick % 10 == 0:
            memory.create_event(
                event_type=MorphologyEventType.SALIENCE_NETWORK_UPDATED,
                source_id="salience_network_layer",
                metadata=metadata,
            )

    def get_global_salience(self) -> float:
        """Return the current smoothed global salience."""
        return self.state.smoothed_salience

    def get_salience_vector(self) -> dict[str, float]:
        """Return the last raw per-channel salience vector."""
        return dict(self.state.salience_vector)

    def get_dominant_source(self) -> str:
        """Return the channel that contributed most to current salience."""
        return self.state.dominant_source

    def get_state(self) -> SalienceState:
        """Return the full observable state."""
        return self.state

    def reset(self) -> None:
        """Reset the layer to its initial state."""
        self.state = SalienceState()
        self._history.clear()
