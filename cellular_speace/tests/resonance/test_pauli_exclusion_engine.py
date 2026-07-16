import pytest
from speace_core.cellular_brain.resonance.pauli_exclusion_engine import (
    PauliExclusionEngine,
    CognitiveQuantumNumbers,
)


@pytest.fixture
def engine():
    return PauliExclusionEngine(engine_id="test_pauli")


class TestCognitiveQuantumNumbers:
    def test_to_tuple(self):
        qn = CognitiveQuantumNumbers(
            region_id="prefrontal",
            frequency_band="beta",
            function_type="executive",
            encoding_dimension=1,
        )
        t = qn.to_tuple()
        assert t == ("prefrontal", "beta", "executive", 1)

    def test_to_signature(self):
        qn1 = CognitiveQuantumNumbers(
            region_id="prefrontal", frequency_band="beta", function_type="executive"
        )
        qn2 = CognitiveQuantumNumbers(
            region_id="prefrontal", frequency_band="beta", function_type="executive"
        )
        assert qn1.to_signature() == qn2.to_signature()

    def test_different_signatures(self):
        qn1 = CognitiveQuantumNumbers(
            region_id="prefrontal", frequency_band="beta", function_type="executive"
        )
        qn2 = CognitiveQuantumNumbers(
            region_id="hippocampus", frequency_band="theta", function_type="memory"
        )
        assert qn1.to_signature() != qn2.to_signature()


class TestPauliExclusionEngine:
    def test_init(self, engine):
        assert engine.engine_id == "test_pauli"
        assert len(engine.occupied_states) == 0

    def test_try_occupy_success(self, engine):
        qn = CognitiveQuantumNumbers(
            region_id="prefrontal", frequency_band="beta", function_type="executive"
        )
        result = engine.try_occupy("agent1", qn)
        assert result is True
        assert "agent1" in engine.occupied_states

    def test_try_occupy_collision(self, engine):
        qn = CognitiveQuantumNumbers(
            region_id="prefrontal", frequency_band="beta", function_type="executive"
        )
        assert engine.try_occupy("agent1", qn)
        assert engine.try_occupy("agent2", qn) is False

    def test_release(self, engine):
        qn = CognitiveQuantumNumbers(
            region_id="prefrontal", frequency_band="beta", function_type="executive"
        )
        engine.try_occupy("agent1", qn)
        engine.release("agent1")
        assert "agent1" not in engine.occupied_states
        assert engine.try_occupy("agent2", qn) is True

    def test_find_collisions(self, engine):
        qn = CognitiveQuantumNumbers(
            region_id="prefrontal", frequency_band="beta", function_type="executive"
        )
        engine.try_occupy("agent1", qn)
        colliders = engine.find_collisions("agent2", qn)
        assert "agent1" in colliders

    def test_find_collisions_no_collision(self, engine):
        qn1 = CognitiveQuantumNumbers(region_id="prefrontal", frequency_band="beta", function_type="executive")
        qn2 = CognitiveQuantumNumbers(region_id="hippocampus", frequency_band="theta", function_type="memory")
        engine.try_occupy("agent1", qn1)
        colliders = engine.find_collisions("agent2", qn2)
        assert len(colliders) == 0

    def test_find_available_state_preferred(self, engine):
        qn = CognitiveQuantumNumbers(region_id="prefrontal", frequency_band="beta", function_type="executive")
        result = engine.find_available_state("agent1", qn)
        assert result is not None
        assert result.to_signature() == qn.to_signature()

    def test_find_available_state_after_collision(self, engine):
        qn = CognitiveQuantumNumbers(region_id="prefrontal", frequency_band="beta", function_type="executive")
        engine.try_occupy("agent1", qn)
        result = engine.find_available_state("agent2", qn)
        assert result is not None
        assert result.to_signature() != qn.to_signature()

    def test_detect_collision_risk_zero(self, engine):
        qn = CognitiveQuantumNumbers(region_id="prefrontal", frequency_band="beta", function_type="executive")
        risk = engine.detect_collision_risk("agent1", qn)
        assert risk == 0.0

    def test_detect_collision_risk_positive(self, engine):
        qn = CognitiveQuantumNumbers(region_id="prefrontal", frequency_band="beta", function_type="executive")
        engine.try_occupy("agent1", qn)
        risk = engine.detect_collision_risk("agent2", qn)
        assert risk > 0.0

    def test_force_differentiation(self, engine):
        qn = CognitiveQuantumNumbers(region_id="prefrontal", frequency_band="beta", function_type="executive")
        engine.try_occupy("agent1", qn)
        result = engine.force_differentiation("agent2", qn)
        assert result is not None
        assert result.to_signature() != qn.to_signature()

    def test_get_occupancy_count(self, engine):
        assert engine.get_occupancy_count() == 0
        engine.try_occupy("a1", CognitiveQuantumNumbers(region_id="r1", frequency_band="alpha", function_type="exec"))
        assert engine.get_occupancy_count() == 1

    def test_get_unique_state_count(self, engine):
        engine.try_occupy("a1", CognitiveQuantumNumbers(region_id="r1", frequency_band="alpha", function_type="exec"))
        engine.try_occupy("a2", CognitiveQuantumNumbers(region_id="r1", frequency_band="beta", function_type="exec"))
        assert engine.get_unique_state_count() == 2

    def test_reset(self, engine):
        engine.try_occupy("a1", CognitiveQuantumNumbers(region_id="r1", frequency_band="alpha", function_type="exec"))
        engine.reset()
        assert len(engine.occupied_states) == 0
        assert engine.exclusion_violations == 0

    def test_state_not_released_on_different_signature(self, engine):
        qn = CognitiveQuantumNumbers(region_id="r1", frequency_band="alpha", function_type="exec")
        engine.try_occupy("a1", qn)
        assert engine.try_occupy("a2", CognitiveQuantumNumbers(region_id="r1", frequency_band="beta", function_type="exec")) is True
