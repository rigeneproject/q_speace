"""T-SPB-3-B — declarative event router for SPEACE areas.

Decides which SPEACE area handles an incoming ``Event``. The router is
pure: it returns a decision without performing any side effect, so it
can be unit-tested in isolation and reused from any consumer (CLI,
orchestrator, webchat, evolution council).

The router is intentionally **declarative** — a list of
:class:`RouteRule` objects is consulted top-to-bottom and the first
matching rule wins. This keeps the routing logic auditable and lets
us print the whole policy as a BCEL-style catalogue.

The current rules are:

- **LLM-area rule** (``text_input`` event) — fires when an event has a
  non-empty ``text`` field. Routes to ``SpikingBrainCortex`` with
  ``area="language"``. This is the only rule that talks to the LLM
  backend; everything else stays native.

- **Quantum-area rule** (``quantum_state`` event) — fires for
  structured quantum inputs (state vectors, density matrices). Routes
  to the orchestrator's native quantum layer (stub for now; the real
  routing lives in ``QuantumOrchestrator.tick``).

- **Spiking-area rule** (``spike_train`` event) — fires for raw spike
  trains. Routes to ``dynamic_spikes`` / ``correlation`` directly,
  bypassing the ILF for performance.

- **Default** — falls back to the ``native`` area (orchestrator
  general-purpose tick). The BCEL catalog in ``bcel/catalog.py``
  stays the authoritative list of *which* areas exist; this router
  decides *which one* handles *this* event.

The router does not own any backend; it only returns a decision. The
caller is responsible for dispatching.
"""

from __future__ import annotations

import heapq
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Event:
    """An incoming stimulus for the SPEACE organism.

    Attributes:
        kind: short identifier (e.g. ``"text_input"``, ``"quantum_state"``).
        text: optional free-form text. Required for ``text_input`` events.
        payload: structured data attached to the event (state vector,
            spike train, etc.). May be empty.
    """

    kind: str
    text: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RouteDecision:
    """Outcome of routing one :class:`Event`."""

    area: str  # "language" | "quantum" | "spiking" | "native"
    rule_name: str
    reason: str
    confidence: float  # 0..1 — how strongly the rule matched


# A pure predicate over an Event.
Predicate = Callable[[Event], bool]


@dataclass(frozen=True)
class RouteRule:
    """A single routing rule: name, area, predicate, base confidence."""

    name: str
    area: str
    predicate: Predicate
    base_confidence: float = 1.0
    reason: str = ""


def _has_text(event: Event) -> bool:
    return event.kind == "text_input" and bool(event.text.strip())


def _has_quantum_state(event: Event) -> bool:
    if event.kind != "quantum_state":
        return False
    p = event.payload
    return ("state_vector" in p) or ("density_matrix" in p)


def _has_spike_train(event: Event) -> bool:
    if event.kind != "spike_train":
        return False
    p = event.payload
    return "spikes" in p and "vth" in p


DEFAULT_RULES: tuple[RouteRule, ...] = (
    RouteRule(
        name="language_llm_area",
        area="language",
        predicate=_has_text,
        base_confidence=0.9,
        reason="text_input routed to SpikingBrainCortex (language area)",
    ),
    RouteRule(
        name="quantum_native_area",
        area="quantum",
        predicate=_has_quantum_state,
        base_confidence=0.95,
        reason="quantum_state routed to native quantum orchestrator",
    ),
    RouteRule(
        name="spiking_native_area",
        area="spiking",
        predicate=_has_spike_train,
        base_confidence=0.85,
        reason="spike_train routed to native spiking primitives",
    ),
)


DEFAULT_FALLBACK = RouteDecision(
    area="native",
    rule_name="default_native_fallback",
    reason="no rule matched — falling back to native orchestrator tick",
    confidence=0.0,
)


class EventRouter:
    """Stateless router. Holds an ordered tuple of :class:`RouteRule`."""

    def __init__(self, rules: Sequence[RouteRule] = DEFAULT_RULES) -> None:
        self._rules: tuple[RouteRule, ...] = tuple(rules)

    @property
    def rules(self) -> tuple[RouteRule, ...]:
        return self._rules

    def route(self, event: Event) -> RouteDecision:
        """Return the first matching rule's decision, or the default."""
        for rule in self._rules:
            if rule.predicate(event):
                return RouteDecision(
                    area=rule.area,
                    rule_name=rule.name,
                    reason=rule.reason or f"matched {rule.name}",
                    confidence=float(rule.base_confidence),
                )
        return DEFAULT_FALLBACK


