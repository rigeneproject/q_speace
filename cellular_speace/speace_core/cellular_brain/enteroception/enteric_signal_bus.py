"""EntericSignalBus — the "vagus nerve" of SPEACE.

80 % afferent (gut → brain): carries microbiome state, metabolite
profile, and inflammation level to the workspace and interoception.

20 % efferent (brain → gut): carries stress and drive signals to
modulate the microbiome.

The bus operates on a slower timescale than neural modulation to
prevent rapid gut-brain oscillations.
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

_logger = logging.getLogger(__name__)


ENTERCEPTION_CHANNELS = (
    "microbiome_diversity",
    "scfa_level",
    "gut_serotonin",
    "gut_gaba",
    "gut_dopamine",
    "gut_inflammation",
    "novelty_boost",
    "gut_feeling",
)


@dataclass
class EnteroceptiveSnapshot:
    tick: int
    wall_time: float
    signals: Dict[str, float] = field(default_factory=dict)
    gut_feeling: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tick": self.tick,
            "wall_time": self.wall_time,
            "signals": dict(self.signals),
            "gut_feeling": float(self.gut_feeling),
        }


class EntericSignalBus:
    def __init__(
        self,
        update_interval: int = 10,
        channels: Optional[List[str]] = None,
    ):
        self.update_interval = update_interval
        self.channels: List[str] = list(channels or list(ENTERCEPTION_CHANNELS))
        self._tick: int = 0
        self._ticks_since_update: int = 0
        self._snapshot: EnteroceptiveSnapshot = EnteroceptiveSnapshot(
            tick=0, wall_time=time.time()
        )
        self._history: List[EnteroceptiveSnapshot] = []
        self._max_history: int = 512

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def read(
        self,
        microbiome_modulator: Any = None,
        stress_level: float = 0.0,
        coherence: float = 0.5,
    ) -> Optional[EnteroceptiveSnapshot]:
        """Sample the microbiome and produce an enteroceptive snapshot.

        Only produces a new snapshot every ``update_interval`` ticks to
        model the slower gut-brain timescale.  Returns ``None`` on
        intermediate ticks.
        """
        self._tick += 1
        self._ticks_since_update += 1

        if self._ticks_since_update < self.update_interval:
            return None

        self._ticks_since_update = 0

        signals: Dict[str, float] = {}

        if microbiome_modulator is not None:
            diversity = self._safe_call(microbiome_modulator, "get_diversity", default=0.5)
            signals["microbiome_diversity"] = max(0.0, min(1.0, float(diversity)))

            metabolites = self._safe_call(microbiome_modulator, "tick", default=None,
                                          stress_level=stress_level,
                                          substrate_input=0.5,
                                          coherence=coherence)
            if metabolites is None:
                metabolites = {}
        else:
            signals["microbiome_diversity"] = 0.5
            metabolites = {}

        signals["scfa_level"] = float(metabolites.get("scfa", 0.0))
        signals["gut_serotonin"] = float(metabolites.get("serotonin_precursor", 0.0))
        signals["gut_gaba"] = float(metabolites.get("gaba_precursor", 0.0))
        signals["gut_dopamine"] = float(metabolites.get("dopamine_precursor", 0.0))
        signals["gut_inflammation"] = float(metabolites.get("inflammatory_cytokine", 0.0))
        signals["novelty_boost"] = float(metabolites.get("novelty_signal", 0.0))

        for k in signals:
            signals[k] = max(0.0, min(1.0, signals[k]))

        gut_feeling = self._compute_gut_feeling(signals)
        signals["gut_feeling"] = gut_feeling

        snap = EnteroceptiveSnapshot(
            tick=self._tick,
            wall_time=time.time(),
            signals=signals,
            gut_feeling=gut_feeling,
        )
        self._snapshot = snap
        self._history.append(snap)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history // 2:]
        return snap

    def vector(self, snapshot: Optional[EnteroceptiveSnapshot] = None) -> List[float]:
        snap = snapshot or self._snapshot
        return [float(snap.signals.get(c, 0.0)) for c in self.channels]

    def get_gut_feeling(self, snapshot: Optional[EnteroceptiveSnapshot] = None) -> float:
        return float((snapshot or self._snapshot).gut_feeling)

    def broadcast_to_workspace(self, workspace: Any, target_dim: int = 64) -> None:
        if workspace is None or not hasattr(workspace, "broadcast"):
            return
        vec = self.vector()
        if len(vec) < target_dim:
            vec = vec + [0.0] * (target_dim - len(vec))
        else:
            vec = vec[:target_dim]
        try:
            workspace.broadcast("enteroception", vec)
        except Exception as exc:
            _logger.debug("Enteroceptive broadcast failed: %s", exc)

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #

    def save_history(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump([s.to_dict() for s in self._history], fh, indent=2)

    @property
    def last_snapshot(self) -> EnteroceptiveSnapshot:
        return self._snapshot

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _compute_gut_feeling(self, signals: Dict[str, float]) -> float:
        low_diversity = max(0.0, 1.0 - signals.get("microbiome_diversity", 0.5))
        inflammation = signals.get("gut_inflammation", 0.0)
        return min(1.0, low_diversity * 0.5 + inflammation * 0.5)

    @staticmethod
    def _safe_call(obj: Any, method_name: str, default: Any = None, **kwargs) -> Any:
        if obj is None:
            return default
        method = getattr(obj, method_name, None)
        if method is None or not callable(method):
            return default
        try:
            return method(**kwargs)
        except Exception:
            return default
