import pytest

from speace_core.metabolism.metabolic_cycle import MetabolicCycle
from speace_core.metabolism.waste_clearance import WasteClearanceEngine


def test_metabolic_cycle_creation():
    mc = MetabolicCycle()
    assert mc.current_energy == 1.0
    assert mc.stats is not None
    assert mc.stats["total_acquired"] == 0.0


def test_metabolic_cycle_tick_without_orchestrator():
    mc = MetabolicCycle()
    state = mc.tick(None)
    assert state is not None
    assert state.mode == "normal"
    assert mc.stats["total_acquired"] >= 0.0
    assert mc.stats["total_consumed"] >= 0.0


def test_metabolic_cycle_multiple_ticks():
    mc = MetabolicCycle()
    for _ in range(10):
        state = mc.tick(None)
    assert mc.current_energy > 0.0  # basic mode stays positive


def test_metabolic_cycle_snapshot():
    mc = MetabolicCycle()
    mc.tick(None)
    snap = mc.snapshot()
    assert "tick" in snap
    assert "current_energy" in snap
    assert "stats" in snap
    assert snap["tick"] >= 1


def test_waste_clearance_creation():
    wc = WasteClearanceEngine()
    assert wc.pending_waste == 0.0


def test_waste_clearance_add():
    wc = WasteClearanceEngine()
    wc.add_waste(0.1)
    assert wc.pending_waste == 0.1


def test_waste_clearance_capped():
    wc = WasteClearanceEngine()
    wc.add_waste(2.0)
    assert wc.pending_waste == 1.0  # capped at 1.0


def test_waste_clearance_scan_interval():
    wc = WasteClearanceEngine(scan_interval_ticks=5, max_waste_before_forced=1.0)
    wc.add_waste(0.2)
    # Should not clear until tick 5 (waste < max_waste_before_forced)
    for _ in range(4):
        cleared = wc.tick(None)
        assert cleared == 0.0
    # Tick 5 should clear
    cleared = wc.tick(None)
    assert cleared >= 0.0


def test_waste_clearance_forced_above_threshold():
    wc = WasteClearanceEngine(scan_interval_ticks=50, max_waste_before_forced=0.2)
    wc.add_waste(0.3)
    cleared = wc.tick(None)  # forced clearance because waste > 0.2
    assert cleared > 0.0


def test_waste_clearance_snapshot():
    wc = WasteClearanceEngine()
    wc.add_waste(0.1)
    snap = wc.snapshot()
    assert "pending_waste" in snap
    assert "total_cleared" in snap
    assert "scan_interval" in snap
