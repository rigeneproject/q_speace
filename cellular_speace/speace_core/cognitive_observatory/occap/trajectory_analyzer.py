from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from speace_core.cognitive_observatory.occap.occap_calculator import OCCapState


@dataclass
class TrajectoryPoint:
    tick: int
    occap: float
    speed: float
    acceleration: float
    phase_coords: Tuple[float, float, float]

    @property
    def stability(self) -> float:
        return 1.0 - min(1.0, abs(self.acceleration) * 10)


@dataclass
class DevelopmentalStage:
    name: str
    start_tick: int
    end_tick: int
    mean_occap: float
    mean_speed: float
    mean_stability: float
    trajectory_volume: float


class TrajectoryAnalyzer:
    """Analyzes Ψ(t) — the evolutionary trajectory of Ω through state space.

    Tracks state-field history, computes speed, acceleration, stability,
    phase portrait coordinates, and developmental stages.
    """

    def __init__(self, window: int = 100):
        self.window = window
        self._history: List[OCCapState] = []
        self._trajectory: List[TrajectoryPoint] = []
        self._stages: List[DevelopmentalStage] = []
        self._current_stage_start: int = 0

    def update(self, state: OCCapState) -> None:
        """Append a state and recompute trajectory metrics."""
        self._history.append(state)
        self._trajectory.append(self._compute_point(state))
        self._detect_stages()

    def _compute_point(self, state: OCCapState) -> TrajectoryPoint:
        tick = state.tick

        # Speed: |ΔΩ| / Δt (Euclidean distance in state space)
        speed = 0.0
        if len(self._history) >= 2:
            prev = self._history[-2]
            dims = [state.occap - prev.occap, state.C_mag - prev.C_mag]
            if len(self._history) >= 3:
                dims.append(state.I - prev.I)
            speed = math.sqrt(sum(d ** 2 for d in dims))

        # Acceleration: Δspeed / Δt
        acceleration = 0.0
        if len(self._trajectory) >= 1:
            prev_speed = self._trajectory[-1].speed
            acceleration = speed - prev_speed

        # Phase coordinates: projection of Ω into 3D phase space
        phase_coords = (
            state.occap,
            state.I,
            state.Phi,
        )

        return TrajectoryPoint(
            tick=tick,
            occap=state.occap,
            speed=round(speed, 4),
            acceleration=round(acceleration, 4),
            phase_coords=phase_coords,
        )

    @property
    def current_speed(self) -> float:
        if not self._trajectory:
            return 0.0
        return self._trajectory[-1].speed

    @property
    def current_acceleration(self) -> float:
        if not self._trajectory:
            return 0.0
        return self._trajectory[-1].acceleration

    @property
    def current_stability(self) -> float:
        if not self._trajectory:
            return 1.0
        return self._trajectory[-1].stability

    @property
    def exploration_volume(self) -> float:
        """Volume of state space explored (bounding box product)."""
        if len(self._history) < 2:
            return 0.0
        occap_vals = [s.occap for s in self._history]
        i_vals = [s.I for s in self._history]
        phi_vals = [s.Phi for s in self._history]
        vol = (
            (max(occap_vals) - min(occap_vals))
            * (max(i_vals) - min(i_vals))
            * (max(phi_vals) - min(phi_vals))
        )
        return round(max(0.0, vol), 4)

    def _detect_stages(self) -> None:
        """Detect developmental stages based on speed and stability changes."""
        if len(self._trajectory) < 20:
            return

        recent = self._trajectory[-20:]
        avg_speed = sum(p.speed for p in recent) / len(recent)
        avg_stability = sum(p.stability for p in recent) / len(recent)

        latest = self._trajectory[-1]
        current_stage_name = self._classify_stage(avg_speed, avg_stability, latest.occap)

        if not self._stages:
            self._stages.append(DevelopmentalStage(
                name=current_stage_name,
                start_tick=0,
                end_tick=latest.tick,
                mean_occap=latest.occap,
                mean_speed=avg_speed,
                mean_stability=avg_stability,
                trajectory_volume=self.exploration_volume,
            ))
            return

        current = self._stages[-1]
        if current.name != current_stage_name and latest.tick - current.start_tick >= 20:
            current.end_tick = latest.tick
            self._stages.append(DevelopmentalStage(
                name=current_stage_name,
                start_tick=latest.tick,
                end_tick=latest.tick,
                mean_occap=latest.occap,
                mean_speed=avg_speed,
                mean_stability=avg_stability,
                trajectory_volume=self.exploration_volume,
            ))
        else:
            current.end_tick = latest.tick
            # Update running averages
            stage_states = [
                s for s in self._history
                if current.start_tick <= s.tick <= latest.tick
            ]
            if stage_states:
                current.mean_occap = sum(s.occap for s in stage_states) / len(stage_states)
            current.mean_speed = avg_speed
            current.mean_stability = avg_stability
            current.trajectory_volume = self.exploration_volume

    @staticmethod
    def _classify_stage(speed: float, stability: float, occap: float) -> str:
        if occap < 0.3 and speed > 0.01:
            return "emergence"
        if speed > 0.05:
            return "rapid_growth"
        if stability > 0.8 and occap > 0.6:
            return "maturity"
        if stability > 0.6:
            return "consolidation"
        if speed < 0.01 and occap < 0.4:
            return "stagnation"
        return "adaptation"

    def get_stages_report(self) -> List[Dict]:
        return [
            {
                "name": s.name,
                "start_tick": s.start_tick,
                "end_tick": s.end_tick,
                "mean_occap": s.mean_occap,
                "mean_speed": s.mean_speed,
                "mean_stability": s.mean_stability,
                "trajectory_volume": s.trajectory_volume,
            }
            for s in self._stages
        ]

    def get_trajectory_summary(self) -> Dict:
        if not self._trajectory:
            return {"ticks_tracked": 0}

        return {
            "ticks_tracked": len(self._trajectory),
            "current_speed": self.current_speed,
            "current_acceleration": self.current_acceleration,
            "current_stability": self.current_stability,
            "exploration_volume": self.exploration_volume,
            "current_stage": self._stages[-1].name if self._stages else "unknown",
            "stages": self.get_stages_report(),
        }

    def clear(self) -> None:
        self._history.clear()
        self._trajectory.clear()
        self._stages.clear()
