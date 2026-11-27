"""Kinetica Cognitive Regime FSM & Homeodyna Overload Rerouting / E-I Balance (T256-03).

Synthesized via BCEL from ``SPEACE PROTOTIPO CLAUDE`` (``SPEACE_Cortex/morphogenesis_engine.py``):
- Biological morphogenesis terminology is treated strictly as finite-state control and
  graph-routing operators.
- ``KineticaRegimeController`` governs bounded compute/exploration configurations across
  7 operational regimes with fail-safe ``EMERGENCY`` diversion on resource overload and
  coherence gating on ``META_COGNITION``.
- ``HomeodynaBalanceController`` evaluates excitation-inhibition / coherence / resource
  equilibrium and computes non-destructive bypass paths around overloaded nodes.
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum


class CognitiveRegime(StrEnum):
    """Operational compute & exploration regimes (Kinetica FSM)."""

    REACTIVE_PARSING = "reactive_parsing"
    DELIBERATIVE_REASONING = "deliberative_reasoning"
    RECURSIVE_ABSTRACTION = "recursive_abstraction"
    CREATIVE_SYNTHESIS = "creative_synthesis"
    META_COGNITION = "meta_cognition"
    EMERGENCY = "emergency"
    IDLE = "idle"


@dataclass(frozen=True)
class RegimeConfig:
    """Bounded execution budget associated with one :class:`CognitiveRegime`."""

    parallel_units: int
    depth_limit: int
    timeout_ms: int
    exploration_rate: float


@dataclass(frozen=True)
class RegimeTransition:
    """Immutable record of a Kinetica regime transition."""

    from_regime: CognitiveRegime
    to_regime: CognitiveRegime
    trigger: str
    phi: float
    resource_usage: float


_DEFAULT_REGIME_CONFIGS: dict[CognitiveRegime, RegimeConfig] = {
    CognitiveRegime.REACTIVE_PARSING: RegimeConfig(3, 2, 500, 0.10),
    CognitiveRegime.DELIBERATIVE_REASONING: RegimeConfig(5, 5, 5000, 0.30),
    CognitiveRegime.RECURSIVE_ABSTRACTION: RegimeConfig(4, 8, 10000, 0.50),
    CognitiveRegime.CREATIVE_SYNTHESIS: RegimeConfig(6, 6, 15000, 0.80),
    CognitiveRegime.META_COGNITION: RegimeConfig(2, 3, 20000, 0.40),
    CognitiveRegime.EMERGENCY: RegimeConfig(1, 1, 200, 0.00),
    CognitiveRegime.IDLE: RegimeConfig(0, 0, 0, 0.05),
}

_HIGH_COST_REGIMES: frozenset[CognitiveRegime] = frozenset(
    {
        CognitiveRegime.DELIBERATIVE_REASONING,
        CognitiveRegime.RECURSIVE_ABSTRACTION,
        CognitiveRegime.CREATIVE_SYNTHESIS,
    }
)


class KineticaRegimeController:
    """Deterministic 7-state cognitive-regime controller with overload protection (T256-03)."""

    def __init__(
        self,
        *,
        initial_regime: CognitiveRegime = CognitiveRegime.IDLE,
        overload_threshold: float = 0.90,
        meta_min_phi: float = 0.60,
    ) -> None:
        if not math.isfinite(overload_threshold) or not (0.0 < overload_threshold <= 1.0):
            raise ValueError("overload_threshold must be finite and in (0, 1]")
        if not math.isfinite(meta_min_phi) or not (0.0 <= meta_min_phi <= 1.0):
            raise ValueError("meta_min_phi must be finite and in [0, 1]")

        self.current_regime: CognitiveRegime = initial_regime
        self.overload_threshold = float(overload_threshold)
        self.meta_min_phi = float(meta_min_phi)
        self._history: deque[RegimeTransition] = deque(maxlen=64)
        self._rules: dict[tuple[CognitiveRegime, str], CognitiveRegime] = {
            (CognitiveRegime.IDLE, "task_start"): CognitiveRegime.REACTIVE_PARSING,
            (CognitiveRegime.REACTIVE_PARSING, "complex_reasoning"): (
                CognitiveRegime.DELIBERATIVE_REASONING
            ),
            (CognitiveRegime.DELIBERATIVE_REASONING, "pattern_found"): (
                CognitiveRegime.RECURSIVE_ABSTRACTION
            ),
            (CognitiveRegime.RECURSIVE_ABSTRACTION, "creative_needed"): (
                CognitiveRegime.CREATIVE_SYNTHESIS
            ),
            (CognitiveRegime.CREATIVE_SYNTHESIS, "self_reflection"): CognitiveRegime.META_COGNITION,
            (CognitiveRegime.DELIBERATIVE_REASONING, "self_reflection"): (
                CognitiveRegime.META_COGNITION
            ),
            (CognitiveRegime.META_COGNITION, "task_complete"): CognitiveRegime.IDLE,
            (CognitiveRegime.REACTIVE_PARSING, "task_complete"): CognitiveRegime.IDLE,
            (CognitiveRegime.REACTIVE_PARSING, "overload"): CognitiveRegime.EMERGENCY,
            (CognitiveRegime.DELIBERATIVE_REASONING, "overload"): CognitiveRegime.EMERGENCY,
            (CognitiveRegime.RECURSIVE_ABSTRACTION, "overload"): CognitiveRegime.EMERGENCY,
            (CognitiveRegime.EMERGENCY, "stabilized"): CognitiveRegime.REACTIVE_PARSING,
        }

    @property
    def history(self) -> tuple[RegimeTransition, ...]:
        return tuple(self._history)

    def config_for(self, regime: CognitiveRegime | None = None) -> RegimeConfig:
        target = self.current_regime if regime is None else regime
        return _DEFAULT_REGIME_CONFIGS[target]

    def evaluate_transition(
        self,
        trigger: str,
        *,
        phi: float = 0.70,
        resource_usage: float = 0.50,
    ) -> CognitiveRegime | None:
        if not math.isfinite(phi) or not (0.0 <= phi <= 1.0):
            raise ValueError("phi must be finite and in [0, 1]")
        if not math.isfinite(resource_usage) or not (0.0 <= resource_usage <= 1.0):
            raise ValueError("resource_usage must be finite and in [0, 1]")

        candidate = self._rules.get((self.current_regime, trigger))
        if candidate is None:
            if (
                resource_usage > self.overload_threshold
                and self.current_regime != CognitiveRegime.EMERGENCY
            ):
                return CognitiveRegime.EMERGENCY
            return None

        if candidate in _HIGH_COST_REGIMES and resource_usage > self.overload_threshold:
            return CognitiveRegime.EMERGENCY
        if candidate == CognitiveRegime.META_COGNITION and phi < self.meta_min_phi:
            return None
        return candidate

    def step(
        self,
        trigger: str,
        *,
        phi: float = 0.70,
        resource_usage: float = 0.50,
    ) -> RegimeTransition | None:
        nxt = self.evaluate_transition(trigger, phi=phi, resource_usage=resource_usage)
        if nxt is None or nxt == self.current_regime:
            return None
        rec = RegimeTransition(
            from_regime=self.current_regime,
            to_regime=nxt,
            trigger=trigger,
            phi=float(phi),
            resource_usage=float(resource_usage),
        )
        self.current_regime = nxt
        self._history.append(rec)
        return rec


@dataclass(frozen=True)
class HomeodynaEvaluation:
    """Equilibrium score, E/I balance, violations, and compensation directives."""

    balance_score: float
    ei_balance: float
    violations: tuple[str, ...]
    recommended_actions: tuple[str, ...]


class HomeodynaBalanceController:
    """Structural E/I balance evaluator and overload path rerouter (T256-03)."""

    def __init__(
        self,
        *,
        target_phi: float = 0.65,
        phi_tolerance: float = 0.15,
        min_ei_balance: float = 0.40,
    ) -> None:
        for name, val in (
            ("target_phi", target_phi),
            ("phi_tolerance", phi_tolerance),
            ("min_ei_balance", min_ei_balance),
        ):
            if not math.isfinite(val) or not (0.0 <= val <= 1.0):
                raise ValueError(f"{name} must be finite and in [0, 1]")
        self.target_phi = float(target_phi)
        self.phi_tolerance = float(phi_tolerance)
        self.min_ei_balance = float(min_ei_balance)

    def evaluate(
        self,
        *,
        phi: float,
        excitation: float,
        inhibition: float,
        resource_usage: float,
    ) -> HomeodynaEvaluation:
        for name, val in (
            ("phi", phi),
            ("excitation", excitation),
            ("inhibition", inhibition),
            ("resource_usage", resource_usage),
        ):
            if not math.isfinite(val) or not (0.0 <= val <= 1.0):
                raise ValueError(f"{name} must be finite and in [0, 1]")

        violations: list[str] = []
        actions: list[str] = []
        score = 1.0

        dev = abs(phi - self.target_phi)
        if dev > self.phi_tolerance:
            violations.append(f"phi_deviation:{dev:.3f}")
            actions.append("stabilize")
            score -= min(1.0, dev)

        ei_balance = 1.0 - abs(excitation - inhibition)
        if ei_balance < self.min_ei_balance:
            violations.append(f"ei_imbalance:{ei_balance:.3f}")
            actions.append("reconfigure")
            score *= max(0.0, ei_balance)

        if resource_usage > 0.95:
            violations.append("resource_overload")
            actions.append("prune")
            score *= 0.50
        elif resource_usage > 0.85:
            violations.append("resource_high")
            actions.append("prune")
            score *= 0.80

        return HomeodynaEvaluation(
            balance_score=float(max(0.0, min(1.0, score))),
            ei_balance=float(ei_balance),
            violations=tuple(violations),
            recommended_actions=tuple(dict.fromkeys(actions)),
        )

    @staticmethod
    def reroute_path(
        current_path: Sequence[str],
        overloaded_node: str,
        bypass_candidates: Sequence[str],
    ) -> tuple[str, ...]:
        """Return a new path replacing ``overloaded_node`` with the first healthy bypass node."""
        path = list(current_path)
        if overloaded_node not in path:
            return tuple(path)
        idx = path.index(overloaded_node)
        prefix = path[:idx]
        suffix = path[idx + 1 :]
        used = set(prefix) | set(suffix) | {overloaded_node}
        replacement = next((c for c in bypass_candidates if c and c not in used), None)
        if replacement is not None:
            return (*prefix, replacement, *suffix)
        return (*prefix, *suffix)
