from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from speace_core.cellular_brain.psn.physiological_signal_bus import PhysiologicalSignalBus

from speace_core.cognitive_observatory.occap.complexity_metrics import ComplexityMetrics
from speace_core.cognitive_observatory.occap.integration_metrics import IntegrationMetrics
from speace_core.cognitive_observatory.occap.plasticity_metrics import PlasticityMetrics
from speace_core.cognitive_observatory.occap.coherence_metrics import CoherenceMetrics
from speace_core.cognitive_observatory.occap.metabolic_metrics import MetabolicMetrics
from speace_core.cognitive_observatory.occap.resilience_metrics import ResilienceMetrics
from speace_core.cognitive_observatory.occap.efficiency_metrics import EfficiencyMetrics
from speace_core.cognitive_observatory.occap.trajectory_analyzer import TrajectoryAnalyzer


# ── Data structures ─────────────────────────────────────────────


@dataclass
class ComplexityVector:
    """5-dimensional complexity vector C = [C_s, C_f, C_r, C_i, C_t]."""
    structural: float = 0.0
    functional: float = 0.0
    regulatory: float = 0.0
    informational: float = 0.0
    temporal: float = 0.0

    @property
    def magnitude(self) -> float:
        """Weighted |C| with default w_C = [0.25, 0.20, 0.20, 0.15, 0.20]."""
        w = [0.25, 0.20, 0.20, 0.15, 0.20]
        return (
            w[0] * self.structural
            + w[1] * self.functional
            + w[2] * self.regulatory
            + w[3] * self.informational
            + w[4] * self.temporal
        )

    def as_tuple(self) -> Tuple[float, float, float, float, float]:
        return (self.structural, self.functional, self.regulatory, self.informational, self.temporal)


@dataclass
class OCCapState:
    """Full state field Ω(t) = {C, I, P, Φₒ, M, R} with computed metrics."""
    tick: int
    C: ComplexityVector = field(default_factory=ComplexityVector)
    I: float = 0.0
    P: float = 0.0
    Phi: float = 0.0
    M: float = 0.0
    R: float = 0.0
    occap: float = 0.0
    oceff: float = 0.0
    C_mag: float = 0.0
    weights_used: Dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "tick": self.tick,
            "C_s": self.C.structural,
            "C_f": self.C.functional,
            "C_r": self.C.regulatory,
            "C_i": self.C.informational,
            "C_t": self.C.temporal,
            "C_mag": self.C_mag,
            "I": self.I,
            "P": self.P,
            "Phi": self.Phi,
            "M": self.M,
            "R": self.R,
            "occap": self.occap,
            "oceff": self.oceff,
        }


# ── Autoregulation threshold presets ────────────────────────────

AUTOREGULATION_DEFAULTS = {
    "M_crisis": 0.2,
    "Phi_crisis": 0.3,
    "P_min": 0.15,
    "R_min": 0.2,
    "OCEff_target": 0.1,
}


# ── Main calculator ─────────────────────────────────────────────


