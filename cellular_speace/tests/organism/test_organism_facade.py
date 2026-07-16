import pytest

from speace_core.organism.organism_facade import Organism, IDENTITY_VECTOR_SIZE, IDENTITY_VECTOR_DIMENSIONS


def test_organism_creation():
    o = Organism()
    assert o.organism_id is not None
    assert len(o.organism_id) > 0
    assert len(o.identity_vector) == IDENTITY_VECTOR_SIZE


def test_organism_identity_persistence():
    o1 = Organism()
    o2 = Organism()
    assert o1.organism_id == o2.organism_id  # deterministic from DNA identity


def test_identity_vector_dimensions():
    # Verify all 10 dimensions are present
    expected = [
        "coherence_phi",
        "energy_level",
        "developmental_stage_norm",
        "clone_count_norm",
        "narrative_coherence",
        "metabolic_mode_norm",
        "health_score",
        "identity_divergence",
        "self_model_consistency",
        "bcel_coverage",
    ]
    assert IDENTITY_VECTOR_DIMENSIONS == expected
    assert len(expected) == 10


def test_self_boundary_same():
    o = Organism()
    vec = o.identity_vector
    assert o.is_self(vec) is True
    assert o.self_distance(vec) == 0.0


def test_self_boundary_different():
    o = Organism()
    other = [0.9] * IDENTITY_VECTOR_SIZE
    dist = o.self_distance(other)
    assert dist > 0.0


def test_self_wrong_size():
    o = Organism()
    assert o.is_self([1.0, 2.0]) is False  # wrong dimension
    assert o.self_distance([1.0, 2.0]) == 1.0


def test_identity_digest_stable():
    o = Organism()
    d1 = o.get_identity_digest()
    d2 = o.get_identity_digest()
    assert d1 == d2
    assert len(d1) == 16


def test_snapshot():
    o = Organism()
    snap = o.snapshot()
    assert "organism_id" in snap
    assert "identity_vector" in snap
    assert "developmental_stage" in snap
    assert snap["developmental_stage"] == "stage_0"


def test_update_with_none():
    o = Organism()
    o.update(None)  # should not crash
    snap = o.snapshot()
    assert snap["developmental_stage"] == "stage_0"


def test_lifecycle_property():
    o = Organism()
    assert o.lifecycle is not None
    assert o.lifecycle.current_state == "initializing"
