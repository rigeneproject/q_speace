"""T172 — ExplorationPolicy (Module C of the Information Value triad).

Implements the deterministic policy ``π(a|s, V)`` that maps an organismic
state ``s`` and the current informational value ``V`` to a proposed action.

Critically: this module **proposes** actions through the existing
``EmbodiedActionActuator`` governance layer. It never executes actions
directly. This keeps the policy inside the safety envelope defined by
``AGENTS.md`` §3 (cyber-physical domain requires human gate).

Inputs
------
- ``state``  : dict of scalar signals (energy, coherence, novelty, ...)
- ``V``      : the informational value from :class:`InformationalValueFunction`

Output
------
- :class:`ActionProposal` (kind, params, score, rationale)

The proposal kinds are intentionally narrow and map 1-to-1 to the
``DEFAULT_ACTION_MAP`` of :class:`ActiveInferenceEmbodiedLoop`. This means
the proposal can be fed directly to ``EmbodiedActionActuator.propose_action``
without any new actuator wiring.

Mapping to DNA
--------------
The policy does not modify the genome. It encodes the missing BCEL
equivalence ``motivational_dopaminergic_loop``: a closed-loop policy that
selects actions so as to maintain V in the sweet-spot band. When V drops
below the starvation threshold the policy pushes toward exploration; when
V climbs toward the chaotic regime the policy pushes toward consolidation.

Mapping to BCEL
---------------
- Biological structure: dopaminergic reward prediction error loop
- Preserved function: select actions that maximise an internal reward
  surrogate (here: V)
- Removed constraints (accidental): vesicle release latency, receptor
  desensitization kinetics
- Kept constraints (functional): value-based action selection,
  exploration/exploitation balance, satiation / starvation signals
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple


class ProposalKind(str, Enum):
    """The narrow set of proposal kinds accepted by ``EmbodiedActionActuator``.

    Kept in lock-step with :class:`ActiveInferenceEmbodiedLoop.DEFAULT_ACTION_MAP`.
    """

    OBSERVE = "observe"
    ACTUATE = "actuate"
    REQUEST_SLEEP = "request_sleep"
    REQUEST_RESUME = "request_resume"
    CHECKPOINT = "checkpoint"
    GARBAGE_COLLECT = "garbage_collect"


@dataclass
class ActionProposal:
    """A *proposal* emitted by the exploration policy.

    It is intentionally a value object — not an executed action. The caller
    is expected to forward it through the existing action governance.
    """

    kind: ProposalKind
    params: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    rationale: str = ""
    regime: str = ""
    V: float = 0.0
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind.value,
            "params": dict(self.params),
            "score": round(self.score, 6),
            "rationale": self.rationale,
            "regime": self.regime,
            "V": round(self.V, 6),
            "timestamp": self.timestamp,
        }


class ExplorationPolicy:
    """Deterministic policy ``π(a | s, V)``.

    The policy is intentionally simple and auditable. It is built from a
    small set of regime-dependent rules, all driven by the informational
    value ``V`` and a handful of organismic signals.
    """

    # V_normalised thresholds (see InformationalValueFunction).
    STARVATION_V: float = -0.30  # below this → push to explore aggressively
    CHAOS_V: float = -0.30      # alias for symmetry with chaos regime
    SWEET_LOWER: float = 0.10   # inside this band → low-pressure maintenance
    SWEET_UPPER: float = 0.60   # inside this band → low-pressure maintenance
    SATIATION_V: float = 0.40   # above this → reduce exploration pressure

    # Energy / coherence guard rails
    ENERGY_LOW: float = 0.25
    COHERENCE_LOW: float = 0.25

    def __init__(
        self,
        novelty_weight: float = 0.35,
        energy_weight: float = 0.25,
        coherence_weight: float = 0.20,
        value_weight: float = 0.20,
    ) -> None:
        total = novelty_weight + energy_weight + coherence_weight + value_weight
        if total <= 0:
            raise ValueError("weights must sum to a positive number")
        self._w = {
            "novelty": novelty_weight / total,
            "energy": energy_weight / total,
            "coherence": coherence_weight / total,
            "value": value_weight / total,
        }
        self._history: list[ActionProposal] = []

    # ------------------------------------------------------------------ #
    # Core policy
    # ------------------------------------------------------------------ #

    def propose(
        self,
        state: Dict[str, float],
        V: float,
    ) -> ActionProposal:
        """Compute the next action proposal given ``state`` and ``V``."""
        novelty = self._g(state, "novelty", 0.5)
        energy = self._g(state, "energy", 1.0)
        coherence = self._g(state, "coherence", 1.0)
        regime = self._classify_regime(V, energy, coherence)

        # Score baseline: weighted sum of state signals + V term.
        score = (
            self._w["novelty"] * novelty
            + self._w["energy"] * energy
            + self._w["coherence"] * coherence
            + self._w["value"] * max(0.0, (V + 1.0) / 2.0)
        )

        kind, params, rationale = self._select_action(
            regime=regime,
            novelty=novelty,
            energy=energy,
            coherence=coherence,
        )

        proposal = ActionProposal(
            kind=kind,
            params=params,
            score=score,
            rationale=rationale,
            regime=regime,
            V=V,
            timestamp=time.time(),
        )
        self._history.append(proposal)
        if len(self._history) > 1024:
            self._history = self._history[-512:]
        return proposal

    # ------------------------------------------------------------------ #
    # Regime classification
    # ------------------------------------------------------------------ #

    def _classify_regime(self, V: float, energy: float, coherence: float) -> str:
        # Safety overrides always win.
        if energy < self.ENERGY_LOW:
            return "energy_crisis"
        if coherence < self.COHERENCE_LOW:
            return "coherence_crisis"

        if V < self.STARVATION_V:
            return "starvation"  # too rigid / too chaotic → must explore
        if self.SWEET_LOWER <= V <= self.SWEET_UPPER:
            return "sweet_spot"
        if V > self.SATIATION_V:
            return "satiation"  # over-exciting → consolidate
        return "suboptimal"

    # ------------------------------------------------------------------ #
    # Action selection
    # ------------------------------------------------------------------ #

    def _select_action(
        self,
        regime: str,
        novelty: float,
        energy: float,
        coherence: float,
    ) -> Tuple[ProposalKind, Dict[str, Any], str]:
        if regime == "energy_crisis":
            return (
                ProposalKind.REQUEST_SLEEP,
                {"category": "energy_crisis"},
                "energy_below_floor",
            )
        if regime == "coherence_crisis":
            return (
                ProposalKind.CHECKPOINT,
                {"scope": "coherence_recovery", "reason": "coherence_low"},
                "coherence_below_floor",
            )
        if regime == "starvation":
            return (
                ProposalKind.ACTUATE,
                {
                    "signal_type": "request_change",
                    "driver": "informational_starvation",
                    "novelty": round(novelty, 4),
                },
                "V_below_starvation_threshold_seek_variation",
            )
        if regime == "satiation":
            return (
                ProposalKind.GARBAGE_COLLECT,
                {"category": "consolidation", "trigger": "V_above_satiation"},
                "V_above_satiation_consolidate",
            )
        # Sweet spot or suboptimal: cheap, low-pressure probe.
        return (
            ProposalKind.OBSERVE,
            {"category": "value_probe", "novelty": round(novelty, 4)},
            "within_sweet_band_observe",
        )

    # ------------------------------------------------------------------ #
    # Diagnostics
    # ------------------------------------------------------------------ #

    def history(self, limit: int = 50) -> list[ActionProposal]:
        return list(self._history[-limit:])

    def summary(self) -> Dict[str, Any]:
        if not self._history:
            return {"n_proposals": 0, "regime_counts": {}, "mean_score": 0.0}
        regime_counts: Dict[str, int] = {}
        for p in self._history:
            regime_counts[p.regime] = regime_counts.get(p.regime, 0) + 1
        mean_score = sum(p.score for p in self._history) / len(self._history)
        return {
            "n_proposals": len(self._history),
            "regime_counts": regime_counts,
            "mean_score": round(mean_score, 6),
            "weights": dict(self._w),
        }

    @staticmethod
    def _g(state: Dict[str, float], key: str, default: float) -> float:
        v = state.get(key, default)
        try:
            x = float(v)
        except (TypeError, ValueError):
            return default
        if x < 0.0:
            return 0.0
        if x > 1.0:
            return 1.0
        return x
