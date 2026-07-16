"""Tests for Metacognitive Engine (L5)."""

import pytest


class TestMetacognitiveEngine:
    def test_record_decision_quality(self, metacognitive):
        s = metacognitive.record_decision_quality(
            decision_id="d:1", confidence=0.8,
            context_completeness=0.7, evidence_quality=0.9,
            hypotheses_considered=3, subsystem="test",
        )
        assert s.decision_id == "d:1"
        assert s.confidence == 0.8
        assert s.context_completeness == 0.7

    def test_record_outcome(self, metacognitive):
        metacognitive.record_decision_quality("d:1", confidence=0.8)
        metacognitive.record_outcome("d:1", accuracy=0.9, subsequent_errors=0)
        scores = metacognitive.get_decision_scores("d:1")
        assert scores[0].accuracy == 0.9
        assert scores[0].subsequent_errors == 0

    def test_record_outcome_new(self, metacognitive):
        metacognitive.record_outcome("d:new", accuracy=0.5)
        scores = metacognitive.get_decision_scores("d:new")
        assert len(scores) >= 1

    def test_get_recent_scores(self, metacognitive):
        metacognitive.record_decision_quality("d:1")
        metacognitive.record_decision_quality("d:2")
        assert len(metacognitive.get_recent_scores(limit=5)) == 2

    def test_get_average_confidence(self, metacognitive):
        metacognitive.record_decision_quality("d:1", confidence=0.8)
        metacognitive.record_decision_quality("d:2", confidence=0.6)
        assert metacognitive.get_average_confidence(window=10) == 0.7

    def test_get_average_accuracy(self, metacognitive):
        assert metacognitive.get_average_accuracy() == 0.5  # no outcomes
        metacognitive.record_decision_quality("d:1", confidence=0.8)
        metacognitive.record_outcome("d:1", accuracy=0.9)
        assert metacognitive.get_average_accuracy(window=10) == 0.9

    def test_get_calibration_error(self, metacognitive):
        assert metacognitive.get_calibration_error() == pytest.approx(0.5)  # no outcomes
        metacognitive.record_decision_quality("d:1", confidence=0.8)
        metacognitive.record_outcome("d:1", accuracy=0.7)
        # calibration = |0.8 - 0.7| = 0.1
        assert metacognitive.get_calibration_error(window=10) == pytest.approx(0.1)

    def test_get_average_context_completeness(self, metacognitive):
        metacognitive.record_decision_quality("d:1", context_completeness=0.9)
        metacognitive.record_decision_quality("d:2", context_completeness=0.7)
        assert metacognitive.get_average_context_completeness() == 0.8

    def test_get_recurring_error_patterns(self, metacognitive):
        metacognitive.record_decision_quality("d:1", subsystem="brain")
        metacognitive.record_outcome("d:1", accuracy=0.5, subsequent_errors=3)
        metacognitive.record_decision_quality("d:2", subsystem="brain")
        metacognitive.record_outcome("d:2", accuracy=0.5, subsequent_errors=2)
        metacognitive.record_decision_quality("d:3", subsystem="memory")
        metacognitive.record_outcome("d:3", accuracy=0.5, subsequent_errors=1)
        patterns = metacognitive.get_recurring_error_patterns(min_frequency=1)
        subs = {p["subsystem"] for p in patterns}
        assert "brain" in subs
        assert "memory" in subs

    def test_get_comprehensive_report(self, metacognitive):
        metacognitive.record_decision_quality("d:1", confidence=0.8)
        metacognitive.record_outcome("d:1", accuracy=0.9)
        report = metacognitive.get_comprehensive_metacognitive_report()
        assert "average_confidence" in report
        assert "calibration_error" in report
        assert "recent_decisions" in report
