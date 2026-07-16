"""Tests for Narrative Memory (L3)."""


class TestNarrativeMemory:
    def test_record_event(self, narrative):
        e = narrative.record_event(
            event_type="test", description="test event",
            interpretation="because X", learning="do Y",
        )
        assert e.id.startswith("narrative:")
        assert e.event_type == "test"
        assert e.learning == "do Y"

    def test_record_mutation_event(self, narrative):
        e = narrative.record_mutation_event("gene mutated", ilf_delta=0.05)
        assert e.event_type == "mutation"
        assert e.subsystem == "evolution"
        assert e.ilf_delta == 0.05

    def test_record_decision_event(self, narrative):
        e = narrative.record_decision_event("decided X", cci_delta=0.02)
        assert e.event_type == "decision"
        assert e.subsystem == "cognitive"

    def test_record_error_event(self, narrative):
        e = narrative.record_error_event("something broke", ilf_delta=-0.1)
        assert e.event_type == "error"
        assert e.subsystem == "monitoring"

    def test_record_learning_event(self, narrative):
        e = narrative.record_learning_event("learned to validate input", cci_delta=0.05)
        assert e.event_type == "learning"
        assert e.subsystem == "metacognitive"

    def test_record_adaptation_event(self, narrative):
        e = narrative.record_adaptation_event("adapted to new context", ilf_delta=0.03)
        assert e.event_type == "adaptation"
        assert e.subsystem == "ilf"

    def test_get_timeline(self, narrative):
        narrative.record_event("type_a", "event 1")
        narrative.record_event("type_b", "event 2")
        timeline = narrative.get_timeline(limit=10)
        assert len(timeline) == 2

    def test_get_timeline_filtered(self, narrative):
        narrative.record_event("error", "err 1")
        narrative.record_event("decision", "dec 1")
        narrative.record_event("error", "err 2")
        errors = narrative.get_timeline(limit=10, event_type="error")
        assert len(errors) == 2
        decisions = narrative.get_timeline(limit=10, event_type="decision")
        assert len(decisions) == 1

    def test_get_events_by_type(self, narrative):
        narrative.record_event("error", "err 1")
        narrative.record_event("error", "err 2")
        assert len(narrative.get_events_by_type("error")) == 2
        assert len(narrative.get_events_by_type("decision")) == 0

    def test_get_recent_errors(self, narrative):
        narrative.record_event("error", "err 1")
        narrative.record_event("decision", "dec 1")
        narrative.record_event("error", "err 2")
        assert len(narrative.get_recent_errors(limit=5)) == 2

    def test_get_event(self, narrative):
        e = narrative.record_event("test", "my event")
        assert narrative.get_event(e.id) is e
        assert narrative.get_event("nonexistent") is None

    def test_get_causal_chain(self, narrative):
        e1 = narrative.record_event("root", "root event")
        e2 = narrative.record_event(
            "child", "child event", causal_parents=[e1.id],
        )
        e3 = narrative.record_event(
            "grandchild", "grandchild event", causal_parents=[e2.id],
        )
        chain = narrative.get_causal_chain(e3.id, max_depth=5)
        assert len(chain) == 3

    def test_get_learning_effectiveness(self, narrative):
        assert narrative.get_learning_effectiveness() == 0.5  # no events
        narrative.record_event("test", "e1", learning="learned X")
        narrative.record_event("test", "e2", learning="")
        eff = narrative.get_learning_effectiveness(window=10)
        assert eff == 0.5  # 1 out of 2

    def test_get_event_count_by_type(self, narrative):
        narrative.record_event("error", "e1")
        narrative.record_event("error", "e2")
        narrative.record_event("decision", "d1")
        counts = narrative.get_event_count_by_type()
        assert counts.get("error") == 2
        assert counts.get("decision") == 1