# ----------------------------------------------------------------------
# T249-04: Cross-inhibited utility drives, CostAwareRouter, GOAP & LIFO stack
# ----------------------------------------------------------------------


class UtilityDriveSystem:
    """Leaky-integrator control variables with mutual cross-inhibition (T249-04).

    Synthesized via BCEL from ``cellular_speace_ollama`` ``UtilityDriveSystem``:
    limbic/dopaminergic metaphors are *accidental* and removed; bounded leaky
    control scalars with winner-inhibits-loser mutual cross-inhibition survive.
    """

    def __init__(
        self,
        drives: Sequence[str] = ("exploration", "energy_conservation", "safety", "accuracy"),
        *,
        decay: float = 0.75,
        antagonistic_pairs: Sequence[tuple[str, str]] = (("exploration", "energy_conservation"),),
    ) -> None:
        unique = list(dict.fromkeys(drives))
        if not unique or any(not d for d in unique):
            raise ValueError("drives must be non-empty strings")
        if not math.isfinite(decay) or not (0.0 <= decay < 1.0):
            raise ValueError("decay must be finite and in [0, 1)")
        drive_set = set(unique)
        for a, b in antagonistic_pairs:
            if a not in drive_set or b not in drive_set or a == b:
                raise ValueError(f"invalid antagonistic pair ({a!r}, {b!r})")

        self._drives: tuple[str, ...] = tuple(unique)
        self.decay = float(decay)
        self.antagonistic_pairs: tuple[tuple[str, str], ...] = tuple(antagonistic_pairs)
        self._levels: dict[str, float] = dict.fromkeys(self._drives, 0.5)

    @property
    def levels(self) -> dict[str, float]:
        return dict(self._levels)

    def step(self, inputs: Mapping[str, float]) -> dict[str, float]:
        """Update control scalars with leaky integration + mutual cross-inhibition."""
        for k, v in inputs.items():
            if k not in self._levels:
                raise KeyError(f"unknown drive: {k!r}")
            if not math.isfinite(v) or not (0.0 <= v <= 1.0):
                raise ValueError(f"input[{k!r}] must be finite and in [0, 1]")

        for d in self._drives:
            u = float(inputs.get(d, self._levels[d]))
            self._levels[d] = float(
                max(0.0, min(1.0, self.decay * self._levels[d] + (1.0 - self.decay) * u))
            )

        for a, b in self.antagonistic_pairs:
            va, vb = self._levels[a], self._levels[b]
            if va >= vb:
                self._levels[b] = float(max(0.0, vb * (1.0 - 0.5 * va)))
            else:
                self._levels[a] = float(max(0.0, va * (1.0 - 0.5 * vb)))

        return dict(self._levels)


@dataclass(frozen=True)
class CostRouteSpec:
    """Precondition-gated, cost-aware routing option (T249-04)."""

    name: str
    area: str
    preconditions: frozenset[str] = frozenset()
    drive_weights: Mapping[str, float] = field(default_factory=dict)
    energy_cost: float = 0.0
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.name or not self.area:
            raise ValueError("name and area must be non-empty")
        if not math.isfinite(self.energy_cost) or self.energy_cost < 0.0:
            raise ValueError("energy_cost must be finite and >= 0")
        for k, v in self.drive_weights.items():
            if not math.isfinite(v):
                raise ValueError(f"drive_weights[{k!r}] must be finite")


class CostAwareRouter:
    """Precondition-gated, cost/Sevo-penalized event dispatcher (T249-04)."""

    def __init__(
        self,
        specs: Sequence[CostRouteSpec],
        *,
        cost_scale: float = 10.0,
    ) -> None:
        if not math.isfinite(cost_scale) or cost_scale <= 0.0:
            raise ValueError("cost_scale must be finite and > 0")
        self._specs: tuple[CostRouteSpec, ...] = tuple(specs)
        self.cost_scale = float(cost_scale)

    def route(
        self,
        active_facts: set[str],
        drive_levels: Mapping[str, float],
    ) -> RouteDecision:
        for k, v in drive_levels.items():
            if not math.isfinite(v):
                raise ValueError(f"drive_levels[{k!r}] must be finite")

        best_util = 0.0
        best_spec: CostRouteSpec | None = None
        for spec in self._specs:
            if not spec.preconditions.issubset(active_facts):
                continue
            gain = sum(
                float(drive_levels.get(d, 0.0)) * float(w) for d, w in spec.drive_weights.items()
            )
            utility = max(0.0, gain - spec.energy_cost / self.cost_scale)
            if utility > best_util:
                best_util = utility
                best_spec = spec

        if best_spec is None:
            return DEFAULT_FALLBACK

        conf = float(min(1.0, best_util / (1.0 + best_util)))
        return RouteDecision(
            area=best_spec.area,
            rule_name=best_spec.name,
            reason=best_spec.reason or f"utility={best_util:.3f}",
            confidence=conf,
        )


