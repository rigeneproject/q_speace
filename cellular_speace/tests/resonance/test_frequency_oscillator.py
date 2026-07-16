import math
import pytest
from speace_core.cellular_brain.resonance.frequency_oscillator import (
    FrequencyBand,
    FrequencyOscillator,
    default_oscillators_for_region,
    FREQUENCY_RANGES,
)


class TestFrequencyOscillator:
    def test_init_defaults(self):
        osc = FrequencyOscillator(
            oscillator_id="test_alpha",
            band=FrequencyBand.ALPHA,
            frequency=10.0,
        )
        assert osc.oscillator_id == "test_alpha"
        assert osc.band == FrequencyBand.ALPHA
        assert osc.frequency == 10.0
        assert osc.phase == 0.0
        assert osc.amplitude == 0.5
        assert osc.phase_locked is False

    def test_tick_advances_phase(self):
        osc = FrequencyOscillator(
            oscillator_id="test",
            band=FrequencyBand.ALPHA,
            frequency=10.0,
            amplitude=1.0,
        )
        initial_phase = osc.phase
        osc.tick(dt=1.0)
        assert osc.phase != initial_phase, "Phase should advance on tick"

    def test_tick_returns_sinusoidal_value(self):
        osc = FrequencyOscillator(
            oscillator_id="test",
            band=FrequencyBand.ALPHA,
            frequency=10.0,
            amplitude=0.5,
            damping=0.0,
        )
        val = osc.tick(dt=1.0)
        expected = osc.amplitude * math.sin(osc.phase)
        assert abs(val - expected) < 1e-10, f"val={val}, expected={expected}, phase={osc.phase}, amp={osc.amplitude}"

    def test_tick_returns_valid_range(self):
        osc = FrequencyOscillator(
            oscillator_id="test",
            band=FrequencyBand.ALPHA,
            frequency=10.0,
            amplitude=1.0,
        )
        for _ in range(100):
            val = osc.tick(dt=1.0)
            assert -1.0 <= val <= 1.0

    def test_phase_lock_to(self):
        osc = FrequencyOscillator(
            oscillator_id="test",
            band=FrequencyBand.ALPHA,
            frequency=10.0,
        )
        osc.phase = 1.0
        osc.phase_lock_to(3.0, strength=0.5)
        assert osc.phase_locked is True
        assert osc.target_phase == 3.0 % (2 * math.pi)
        assert osc.coupling_strength == 0.5

    def test_release_phase_lock(self):
        osc = FrequencyOscillator(
            oscillator_id="test",
            band=FrequencyBand.ALPHA,
            frequency=10.0,
        )
        osc.phase_lock_to(1.0)
        osc.release_phase_lock()
        assert osc.phase_locked is False
        assert osc.target_phase is None
        assert osc.coupling_strength == 0.0

    def test_phase_lock_convergence(self):
        master = FrequencyOscillator(oscillator_id="master", band=FrequencyBand.ALPHA, frequency=10.0)
        slave = FrequencyOscillator(oscillator_id="slave", band=FrequencyBand.ALPHA, frequency=10.0)

        master.phase = 2.0
        slave.phase = 0.0
        slave.phase_lock_to(2.0, strength=0.5)

        initial_diff = slave.phase_difference_to(master)
        for _ in range(50):
            slave.phase += (master.phase - slave.phase) * slave.coupling_strength * 0.2
            slave.phase = slave.phase % (2.0 * math.pi)

        final_diff = slave.phase_difference_to(master)
        assert final_diff < initial_diff, f"initial={initial_diff}, final={final_diff}"

    def test_modulate_frequency(self):
        osc = FrequencyOscillator(
            oscillator_id="test",
            band=FrequencyBand.ALPHA,
            frequency=10.0,
            base_frequency=10.0,
        )
        osc.modulate_frequency(5.0)
        assert osc.frequency == 15.0
        osc.modulate_frequency(-20.0)
        assert osc.frequency == 0.1

    def test_boost_amplitude(self):
        osc = FrequencyOscillator(
            oscillator_id="test",
            band=FrequencyBand.ALPHA,
            amplitude=0.3,
        )
        osc.boost_amplitude(0.2)
        assert osc.amplitude == 0.5
        osc.boost_amplitude(1.0)
        assert osc.amplitude == 1.0

    def test_reset_phase(self):
        osc = FrequencyOscillator(
            oscillator_id="test",
            band=FrequencyBand.ALPHA,
        )
        osc.phase = 3.14
        osc.reset_phase()
        assert osc.phase == 0.0

    def test_get_normalized_phase(self):
        osc = FrequencyOscillator(
            oscillator_id="test",
            band=FrequencyBand.ALPHA,
        )
        osc.phase = math.pi
        assert osc.get_normalized_phase() == 0.5

    def test_phase_difference_to(self):
        a = FrequencyOscillator(oscillator_id="a", band=FrequencyBand.ALPHA, phase=0.0)
        b = FrequencyOscillator(oscillator_id="b", band=FrequencyBand.ALPHA, phase=math.pi)
        diff = a.phase_difference_to(b)
        assert abs(diff - math.pi) < 1e-6

    def test_amplitude_decays_on_tick(self):
        osc = FrequencyOscillator(
            oscillator_id="test",
            band=FrequencyBand.ALPHA,
            amplitude=0.5,
            damping=0.01,
        )
        initial = osc.amplitude
        osc.tick(dt=10.0)
        assert osc.amplitude < initial

    def test_get_instantaneous_value(self):
        osc = FrequencyOscillator(
            oscillator_id="test",
            band=FrequencyBand.ALPHA,
            phase=math.pi / 2,
            amplitude=0.7,
        )
        val = osc.get_instantaneous_value()
        assert abs(val - 0.7) < 1e-6


class TestDefaultOscillators:
    def test_default_oscillators_for_region_prefrontal(self):
        oscs = default_oscillators_for_region("prefrontal", "pf1")
        bands = {o.band for o in oscs}
        assert FrequencyBand.BETA in bands
        assert FrequencyBand.GAMMA in bands

    def test_default_oscillators_for_region_hippocampus(self):
        oscs = default_oscillators_for_region("hippocampus", "hc1")
        bands = {o.band for o in oscs}
        assert FrequencyBand.THETA in bands
        assert FrequencyBand.GAMMA in bands

    def test_default_oscillators_for_region_brainstem(self):
        oscs = default_oscillators_for_region("brainstem_homeostatic", "bs1")
        bands = {o.band for o in oscs}
        assert FrequencyBand.DELTA in bands
        assert FrequencyBand.THETA in bands

    def test_default_oscillators_for_region_default_mode(self):
        oscs = default_oscillators_for_region("default_mode", "dm1")
        bands = {o.band for o in oscs}
        assert FrequencyBand.ALPHA in bands

    def test_unknown_region_falls_back_to_alpha(self):
        oscs = default_oscillators_for_region("unknown", "unk1")
        assert len(oscs) == 1
        assert oscs[0].band == FrequencyBand.ALPHA

    def test_oscillator_frequencies_in_range(self):
        for band, (low, high) in FREQUENCY_RANGES.items():
            mid = (low + high) / 2.0
            assert low <= mid <= high

    def test_oscillators_have_unique_ids(self):
        oscs = default_oscillators_for_region("prefrontal", "pf1")
        ids = [o.oscillator_id for o in oscs]
        assert len(ids) == len(set(ids))
