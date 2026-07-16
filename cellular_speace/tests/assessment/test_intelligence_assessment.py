"""Tests for the SPEACE capability/intelligence assessment battery."""
import pytest

from run_speace_intelligence_assessment import IntelligenceAssessment, main
from speace_core.environment.environment_adapter import EnvironmentAdapter


def test_intelligence_assessment_runs():
    adapter = EnvironmentAdapter(enable_simulator_backend=False)
    assessment = IntelligenceAssessment(adapter)
    report = assessment.run()
    assert 0 <= report.composite_score <= 100
    assert report.elapsed_seconds > 0
    assert report.interpretation != ""


def test_all_subtests_produce_results():
    adapter = EnvironmentAdapter(enable_simulator_backend=False)
    assessment = IntelligenceAssessment(adapter)
    report = assessment.run()
    for field in [
        "associative_recall",
        "sequence_prediction",
        "grid_navigation",
        "homeostatic_stability",
        "plasticity",
        "cor_activity",
    ]:
        assert getattr(report, field), f"{field} missing"
