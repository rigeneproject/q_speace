"""Tests for PhysioNeuralTransducer."""
import numpy as np
import pytest
from speace_core.cellular_brain.embodiment.physio_neural_transducer import (
    PhysioNeuralTransducer,
    SignalType,
    TransductionConfig,
)


@pytest.fixture
def transducer():
    return PhysioNeuralTransducer()


class TestTransductionConfig:
    def test_default_for_audio(self):
        config = TransductionConfig.default_for(SignalType.AUDIO)
        assert config.filter_count == 12
        assert config.min_freq == 20.0
        assert config.max_freq == 20000.0

    def test_default_for_temperature(self):
        config = TransductionConfig.default_for(SignalType.TEMPERATURE)
        assert config.spike_rate_max == 20

    def test_default_for_unknown(self):
        config = TransductionConfig.default_for(SignalType.PROPRIOCEPTIVE)
        assert config.filter_count == 6


class TestPhysioNeuralTransducer:
    def test_transduce_sine_wave_produces_spikes(self, transducer):
        t = np.linspace(0, 0.1, 4410)
        signal = np.sin(2 * np.pi * 440 * t)
        spikes = transducer.transduce(signal, sample_rate=44100.0, signal_type=SignalType.AUDIO)
        assert len(spikes) > 0

    def test_transduce_empty_returns_empty(self, transducer):
        spikes = transducer.transduce(np.array([]), signal_type=SignalType.AUDIO)
        assert spikes == []

    def test_transduce_silence_returns_few_or_no_spikes(self, transducer):
        signal = np.zeros(4410)
        spikes = transducer.transduce(signal, sample_rate=44100.0, signal_type=SignalType.AUDIO)
        assert len(spikes) == 0

    def test_spike_fields(self, transducer):
        t = np.linspace(0, 0.05, 2205)
        signal = np.sin(2 * np.pi * 1000 * t)
        spikes = transducer.transduce(signal, sample_rate=44100.0, signal_type=SignalType.AUDIO)
        if spikes:
            s = spikes[0]
            assert "source_z" in s
            assert "timestamp" in s
            assert "phase" in s
            assert "inter_spike_interval" in s
            assert "strength" in s
            assert "payload" in s

    def test_spike_strength_is_normalized(self, transducer):
        t = np.linspace(0, 0.02, 882)
        signal = np.sin(2 * np.pi * 500 * t) * 0.5
        spikes = transducer.transduce(signal, sample_rate=44100.0, signal_type=SignalType.AUDIO)
        for s in spikes:
            assert 0.0 <= s["strength"] <= 1.0

    def test_phase_in_range(self, transducer):
        t = np.linspace(0, 0.02, 882)
        signal = np.sin(2 * np.pi * 500 * t)
        spikes = transducer.transduce(signal, sample_rate=44100.0, signal_type=SignalType.AUDIO)
        for s in spikes:
            assert 0.0 <= s["phase"] <= 1.0

    def test_timestamp_monotonic(self, transducer):
        t = np.linspace(0, 0.1, 4410)
        signal = np.sin(2 * np.pi * 440 * t)
        spikes = transducer.transduce(signal, sample_rate=44100.0, signal_type=SignalType.AUDIO)
        timestamps = [s["timestamp"] for s in spikes]
        assert all(timestamps[i] <= timestamps[i + 1] for i in range(len(timestamps) - 1))

    def test_different_signals_produce_different_patterns(self, transducer):
        t = np.linspace(0, 0.2, 8820)
        low = np.sin(2 * np.pi * 100 * t)
        high = np.sin(2 * np.pi * 5000 * t)
        spikes_low = transducer.transduce(low, sample_rate=44100.0, signal_type=SignalType.AUDIO)
        spikes_high = transducer.transduce(high, sample_rate=44100.0, signal_type=SignalType.AUDIO)
        # Different frequency content should produce different band activation
        z_low = {s["source_z"] for s in spikes_low}
        z_high = {s["source_z"] for s in spikes_high}
        assert z_low != z_high
