"""T229 tests for the four decision rules on hand-checkable archives."""

from statistics import mean

from q_speace.experiments.context_decay_memory import GRID, Entry, choose, shuffled
from q_speace.experiments.error_memory_verifier import verify


def archive() -> tuple[Entry, ...]:
    return tuple(
        Entry(i, float(i), (0.0, 2.0, 2.0, 2.0, 1.0) if i < 7 else (3.0, 2.0, 2.0, 2.0, 0.0))
        for i in range(16)
    )


def test_grid_verified_and_a_ignores_archive() -> None:
    assert all(verify(d).status == "VALIDA" for d in GRID)
    a = choose("A", 0.25, ())
    assert a == choose("A", 0.25, archive())
    assert a["decay"] == 0.9
    assert a["neighbors"] == []


def test_global_and_contextual_decisions_use_different_evidence() -> None:
    rows = archive()
    assert choose("B", 0, rows)["decay"] == 0.995
    assert choose("B", 15, rows)["scores"] == choose("B", 0, rows)["scores"]
    local = choose("C", 0.0, rows)
    assert local["decay"] == 0.75
    assert [n["index"] for n in local["neighbors"]] == list(range(7))
    assert [n["distance"] for n in local["neighbors"]] == list(range(7))
    assert local["scores"] == [0, 2, 2, 2, 1]
    assert choose("C", 15, rows)["decay"] == 0.995


def test_permutation_keeps_every_outcome_and_each_column_mean_exactly() -> None:
    rows = archive()
    swapped = shuffled(rows, seed=17)
    assert swapped != rows and swapped == shuffled(rows, seed=17)
    assert rows == archive()
    assert sorted(r.context for r in rows) == sorted(r.context for r in swapped)
    assert [(r.index, r.losses) for r in rows] == [(r.index, r.losses) for r in swapped]
    for col in range(len(GRID)):
        assert mean(r.losses[col] for r in rows) == mean(r.losses[col] for r in swapped)
    assert choose("B", 0.0, rows)["scores"] == choose("B", 0.0, swapped)["scores"]
    assert choose("C", 3.0, swapped) == choose("D", 3.0, swapped)


def test_neighbor_ties_use_stable_index_and_loss_ties_use_grid_order() -> None:
    rows = tuple(Entry(i, 0.0, (1.0,) * len(GRID)) for i in reversed(range(12)))
    decision = choose("C", 0.0, rows)
    assert decision["decay"] == GRID[0]
    assert [n["index"] for n in decision["neighbors"]] == list(range(7))
