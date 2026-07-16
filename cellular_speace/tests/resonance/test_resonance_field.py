import pytest
from speace_core.cellular_brain.resonance.resonance_field import ResonanceField
from speace_core.cellular_brain.resonance.frequency_oscillator import (
    FrequencyBand,
    FrequencyOscillator,
)


@pytest.fixture
def field():
    return ResonanceField(field_id="test_field")


@pytest.fixture
def sample_oscillators():
    return [
        FrequencyOscillator(
            oscillator_id="osc1", band=FrequencyBand.ALPHA, frequency=10.0, amplitude=0.5
        ),
        FrequencyOscillator(
            oscillator_id="osc2", band=FrequencyBand.BETA, frequency=20.0, amplitude=0.7
        ),
        FrequencyOscillator(
            oscillator_id="osc3", band=FrequencyBand.ALPHA, frequency=10.0, amplitude=0.3
        ),
    ]


class TestResonanceField:
    def test_init(self, field):
        assert field.field_id == "test_field"
        assert len(field.oscillators) == 0

    def test_add_oscillator(self, field):
        osc = FrequencyOscillator(oscillator_id="o1", band=FrequencyBand.ALPHA)
        field.add_oscillator(osc, "region1")
        assert "o1" in field.oscillators
        assert "region1" in field.source_map
        assert "o1" in field.source_map["region1"]

    def test_remove_oscillator(self, field):
        osc = FrequencyOscillator(oscillator_id="o1", band=FrequencyBand.ALPHA)
        field.add_oscillator(osc, "region1")
        field.remove_oscillator("o1")
        assert "o1" not in field.oscillators

    def test_remove_source(self, field, sample_oscillators):
        for o in sample_oscillators:
            field.add_oscillator(o, "region1")
        field.remove_source("region1")
        assert "region1" not in field.source_map
        assert len(field.oscillators) == 0

    def test_tick_all(self, field, sample_oscillators):
        for o in sample_oscillators:
            field.add_oscillator(o, "region1")
        outputs = field.tick_all(dt=1.0)
        assert len(outputs) == 3
        for oid, val in outputs.items():
            assert isinstance(val, float)
            assert -1.0 <= val <= 1.0

    def test_tick_all_advances_phase(self, field, sample_oscillators):
        for o in sample_oscillators:
            field.add_oscillator(o, "region1")
        phases_before = {oid: field.oscillators[oid].phase for oid in field.oscillators}
        field.tick_all(dt=1.0)
        for oid in field.oscillators:
            assert field.oscillators[oid].phase != phases_before[oid]

    def test_get_field_state(self, field, sample_oscillators):
        for o in sample_oscillators:
            field.add_oscillator(o, "region1")
        states = field.get_field_state()
        assert "alpha" in states
        assert "beta" in states
        assert states["alpha"].band == FrequencyBand.ALPHA
        assert states["beta"].band == FrequencyBand.BETA

    def test_get_field_state_filtered(self, field, sample_oscillators):
        for o in sample_oscillators:
            field.add_oscillator(o, "region1")
        states = field.get_field_state(band=FrequencyBand.ALPHA)
        assert "alpha" in states
        assert "beta" not in states

    def test_get_global_coherence_empty(self, field):
        assert field.get_global_coherence() == 0.0

    def test_get_global_coherence_synchronized(self, field):
        osc1 = FrequencyOscillator(oscillator_id="o1", band=FrequencyBand.ALPHA, phase=0.0, amplitude=1.0)
        osc2 = FrequencyOscillator(oscillator_id="o2", band=FrequencyBand.ALPHA, phase=0.0, amplitude=1.0)
        field.add_oscillator(osc1, "r1")
        field.add_oscillator(osc2, "r1")
        coherence = field.get_global_coherence()
        assert coherence > 0.99

    def test_get_global_coherence_opposite_phases(self, field):
        import math
        osc1 = FrequencyOscillator(oscillator_id="o1", band=FrequencyBand.ALPHA, phase=0.0, amplitude=1.0)
        osc2 = FrequencyOscillator(oscillator_id="o2", band=FrequencyBand.ALPHA, phase=math.pi, amplitude=1.0)
        field.add_oscillator(osc1, "r1")
        field.add_oscillator(osc2, "r1")
        coherence = field.get_global_coherence()
        assert coherence < 0.1

    def test_get_source_coherence(self, field, sample_oscillators):
        for o in sample_oscillators:
            field.add_oscillator(o, "region1")
        coherence = field.get_source_coherence("region1")
        assert 0.0 <= coherence <= 1.0

    def test_get_source_coherence_unknown_source(self, field):
        coherence = field.get_source_coherence("unknown")
        assert coherence == 0.0

    def test_get_dominant_frequency(self, field, sample_oscillators):
        for o in sample_oscillators:
            field.add_oscillator(o, "region1")
        freq, mag = field.get_dominant_frequency()
        assert isinstance(freq, float)
        assert isinstance(mag, float)
        assert freq > 0

    def test_reset(self, field, sample_oscillators):
        for o in sample_oscillators:
            field.add_oscillator(o, "region1")
        field.tick_all(dt=10.0)
        field.reset()
        for osc in field.oscillators.values():
            assert osc.phase == 0.0
            assert osc.phase_locked is False

    def test_wave_state_has_phase_and_amplitude(self, field, sample_oscillators):
        for o in sample_oscillators:
            field.add_oscillator(o, "region1")
        field.tick_all(dt=1.0)
        states = field.get_field_state()
        for ws in states.values():
            assert hasattr(ws, "phase")
            assert hasattr(ws, "amplitude")
            assert hasattr(ws, "coherence")
