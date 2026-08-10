"""Tests for T206 calibration evaluation."""

from __future__ import annotations

import numpy as np
import pytest

from q_speace.spiking_brain.evaluation import calibration_report


def test_perfect_forecast_has_zero_calibration_error() -> None:
    report = calibration_report(np.array([0.0, 1.0]), np.array([0, 1]))
    assert report.samples == 2
    assert report.brier_score == pytest.approx(0.0)
    assert report.expected_calibration_error == pytest.approx(0.0)


def test_overconfident_forecast_is_penalized() -> None:
    report = calibration_report(np.array([0.9, 0.9]), np.array([0, 0]))
    assert report.brier_score == pytest.approx(0.81)
    assert report.expected_calibration_error == pytest.approx(0.9)


def test_calibration_rejects_unlabelled_or_invalid_data() -> None:
    with pytest.raises(ValueError):
        calibration_report(np.array([]), np.array([]))
    with pytest.raises(ValueError):
        calibration_report(np.array([0.2]), np.array([0.5]))
