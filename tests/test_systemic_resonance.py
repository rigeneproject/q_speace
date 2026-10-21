from math import nan

import pytest

from q_speace.systemic_resonance import NodeState, ResonanceEngine


def make_node(index: int, *, entropy: float = 0.05, tension: float = 0.10) -> NodeState:
    return NodeState(f"node-{index}", load=0.2, entropy=entropy, tension=tension, phase=0.0)


def test_empty_engine_has_empty_health() -> None:
    health = ResonanceEngine().assess_health()
    assert health.state == "empty"
    assert health.clusters == ()


def test_aligned_low_entropy_six_node_cluster_is_stable() -> None:
    engine = ResonanceEngine()
    for index in range(6):
        engine.update_node_state(make_node(index))

    health = engine.assess_health()

    assert health.state == "stable"
    assert len(health.clusters) == 1
    assert health.clusters[0].node_ids == tuple(f"node-{index}" for index in range(6))


def test_high_entropy_prevents_cluster() -> None:
    engine = ResonanceEngine()
    for index in range(6):
        engine.update_node_state(make_node(index, entropy=0.9))

    assert engine.assess_health().state == "degraded"
    assert engine.find_hexagonal_clusters() == ()


def test_high_tension_degrades_even_a_resonant_cluster() -> None:
    engine = ResonanceEngine()
    for index in range(6):
        engine.update_node_state(make_node(index, tension=0.9))

    health = engine.assess_health()
    assert health.clusters
    assert health.state == "degraded"


@pytest.mark.parametrize("field,value", [("load", -0.1), ("entropy", 1.1), ("tension", nan)])
def test_invalid_telemetry_is_rejected(field: str, value: float) -> None:
    values = {"load": 0.1, "entropy": 0.1, "tension": 0.1}
    values[field] = value
    with pytest.raises(ValueError):
        NodeState("node", phase=0.0, **values)
