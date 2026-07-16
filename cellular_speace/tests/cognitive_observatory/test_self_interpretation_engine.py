"""Tests for Self Interpretation Engine (L7)."""


class TestSelfInterpretationEngine:
    def test_interpret_event(self, interpretation):
        interp = interpretation.interpret_event(
            event_id="e:1",
            what="Something happened",
            why="Because of X",
            contributing_factors=["factor A"],
            supporting_evidence=["evidence 1"],
            learning="Do Y next time",
            coherence_impact=-0.05,
            recommendation="Add validation",
        )
        assert interp.event_id == "e:1"
        assert interp.why == "Because of X"
        assert "validation" in interp.recommendation

    def test_interpret_event_auto_why(self, interpretation, state_graph):
        # First create a causal chain
        a = state_graph.record_thought("cause_A")
        b = state_graph.record_error("effect_B")
        state_graph.link_causal(a.id, b.id)
        interp = interpretation.interpret_event(event_id=b.id, what="error happened")
        assert "cause_A" in interp.why

    def test_interpret_narrative_event(self, interpretation, narrative):
        e = narrative.record_event("error", "my error", interpretation="because X")
        interp = interpretation.interpret_narrative_event(e)
        assert interp.event_id == e.id
        assert interp.what == "my error"

    def test_get_interpretation(self, interpretation):
        i = interpretation.interpret_event("e:1", what="test")
        assert interpretation.get_interpretation("e:1") is i
        assert interpretation.get_interpretation("nonexistent") is None

    def test_get_all_interpretations(self, interpretation):
        interpretation.interpret_event("e:1", what="test 1")
        interpretation.interpret_event("e:2", what="test 2")
        assert len(interpretation.get_all_interpretations()) == 2

    def test_get_recent_interpretations(self, interpretation):
        interpretation.interpret_event("e:1", what="older")
        interpretation.interpret_event("e:2", what="newer")
        recent = interpretation.get_recent_interpretations(limit=1)
        assert len(recent) == 1

    def test_explain_cci_change(self, interpretation):
        interp = interpretation.explain_cci_change(-0.1, context="high error rate")
        assert "CCI decreased" in interp.why
        assert "high error rate" in interp.why

    def test_explain_cci_increase(self, interpretation):
        interp = interpretation.explain_cci_change(0.1)
        assert "CCI increased" in interp.why

    def test_summarize_self_understanding(self, interpretation):
        interpretation.interpret_event("e:1", what="error occurred", learning="fixed")
        summary = interpretation.summarize_self_understanding()
        assert summary["recent_interpretations"] >= 1