@dataclass(frozen=True)
class GOAPAction:
    """Propositional action template for simulated A* planning (T249-04)."""

    name: str
    preconditions: frozenset[str]
    add_effects: frozenset[str]
    del_effects: frozenset[str] = frozenset()
    cost: float = 1.0

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("action name must be non-empty")
        if not math.isfinite(self.cost) or self.cost <= 0.0:
            raise ValueError("action cost must be finite and > 0")


class GOAPPlanner:
    """Bounded deterministic A* planner; strictly ``simulate_only=True`` (T249-04)."""

    def __init__(
        self,
        actions: Sequence[GOAPAction],
        *,
        simulate_only: bool = True,
        max_expansions: int = 256,
    ) -> None:
        if not simulate_only:
            raise ValueError("GOAPPlanner requires simulate_only=True (no direct actuation)")
        if max_expansions < 1:
            raise ValueError("max_expansions must be >= 1")
        self._actions: tuple[GOAPAction, ...] = tuple(actions)
        self.simulate_only = True
        self.max_expansions = max_expansions

    def plan(
        self,
        initial_state: frozenset[str],
        goal_state: frozenset[str],
    ) -> list[GOAPAction] | None:
        """Find minimum-cost action sequence satisfying ``goal_state``, or None if unreachable."""
        if goal_state.issubset(initial_state):
            return []

        counter = 0
        start_h = float(len(goal_state - initial_state))
        frontier: list[tuple[float, float, int, frozenset[str], list[GOAPAction]]] = [
            (start_h, 0.0, counter, initial_state, [])
        ]
        best_g: dict[frozenset[str], float] = {initial_state: 0.0}
        expansions = 0

        while frontier and expansions < self.max_expansions:
            _f, g, _tie, state, path = heapq.heappop(frontier)
            if goal_state.issubset(state):
                return path
            expansions += 1
            for action in self._actions:
                if not action.preconditions.issubset(state):
                    continue
                next_state = (state - action.del_effects) | action.add_effects
                new_g = g + action.cost
                if new_g < best_g.get(next_state, float("inf")):
                    best_g[next_state] = new_g
                    counter += 1
                    h = float(len(goal_state - next_state))
                    heapq.heappush(
                        frontier, (new_g + h, new_g, counter, next_state, [*path, action])
                    )
        return None


@dataclass
class HypothesisEntry:
    """Candidate hypothesis stored on a backtracking workspace stack (T249-04)."""

    hypothesis_id: str
    match_score: float
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)
    abandoned: bool = False

    def __post_init__(self) -> None:
        if not self.hypothesis_id:
            raise ValueError("hypothesis_id must be non-empty")
        if not math.isfinite(self.match_score) or not (0.0 <= self.match_score <= 1.0):
            raise ValueError("match_score must be finite and in [0, 1]")


class HypothesisStack:
    """Bounded LIFO hypothesis workspace with pros/cons pruning & backtracking."""

    def __init__(self, max_depth: int = 32) -> None:
        if max_depth < 1:
            raise ValueError("max_depth must be >= 1")
        self.max_depth = max_depth
        self._stack: list[HypothesisEntry] = []

    def push(self, entry: HypothesisEntry) -> None:
        if len(self._stack) >= self.max_depth:
            raise ValueError(f"HypothesisStack max_depth ({self.max_depth}) exceeded")
        self._stack.append(entry)

    def prune_weak(self, min_score: float = 0.15) -> int:
        """Mark hypotheses with ``match_score < min_score`` and ``len(cons) > len(pros)`` abandoned."""
        if not math.isfinite(min_score):
            raise ValueError("min_score must be finite")
        abandoned = 0
        for h in self._stack:
            if not h.abandoned and h.match_score < min_score and len(h.cons) > len(h.pros):
                h.abandoned = True
                abandoned += 1
        return abandoned

    def backtrack(self) -> HypothesisEntry | None:
        """Pop abandoned top hypotheses and return the latest viable hypothesis (or None)."""
        while self._stack and self._stack[-1].abandoned:
            self._stack.pop()
        return self._stack[-1] if self._stack else None

    def active_count(self) -> int:
        return sum(1 for h in self._stack if not h.abandoned)
