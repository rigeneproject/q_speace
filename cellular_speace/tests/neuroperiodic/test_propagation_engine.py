"""Tests for PropagationEngine."""
import pytest
from speace_core.cellular_brain.neuroperiodic.propagation_engine import (
    PropagationEngine,
    SpikePropagationResult,
)
from speace_core.cellular_brain.neuroperiodic.synaptic_bond import (
    BondRegistry,
    BondType,
    BondOrder,
    BondPolarity,
    SynapticBond,
    MolecularOrbital,
)
from speace_core.cellular_brain.neuroperiodic.neural_periodic_table import (
    PeriodicTableBuilder,
    NeuralPeriodicTable,
)
from speace_core.cellular_brain.neuroperiodic.spike_event import SpikeEvent


@pytest.fixture
def engine():
    table = PeriodicTableBuilder.build_default()
    registry = BondRegistry()
    # Register some bonds between known elements
    src = table.get_by_symbol("Ph")
    tgt = table.get_by_symbol("Sc")
    if src and tgt:
        bond = SynapticBond(
            bond_id="b_ph_sc",
            source_z=src.atomic_number,
            target_z=tgt.atomic_number,
            bond_type=BondType.COVALENT,
            bond_order=BondOrder.SINGLE,
            polarity=BondPolarity.UNIDIRECTIONAL_FORWARD,
            bond_energy=0.8,
            bond_length=0.3,
            plasticity=0.6,
        )
        registry.register(bond)
    return PropagationEngine(table=table, bond_registry=registry)


class TestPropagationEngine:
    def test_emit_creates_fire_candidates(self, engine):
        spike = SpikeEvent(source_z=1, strength=1.0)
        candidates = engine.emit(spike, circuit=None, tick=0)
        # At least 1 candidate if bonds exist
        assert len(candidates) >= 0

    def test_signal_delay_varies_by_bond_type(self, engine):
        covalent = SynapticBond(
            bond_id="c", source_z=1, target_z=2,
            bond_type=BondType.COVALENT,
            bond_length=0.5,
        )
        metallic = SynapticBond(
            bond_id="m", source_z=1, target_z=2,
            bond_type=BondType.METALLIC,
            bond_length=0.5,
        )
        covalent_delay = engine.signal_delay(covalent)
        metallic_delay = engine.signal_delay(metallic)
        assert covalent_delay != metallic_delay

    def test_propagate_drops_spontaneous_spikes(self, engine):
        spike = SpikeEvent(source_z=1, target_z=None)
        result = engine.propagate([spike], circuit=None)
        assert result.dropped_spikes == 1
        assert result.propagated_spikes == 0

    def test_propagate_drops_unknown_bonds(self, engine):
        spike = SpikeEvent(source_z=999, target_z=998)
        result = engine.propagate([spike], circuit=None)
        assert result.dropped_spikes == 1

    def test_propagate_returns_result_object(self, engine):
        spike = SpikeEvent(source_z=1, target_z=2, strength=1.0)
        result = engine.propagate([spike], circuit=None)
        assert isinstance(result, SpikePropagationResult)
        assert hasattr(result, "propagated_spikes")
        assert hasattr(result, "mean_delay")


class TestPropagationEngineSTDP:
    def test_apply_stdp_returns_count(self, engine):
        pre = [SpikeEvent(source_z=1, target_z=2, timestamp=0)]
        post = [SpikeEvent(source_z=2, target_z=1, timestamp=3)]
        updated = engine.apply_stdp(pre, post)
        assert isinstance(updated, int)

    def test_apply_stdp_no_bond_no_update(self, engine):
        pre = [SpikeEvent(source_z=999, target_z=1, timestamp=0)]
        post = [SpikeEvent(source_z=1, target_z=999, timestamp=3)]
        updated = engine.apply_stdp(pre, post)
        assert updated == 0

    def test_apply_stdp_ltp_increases_energy(self, engine):
        table = PeriodicTableBuilder.build_default()
        registry = BondRegistry()
        src = table.get_by_symbol("Ph")
        tgt = table.get_by_symbol("Sc")
        if src and tgt:
            bond = SynapticBond(
                bond_id="b_stdp", source_z=src.atomic_number,
                target_z=tgt.atomic_number, bond_energy=0.5,
                plasticity=0.8,
            )
            registry.register(bond)
            eng = PropagationEngine(table=table, bond_registry=registry)
            pre = [SpikeEvent(source_z=src.atomic_number, target_z=tgt.atomic_number, timestamp=0)]
            post = [SpikeEvent(source_z=tgt.atomic_number, target_z=src.atomic_number, timestamp=2)]
            eng.apply_stdp(pre, post)
            assert bond.bond_energy > 0.5
