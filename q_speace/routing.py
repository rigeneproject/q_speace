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

from collections.abc import Callable, Sequence
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
