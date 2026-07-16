"""Tests for AGIReadinessScore."""

import pytest

from speace_core.cellular_brain.agi_readiness.agi_readiness_score import (
    AGIReadinessDimension,
    AGIReadinessScore,
    load_last_report,
)


def test_dimension_clamps_score():
    d = AGIReadinessDimension(name="x", score=1.5, weight=1.0)
    assert d.score == 1.0

    d = AGIReadinessDimension(name="x", score=-0.5, weight=1.0)
    assert d.score == 0.0


def test_weights_are_normalized():
    scorer = AGIReadinessScore(weights={"autonomy": 2.0})
    total = sum(scorer.weights.values())
    assert round(total, 6) == 1.0
    assert scorer.weights["autonomy"] > scorer.DEFAULT_WEIGHTS["autonomy"]


def test_empty_inputs_produce_low_score():
    scorer = AGIReadinessScore()
    report = scorer.evaluate()
    assert report.aggregate_score < 0.2
    assert not report.is_agi_like
    assert not report.is_agi_robust


def test_high_inputs_produce_agi_like_score():
    scorer = AGIReadinessScore()
    report = scorer.evaluate(
        runtime_state={"runtime_hours": 5.0, "tick_count": 10000, "coherence_phi": 0.85, "anomaly_count": 0},
        learning_state={"prediction_errors": [0.9, 0.7, 0.5, 0.3, 0.1]},
        causal_state={"observation_count": 80, "unique_actions": 15, "prediction_accuracy": 0.85},
        test_state={"passed": 50, "failed": 0, "skipped": 0},
        metacognition_state={"limitation_signals": 30, "diagnoses": 15, "detection_accuracy": 0.85},
        self_improvement_state={"proposals_total": 20, "proposals_accepted": 18, "patches_executed": 18, "patches_successful": 16},
        language_state={"grounding_count": 150, "dialogue_coherence": 0.8, "spontaneous_utterances": 10},
        embodiment_state={"sensor_count": 6, "action_count": 20, "successful_actions": 18},
    )
    assert report.aggregate_score >= 0.55
    assert report.is_agi_like
    assert report.is_agi_robust


def test_report_roundtrip(tmp_path):
    scorer = AGIReadinessScore()
    report = scorer.evaluate(
        runtime_state={"runtime_hours": 2.0, "tick_count": 100, "coherence_phi": 0.5, "anomaly_count": 1},
    )
    path = report.save(tmp_path / "report.json")
    loaded = load_last_report(tmp_path)
    assert loaded is not None
    assert loaded.aggregate_score == pytest.approx(report.aggregate_score, abs=1e-4)
    assert loaded.dimensions[0].name == report.dimensions[0].name


def test_load_last_report_missing_dir():
    assert load_last_report(__import__("pathlib").Path("/nonexistent/agi_readiness")) is None
