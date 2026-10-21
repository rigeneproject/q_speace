from math import nan

import pytest

from q_speace.systemic_resonance import NodeState, ResonanceEngine


def node(index: int, *, entropy: float = 0.05, tension: float = 0.1) -> NodeState:
    return NodeState(f"n{index}", 0.2, entropy, tension, 0.0)


def populated_engine() -> ResonanceEngine:
    engine = ResonanceEngine()
    for index in range(6):
        engine.update_node_state(node(index))
    return engine


def test_empty_engine_is_empty() -> None:
    assert ResonanceEngine().assess_health().state == "empty"


def test_aligned_six_node_cluster_is_stable() -> None:
    health = populated_engine().assess_health()
    assert health.state == "stable"
    assert len(health.clusters) == 1


def test_entropy_and_tension_degrade_health() -> None:
    entropy_engine = ResonanceEngine()
    tension_engine = ResonanceEngine()
    for index in range(6):
        entropy_engine.update_node_state(node(index, entropy=0.9))
        tension_engine.update_node_state(node(index, tension=0.9))
    assert entropy_engine.assess_health().state == "degraded"
    assert tension_engine.assess_health().state == "degraded"


def test_controlled_failure_beats_single_path_baseline() -> None:
    result = populated_engine().compare_controlled_failure({"n0"})
    assert result.redundant_capacity == pytest.approx(5 / 6)
    assert result.single_path_capacity == 0.0


@pytest.mark.parametrize("field,value", [("load", -0.1), ("entropy", 1.1), ("tension", nan)])
def test_invalid_telemetry_is_rejected(field: str, value: float) -> None:
    values = {"load": 0.1, "entropy": 0.1, "tension": 0.1}
    values[field] = value
    with pytest.raises(ValueError):
        NodeState("n", phase=0.0, **values)
