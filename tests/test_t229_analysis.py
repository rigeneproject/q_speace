"""T229 analysis on known matched outcomes, independently of the runtime."""

from collections.abc import Sequence
from typing import Any

import pytest

from q_speace.experiments.context_decay_analysis import summarize


def episode(i: int, family: str, c_loss: float, d_losses: Sequence[float]) -> dict[str, Any]:
    rows: list[tuple[str, float, float, int | None]] = [
        ("A", 0.9, 6.0, None),
        ("B", 0.8, 4.0, None),
        ("C", 0.8 if c_loss == 4 else 0.75, c_loss, None),
    ]
    for seed, value in enumerate(d_losses):
        rows.append(("D", 0.8 if value == 4 else 0.995, value, seed))
    return {
        "id": str(i),
        "family": family,
        "decisions": [
            {
                "condition": condition,
                "permutation_seed": perm,
                "decay": decay,
                "loss": value,
                "prefix_loss": 0.1,
                "perturbation_loss": value - 0.3,
                "return_loss": 0.2,
                "lookup_ns": 11,
                "recovered": value < 5,
                "censored_ticks": 5 if value < 5 else 22,
            }
            for condition, decay, value, perm in rows
        ],
    }


def test_paired_bootstrap_counts_episodes_and_keeps_same_choice() -> None:
    # One independent episode per stratum. Stratified resampling must have
    # zero width, even though the eight D decisions on one episode disagree.
    data = [
        episode(1, "triangle", 4, [4] * 4 + [8] * 4),
        episode(2, "rectangle", 2, [1] * 8),
    ]
    summary = summarize(data)
    overall = summary["all"]
    assert overall["n_episodes"] == 2
    assert overall["contrasts"]["B_minus_C"] == {"mean": 1.0, "ci95": [1.0, 1.0]}
    assert overall["contrasts"]["D_minus_C"] == {"mean": 0.5, "ci95": [0.5, 0.5]}
    assert summary["both_primary_lower_bounds_positive"]
    assert overall["arms"]["D"]["loss"] == 3.5
    assert overall["arms"]["D"]["recovered"] == 0.75
    assert overall["choices"]["C_vs_B"]["fraction_changed"] == 0.5
    choices = overall["choices"]["C_vs_D"]
    assert choices["changed"] == 1.5
    assert choices["improved"] == 0.5
    assert choices["worsened"] == 1.0
    assert choices["tied"] == 0.0
    assert choices["decision_counts"]["unchanged"] == 4
    assert choices["decision_counts"]["worsened"] == 8
    assert summary["by_family"]["rectangle"]["contrasts"]["D_minus_C"]["mean"] == -1.0


def test_repeated_d_comparisons_are_not_independent_samples() -> None:
    data = [
        episode(1, "rectangle", 4, [3] * 8),
        episode(2, "rectangle", 4, [7] * 8),
    ]
    result = summarize(data)
    assert result["all"]["contrasts"]["D_minus_C"] == {"mean": 1.0, "ci95": [-1.0, 3.0]}
    assert not result["both_primary_lower_bounds_positive"]


def test_missing_or_duplicate_decisions_are_detected() -> None:
    incomplete = episode(1, "triangle", 3, [7] * 7)
    with pytest.raises(ValueError, match="eight"):
        summarize([incomplete])
    complete = episode(1, "triangle", 3, [7] * 8)
    with pytest.raises(ValueError, match="duplicate"):
        summarize([complete, complete])
