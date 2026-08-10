from __future__ import annotations

import numpy as np

from q_speace.radio import (
    ComplianceFilter,
    DigitalTwinRF,
    MetasurfaceController,
    NullSDR,
    RadioEmulator,
    RegulatoryLimits,
    SpectrumSensor,
    WavefrontModulator,
)
from q_speace.radio.models import BeamformingConfig, FrequencyRange, Waveform


class TestNullSDR:
    def test_transmit_returns_report(self) -> None:
        sdr = NullSDR()
        w = Waveform(iq_samples=np.array([1.0, 0.0j]), sample_rate=1e6)
        r = sdr.transmit(w)
        assert r.success
        assert r.frequency_hz == w.center_freq_hz

    def test_receive_returns_waveform(self) -> None:
        sdr = NullSDR()
        w = sdr.receive(2.4e9, 1e6, 0.001)
        assert len(w.iq_samples) > 0

    def test_scan_spectrum_returns_readings(self) -> None:
        sdr = NullSDR()
        readings = sdr.scan_spectrum(2.4e9, 2.5e9, 10)
        assert len(readings) == 10
        for r in readings:
            assert r.rssi_dbm < 0


class TestWavefrontModulator:
    def test_encode_decode_roundtrip(self) -> None:
        mod = WavefrontModulator(seed=42)
        state = np.array([0.5, 0.3, 0.1, 0.1])
        waveform = mod.encode(state)
        recovered = mod.decode_to_q_star(waveform, expected_dim=4)
        state_n = state / np.linalg.norm(state)
        assert np.allclose(np.sort(state_n), np.sort(recovered), atol=0.15)

    def test_encode_q_star(self) -> None:
        mod = WavefrontModulator(seed=42)
        q = np.array([0.6, 0.2, 0.1, 0.1])
        w = mod.encode_q_star(q)
        assert len(w.iq_samples) > 0


class TestSpectrumSensor:
    def test_sense_returns_reading(self) -> None:
        sensor = SpectrumSensor(seed=42)
        reading = sensor.sense()
        assert reading.rssi_dbm < 0
        assert 0.0 <= reading.quality_index <= 1.0

    def test_environment_map(self) -> None:
        sensor = SpectrumSensor(seed=42)
        emap = sensor.environment_map
        assert len(emap) > 0


class TestMetasurfaceController:
    def test_beamform_noop_when_inactive(self) -> None:
        ctrl = MetasurfaceController(seed=42)
        w = Waveform(iq_samples=np.array([1.0, 0.0j]))
        shaped = ctrl.beamform(w)
        assert np.allclose(shaped.iq_samples, w.iq_samples)

    def test_beamform_changes_waveform_when_active(self) -> None:
        ctrl = MetasurfaceController(seed=42)
        ctrl.activate()
        w = Waveform(iq_samples=np.array([1.0, 0.0j]))
        shaped = ctrl.beamform(w, azimuth_deg=30.0)
        assert not np.allclose(shaped.iq_samples, w.iq_samples)

    def test_interference_pattern(self) -> None:
        ctrl = MetasurfaceController()
        bf = ctrl.interference_pattern((1.0, 0.0, 0.5))
        assert isinstance(bf, BeamformingConfig)


class TestComplianceFilter:
    def test_pass_legal_waveform(self) -> None:
        limits = RegulatoryLimits(max_power_dbm=30.0)
        cf = ComplianceFilter(limits=limits)
        w = Waveform(
            iq_samples=np.array([1.0, 0.0j]),
            center_freq_hz=2.45e9,
            power_dbm=20.0,
        )
        r = cf.check(w)
        assert r.passed

    def test_block_high_power(self) -> None:
        limits = RegulatoryLimits(max_power_dbm=0.0)
        cf = ComplianceFilter(limits=limits)
        w = Waveform(
            iq_samples=np.array([1.0, 0.0j]),
            center_freq_hz=2.45e9,
            power_dbm=20.0,
        )
        r = cf.check(w)
        assert not r.passed
        assert not r.power_ok

    def test_block_out_of_band(self) -> None:
        limits = RegulatoryLimits(allowed_bands=[FrequencyRange(2.4e9, 2.5e9)])
        cf = ComplianceFilter(limits=limits)
        w = Waveform(
            iq_samples=np.array([1.0, 0.0j]),
            center_freq_hz=3.5e9,
            power_dbm=10.0,
        )
        r = cf.check(w)
        assert not r.passed
        assert not r.frequency_ok


class TestRadioEmulator:
    def test_validate_tracks_history(self) -> None:
        emu = RadioEmulator()
        w = Waveform(
            iq_samples=np.array([1.0, 0.0j]),
            center_freq_hz=2.45e9,
            power_dbm=10.0,
        )
        r = emu.validate(w)
        assert r.passed
        assert len(emu.validation_history) == 1
        assert emu.pass_rate == 1.0

    def test_rejects_noncompliant(self) -> None:
        limits = RegulatoryLimits(max_power_dbm=-10.0)
        emu = RadioEmulator(compliance=ComplianceFilter(limits=limits))
        w = Waveform(
            iq_samples=np.array([1.0, 0.0j]),
            center_freq_hz=2.45e9,
            power_dbm=20.0,
        )
        r = emu.validate(w)
        assert not r.passed


class TestDigitalTwinRF:
    def test_summary_returns_reasonable_values(self) -> None:
        dt = DigitalTwinRF()
        s = dt.summary()
        assert s["cascaded_gain_db"] > 0
        assert s["noise_figure_db"] > 0
        assert s["sensitivity_dbm_1mhz"] < 0

    def test_link_budget_returns_all_keys(self) -> None:
        dt = DigitalTwinRF()
        result = dt.estimate_link_budget(
            tx_power_dbm=20.0,
            tx_gain_dbi=6.0,
            rx_gain_dbi=3.0,
            distance_m=100.0,
            frequency_hz=2.45e9,
        )
        for key in (
            "tx_power_dbm",
            "path_loss_db",
            "received_power_dbm",
            "rx_sensitivity_dbm",
            "margin_db",
        ):
            assert key in result


class TestModels:
    def test_waveform_power_conversion(self) -> None:
        w = Waveform(iq_samples=np.array([1.0j, 0.0]), power_dbm=0.0)
        assert abs(w.power_watts - 0.001) < 1e-6

    def test_spectrum_quality_index(self) -> None:
        from q_speace.radio.models import SpectrumReading

        r = SpectrumReading(center_freq_hz=2.4e9, bandwidth_hz=1e6, rssi_dbm=-100.0, snr_db=30.0)
        assert r.quality_index > 0.9
        assert r.is_clear
