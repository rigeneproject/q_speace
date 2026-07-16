"""Shared fixtures for Cognitive Self Observatory tests."""

import pytest

from speace_core.cognitive_observatory.persistence.observatory_store import ObservatoryStore
from speace_core.cognitive_observatory.cognitive_state_graph import CognitiveStateGraph
from speace_core.cognitive_observatory.self_model import SelfModelEngine
from speace_core.cognitive_observatory.narrative_memory import NarrativeMemory
from speace_core.cognitive_observatory.metacognitive_engine import MetacognitiveEngine
from speace_core.cognitive_observatory.coherence_engine import CoherenceEngine
from speace_core.cognitive_observatory.causal_evolution_graph import CausalEvolutionGraph
from speace_core.cognitive_observatory.self_interpretation_engine import SelfInterpretationEngine
from speace_core.cognitive_observatory.observatory import CognitiveObservatory


@pytest.fixture
def store():
    s = ObservatoryStore(data_dir="data/cognitive_observatory_test")
    s.clear()
    return s


@pytest.fixture
def state_graph(store):
    return CognitiveStateGraph(store=store)


@pytest.fixture
def self_model(store):
    return SelfModelEngine(store=store)


@pytest.fixture
def narrative(store):
    return NarrativeMemory(store=store)


@pytest.fixture
def metacognitive(store):
    return MetacognitiveEngine(store=store)


@pytest.fixture
def coherence(store, self_model, narrative, metacognitive):
    return CoherenceEngine(
        store=store, self_model=self_model,
        narrative_memory=narrative, metacognitive=metacognitive,
    )


@pytest.fixture
def causal_evolution(state_graph):
    return CausalEvolutionGraph(state_graph=state_graph)


@pytest.fixture
def interpretation(state_graph, narrative, store):
    return SelfInterpretationEngine(store=store, state_graph=state_graph, narrative=narrative)


@pytest.fixture
def observatory(store):
    return CognitiveObservatory(store=store)
