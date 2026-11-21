"""Counterfactual branch and information-boundary tests for T229."""

import asyncio

import numpy as np
import pytest

from q_speace.experiments.context_decay_runtime import measure, prepare


def test_prefix_observations_are_unchanged_by_future_shape() -> None:
    rect = asyncio.run(prepare(174, "rectangle"))
    tri = asyncio.run(prepare(174, "triangle"))
    assert rect.description["latent"] != tri.description["latent"]
    assert rect.prefix == tri.prefix
    assert rect.snapshot_id == tri.snapshot_id
    readings = [t["input"][1] for t in rect.prefix]
    assert rect.context == tri.context == float(np.std(readings)) / 0.25


def test_independent_branches_use_real_kernel_and_score_all_ticks() -> None:
    episode = asyncio.run(prepare(347, "triangle"))
    slow = asyncio.run(measure(episode, 0.995))
    fast = asyncio.run(measure(episode, 0.75))
    repeat = asyncio.run(measure(episode, 0.995))
    assert repeat == slow
    assert slow["ticks"][:8] == fast["ticks"][:8] == episode.prefix
    assert len(episode.cortex._history) == 8
    assert len(episode.cortex._reports) == 8
    assert len(asyncio.run(episode.cortex.memory.recent(256))) == 8
    assert slow["ticks"][8]["q_star"] != fast["ticks"][8]["q_star"]
    for row, decay in ((slow, 0.995), (fast, 0.75)):
        assert len(row["ticks"]) == 48
        for tick in row["ticks"]:
            assert tick["approved"]
            assert tick["decay"] == (0.9 if tick["tick"] <= 8 else decay)
            assert tick["tv"] == pytest.approx(
                np.abs(np.subtract(tick["q_star"], tick["reference"])).sum() / 2
            )
        assert row["prefix_loss"] + row["perturbation_loss"] + row["return_loss"] == row["loss"]
        assert row["loss"] == pytest.approx(sum(t["tv"] for t in row["ticks"]))
    with pytest.raises(ValueError, match="certified"):
        asyncio.run(measure(episode, 0.5))
