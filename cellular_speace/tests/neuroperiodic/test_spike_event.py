"""Tests for SpikeEvent datatype."""
import math
import pytest
from speace_core.cellular_brain.neuroperiodic.spike_event import SpikeEvent


class TestSpikeEventCreation:
    def test_default_values(self):
        event = SpikeEvent(source_z=3, target_z=5)
        assert event.source_z == 3
        assert event.target_z == 5
        assert event.timestamp == 0
        assert 0.0 <= event.phase < 2.0 * math.pi
        assert event.inter_spike_interval == 1
        assert event.strength == 1.0
        assert len(event.spike_id) == 8

    def test_spontaneous_firing(self):
        event = SpikeEvent(source_z=3)
        assert event.target_z is None

    def test_temporal_code_format(self):
        event = SpikeEvent(source_z=1, timestamp=10, phase=math.pi, inter_spike_interval=5, strength=0.8)
        code = event.temporal_code()
        assert len(code) == 3
        assert code[0] == 5.0
        assert code[1] == pytest.approx(0.5)
        assert code[2] == 0.8

    def test_temporal_code_phase_zero(self):
        event = SpikeEvent(source_z=1, phase=0.0)
        code = event.temporal_code()
        assert code[1] == 0.0

    def test_temporal_code_phase_2pi(self):
        event = SpikeEvent(source_z=1, phase=2.0 * math.pi - 0.001)
        code = event.temporal_code()
        assert code[1] == pytest.approx(1.0, abs=0.001)

    def test_strength_classification(self):
        strong = SpikeEvent(source_z=1, strength=0.9)
        weak = SpikeEvent(source_z=1, strength=0.2)
        assert strong.is_strong()
        assert weak.is_weak()
        assert not strong.is_weak()
        assert not weak.is_strong()

    def test_spike_id_is_unique(self):
        ids = {SpikeEvent(source_z=1).spike_id for _ in range(100)}
        assert len(ids) == 100


class TestSpikeEventPropagation:
    def test_with_propagation_adjusts_strength(self):
        event = SpikeEvent(source_z=1, target_z=2, strength=1.0)
        bond = _make_mock_bond(bid="b1", src_z=1, tgt_z=2,
                                amplification=0.8, delay=0.5)
        propagated = event.with_propagation(bond)
        assert propagated.strength == pytest.approx(0.8)

    def test_with_propagation_increases_timestamp(self):
        event = SpikeEvent(source_z=1, target_z=2, timestamp=0, strength=1.0)
        bond = _make_mock_bond(bid="b1", src_z=1, tgt_z=2,
                                amplification=1.0, delay=0.3)
        propagated = event.with_propagation(bond)
        assert propagated.timestamp == 3

    def test_with_propagation_preserves_payload(self):
        event = SpikeEvent(source_z=1, target_z=2, strength=1.0, payload={"key": "val"})
        bond = _make_mock_bond(bid="b1", src_z=1, tgt_z=2,
                                amplification=1.0, delay=0.0)
        propagated = event.with_propagation(bond)
        assert propagated.payload == {"key": "val"}


def _make_mock_bond(bid="b1", src_z=1, tgt_z=2,
                    amplification=1.0, delay=0.0):
    class MockMolecule:
        def amplification_factor(self):
            return amplification

    class MockBond:
        bond_id = bid
        source_z = src_z
        target_z = tgt_z
        molecule = MockMolecule()

        def signal_delay(self):
            return delay

    return MockBond()
