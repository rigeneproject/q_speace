"""T-HOME-02 — PhysiologicalSignalBus → GlobalHomeostaticDrive adapter.

Acceptance checks (T-HOME-02 spec §5):
1. controlled PSN stream variations produce measurable, reproducible drive
   changes (≥ 5 runs);
2. stale/absent signals → documented hold policy, no errors, no jumps;
3. with no PSN sources the drive behaviour is identical to pre-T-HOME-02;
4. clamping: an out-of-scale signal cannot push contributions outside the
   declared modulation bounds;
4b. unregistered signals are rejected (ontologia PSN);
5. survival source can be decoupled from mean_energy (psn_damage);
6. orchestrator wiring behind a dedicated flag (default off).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from speace_core.cellular_brain.dynamics.global_homeostatic_drive import (
    GlobalHomeostaticDrive,
)
from speace_core.cellular_brain.psn import PhysiologicalSignalBus, Physiome
from speace_core.cellular_brain.regulation.physio_drive_adapter import (
    PhysioDriveAdapter,
    PhysioMapping,
)

_PHYSIOLOGY_DIR = (
    Path(__file__).resolve().parents[2]
    / "speace_core"
    / "dna"
    / "genome"
    / "physiology"
)


def _build_psn() -> PhysiologicalSignalBus:
    physiome = Physiome(str(_PHYSIOLOGY_DIR))
    physiome.load()
    return PhysiologicalSignalBus(physiome)


class StubPsn:
    """Minimal PSN stand-in for clamp/edge-case tests."""

    def __init__(self, values: dict | None = None, registered: set | None = None):
        self._values = dict(values or {})
        self.physiome = type(
            "P",
            (),
            {
                "is_signal_registered": staticmethod(
                    lambda sid: registered is None or sid in registered
                )
            },
        )()

    def read_stream(self, signal_id: str):
        return self._values.get(signal_id)

    def clear_stream(self, signal_id: str) -> None:
        self._values.pop(signal_id, None)


def _synced_adapter(psn, drive, mappings=None) -> PhysioDriveAdapter:
    return PhysioDriveAdapter(psn=psn, drive=drive, mappings=mappings)


class TestReproducibleModulation:
    def test_stream_variation_moves_drive_measurably_across_runs(self):
        results = []
        for _ in range(5):
            psn = _build_psn()
            drive = GlobalHomeostaticDrive()
            drive.update_drive("efficiency", 0.5)
            mapping = PhysioMapping("energy", "efficiency", weight=0.4)
            adapter = _synced_adapter(psn, drive, [mapping])

            psn.publish_stream("energy", 0.1)
            adapter.sync(1)
            low_val = drive.get_drive_value("efficiency")

            psn.publish_stream("energy", 0.9)
            adapter.sync(2)
            high_val = drive.get_drive_value("efficiency")

            results.append((low_val, high_val))

        assert all(hi - lo > 0.15 for lo, hi in results)  # measurable
        assert len(set(results)) == 1  # reproducible


class TestStalenessPolicies:
    def test_never_seen_signal_does_not_touch_drive(self):
        psn = _build_psn()
        drive = GlobalHomeostaticDrive()
        drive.update_drive("exploration", 0.42)

        adapter = _synced_adapter(psn, drive)
        report = adapter.sync(1)

        assert drive.get_drive_value("exploration") == 0.42
        assert any(s["policy"] == "no_data_ever" for s in report["stale"])

    def test_hold_within_max_age_no_discontinuity(self):
        psn = StubPsn(values={"energy": 0.7}, registered={"energy"})
        drive = GlobalHomeostaticDrive()
        drive.update_drive("efficiency", 0.5)

        mapping = PhysioMapping("energy", "efficiency", max_age_ticks=3)
        adapter = _synced_adapter(psn, drive, [mapping])

        adapter.sync(1)
        applied = drive.get_drive_value("efficiency")

        # Stream disappears but within max_age → hold, same value
        psn.clear_stream("energy")
        adapter.sync(2)
        held = drive.get_drive_value("efficiency")

        assert held == pytest.approx(applied)
        assert any(
            s.get("policy") == "hold" for s in adapter.last_sync["stale"]
        )

    def test_decay_to_setpoint_after_max_age(self):
        psn = StubPsn(values={"energy": 0.8}, registered={"energy"})
        drive = GlobalHomeostaticDrive()
        drive.update_drive("efficiency", 0.1)

        mapping = PhysioMapping(
            "energy", "efficiency", max_age_ticks=2, stale_policy="decay_to_setpoint"
        )
        adapter = _synced_adapter(psn, drive, [mapping])

        adapter.sync(1)
        adapter.sync(2)  # still holding

        # Beyond max_age with no stream: pulled toward setpoint (0.6)
        psn.clear_stream("energy")
        adapter.sync(5)
        value = drive.get_drive_value("efficiency")

        assert 0.1 < value <= 0.6 + 1e-9
        assert any(
            s.get("policy") == "decay_to_setpoint" for s in adapter.last_sync["stale"]
        )


class TestRejectionAndClamping:
    def test_unregistered_signal_rejected(self):
        psn = StubPsn(values={"evil": 1.0}, registered={"energy"})
        drive = GlobalHomeostaticDrive()
        drive.update_drive("efficiency", 0.5)

        mapping = PhysioMapping("evil", "efficiency", weight=1.0)
        adapter = _synced_adapter(psn, drive, [mapping])
        report = adapter.sync(1)

        assert drive.get_drive_value("efficiency") == 0.5
        assert any(
            r["reason"] == "unregistered_in_physiome" for r in report["rejected"]
        )

    def test_out_of_scale_signal_is_clamped(self):
        psn = StubPsn(values={"energy": 5.0}, registered={"energy"})
        drive = GlobalHomeostaticDrive()
        drive.update_drive("efficiency", 0.5)

        adapter = _synced_adapter(psn, drive)  # default weight 0.2
        adapter.sync(1)

        value = drive.get_drive_value("efficiency")
        # clamped contribution in [0,1] → blend stays within the declared range
        assert value == pytest.approx(0.6, abs=1e-9)
        assert adapter.last_sync["applied"]["efficiency"]["value"] == pytest.approx(
            0.6, abs=1e-9
        )


class TestRetrocompatibility:
    def test_no_psn_sources_leaves_drives_bit_identical(self):
        drive_a = GlobalHomeostaticDrive()
        drive_b = GlobalHomeostaticDrive()
        for d in (drive_a, drive_b):
            d.update_drive("survival", 0.8)
            d.update_drive("efficiency", 0.4)
            d.update_drive("exploration", 0.3)
            d.update_drive("stability", 0.7)

        psn = _build_psn()  # no streams published
        adapter = _synced_adapter(psn, drive_a)
        adapter.sync(1)
        drive_a.step()
        drive_b.step()

        assert drive_a.get_global_modulation() == drive_b.get_global_modulation()
        for name in drive_a.list_drives():
            assert drive_a.get_drive_value(name) == drive_b.get_drive_value(name)


class TestSurvivalSourceDecoupling:
    def test_damage_stream_can_feed_survival(self):
        psn = _build_psn()
        drive = GlobalHomeostaticDrive()

        mapping = PhysioMapping("damage", "survival", transform="identity", weight=0.3)
        adapter = _synced_adapter(psn, drive, [mapping])

        drive.update_drive("survival", 0.0)
        psn.publish_stream("damage", 0.8)
        adapter.sync(1)

        # 0.0 + 0.3 * 0.8 = 0.24 → independent from mean_energy
        assert drive.get_drive_value("survival") == pytest.approx(0.24, abs=1e-9)


class TestOrchestratorWiring:
    def _orch(self, **flags):
        from speace_core.dna.models import SharedGenome
        from speace_core.orchestrator import CellularBrainOrchestrator

        genome = SharedGenome(cell_type="neuron", genome_id="t-home-02")
        return CellularBrainOrchestrator(
            genome=genome,
            circuit=CellularBrainOrchestrator.build_mvp(genome).circuit,
            **flags,
        )

    def test_adapter_wired_behind_flag(self):
        orch = self._orch(
            homeostatic_drive_enabled=True,
            psn_enabled=True,
            physio_drive_enabled=True,
        )
        assert orch._physio_drive_adapter is not None

    def test_flag_off_keeps_adapter_absent(self):
        orch = self._orch(homeostatic_drive_enabled=True, psn_enabled=True)
        assert orch._physio_drive_adapter is None

    def test_survival_source_psn_damage(self):
        orch = self._orch(
            homeostatic_drive_enabled=True,
            psn_enabled=True,
            physio_drive_enabled=True,
            survival_drive_source="psn_damage",
        )
        orch._psn_bus.publish_stream("damage", 0.9)
        import asyncio

        asyncio.run(orch.run_ticks(1))

        # Survival follows the PSN damage stream (tick_begin homeostatic
        # corrections may adjust it slightly) — NOT 1 - mean_energy.
        damage_now = orch._psn_bus.read_stream("damage")
        assert damage_now is not None
        assert orch._homeostatic_drive.get_drive_value("survival") == pytest.approx(
            damage_now, abs=1e-6
        )
        assert orch.latest_metrics is not None
        assert orch._homeostatic_drive.get_drive_value("survival") != pytest.approx(
            1.0 - orch.latest_metrics.mean_energy
        )

    def test_survival_source_default_matches_prewiring(self):
        orch = self._orch(homeostatic_drive_enabled=True, psn_enabled=True)
        import asyncio

        asyncio.run(orch.run_ticks(1))
        metrics = orch.latest_metrics

        assert metrics is not None
        assert orch._homeostatic_drive.get_drive_value("survival") == pytest.approx(
            1.0 - metrics.mean_energy
        )
