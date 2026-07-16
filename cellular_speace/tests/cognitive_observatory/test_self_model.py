"""Tests for Self Model Engine (L2)."""


class TestSelfModelEngine:
    def test_empty_init(self, self_model):
        summary = self_model.get_self_summary()
        assert summary["identity_name"] == "SPEACE"
        assert summary["active_goals"] == []
        assert summary["consistency"] == 0.5

    def test_update_identity(self, self_model):
        self_model.update_identity({"entity_name": "SPEACE-TEST", "nature": "digital"})
        assert self_model.model.identity["entity_name"] == "SPEACE-TEST"

    def test_set_goals(self, self_model):
        self_model.set_goals([{"name": "goal1"}, {"name": "goal2"}])
        assert len(self_model.model.active_goals) == 2

    def test_add_remove_goal(self, self_model):
        self_model.add_goal({"name": "test_goal"})
        assert len(self_model.model.active_goals) == 1
        self_model.remove_goal("test_goal")
        assert len(self_model.model.active_goals) == 0

    def test_set_constraints(self, self_model):
        self_model.set_constraints(["c1", "c2"])
        assert len(self_model.model.active_constraints) == 2

    def test_update_capability(self, self_model):
        self_model.update_capability("reasoning", 0.9)
        assert self_model.model.capabilities["reasoning"] == 0.9

    def test_add_weakness(self, self_model):
        self_model.add_weakness("poor_memory")
        assert "poor_memory" in self_model.model.known_weaknesses
        self_model.add_weakness("poor_memory")  # no duplicate
        assert len(self_model.model.known_weaknesses) == 1

    def test_add_error(self, self_model):
        self_model.add_error({"type": "timeout", "count": 1})
        assert len(self_model.model.known_errors) == 1

    def test_add_blind_spot(self, self_model):
        self_model.add_blind_spot("external_data")
        assert "external_data" in self_model.model.blind_spots

    def test_update_genome_state(self, self_model):
        self_model.update_genome_state({"genes": 100})
        assert self_model.model.genome_state["genes"] == 100

    def test_update_ilf_state(self, self_model):
        self_model.update_ilf_state({"coherence": 0.7, "entropy": 0.3})
        assert self_model.model.ilf_state["coherence"] == 0.7

    def test_update_bcel_coverage(self, self_model):
        self_model.update_bcel_coverage({"mapped": 10, "total": 12})
        assert self_model.model.bcel_coverage["mapped"] == 10

    def test_update_from_orchestrator(self, self_model):
        state = {
            "identity": {"entity_name": "SPEACE"},
            "ilf": {"coherence": 0.8},
            "goals": [{"name": "survive"}],
            "constraints": ["c1"],
            "capabilities": {"reasoning": 0.9},
        }
        self_model.update_from_orchestrator(state)
        summary = self_model.get_self_summary()
        assert summary["identity_name"] == "SPEACE"
        assert "survive" in summary["active_goals"]
        assert summary["capabilities"]["reasoning"] == 0.9

    def test_get_identity_consistency(self, self_model):
        assert self_model.get_identity_consistency() == 0.5
        self_model.update_identity({"invariants": [{"name": "c1"}, {"name": "c2"}]})
        self_model.set_constraints(["c1"])
        consistency = self_model.get_identity_consistency()
        assert consistency > 0.0

    def test_get_self_summary(self, self_model):
        self_model.update_capability("reasoning", 0.95)
        self_model.update_capability("memory", 0.80)
        summary = self_model.get_self_summary()
        caps = summary["capabilities"]
        # Should be sorted by confidence descending
        caps_list = list(caps.items())
        assert caps_list[0][1] >= caps_list[1][1]

    def test_clear(self, self_model):
        self_model.update_identity({"entity_name": "TEST"})
        self_model.clear()
        assert self_model.model.identity == {}