class OCCapCalculator:
    """Main OCCap computation engine.

    Takes a PhysiologicalSignalBus reference and computes Ω(t) = {C, I, P, Φₒ, M, R}
    and OCEff(t) with configurable update frequencies per sub-metric.
    """

    # Update intervals (ticks between recomputations)
    DEFAULT_INTERVALS: Dict[str, int] = {
        "C": 100,
        "I": 1,
        "P": 50,
        "Phi": 10,
        "M": 1,
        "R": 50,
        "OCCap": 10,
        "OCEff": 10,
    }

    # Default OCCap weights: [w_C, w_I, w_P, w_Phi, w_M, w_R]
    DEFAULT_OCCAP_WEIGHTS = [0.20, 0.20, 0.15, 0.20, 0.10, 0.15]

    def __init__(
        self,
        psn: PhysiologicalSignalBus,
        occap_weights: Optional[List[float]] = None,
        intervals: Optional[Dict[str, int]] = None,
        autoregulation_thresholds: Optional[Dict[str, float]] = None,
    ):
        self.psn = psn
        self.occap_weights = occap_weights or list(self.DEFAULT_OCCAP_WEIGHTS)
        self.intervals = {**self.DEFAULT_INTERVALS, **(intervals or {})}
        self.autoreg = {**AUTOREGULATION_DEFAULTS, **(autoregulation_thresholds or {})}

        # Sub-metric providers
        self.complexity = ComplexityMetrics(psn)
        self.integration = IntegrationMetrics(psn)
        self.plasticity = PlasticityMetrics(psn)
        self.coherence = CoherenceMetrics(psn)
        self.metabolic = MetabolicMetrics(psn)
        self.resilience = ResilienceMetrics(psn)
        self.efficiency = EfficiencyMetrics(psn)
        self.trajectory = TrajectoryAnalyzer()

        # Cached values (updated at their respective intervals)
        self._C: ComplexityVector = ComplexityVector()
        self._I: float = 0.0
        self._P: float = 0.0
        self._Phi: float = 0.0
        self._M: float = 0.0
        self._R: float = 0.0

        # Last-computed tick per metric
        self._last_tick: Dict[str, int] = {
            "C": -1000, "I": -1, "P": -1000,
            "Phi": -100, "M": -1, "R": -1000,
            "OCCap": -100, "OCEff": -100,
        }

        # History of computed states
        self._history: List[OCCapState] = []
        self._state_cache: Optional[OCCapState] = None

    # ── Public API ──────────────────────────────────────────────

    def compute(self, tick: int) -> OCCapState:
        """Compute Ω(t) for the current tick.

        Only re-computes sub-metrics that are due for update.
        """
        # Update each component if its interval has elapsed
        if tick - self._last_tick["C"] >= self.intervals["C"]:
            c_tuple = self.complexity.compute(tick)
            self._C = ComplexityVector(*c_tuple)
            self._last_tick["C"] = tick

        if tick - self._last_tick["I"] >= self.intervals["I"]:
            self._I = self.integration.compute(tick)
            self._last_tick["I"] = tick

        if tick - self._last_tick["P"] >= self.intervals["P"]:
            self._P = self.plasticity.compute(tick)
            self._last_tick["P"] = tick

        if tick - self._last_tick["Phi"] >= self.intervals["Phi"]:
            self._Phi = self.coherence.compute(tick)
            self._last_tick["Phi"] = tick

        if tick - self._last_tick["M"] >= self.intervals["M"]:
            self._M = self.metabolic.compute(tick)
            self._last_tick["M"] = tick

        if tick - self._last_tick["R"] >= self.intervals["R"]:
            self._R = self.resilience.compute(tick)
            self._last_tick["R"] = tick

        # OCCap composite (default every 10 ticks)
        C_mag = self._C.magnitude
        w = self.occap_weights
        occap = self._state_cache.occap if self._state_cache else 0.0
        if tick - self._last_tick["OCCap"] >= self.intervals["OCCap"]:
            occap = (
                w[0] * C_mag
                + w[1] * self._I
                + w[2] * self._P
                + w[3] * self._Phi
                + w[4] * self._M
                + w[5] * self._R
            )
            occap = max(0.0, min(1.0, occap))
            self._last_tick["OCCap"] = tick

        # OCEff
        state_for_efficiency = OCCapState(
            tick=tick,
            C=self._C,
            I=self._I,
            P=self._P,
            Phi=self._Phi,
            M=self._M,
            R=self._R,
            occap=occap,
            oceff=0.0,
            C_mag=C_mag,
            weights_used={
                "w_C": w[0], "w_I": w[1], "w_P": w[2],
                "w_Phi": w[3], "w_M": w[4], "w_R": w[5],
            },
        )

        oceff = self._state_cache.oceff if self._state_cache else 0.0
        if tick - self._last_tick["OCEff"] >= self.intervals["OCEff"]:
            oceff = self.efficiency.compute(state_for_efficiency, tick)
            self._last_tick["OCEff"] = tick

        state = OCCapState(
            tick=tick,
            C=self._C,
            I=self._I,
            P=self._P,
            Phi=self._Phi,
            M=self._M,
            R=self._R,
            occap=occap,
            oceff=oceff,
            C_mag=C_mag,
            weights_used={
                "w_C": w[0], "w_I": w[1], "w_P": w[2],
                "w_Phi": w[3], "w_M": w[4], "w_R": w[5],
            },
        )

        self._state_cache = state
        self._history.append(state)
        self.trajectory.update(state)

        self._check_autoregulation(state, tick)
        return state

    @property
    def current_state(self) -> Optional[OCCapState]:
        return self._state_cache

    @property
    def history(self) -> List[OCCapState]:
        return list(self._history)

    def clear_history(self) -> None:
        self._history.clear()
        self.trajectory.clear()

    # ── Autoregulation ──────────────────────────────────────────

    ACTIVATE_MESSAGE = "occap.autoregulation.activate"

    def _check_autoregulation(self, state: OCCapState, tick: int) -> None:
        actions = []

        if state.M < self.autoreg["M_crisis"]:
            actions.append("energy_conservation")
        if state.Phi < self.autoreg["Phi_crisis"]:
            actions.append("coherence_restoration")
        if state.P < self.autoreg["P_min"]:
            actions.append("plasticity_boost")
        if state.R < self.autoreg["R_min"]:
            actions.append("resilience_program")
        if state.oceff < self.autoreg["OCEff_target"] and tick > 100:
            actions.append("efficiency_optimisation")

        if actions:
            self.psn.set_meta_signal("occap_autoreg_actions", 1.0)

    # ── Convenience ─────────────────────────────────────────────

    def get_full_report(self, tick: int) -> Dict[str, Any]:
        state = self.compute(tick)
        return {
            "omega": state.as_dict(),
            "trajectory": self.trajectory.get_trajectory_summary(),
            "history_length": len(self._history),
            "autoregulation_thresholds": dict(self.autoreg),
            "weights": {
                "occap": self.occap_weights,
            },
        }
