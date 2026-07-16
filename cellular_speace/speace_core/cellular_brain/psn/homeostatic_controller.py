from __future__ import annotations

from typing import Dict, Optional

from speace_core.cellular_brain.psn.physiome import Physiome


class HomeostaticController:
    """PD controller for maintaining physiological setpoints.

    Applies proportional-derivative correction to stream signals that
    deviate from their homeostatic setpoints. This stabilises coherence
    (Φₒ) under perturbation by actively dampening deviations before
    they cascade through the dual-bus network.

    The controller reads setpoints from the Physiome's homeostatic_setpoints
    section and applies:

        correction = Kp × error + Kd × (current − previous)

    where error = setpoint − current_value.
    """

    def __init__(
        self,
        physiome: Physiome,
        Kp: float = 0.25,
        Kd: float = 0.08,
        max_correction: float = 0.15,
    ):
        self.Kp = Kp
        self.Kd = Kd
        self.max_correction = max_correction
        self._setpoints: Dict[str, Dict] = dict(physiome.homeostatic_setpoints or {})
        self._prev_values: Dict[str, float] = {}

    def compute_corrections(self, streams: Dict[str, float]) -> Dict[str, float]:
        """Compute PD corrections for all tracked signals.

        Returns a dict of {signal_id: correction_delta} for signals
        that need correction (|correction| > 0.001).
        """
        corrections: Dict[str, float] = {}
        for sid, current in streams.items():
            sp_raw = self._setpoints.get(sid)
            if sp_raw is None:
                continue
            target = sp_raw.get("setpoint", 0.5) if isinstance(sp_raw, dict) else 0.5
            error = target - current

            p_term = self.Kp * error
            prev = self._prev_values.get(sid, current)
            d_term = self.Kd * (current - prev)
            correction = p_term - d_term
            correction = max(-self.max_correction, min(self.max_correction, correction))

            if abs(correction) > 0.001:
                corrections[sid] = correction

            self._prev_values[sid] = current

        return corrections

    @property
    def tracked_signals(self) -> int:
        return len(self._setpoints)

    def has_setpoint(self, signal_id: str) -> bool:
        return signal_id in self._setpoints

    def clear(self) -> None:
        self._prev_values.clear()
