"""Tests for the T-SPB-3-B declarative event router."""

from __future__ import annotations

import numpy as np

from q_speace.routing import (
    DEFAULT_FALLBACK,
    Event,
    EventRouter,
    RouteRule,
)


def test_router_routes_text_input_to_language_area() -> None:
    r = EventRouter()
    decision = r.route(Event(kind="text_input", text="explain Q-SPEACE"))
    assert decision.area == "language"
    assert decision.rule_name == "language_llm_area"
    assert decision.confidence >= 0.5


def test_router_routes_quantum_state_to_quantum_area() -> None:
    r = EventRouter()
    decision = r.route(Event(kind="quantum_state", payload={"state_vector": [1.0, 0.0, 0.0, 0.0]}))
    assert decision.area == "quantum"
    assert decision.rule_name == "quantum_native_area"


def test_router_routes_spike_train_to_spiking_area() -> None:
    r = EventRouter()
    decision = r.route(
        Event(
            kind="spike_train",
            payload={"spikes": np.array([1.0, 0.0, 1.0]), "vth": np.array([0.5])},
        )
    )
    assert decision.area == "spiking"
    assert decision.rule_name == "spiking_native_area"


def test_router_falls_back_to_native_for_unknown_event() -> None:
    r = EventRouter()
    decision = r.route(Event(kind="custom_metric", payload={}))
    assert decision.area == DEFAULT_FALLBACK.area
    assert decision.rule_name == DEFAULT_FALLBACK.rule_name
    assert decision.confidence == 0.0


def test_router_skips_text_rule_when_text_is_empty() -> None:
    r = EventRouter()
    # An empty text must NOT trigger the language area.
    decision = r.route(Event(kind="text_input", text="   "))
    assert decision.area == DEFAULT_FALLBACK.area


def test_router_first_match_wins() -> None:
    # A text event with a quantum payload should match the text rule first
    # (because text_input is declared first in DEFAULT_RULES).
    r = EventRouter()
    decision = r.route(
        Event(
            kind="text_input",
            text="hi",
            payload={"state_vector": [1.0, 0.0]},
        )
    )
    assert decision.area == "language"


def test_router_supports_custom_rules() -> None:
    def _is_alert(event: Event) -> bool:
        return event.kind == "alert" and event.payload.get("severity") == "high"

    custom = EventRouter(
        rules=(
            RouteRule(
                name="high_alert",
                area="native",
                predicate=_is_alert,
                base_confidence=1.0,
                reason="high-severity alert → native orchestrator",
            ),
            *EventRouter().rules,
        )
    )
    decision = custom.route(Event(kind="alert", payload={"severity": "high"}))
    assert decision.rule_name == "high_alert"
    # And still works for normal text
    decision = custom.route(Event(kind="text_input", text="hi"))
    assert decision.area == "language"
