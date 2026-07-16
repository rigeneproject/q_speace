import pytest

from speace_core.cellular_brain.dynamics.salience_network_layer import (
    SalienceNetworkLayer,
    SalienceState,
)
from speace_core.cellular_brain.memory.morphological_memory import MorphologicalMemory
from speace_core.cellular_brain.memory.morphology_events import MorphologyEventType


def test_zero_input_yields_low_salience():
    layer = SalienceNetworkLayer()
    state = layer.tick()
    assert isinstance(state, SalienceState)
    assert 0.0 <= state.global_salience < 0.1
    assert 0.0 <= state.smoothed_salience < 0.1
    assert state.dominant_source == "none"


def test_prediction_error_raises_salience():
    layer = SalienceNetworkLayer()
    state = layer.tick(prediction_error=1.0)
    assert state.global_salience > 0.3
    assert state.dominant_source == "prediction_error"


def test_high_noradrenaline_increases_salience():
    layer = SalienceNetworkLayer()
    state = layer.tick(neuromodulator_arousal=0.9)
    assert state.global_salience > 0.15
    assert state.dominant_source == "neuromodulator_arousal"


def test_interoceptive_and_novelty_contribute():
    layer = SalienceNetworkLayer()
    state = layer.tick(
        interoceptive_salience=0.8,
        novelty_signal=0.8,
        unexpected_event=0.5,
    )
    assert state.global_salience > 0.2
    assert state.dominant_source in ("interoceptive_salience", "novelty_signal")


def test_ema_smoothing_reduces_jump():
    layer = SalienceNetworkLayer(ema_alpha=0.3)
    s1 = layer.tick(prediction_error=1.0)
    s2 = layer.tick(prediction_error=0.0)
    # After a strong signal then zero, smoothed salience should remain
    # positive but lower than the raw peak.
    assert s2.smoothed_salience < s1.global_salience
    assert s2.smoothed_salience > 0.0


def test_burst_event_logged():
    layer = SalienceNetworkLayer()
    memory = MorphologicalMemory()
    layer.tick(
        prediction_error=1.0,
        neuromodulator_arousal=1.0,
        unexpected_event=1.0,
        memory=memory,
    )
    types = [e.event_type for e in memory.events]
    assert MorphologyEventType.SALIENCE_BURST in types


def test_dip_event_logged():
    layer = SalienceNetworkLayer()
    memory = MorphologicalMemory()
    # First establish a high smoothed salience using multiple channels
    layer.tick(
        prediction_error=1.0,
        interoceptive_salience=1.0,
        novelty_signal=1.0,
        neuromodulator_arousal=1.0,
        unexpected_event=1.0,
        memory=memory,
    )
    # Then drop to zero to trigger a dip transition
    layer.tick(memory=memory)
    types = [e.event_type for e in memory.events]
    assert MorphologyEventType.SALIENCE_DIP in types


def test_updated_event_logged_every_ten_ticks():
    layer = SalienceNetworkLayer()
    memory = MorphologicalMemory()
    for _ in range(10):
        layer.tick(prediction_error=0.5, memory=memory)
    types = [e.event_type for e in memory.events]
    assert MorphologyEventType.SALIENCE_NETWORK_UPDATED in types


def test_reset_clears_state():
    layer = SalienceNetworkLayer()
    layer.tick(prediction_error=1.0)
    assert layer.get_global_salience() > 0.0
    layer.reset()
    assert layer.get_global_salience() == 0.0
    assert layer.get_dominant_source() == "none"


def test_custom_weights_change_behavior():
    layer = SalienceNetworkLayer(
        weights={
            "interoceptive_salience": 0.0,
            "prediction_error": 0.0,
            "novelty_signal": 0.0,
            "neuromodulator_arousal": 1.0,
            "unexpected_event": 0.0,
        }
    )
    state = layer.tick(neuromodulator_arousal=0.5)
    assert state.global_salience == pytest.approx(0.5, abs=1e-6)
    assert state.dominant_source == "neuromodulator_arousal"
