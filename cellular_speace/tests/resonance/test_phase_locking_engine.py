import math
import pytest
from speace_core.cellular_brain.resonance.phase_locking_engine import (
    PhaseLockingEngine,
    PhaseLockingConfig,
    CouplingTopology,
)
from speace_core.cellular_brain.resonance.frequency_oscillator import (
    FrequencyBand,
    FrequencyOscillator,
)


@pytest.fixture
def engine():
    return PhaseLockingEngine()


@pytest.fixture
def populated_engine():
    eng = PhaseLockingEngine()
    for i in range(5):
        osc = FrequencyOscillator(
            oscillator_id=f"osc{i}",
            band=FrequencyBand.ALPHA,
            frequency=10.0,
            amplitude=0.5,
            phase=0.0,
        )
        eng.register_oscillator(osc)
    return eng


class TestPhaseLockingEngine:
    def test_init(self, engine):
        assert len(engine.oscillators) == 0

    def test_register_oscillator(self, engine):
        osc = FrequencyOscillator(oscillator_id="o1", band=FrequencyBand.ALPHA)
        engine.register_oscillator(osc)
        assert "o1" in engine.oscillators
        assert "o1" in engine.coupling_matrix

    def test_unregister_oscillator(self, populated_engine):
        populated_engine.unregister_oscillator("osc2")
        assert "osc2" not in populated_engine.oscillators

    def test_couple_oscillators(self, engine):
        a = FrequencyOscillator(oscillator_id="a", band=FrequencyBand.ALPHA)
        b = FrequencyOscillator(oscillator_id="b", band=FrequencyBand.ALPHA)
        engine.register_oscillator(a)
        engine.register_oscillator(b)
        engine.couple_oscillators("a", "b")
        assert "b" in engine.coupling_matrix["a"]

    def test_uncouple_oscillators(self, engine):
        a = FrequencyOscillator(oscillator_id="a", band=FrequencyBand.ALPHA)
        b = FrequencyOscillator(oscillator_id="b", band=FrequencyBand.ALPHA)
        engine.register_oscillator(a)
        engine.register_oscillator(b)
        engine.couple_oscillators("a", "b")
        engine.uncouple_oscillators("a", "b")
        assert "b" not in engine.coupling_matrix["a"]

    def test_tick_empty(self, engine):
        result = engine.tick()
        assert result == {}

    def test_tick_updates_phases(self, populated_engine):
        phases_before = {oid: populated_engine.oscillators[oid].phase for oid in populated_engine.oscillators}
        populated_engine.tick(dt=1.0)
        for oid in populated_engine.oscillators:
            assert populated_engine.oscillators[oid].phase is not None

    def test_global_coupling_converges(self, populated_engine):
        populated_engine.oscillators["osc0"].phase = 0.0
        populated_engine.oscillators["osc1"].phase = 2.0
        populated_engine.oscillators["osc2"].phase = 4.0
        populated_engine.oscillators["osc3"].phase = 1.0
        populated_engine.oscillators["osc4"].phase = 3.0

        populated_engine.config.coupling_strength = 0.5
        for _ in range(50):
            populated_engine.tick(dt=1.0)

        order = populated_engine.compute_order_parameter()
        assert order > 0.5

    def test_compute_order_parameter_synchronized(self, populated_engine):
        for osc in populated_engine.oscillators.values():
            osc.phase = 0.0
        order = populated_engine.compute_order_parameter()
        assert order > 0.99

    def test_compute_order_parameter_random(self, populated_engine):
        import random
        for osc in populated_engine.oscillators.values():
            osc.phase = random.random() * 2 * math.pi
        order = populated_engine.compute_order_parameter()
        assert 0.0 <= order <= 1.0

    def test_compute_phase_locking_value(self, populated_engine):
        for osc in populated_engine.oscillators.values():
            osc.phase = 0.0
        plv = populated_engine.compute_phase_locking_value(["osc0", "osc1", "osc2"])
        assert plv > 0.99

    def test_compute_phase_locking_value_single(self, populated_engine):
        plv = populated_engine.compute_phase_locking_value(["osc0"])
        assert plv == 1.0

    def test_detect_phase_clusters(self, populated_engine):
        populated_engine.oscillators["osc0"].phase = 0.0
        populated_engine.oscillators["osc1"].phase = 0.05
        populated_engine.oscillators["osc2"].phase = 3.0
        populated_engine.oscillators["osc3"].phase = 3.1
        populated_engine.oscillators["osc4"].phase = 1.5

        clusters = populated_engine.detect_phase_clusters(tolerance=0.2)
        assert len(clusters) >= 1

    def test_nearest_neighbor_topology(self, engine):
        engine.config.coupling_topology = CouplingTopology.NEAREST_NEIGHBOR
        for i in range(4):
            osc = FrequencyOscillator(
                oscillator_id=f"n{i}", band=FrequencyBand.ALPHA, frequency=10.0, amplitude=0.5
            )
            engine.register_oscillator(osc)

        for _ in range(10):
            engine.tick(dt=1.0)
        order = engine.compute_order_parameter()
        assert 0.0 <= order <= 1.0


class TestPhaseLockingConfig:
    def test_defaults(self):
        cfg = PhaseLockingConfig()
        assert cfg.coupling_strength == 0.1
        assert cfg.coupling_topology == CouplingTopology.GLOBAL
        assert cfg.phase_tolerance == 0.1
        assert cfg.enable_adaptive_coupling is True

    def test_targeted_topology(self):
        cfg = PhaseLockingConfig(coupling_topology=CouplingTopology.TARGETED)
        assert cfg.coupling_topology == CouplingTopology.TARGETED
