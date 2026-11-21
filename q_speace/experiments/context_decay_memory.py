"""T229 selectors. Their only episode input is the observed prefix statistic."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace
from typing import TypedDict

GRID = (0.75, 0.8, 0.9, 0.975, 0.995)
NEIGHBORS = 7


@dataclass(frozen=True)
class Entry:
    """One development episode, with losses in the fixed order of GRID."""

    index: int
    context: float
    losses: tuple[float, ...]


class Neighbor(TypedDict):
    index: int
    context: float
    distance: float
    losses: list[float]


class Decision(TypedDict):
    decay: float
    rule: str
    context: float
    scores: list[float]
    neighbors: list[Neighbor]


def shuffled(archive: tuple[Entry, ...], seed: int) -> tuple[Entry, ...]:
    """Relabel contexts with a local RNG, retaining each entire outcome row."""
    contexts = [entry.context for entry in archive]
    random.Random(seed).shuffle(contexts)
    return tuple(
        replace(entry, context=context) for entry, context in zip(archive, contexts, strict=True)
    )


def choose(condition: str, context: float, archive: tuple[Entry, ...]) -> Decision:
    """Apply one predeclared rule and return the data underlying its choice.

    C and D execute exactly the same rule. The caller supplies the original
    archive to C or its frozen context permutation to D. The context has
    already been divided by the fixed sensor scale at the observation boundary.
    """
    if condition == "A":
        return {"decay": 0.9, "rule": "fixed", "context": context, "scores": [], "neighbors": []}
    if condition == "B":
        selected = archive
        rule = "global_min_mean"
    elif condition in {"C", "D"}:
        ordered = sorted(archive, key=lambda row: (abs(row.context - context), row.index))
        selected = tuple(ordered[:NEIGHBORS])
        rule = "nearest_min_mean"
    else:
        raise ValueError(f"Unknown T229 condition: {condition!r}")
    if not selected:
        raise ValueError("A memory-based selection requires development episodes")
    scores = [
        math.fsum(row.losses[column] for row in selected) / len(selected)
        for column in range(len(GRID))
    ]
    best = min(range(len(GRID)), key=scores.__getitem__)
    neighbors: list[Neighbor] = [
        {
            "index": row.index,
            "context": row.context,
            "distance": abs(context - row.context),
            "losses": list(row.losses),
        }
        for row in selected
    ]
    return {
        "decay": GRID[best],
        "rule": rule,
        "context": context,
        "scores": scores,
        "neighbors": neighbors,
    }
