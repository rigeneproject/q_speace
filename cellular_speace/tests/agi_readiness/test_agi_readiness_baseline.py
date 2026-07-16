"""Baseline tests for AGI readiness computation."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from speace_core.cellular_brain.agi_readiness.agi_readiness_score import (
    AGIReadinessReport,
    AGIReadinessScore,
)


@pytest.fixture
def evaluator() -> AGIReadinessScore:
    return AGIReadinessScore()


@pytest.fixture
def sample_inputs() -> dict:
    return {
        "runtime_state": {
            "runtime_hours": 5.0,
            "tick_count": 100,
            "coherence_phi": 0.8,
            "anomaly_count": 2,
        },
        "learning_state": {
            "prediction_errors": [0.5, 0.4, 0.3, 0.2, 0.1],
        },
        "causal_state": {
            "observation_count": 60,
            "unique_actions": 12,
            "prediction_accuracy": 0.85,
        },
        "test_state": {
            "passed": 10,
            "failed": 1,
            "skipped": 2,
        },
        "metacognition_state": {
            "limitation_signals": 25,
            "diagnoses": 12,
            "detection_accuracy": 0.9,
        },
        "self_improvement_state": {
            "proposals_total": 10,
            "proposals_accepted": 5,
            "patches_executed": 3,
            "patches_successful": 3,
        },
        "language_state": {
            "grounding_count": 50,
            "dialogue_coherence": 0.7,
            "spontaneous_utterances": 8,
        },
        "embodiment_state": {
            "sensor_count": 5,
            "action_count": 20,
            "successful_actions": 18,
        },
    }


class TestAGIReadinessBaseline:
    def test_score_computable(self, evaluator: AGIReadinessScore, sample_inputs: dict) -> None:
        report = evaluator.evaluate(**sample_inputs, iteration=1)
        assert isinstance(report, AGIReadinessReport)
        assert 0.0 <= report.aggregate_score <= 1.0

    def test_dimensions_non_zero(self, evaluator: AGIReadinessScore, sample_inputs: dict) -> None:
        report = evaluator.evaluate(**sample_inputs, iteration=1)
        for dim in report.dimensions:
            assert dim.score >= 0.0, f"{dim.name} score is negative"
            assert dim.weight > 0.0, f"{dim.name} weight is zero"

    def test_causal_reasoning_coverage(self, evaluator: AGIReadinessScore) -> None:
        dim = evaluator._causal_reasoning({
            "observation_count": 60,
            "unique_actions": 12,
            "prediction_accuracy": 1.0,
        })
        assert dim.score == 1.0

    def test_causal_reasoning_zero(self, evaluator: AGIReadinessScore) -> None:
        dim = evaluator._causal_reasoning({
            "observation_count": 0,
            "unique_actions": 0,
            "prediction_accuracy": 0.0,
        })
        assert dim.score == 0.0

    def test_generalization_basic(self, evaluator: AGIReadinessScore) -> None:
        dim = evaluator._generalization({
            "passed": 10,
            "failed": 0,
            "skipped": 0,
        })
        assert dim.score > 0.0
        assert dim.score <= 1.0

    def test_generalization_zero(self, evaluator: AGIReadinessScore) -> None:
        dim = evaluator._generalization({
            "passed": 0,
            "failed": 0,
            "skipped": 0,
        })
        assert dim.score == 0.0

    def test_report_save_load(self, evaluator: AGIReadinessScore, sample_inputs: dict) -> None:
        report = evaluator.evaluate(**sample_inputs, iteration=5)
        with tempfile.TemporaryDirectory() as tmp:
            path = report.save(Path(tmp) / "report.json")
            assert path.exists()
            data = json.loads(path.read_text(encoding="utf-8"))
            assert data["aggregate_score"] == report.aggregate_score
            assert data["iteration"] == 5
