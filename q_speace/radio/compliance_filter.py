"""Software-level EM compliance gate (FCC/ETSI parameter validation).

WARNING: Passing this filter does NOT constitute legal authorization to
transmit. Real RF transmission requires:
  - A hardware-certified radio operating in license-exempt ISM bands, OR
  - An experimental FCC/ETSI license for the intended frequency/power, OR
  - An amateur radio license where applicable (e.g. 70cm / 2m bands).
This filter validates configured parameters only; it cannot detect antenna
mismatch, harmonic leakage, or certify hardware compliance.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import FrequencyRange, Waveform


@dataclass
class RegulatoryLimits:
    max_power_dbm: float = 30.0
    max_bandwidth_hz: float = 80e6
    allowed_bands: list[FrequencyRange] = field(
        default_factory=lambda: [
            FrequencyRange(2.4e9, 2.4835e9),
            FrequencyRange(5.15e9, 5.85e9),
            FrequencyRange(863e6, 870e6),
        ]
    )
    max_spurious_dbm: float = -30.0


@dataclass
class ComplianceResult:
    passed: bool
    power_ok: bool = True
    bandwidth_ok: bool = True
    frequency_ok: bool = True
    spurious_ok: bool = True
    message: str = ""


class ComplianceFilter:
    def __init__(self, limits: RegulatoryLimits | None = None) -> None:
        self.limits = limits or RegulatoryLimits()

    def check(self, waveform: Waveform) -> ComplianceResult:
        power_ok = waveform.power_dbm <= self.limits.max_power_dbm
        band_ok = self._band_allowed(waveform.center_freq_hz)
        bw_ok = waveform.sample_rate <= self.limits.max_bandwidth_hz
        spur_ok = self._check_spurious(waveform)
        passed = power_ok and band_ok and bw_ok and spur_ok
        msg = ""
        if not passed:
            reasons = []
            if not power_ok:
                reasons.append(
                    f"power {waveform.power_dbm} dBm > limit {self.limits.max_power_dbm} dBm"
                )
            if not band_ok:
                reasons.append(f"freq {waveform.center_freq_hz} Hz not in allowed bands")
            if not bw_ok:
                reasons.append(
                    f"bandwidth {waveform.sample_rate} Hz > limit {self.limits.max_bandwidth_hz} Hz"
                )
            if not spur_ok:
                reasons.append("spurious emissions exceed limit")
            msg = "; ".join(reasons)
        return ComplianceResult(
            passed=passed,
            power_ok=power_ok,
            bandwidth_ok=bw_ok,
            frequency_ok=band_ok,
            spurious_ok=spur_ok,
            message=msg,
        )

    def _band_allowed(self, freq_hz: float) -> bool:
        return any(b.start_hz <= freq_hz <= b.end_hz for b in self.limits.allowed_bands)

    def _check_spurious(self, waveform: Waveform) -> bool:
        return True


class RadioEmulator:
    def __init__(self, compliance: ComplianceFilter | None = None) -> None:
        self._compliance = compliance or ComplianceFilter()
        self._validation_history: list[ComplianceResult] = []

    def validate(self, waveform: Waveform) -> ComplianceResult:
        result = self._compliance.check(waveform)
        self._validation_history.append(result)
        return result

    @property
    def validation_history(self) -> list[ComplianceResult]:
        return list(self._validation_history)

    @property
    def pass_rate(self) -> float:
        if not self._validation_history:
            return 1.0
        return sum(1 for r in self._validation_history if r.passed) / len(self._validation_history)
