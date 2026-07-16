"""IncrementalProgressTracker — T4: metriche di progresso incrementale verso AGI.

Monitora:
  - miglioramento della coerenza (pendenza phi/coherence nel tempo)
  - crescita della complessità (nuove regioni, circuiti, tipi neuronali)
  - accuratezza metacognitiva (miglioramento confidence calibration)
  - autonomia (cicli di self-improvement senza intervento esterno)

Produce report di progresso con trend.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class ProgressMetrics:
    timestamp: float
    coherence_score: float = 0.0
    coherence_trend: float = 0.0  # slope (positive = improving)
    complexity_score: float = 0.0
    complexity_trend: float = 0.0
    metacognitive_accuracy: float = 0.0
    metacognitive_trend: float = 0.0
    autonomy_score: float = 0.0
    autonomy_trend: float = 0.0
    composite_progress: float = 0.0  # weighted average of all scores
    ticks_since_start: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class IncrementalProgressTracker:
    """Traccia il progresso incrementale di SPEACE verso AGI.

    Usage::

        tracker = IncrementalProgressTracker()
        metrics = tracker.tick(
            coherence_phi=0.85,
            n_regions=8,
            n_circuits=3,
            confidence_accuracy=0.72,
            self_improvement_cycles=15,
        )
    """

    def __init__(
        self,
        history_size: int = 1000,
        trend_window: int = 100,
        weights: Optional[Dict[str, float]] = None,
    ):
        self.history_size = history_size
        self.trend_window = trend_window

        self.weights = weights or {
            "coherence": 0.30,
            "complexity": 0.20,
            "metacognitive": 0.25,
            "autonomy": 0.25,
        }

        self._history: List[ProgressMetrics] = []
        self._tick_count: int = 0

    # ------------------------------------------------------------------ #
    # Tick
    # ------------------------------------------------------------------ #

    def tick(
        self,
        coherence_phi: Optional[float] = None,
        n_regions: int = 0,
        n_circuits: int = 0,
        n_neuron_types: int = 0,
        n_synapses: int = 0,
        confidence_accuracy: Optional[float] = None,
        confidence_calibration_error: Optional[float] = None,
        self_improvement_cycles: int = 0,
        successful_patches: int = 0,
        external_interventions: int = 0,
        **kwargs,
    ) -> ProgressMetrics:
        """Calcola metriche di progresso per questo tick."""
        self._tick_count += 1

        # --- Coherence progress ---
        coherence_score = coherence_phi if coherence_phi is not None else 0.0
        coherence_trend = self._compute_trend("coherence_score", coherence_score)

        # --- Complexity progress ---
        complexity_score = self._compute_complexity_score(
            n_regions, n_circuits, n_neuron_types, n_synapses
        )
        complexity_trend = self._compute_trend("complexity_score", complexity_score)

        # --- Metacognitive progress ---
        meta_score = 0.0
        if confidence_accuracy is not None:
            meta_score = confidence_accuracy
        elif confidence_calibration_error is not None:
            meta_score = 1.0 - min(1.0, confidence_calibration_error)
        metacognitive_trend = self._compute_trend("metacognitive_accuracy", meta_score)

        # --- Autonomy progress ---
        autonomy_score = self._compute_autonomy_score(
            self_improvement_cycles, successful_patches, external_interventions
        )
        autonomy_trend = self._compute_trend("autonomy_score", autonomy_score)

        # --- Composite ---
        composite = (
            self.weights["coherence"] * coherence_score
            + self.weights["complexity"] * complexity_score
            + self.weights["metacognitive"] * meta_score
            + self.weights["autonomy"] * autonomy_score
        )

        metrics = ProgressMetrics(
            timestamp=time.time(),
            coherence_score=round(coherence_score, 4),
            coherence_trend=round(coherence_trend, 6),
            complexity_score=round(complexity_score, 4),
            complexity_trend=round(complexity_trend, 6),
            metacognitive_accuracy=round(meta_score, 4),
            metacognitive_trend=round(metacognitive_trend, 6),
            autonomy_score=round(autonomy_score, 4),
            autonomy_trend=round(autonomy_trend, 6),
            composite_progress=round(min(1.0, composite), 4),
            ticks_since_start=self._tick_count,
        )

        self._history.append(metrics)
        if len(self._history) > self.history_size:
            self._history.pop(0)

        return metrics

    # ------------------------------------------------------------------ #
    # Score computations
    # ------------------------------------------------------------------ #

    def _compute_complexity_score(
        self,
        n_regions: int,
        n_circuits: int,
        n_neuron_types: int,
        n_synapses: int,
    ) -> float:
        """Calcola punteggio di complessità normalizzato.

        Considera:
        - numero regioni (max atteso ~20)
        - numero circuiti (max atteso ~10)
        - numero tipi neuronali (max atteso ~8)
        - numero sinapsi (max atteso ~10000)
        """
        r_score = min(1.0, n_regions / 20.0)
        c_score = min(1.0, n_circuits / 10.0)
        t_score = min(1.0, n_neuron_types / 8.0)
        s_score = min(1.0, n_synapses / 10000.0)

        return (r_score * 0.3 + c_score * 0.3 + t_score * 0.2 + s_score * 0.2)

    def _compute_autonomy_score(
        self,
        self_improvement_cycles: int,
        successful_patches: int,
        external_interventions: int,
    ) -> float:
        """Autonomia: capacità di auto-migliorarsi senza interventi esterni.

        Formula: (successful_patches + 1) / (external_interventions + 1)
        scalato e normalizzato.
        """
        if external_interventions == 0 and self_improvement_cycles == 0:
            return 0.0

        ratio = (successful_patches + 1) / max(external_interventions + 1, 1)
        # Normalize: ratio of 10+ = high autonomy
        autonomy = 1.0 - (1.0 / ratio) if ratio > 0 else 0.0

        # Also factor in total self-improvement cycles
        cycle_factor = min(1.0, self_improvement_cycles / 100.0)

        return round((autonomy * 0.6 + cycle_factor * 0.4), 4)

    # ------------------------------------------------------------------ #
    # Trend estimation
    # ------------------------------------------------------------------ #

    def _compute_trend(self, field_name: str, current_value: float) -> float:
        """Stima la pendenza (slope) lineare semplice negli ultimi N punti."""
        window = min(self.trend_window, len(self._history))
        if window < 2:
            return 0.0

        recent = self._history[-window:]
        values = [getattr(m, field_name, 0.0) for m in recent]

        # Add current value
        values.append(current_value)
        n = len(values)
        if n < 2:
            return 0.0

        # Linear regression: slope = (n*sum(xy) - sum(x)*sum(y)) / (n*sum(xx) - sum(x)^2)
        xs = list(range(n))
        sum_x = sum(xs)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(xs, values))
        sum_xx = sum(x * x for x in xs)

        denom = n * sum_xx - sum_x * sum_x
        if denom == 0:
            return 0.0

        slope = (n * sum_xy - sum_x * sum_y) / denom
        return slope

    # ------------------------------------------------------------------ #
    # Diagnostics
    # ------------------------------------------------------------------ #

    def get_progress_report(self) -> Dict[str, Any]:
        """Report completo di progresso."""
        if not self._history:
            return {"status": "no_data"}

        latest = self._history[-1]
        # Overall trend direction
        overall_trend = "improving" if latest.composite_progress > (
            self._history[0].composite_progress if self._history else 0
        ) else "stable"

        return {
            "timestamp": latest.timestamp,
            "ticks_since_start": latest.ticks_since_start,
            "composite_progress": latest.composite_progress,
            "overall_trend": overall_trend,
            "components": {
                "coherence": {
                    "score": latest.coherence_score,
                    "trend": latest.coherence_trend,
                    "direction": "improving" if latest.coherence_trend > 0 else (
                        "declining" if latest.coherence_trend < 0 else "stable"
                    ),
                },
                "complexity": {
                    "score": latest.complexity_score,
                    "trend": latest.complexity_trend,
                    "direction": "improving" if latest.complexity_trend > 0 else (
                        "declining" if latest.complexity_trend < 0 else "stable"
                    ),
                },
                "metacognitive": {
                    "score": latest.metacognitive_accuracy,
                    "trend": latest.metacognitive_trend,
                    "direction": "improving" if latest.metacognitive_trend > 0 else (
                        "declining" if latest.metacognitive_trend < 0 else "stable"
                    ),
                },
                "autonomy": {
                    "score": latest.autonomy_score,
                    "trend": latest.autonomy_trend,
                    "direction": "improving" if latest.autonomy_trend > 0 else (
                        "declining" if latest.autonomy_trend < 0 else "stable"
                    ),
                },
            },
            "history_length": len(self._history),
        }

    def get_progress_since(self, tick_start: int) -> float:
        """Delta di progresso composito da un tick specifico."""
        relevant = [m for m in self._history if m.ticks_since_start >= tick_start]
        if len(relevant) < 2:
            return 0.0
        return round(relevant[-1].composite_progress - relevant[0].composite_progress, 4)

    def get_milestone_progress(self) -> Dict[str, float]:
        """Progresso verso milestone AGI predefinite."""
        if not self._history:
            return {}

        latest = self._history[-1]

        return {
            "coherence_milestone_095": min(
                1.0, latest.coherence_score / 0.95
            ),
            "complexity_milestone_10regions": min(
                1.0, latest.complexity_score / 0.5
            ),
            "metacognitive_milestone_090": min(
                1.0, latest.metacognitive_accuracy / 0.9
            ),
            "autonomy_milestone_independent": min(
                1.0, latest.autonomy_score / 0.8
            ),
            "overall_milestone_agi": min(
                1.0, latest.composite_progress / 0.85
            ),
        }
