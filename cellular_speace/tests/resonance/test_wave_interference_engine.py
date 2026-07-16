import math
import pytest
from speace_core.cellular_brain.resonance.wave_interference_engine import (
    WaveInterferenceEngine,
    InterferencePattern,
    InterferenceType,
)
from speace_core.cellular_brain.resonance.frequency_oscillator import (
    FrequencyBand,
    FrequencyOscillator,
)


@pytest.fixture
def engine():
    return WaveInterferenceEngine(engine_id="test_engine")


@pytest.fixture
def oscillators_constructive():
    return [
        FrequencyOscillator(oscillator_id="o1", band=FrequencyBand.ALPHA, phase=0.0, amplitude=1.0),
        FrequencyOscillator(oscillator_id="o2", band=FrequencyBand.ALPHA, phase=0.0, amplitude=1.0),
        FrequencyOscillator(oscillator_id="o3", band=FrequencyBand.ALPHA, phase=0.0, amplitude=1.0),
    ]


@pytest.fixture
def oscillators_destructive():
    return [
        FrequencyOscillator(oscillator_id="o1", band=FrequencyBand.ALPHA, phase=0.0, amplitude=1.0),
        FrequencyOscillator(oscillator_id="o2", band=FrequencyBand.ALPHA, phase=math.pi, amplitude=1.0),
    ]


class TestWaveInterferenceEngine:
    def test_init(self, engine):
        assert engine.engine_id == "test_engine"
        assert len(engine.patterns) == 0

    def test_compute_interference_empty(self, engine):
        pattern = engine.compute_interference([], "empty")
        assert pattern.interference_type == InterferenceType.DESTRUCTIVE
        assert pattern.amplitude == 0.0

    def test_constructive_interference(self, engine, oscillators_constructive):
        pattern = engine.compute_interference(oscillators_constructive, "constructive")
        assert pattern.interference_type == InterferenceType.CONSTRUCTIVE
        assert pattern.amplitude > 0.9
        assert pattern.strength > 0.9

    def test_destructive_interference(self, engine, oscillators_destructive):
        pattern = engine.compute_interference(oscillators_destructive, "destructive")
        assert pattern.interference_type == InterferenceType.DESTRUCTIVE
        assert pattern.amplitude < 0.1

    def test_pattern_stored(self, engine, oscillators_constructive):
        engine.compute_interference(oscillators_constructive, "stored")
        assert "stored" in engine.patterns
        assert engine.patterns["stored"].pattern_id == "stored"

    def test_interfere_fields(self, engine):
        field_a = [FrequencyOscillator(oscillator_id="a1", band=FrequencyBand.ALPHA, phase=0.0, amplitude=1.0)]
        field_b = [FrequencyOscillator(oscillator_id="b1", band=FrequencyBand.BETA, phase=0.0, amplitude=1.0)]
        pattern = engine.interfere_fields(field_a, field_b, "cross")
        assert pattern.pattern_id == "cross"
        assert len(pattern.source_ids) == 2

    def test_amplify_region(self, engine):
        ref = FrequencyOscillator(oscillator_id="ref", band=FrequencyBand.ALPHA, phase=0.0, amplitude=1.0)
        targets = [
            FrequencyOscillator(oscillator_id="t1", band=FrequencyBand.ALPHA, phase=0.1, amplitude=0.3),
            FrequencyOscillator(oscillator_id="t2", band=FrequencyBand.ALPHA, phase=0.15, amplitude=0.4),
        ]
        engine.amplify_region(targets, ref, amplification_factor=0.2)
        for t in targets:
            assert t.amplitude > 0.3

    def test_suppress_region(self, engine):
        ref = FrequencyOscillator(oscillator_id="ref", band=FrequencyBand.ALPHA, phase=0.0, amplitude=1.0)
        targets = [
            FrequencyOscillator(oscillator_id="t1", band=FrequencyBand.ALPHA, phase=0.1, amplitude=0.8),
            FrequencyOscillator(oscillator_id="t2", band=FrequencyBand.ALPHA, phase=0.15, amplitude=0.9),
        ]
        engine.suppress_region(targets, ref, suppression_factor=0.3)
        for t in targets:
            assert t.amplitude < 0.8

    def test_get_resonance_condition(self, engine):
        a = FrequencyOscillator(oscillator_id="a", band=FrequencyBand.ALPHA, frequency=10.0)
        b = FrequencyOscillator(oscillator_id="b", band=FrequencyBand.ALPHA, frequency=20.0)
        score = engine.get_resonance_condition(a, b)
        assert score > 0.9

    def test_get_resonance_condition_non_resonant(self, engine):
        a = FrequencyOscillator(oscillator_id="a", band=FrequencyBand.ALPHA, frequency=10.0)
        b = FrequencyOscillator(oscillator_id="b", band=FrequencyBand.ALPHA, frequency=7.3)
        score = engine.get_resonance_condition(a, b)
        assert score < 1.0

    def test_find_resonant_pairs(self, engine):
        oscs = [
            FrequencyOscillator(oscillator_id="a", band=FrequencyBand.ALPHA, frequency=10.0),
            FrequencyOscillator(oscillator_id="b", band=FrequencyBand.ALPHA, frequency=20.0),
            FrequencyOscillator(oscillator_id="c", band=FrequencyBand.ALPHA, frequency=15.0),
            FrequencyOscillator(oscillator_id="d", band=FrequencyBand.ALPHA, frequency=30.0),
        ]
        pairs = engine.find_resonant_pairs(oscs, threshold=0.8)
        assert len(pairs) >= 1

    def test_clear_patterns(self, engine, oscillators_constructive):
        engine.compute_interference(oscillators_constructive, "test")
        assert len(engine.patterns) == 1
        engine.clear_patterns()
        assert len(engine.patterns) == 0

    def test_partial_interference(self, engine):
        oscs = [
            FrequencyOscillator(oscillator_id="o1", band=FrequencyBand.ALPHA, phase=0.0, amplitude=1.0),
            FrequencyOscillator(oscillator_id="o2", band=FrequencyBand.ALPHA, phase=math.pi / 2, amplitude=1.0),
        ]
        pattern = engine.compute_interference(oscs, "partial")
        assert pattern.interference_type in (InterferenceType.PARTIAL, InterferenceType.RESONANT)
