"""Offline evaluation utilities for predictive-confidence calibration (T206)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CalibrationReport:
    """Calibration metrics for labelled binary outcomes.

    These metrics evaluate a forecast.  They make no claim about subjective
    awareness, reasoning, or consciousness.
    """

    samples: int
    brier_score: float
    expected_calibration_error: float


def calibration_report(
    confidences: np.ndarray, outcomes: np.ndarray, bins: int = 10
) -> CalibrationReport:
    """Return Brier score and equal-width expected calibration error.

    ``outcomes`` must contain binary labels (0/1).  Empty or mismatched input
    is rejected so a score cannot be fabricated from an incomplete run.
    """
    conf = np.asarray(confidences, dtype=float).ravel()
    actual = np.asarray(outcomes, dtype=float).ravel()
    if conf.size == 0 or conf.size != actual.size:
        raise ValueError("confidences and outcomes must be non-empty and equally sized")
    if bins < 1:
        raise ValueError("bins must be >= 1")
    if np.any((conf < 0.0) | (conf > 1.0)) or np.any((actual < 0.0) | (actual > 1.0)):
        raise ValueError("confidences and outcomes must be in [0, 1]")
    if not np.all(np.isin(actual, [0.0, 1.0])):
        raise ValueError("outcomes must be binary labels")
    brier = float(np.mean((conf - actual) ** 2))
    indices = np.minimum((conf * bins).astype(int), bins - 1)
    ece = 0.0
    for index in range(bins):
        mask = indices == index
        if mask.any():
            ece += float(mask.mean() * abs(conf[mask].mean() - actual[mask].mean()))
    return CalibrationReport(conf.size, brier, float(ece))
