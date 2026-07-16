"""T172 — PerceivedEntropyModule.

Module A of the Information Value triad.

Goal
----
Aggregate the *perceived* entropy of the current organismic context into a
single scalar ``H_local(t) ∈ [0, 1]``. The aggregation is a read-only
observer: it never mutates the underlying engines it taps into.

Inputs (all optional, defaults to 0.0)
-------------------------------------
- ``prediction_error``        — from ``PredictiveCodingEngine.get_prediction_error``
- ``informational_entropy``   — from ``EntropyDynamicsMonitor.summarize()``
- ``signal_diversity``        — from ``InformationDensityEngine`` compartments
- ``novelty``                  — from ``InfantCuriosityLayer.get_average_curiosity``
- ``surprise``                 — from ``ActiveInferenceEngine.expected_free_energy``

Mapping to DNA principles
-------------------------
- ``destructive_entropy_reduction`` (S_ent): high H_local ⇒ pressure to reduce
  destructive entropy through homeostasis / pruning.
- ``generative_variability_preservation`` (V_gen): low H_local ⇒ pressure to
  inject variability / exploration. We do NOT modify the principles; we
  expose a derived scalar.

BCEL classification
--------------------
- Biological structure: integrated cortical + limbic entropy signals
- Functional constraint: ``coherence_preservation`` + ``destructive_entropy_reduction``
- Digital synthesis: weighted aggregate over already-existing scalar signals
- Removed (accidental): raw EEG entropy, neurotransmitter half-lives

Safety
------
This module is a passive observer. It does not write to the genome, the
BCEL catalog, the immune system, or the orchestrator. It only emits
:class:`PerceivedEntropySnapshot` records for downstream policy/value modules
and the Omni-RAG runtime collector.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class PerceivedEntropySnapshot:
    """A single observation of perceived entropy at time t."""

    timestamp: float
    H_local: float
    components: Dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "H_local": round(self.H_local, 6),
            "components": {k: round(v, 6) for k, v in self.components.items()},
            "notes": list(self.notes),
        }


class PerceivedEntropyModule:
    """Aggregates perceived entropy from existing SPEACE signals.

    Usage::

        module = PerceivedEntropyModule()
        snap = module.observe({
            "prediction_error": 0.42,
            "novelty": 0.7,
            "informational_entropy": 0.55,
            "signal_diversity": 0.6,
        })
        # snap.H_local ∈ [0, 1]
    """

    # Default weights — sum to 1.0
    DEFAULT_WEIGHTS: Dict[str, float] = {
        "prediction_error": 0.30,
        "novelty": 0.25,
        "informational_entropy": 0.20,
        "signal_diversity": 0.15,
        "surprise": 0.10,
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None) -> None:
        self._weights: Dict[str, float] = dict(weights or self.DEFAULT_WEIGHTS)
        # Renormalize defensively
        total = sum(max(0.0, w) for w in self._weights.values())
        if total > 0:
            self._weights = {k: max(0.0, v) / total for k, v in self._weights.items()}
        else:
            self._weights = dict(self.DEFAULT_WEIGHTS)
        self._history: list[PerceivedEntropySnapshot] = []

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def observe(self, signals: Dict[str, float]) -> PerceivedEntropySnapshot:
        """Compute H_local from the supplied signals.

        Any missing signal contributes 0.0 (with a note). Signals outside
        ``[0, 1]`` are clipped.
        """
        components: Dict[str, float] = {}
        notes: list[str] = []

        for key, w in self._weights.items():
            raw = signals.get(key)
            if raw is None:
                components[key] = 0.0
                notes.append(f"missing:{key}")
                continue
            try:
                v = float(raw)
            except (TypeError, ValueError):
                components[key] = 0.0
                notes.append(f"non_numeric:{key}")
                continue
            components[key] = max(0.0, min(1.0, v))

        H_local = sum(self._weights[k] * components[k] for k in self._weights)
        H_local = max(0.0, min(1.0, H_local))

        snap = PerceivedEntropySnapshot(
            timestamp=time.time(),
            H_local=H_local,
            components=components,
            notes=notes,
        )
        self._history.append(snap)
        if len(self._history) > 1024:
            self._history = self._history[-512:]
        return snap

    def history(self, limit: int = 50) -> list[PerceivedEntropySnapshot]:
        return list(self._history[-limit:])

    def mean(self, window: int = 50) -> float:
        if not self._history:
            return 0.0
        recent = self._history[-window:]
        return sum(s.H_local for s in recent) / len(recent)

    def derivative(self, window: int = 5) -> float:
        """Return the average H_local delta over the last ``window`` snapshots."""
        if len(self._history) < 2:
            return 0.0
        recent = self._history[-max(2, window):]
        deltas = [
            recent[i].H_local - recent[i - 1].H_local
            for i in range(1, len(recent))
        ]
        return sum(deltas) / len(deltas) if deltas else 0.0

    def summary(self) -> Dict[str, Any]:
        return {
            "current_H_local": round(self._history[-1].H_local, 6) if self._history else 0.0,
            "mean_H_local": round(self.mean(), 6),
            "derivative": round(self.derivative(), 6),
            "n_snapshots": len(self._history),
            "weights": dict(self._weights),
        }

    @staticmethod
    def shannon_normalised(values: list[float]) -> float:
        """Helper: normalised Shannon entropy in [0, 1] from a vector."""
        if not values:
            return 0.0
        total = sum(max(0.0, v) for v in values)
        if total <= 0:
            return 0.0
        probs = [max(0.0, v) / total for v in values]
        probs = [p for p in probs if p > 0]
        if not probs:
            return 0.0
        H = -sum(p * math.log(p) for p in probs)
        max_H = math.log(len(probs)) if len(probs) > 1 else 1.0
        return H / max_H if max_H > 0 else 0.0
