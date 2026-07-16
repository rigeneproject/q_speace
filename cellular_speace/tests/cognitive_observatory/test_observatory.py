"""Tests for CognitiveObservatory orchestrator (L1-L8)."""


class TestCognitiveObservatory:
    def test_init(self, observatory):
        assert observatory.state_graph is not None
        assert observatory.self_model is not None
        assert observatory.narrative is not None
        assert observatory.coherence is not None
        assert observatory.metacognitive is not None
        assert observatory.causal_evolution is not None
        assert observatory.interpretation is not None

    def test_on_tick_empty(self, observatory):
        result = observatory.on_tick()
        assert "cci" in result
        assert "cci_components" in result
        assert "state_graph_size" in result
        assert "narrative_count" in result
        assert "elapsed_ms" in result

    def test_on_tick_with_orchestrator_state(self, observatory):
        state = {
            "identity": {"entity_name": "SPEACE-TEST"},
            "ilf": {"coherence": 0.8},
            "goals": [{"name": "test_goal"}],
            "constraints": ["c1"],
            "capabilities": {"reasoning": 0.9},
        }
        result = observatory.on_tick(orchestrator_state=state)
        summary = observatory.self_model.get_self_summary()
        assert summary["identity_name"] == "SPEACE-TEST"

    def test_on_tick_updates_narrative(self, observatory):
        observatory.narrative.record_event("test", "test event")
        result = observatory.on_tick()
        assert result["narrative_count"] >= 1

    def test_get_full_cognitive_audit(self, observatory):
        # Populate some data
        observatory.state_graph.record_thought("test_thought")
        observatory.state_graph.record_decision("test_decision")
        observatory.narrative.record_event("test", "test_event")
        observatory.metacognitive.record_decision_quality("d:1", confidence=0.8)
        observatory.metacognitive.record_outcome("d:1", accuracy=0.9)

        audit = observatory.get_full_cognitive_audit()
        assert "cci" in audit
        assert "cci_components" in audit
        assert "cci_trend" in audit
        assert "self_summary" in audit
        assert "metacognitive" in audit
        assert "narrative_events" in audit
        assert "state_graph" in audit
        assert "self_understanding" in audit

    def test_get_coherence_report(self, observatory):
        observatory.coherence.compute_cci()
        observatory.coherence.compute_cci()
        report = observatory.get_coherence_report()
        assert "current_cci" in report
        assert "cci_trend_20" in report
        assert "cci_history" in report

    def test_get_narrative_timeline(self, observatory):
        observatory.narrative.record_event("test", "event 1")
        observatory.narrative.record_event("error", "event 2")
        timeline = observatory.get_narrative_timeline(limit=10)
        assert len(timeline) == 2
        filtered = observatory.get_narrative_timeline(limit=10, event_type="error")
        assert len(filtered) == 1

    def test_causal_trace_upstream(self, observatory):
        a = observatory.state_graph.record_thought("cause")
        b = observatory.state_graph.record_error("effect")
        observatory.state_graph.link_causal(a.id, b.id)
        result = observatory.causal_trace(b.id, direction="upstream", depth=3)
        assert result["start_id"] == b.id
        assert result["direction"] == "upstream"

    def test_causal_trace_downstream(self, observatory):
        a = observatory.state_graph.record_thought("source")
        b = observatory.state_graph.record_action("result")
        observatory.state_graph.link_causal(a.id, b.id)
        result = observatory.causal_trace(a.id, direction="downstream", depth=3)
        assert result["start_id"] == a.id
        assert result["direction"] == "downstream"

    def test_clear(self, observatory):
        observatory.state_graph.record_thought("t1")
        observatory.self_model.update_identity({"entity_name": "TEST"})
        observatory.clear()
        assert observatory.state_graph.node_count() == 0
