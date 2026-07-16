"""Tests for Coherence Engine (L4)."""

import pytest

from speace_core.cognitive_observatory.coherence_engine import CoherenceEngine


class TestCoherenceEngine:
    def test_compute_cci_without_deps(self, store):
        c = CoherenceEngine(store=store)
        components = c.compute_cci()
        assert components.compute() == pytest.approx(0.5)  # all defaults

    def test_compute_cci_with_deps(self, coherence):
        components = coherence.compute_cci()
        assert 0.0 <= components.compute() <= 1.0

    def test_get_current_cci(self, coherence):
        coherence.compute_cci()
        cci = coherence.get_current_cci()
        assert 0.0 <= cci <= 1.0

    def test_get_cci_history(self, coherence):
        coherence.compute_cci()
        coherence.compute_cci()
        history = coherence.get_cci_history(limit=10)
        assert len(history) == 2

    def test_get_cci_trend(self, coherence):
        trend = coherence.get_cci_trend(window=5)
        assert isinstance(trend, float)

    def test_cci_changes_with_learning(self, coherence, narrative):
        # Without any learning events, CCI learning component is low
        c1 = coherence.compute_cci()
        # Add learning events
        narrative.record_event("learning", "learned X", learning="important lesson")
        narrative.record_event("learning", "learned Y", learning="another lesson")
        c2 = coherence.compute_cci()
        # Learning effectiveness should increase
        assert c2.c_learning >= c1.c_learning

    def test_identity_coherence(self, coherence, self_model):
        self_model.update_identity({"invariants": [{"name": "i1"}, {"name": "i2"}]})
        self_model.set_constraints(["i1", "i2"])
        components = coherence.compute_cci()
        assert components.c_identity > 0.5

    def test_memory_coherence(self, coherence, narrative):
        narrative.record_event("test", "e1", learning="l")
        components = coherence.compute_cci()
        assert components.c_memory >= 0.0
