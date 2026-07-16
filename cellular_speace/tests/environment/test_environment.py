"""Tests for SPEACE external task environments."""
import pytest

from speace_core.environment.cognitive_prediction_environment import (
    CognitivePredictionEnvironment,
    SequenceMode,
)
from speace_core.environment.grid_world_environment import GridWorldEnvironment
from speace_core.environment.environment_adapter import EnvironmentAdapter


def test_prediction_environment_generates_periodic_sequence():
    env = CognitivePredictionEnvironment(
        input_size=10,
        output_size=10,
        mode=SequenceMode.PERIODIC,
        episode_length=20,
        seed=42,
    )
    env.reset_episode()
    p0 = env.current_input()
    p1 = env.true_next()
    assert len(p0) == 10
    assert len(p1) == 10
    assert p0 != p1 or sum(p0) > 0


def test_prediction_evaluates_reward():
    env = CognitivePredictionEnvironment(input_size=10, output_size=10)
    reward, error = env.evaluate_prediction([1.0] * 10, [1.0] * 10)
    assert reward > 0.9
    assert error < 0.1

    reward2, error2 = env.evaluate_prediction([0.0] * 10, [1.0] * 10)
    assert reward2 < 0.5
    assert error2 > 0.5


def test_prediction_episode_runs_with_orchestrator():
    adapter = EnvironmentAdapter(enable_simulator_backend=False)
    summary = adapter.run_prediction_episode(mode=SequenceMode.PERIODIC, steps=20)
    assert summary["steps"] >= 19
    assert "mean_reward" in summary
    assert "cor_collapses" in summary


def test_grid_world_resets_and_steps():
    env = GridWorldEnvironment(dimensions=1, size=10, max_steps=20, seed=42)
    obs = env.reset()
    assert len(obs) == 10
    assert env.agent != env.target


def test_grid_world_episode_runs_with_orchestrator():
    adapter = EnvironmentAdapter(enable_simulator_backend=False)
    summary = adapter.run_grid_episode(dimensions=1, size=5)
    assert summary["steps"] > 0
    assert "total_reward" in summary



def test_associative_recall_environment_builds_pairs():
    from speace_core.environment.associative_recall_environment import AssociativeRecallEnvironment
    env = AssociativeRecallEnvironment(input_size=10, output_size=10, num_pairs=4, seed=42)
    assert len(env._pairs) == 4
    cue, target = env._pairs[0]
    assert len(cue) == 10
    assert len(target) == 10


def test_associative_recall_episode_runs_with_orchestrator():
    from speace_core.environment.associative_recall_environment import AssociativeRecallEnvironment
    adapter = EnvironmentAdapter(enable_simulator_backend=False)
    summary = adapter.run_associative_recall_episode(num_pairs=3, study_repetitions=2, test_length=5)
    assert summary["study_steps"] == 6
    assert summary["test_steps"] == 5
    assert "mean_study_reward" in summary
    assert "mean_test_reward" in summary
