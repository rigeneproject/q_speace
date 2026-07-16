"""Tests for AutonomousCognitiveLoop."""

import pytest

from speace_core.cellular_brain.runtime.autonomous_cognitive_loop import (
    AutonomousCognitiveLoop,
)


def test_loop_initializes(tmp_path):
    loop = AutonomousCognitiveLoop(data_root=tmp_path / "acl_init")
    assert loop.stats.ticks == 0
    assert loop.dynamics.num_neurons >= 2


def test_loop_tick_increments_stats(tmp_path):
    loop = AutonomousCognitiveLoop(data_root=tmp_path / "acl_tick")
    record = loop.tick()
    assert loop.stats.ticks == 1
    assert "workspace" in record
    assert "sensors" in record
    assert loop.runtime_log_path.exists()


def test_loop_run_produces_state(tmp_path):
    loop = AutonomousCognitiveLoop(data_root=tmp_path / "acl_run")
    stats = loop.run(n_ticks=20)
    assert stats.ticks == 20
    assert stats.sensor_samples == 20
    summary = loop.summary()
    assert summary["stats"]["ticks"] == 20


def test_prediction_errors_logged(tmp_path):
    loop = AutonomousCognitiveLoop(data_root=tmp_path / "acl_pred")
    loop.run(n_ticks=10)
    assert loop.prediction_error_path.exists()
    text = loop.prediction_error_path.read_text(encoding="utf-8").strip()
    assert text
    lines = text.splitlines()
    assert len(lines) == 10
