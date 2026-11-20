"""Tests for the T222 Phase 0 calibration-only harness."""

from __future__ import annotations

import inspect

import numpy as np

from q_speace.bcel import BCELCatalog
from q_speace.spiking import (
    CalibrationConfig,
    CodecConfig,
    make_calibration_dataset,
    max_abs_cohens_d,
    run_calibration,
)


def _config() -> CalibrationConfig:
    return CalibrationConfig(
        n_train=64,
        n_calibration=32,
        n_features=6,
        codec=CodecConfig(levels=3, codebook_size=6, seed=1),
        seed_split=2,
        seed_codebook=1,
        seed_corruption=3,
    )


def test_dataset_has_only_train_and_calibration_partitions() -> None:
    dataset = make_calibration_dataset(_config())
    assert dataset.x_train.shape == (64, 6)
    assert dataset.x_calibration.shape == (32, 6)
    assert dataset.y_calibration.shape == (32,)
    assert not hasattr(dataset, "x_heldout")


def test_calibration_report_never_claims_dod_or_heldout() -> None:
    report = run_calibration(_config(), run_id="cal-001").report
    assert report["status"] == "calibration_only"
    assert report["dod_eligible"] is False
    assert report["heldout_used"] is False
    assert report["thresholds_locked"] is False
    assert report["partitions"]["train_samples"] == 64
    assert report["partitions"]["calibration_samples"] == 32
    assert report["partitions"]["evaluation_samples"] == 0


def test_calibration_records_observations_for_all_configurations() -> None:
    report = run_calibration(_config()).report
    observations = report["observations"]
    assert set(observations["probe_effect_size"]) == {"spike", "codec", "spike+codec"}
    assert len(observations["degradation"]) == 3
    assert len(observations["corruption"]) == 3
    assert observations["reconstruction"]["mse_total"] >= 0.0


def test_cost_registers_do_not_fabricate_sevo_or_measured_joules() -> None:
    cost = run_calibration(_config()).report["cost_registers"]
    assert cost["sevo"] is None
    assert cost["sevo_reason"]
    assert cost["measured_joules"] == "non misurati"
    assert cost["measured_joules_reason"]
    assert isinstance(cost["estimated_joules"]["spike"], float)
    assert cost["estimated_joules"]["codec"] is None
    assert cost["estimated_joules"]["label"] == "estimated, not measured"


def test_calibration_is_deterministic_for_the_same_config() -> None:
    first = run_calibration(_config()).report["observations"]
    second = run_calibration(_config()).report["observations"]
    assert first["probe_effect_size"] == second["probe_effect_size"]
    assert first["reconstruction"] == second["reconstruction"]
    assert first["degradation"] == second["degradation"]
    assert first["corruption"] == second["corruption"]


def test_harness_does_not_accept_a_heldout_argument() -> None:
    for function in (run_calibration, make_calibration_dataset):
        parameters = inspect.signature(function).parameters
        assert "heldout" not in parameters
        assert "x_heldout" not in parameters


def test_probe_effect_size_is_positive_for_a_separable_signal() -> None:
    readout = np.array([[0.0], [0.1], [5.0], [5.1]])
    labels = np.array([0, 0, 1, 1])
    assert max_abs_cohens_d(readout, labels) > 1.0


def test_t222_bcel_entries_are_registered() -> None:
    catalog = BCELCatalog()
    assert catalog.get("Coarse-to-fine generation as cognition (T222)").classification == (
        "accidental"
    )
    assert catalog.is_functional("Multiscale residual quantization (T222)")
    assert catalog.is_functional("Learned discrete concept code (T222)")
