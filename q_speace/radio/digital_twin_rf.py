from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class RFComponentModel:
    name: str
    gain_db: float = 0.0
    noise_figure_db: float = 0.0
    p1db_dbm: float = 20.0
    ip3_dbm: float = 30.0

    def output_power_dbm(self, input_power_dbm: float) -> float:
        return input_power_dbm + self.gain_db

    def noise_floor_dbm(self, bandwidth_hz: float) -> float:
        thermal = -174.0 + 10.0 * math.log10(bandwidth_hz)
        return thermal + self.noise_figure_db

    def is_linear(self, input_power_dbm: float) -> bool:
        return input_power_dbm + self.gain_db <= self.p1db_dbm - 1.0


@dataclass
class DigitalTwinRFConfig:
    lna: RFComponentModel | None = None
    mixer: RFComponentModel | None = None
    filter_loss_db: float = 2.0
    adc_bits: int = 12
    adc_sample_rate: float = 30.72e6

    def __post_init__(self) -> None:
        if self.lna is None:
            self.lna = RFComponentModel(
                name="LNA", gain_db=20.0, noise_figure_db=1.5, p1db_dbm=-10.0, ip3_dbm=5.0
            )
        if self.mixer is None:
            self.mixer = RFComponentModel(
                name="Mixer", gain_db=-6.0, noise_figure_db=8.0, p1db_dbm=5.0, ip3_dbm=15.0
            )


class DigitalTwinRF:
    def __init__(self, config: DigitalTwinRFConfig | None = None) -> None:
        self.config = config or DigitalTwinRFConfig()
        c = self.config
        self._chain = [
            c.lna,
            c.mixer,
        ]
        self._measurement_history: list[dict[str, float]] = []

    def predict_cascaded_gain(self) -> float:
        return sum(c.gain_db for c in self._chain) - self.config.filter_loss_db

    def predict_noise_figure(self) -> float:
        f_total = 1.0
        gain_linear = 1.0
        for comp in self._chain:
            f = 10.0 ** (comp.noise_figure_db / 10.0)
            g = 10.0 ** (comp.gain_db / 10.0)
            f_total += (f - 1.0) / gain_linear
            gain_linear *= g
        return 10.0 * math.log10(f_total)

    def predict_sensitivity(self, bandwidth_hz: float = 1e6) -> float:
        nf = self.predict_noise_figure()
        thermal = -174.0 + 10.0 * math.log10(bandwidth_hz)
        return thermal + nf + 10.0

    def predict_linearity(self, input_power_dbm: float) -> tuple[bool, float]:
        cumulative = input_power_dbm
        for comp in self._chain:
            if not comp.is_linear(cumulative):
                return False, comp.output_power_dbm(cumulative)
            cumulative = comp.output_power_dbm(cumulative)
        return True, cumulative

    def predict_max_adc_snr(self) -> float:
        return 6.02 * self.config.adc_bits + 1.76

    def estimate_link_budget(
        self,
        tx_power_dbm: float,
        tx_gain_dbi: float,
        rx_gain_dbi: float,
        distance_m: float,
        frequency_hz: float,
    ) -> dict[str, float]:
        path_loss = 20.0 * math.log10(distance_m) + 20.0 * math.log10(frequency_hz) - 147.55
        received = tx_power_dbm + tx_gain_dbi + rx_gain_dbi - path_loss
        rx_sensitivity = self.predict_sensitivity()
        margin = received - rx_sensitivity
        result = {
            "tx_power_dbm": tx_power_dbm,
            "path_loss_db": path_loss,
            "received_power_dbm": received,
            "rx_sensitivity_dbm": rx_sensitivity,
            "margin_db": margin,
        }
        self._measurement_history.append(result)
        return result

    def summary(self) -> dict[str, float]:
        return {
            "cascaded_gain_db": self.predict_cascaded_gain(),
            "noise_figure_db": self.predict_noise_figure(),
            "sensitivity_dbm_1mhz": self.predict_sensitivity(1e6),
            "max_adc_snr_db": self.predict_max_adc_snr(),
        }
