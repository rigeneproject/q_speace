"""Paired analysis for T229. An episode is the sampling unit in every contrast."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from typing import Any

import numpy as np

BOOTSTRAP_REPLICATES = 4000
BOOTSTRAP_SEED = 22977
METRICS = (
    "loss",
    "prefix_loss",
    "perturbation_loss",
    "return_loss",
    "recovered",
    "censored_ticks",
    "lookup_ns",
)
ARMS = ("A", "B", "C", "D")
Row = dict[str, Any]
ArmRows = dict[str, list[Row]]


def _paired_arms(episode: Row) -> ArmRows:
    arms: ArmRows = {name: [] for name in ARMS}
    for decision in episode["decisions"]:
        arms[decision["condition"]].append(decision)
    if any(len(arms[name]) != 1 for name in ("A", "B", "C")):
        raise ValueError("Expected exactly one A, B and C decision per episode")
    perms = {d["permutation_seed"] for d in arms["D"]}
    if len(arms["D"]) != 8 or len(perms) != 8 or None in perms:
        raise ValueError("Expected eight distinct D permutations in each episode")
    return arms


def _choice_counts(pairs: Sequence[ArmRows], other: str) -> Row:
    """Count changed choices and their outcome, weighting each episode equally."""
    counts: Counter[str] = Counter()
    for arms in pairs:
        c = arms["C"][0]
        for comparison in arms[other]:
            if comparison["decay"] == c["decay"]:
                counts["unchanged"] += 1
            elif c["loss"] < comparison["loss"]:
                counts["improved"] += 1
            elif c["loss"] > comparison["loss"]:
                counts["worsened"] += 1
            else:
                counts["tied"] += 1
    counts["changed"] = counts["improved"] + counts["worsened"] + counts["tied"]
    per_episode = len(pairs[0][other])
    categories = ("changed", "improved", "worsened", "tied", "unchanged")
    return {
        "n_episodes": len(pairs),
        "comparisons_per_episode": per_episode,
        "fraction_changed": counts["changed"] / (len(pairs) * per_episode),
        **{key: counts[key] / per_episode for key in categories},
        "decision_counts": {key: counts[key] for key in categories},
    }


def _group(pairs: Sequence[ArmRows], families: Sequence[str]) -> Row:
    # The inner mean reduces the D permutations within each episode. Keeping
    # the episode axis here also retains zero-difference pairs in the bootstrap.
    means = np.array(
        [
            [np.mean([[r[key] for key in METRICS] for r in arms[name]], axis=0) for name in ARMS]
            for arms in pairs
        ],
        dtype=float,
    )
    if not np.isfinite(means).all():
        raise ValueError("Non-finite episode measure")
    b_loss, c_loss, d_loss = means[:, 1:, 0].T
    deltas = np.column_stack((b_loss - c_loss, d_loss - c_loss))
    strata: dict[str, list[int]] = defaultdict(list)
    for i, family in enumerate(families):
        strata[family].append(i)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    samples = np.zeros((BOOTSTRAP_REPLICATES, 2))
    for family in sorted(strata):
        indices = strata[family]
        sampled = rng.choice(indices, size=(BOOTSTRAP_REPLICATES, len(indices)))
        samples += deltas[sampled].sum(axis=1)
    quantiles = np.percentile(samples / len(pairs), [2.5, 97.5], axis=0)
    totals = means.mean(axis=0)
    return {
        "n_episodes": len(pairs),
        "arms": {
            name: dict(zip(METRICS, totals[index].tolist(), strict=True))
            for index, name in enumerate(ARMS)
        },
        "contrasts": {
            name: {"mean": float(deltas[:, i].mean()), "ci95": quantiles[:, i].tolist()}
            for i, name in enumerate(("B_minus_C", "D_minus_C"))
        },
        "choices": {f"C_vs_{other}": _choice_counts(pairs, other) for other in ("B", "D")},
    }


def summarize(episodes: list[Row]) -> Row:
    """Aggregate completed decisions with 95% stratified paired bootstrap intervals."""
    if not episodes:
        raise ValueError("At least one completed episode is required")
    if len({e["id"] for e in episodes}) != len(episodes):
        raise ValueError("Found duplicate evaluation episode ids")
    pairs = [_paired_arms(e) for e in episodes]
    families = [str(e["family"]) for e in episodes]
    perm_sets = {frozenset(d["permutation_seed"] for d in p["D"]) for p in pairs}
    if len(perm_sets) != 1:
        raise ValueError("D permutation seeds differ across episodes")
    overall = _group(pairs, families)
    return {
        "bootstrap": {
            "replicates": BOOTSTRAP_REPLICATES,
            "seed": BOOTSTRAP_SEED,
            "method": "Paired episode percentile 95%, stratified by perturbation family",
        },
        "all": overall,
        "by_family": {
            f: _group(group, [f] * len(group))
            for f in sorted(set(families))
            if (group := [p for p, family in zip(pairs, families, strict=True) if family == f])
        },
        "both_primary_lower_bounds_positive": all(
            contrast["ci95"][0] > 0 for contrast in overall["contrasts"].values()
        ),
    }
