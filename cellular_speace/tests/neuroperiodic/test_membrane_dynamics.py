"""Tests for MembraneDynamics LIF model."""
import pytest
from speace_core.cellular_brain.neuroperiodic.membrane_dynamics import (
    MembraneDynamics,
    MembraneState,
)
from speace_core.cellular_brain.neuroperiodic.neural_element import (
    NeuralElement,
    ElementPeriod,
    ElementGroup,
    ElementBlock,
    ValenceState,
    OrbitalConfiguration,
)


def _make_element(
    period=ElementPeriod.SENSORY_TRANSDUCTION,
    group=ElementGroup.SENSORY_AUDITORY,
    block=ElementBlock.P_BLOCK,
    ionization_energy=0.5,
    atomic_radius=0.5,
    electronegativity=0.4,
    mass=0.3,
):
    return NeuralElement(
        atomic_number=1,
        symbol="Te",
        name="Test",
        period=period,
        group=group,
        block=block,
        valence=ValenceState.MODULATORY,
        electronegativity=electronegativity,
        ionization_energy=ionization_energy,
        atomic_radius=atomic_radius,
        mass=mass,
        orbital_config=OrbitalConfiguration(),
        cell_types=["test_neuron"],
    )


class TestMembraneDynamicsParameters:
    def test_threshold_from_ionization_energy(self):
        md = MembraneDynamics()
        low = _make_element(ionization_energy=0.2)
        high = _make_element(ionization_energy=0.9)
        assert md.threshold(low) == pytest.approx(0.2)
        assert md.threshold(high) == pytest.approx(0.9)

    def test_threshold_clamped(self):
        md = MembraneDynamics()
        very_low = _make_element(ionization_energy=0.0)
        very_high = _make_element(ionization_energy=1.0)
        assert md.threshold(very_low) == pytest.approx(0.1)
        assert md.threshold(very_high) == pytest.approx(1.0)

    def test_tau_from_period(self):
        md = MembraneDynamics()
        sensory = _make_element(period=ElementPeriod.SENSORY_TRANSDUCTION)
        executive = _make_element(period=ElementPeriod.EXECUTIVE)
        assert md.tau(sensory) == 2.0
        assert md.tau(executive) == 12.0
        assert md.tau(executive) > md.tau(sensory)

    def test_lateral_inhibition_from_electronegativity(self):
        md = MembraneDynamics()
        low = _make_element(electronegativity=0.2)
        high = _make_element(electronegativity=0.8)
        assert md.lateral_inhibition(low) == 0.1
        assert md.lateral_inhibition(high) == 0.4

    def test_refractory_period_from_block(self):
        md = MembraneDynamics()
        s_block = _make_element(block=ElementBlock.S_BLOCK)
        p_block = _make_element(block=ElementBlock.P_BLOCK)
        d_block = _make_element(block=ElementBlock.D_BLOCK)
        assert md.refractory_period(s_block) == 3
        assert md.refractory_period(p_block) == 2
        assert md.refractory_period(d_block) == 1


class TestMembraneDynamicsStep:
    def test_step_increases_potential_with_input(self):
        md = MembraneDynamics()
        element = _make_element(ionization_energy=0.5)
        state = md.step("n1", input_current=0.5, element=element)
        assert state.potential > 0.0

    def test_step_potential_is_bounded(self):
        md = MembraneDynamics()
        element = _make_element(ionization_energy=0.5)
        state = md.step("n1", input_current=10.0, element=element)
        assert state.potential <= 2.0

    def test_step_no_input_decays(self):
        md = MembraneDynamics()
        element = _make_element(ionization_energy=0.5, period=ElementPeriod.EXECUTIVE)
        md.step("n1", input_current=1.0, element=element)
        after = md.step("n1", input_current=0.0, element=element)
        assert after.potential < 1.0

    def test_refractory_period_suppresses(self):
        md = MembraneDynamics()
        element = _make_element(block=ElementBlock.S_BLOCK)
        md.step("n1", input_current=1.0, element=element)
        md.reset("n1", element)
        # During refractory, potential should stay 0
        for _ in range(3):
            state = md.step("n1", input_current=1.0, element=element)
            assert state.potential == 0.0
        # After refractory, potential should rise
        state = md.step("n1", input_current=1.0, element=element)
        assert state.potential > 0.0


class TestMembraneDynamicsFire:
    def test_should_fire_below_threshold(self):
        md = MembraneDynamics()
        element = _make_element(ionization_energy=0.8)
        md.step("n1", input_current=0.3, element=element)
        assert not md.should_fire("n1", element)

    def test_should_fire_above_threshold(self):
        md = MembraneDynamics()
        element = _make_element(ionization_energy=0.2, electronegativity=0.1)
        md.step("n1", input_current=0.5, element=element)
        assert md.should_fire("n1", element)

    def test_reset_sets_refractory(self):
        md = MembraneDynamics()
        element = _make_element(block=ElementBlock.P_BLOCK)
        md.step("n1", input_current=1.0, element=element)
        md.reset("n1", element, tick=10)
        state = md.get_state("n1")
        assert state.potential == 0.0
        assert state.refractory_ticks == 2
        assert state.last_spike_tick == 10
        assert state.spike_count == 1

    def test_reset_increases_adaptation(self):
        md = MembraneDynamics()
        element = _make_element(ionization_energy=0.5)
        md.reset("n1", element)
        state = md.get_state("n1")
        a1 = state.adaptation
        md.reset("n1", element)
        assert md.get_state("n1").adaptation > a1
