"""T-GOV-01 — Digital twin as pre-execution guardrail.

Acceptance checks (from T-GOV-01 spec):
- predicted-state invariants reject unsafe proposals;
- twin unavailable / prediction failure → conservative refusal (strict);
- actuator integration: blocked proposals never enter the queue and the
  impact check is recorded in the proposal + audit;
- proposals without checker keep the previous behavior;
- a real DigitalTwinModel with in-bounds state lets normal proposals through.
"""

from __future__ import annotations

from speace_core.cellular_brain.action_governance.impact_check import (
    DEFAULT_IMPACT_INVARIANTS,
    TwinImpactChecker,
)
from speace_core.cellular_brain.embodiment.embodied_action_actuator import (
    EmbodiedActionActuator,
)
from speace_core.cellular_brain.embodiment.physical_environment_model import (
    PhysicalEnvironmentModel,
)


class StubTwin:
    """DigitalTwinModel stand-in with a canned simulation trace."""

    def __init__(self, final_state: dict[str, float]) -> None:
        self._final_state = dict(final_state)
        self.last_action: dict[str, float] | None = None

    def simulate_action(self, action: dict[str, float], horizon_ticks: int = 5):
        self.last_action = dict(action)
        return {
            "action": action,
            "horizon_ticks": horizon_ticks,
            "trace": [{"tick": 1, "state": dict(self._final_state)}],
            "changes": {},
            "primary_effects": [],
        }


def _in_bounds_state() -> dict[str, float]:
    return {
        "cpu_avg": 40.0,
        "mem_used": 55.0,
        "disk_used": 60.0,
        "net_in": 10.0,
        "net_out": 10.0,
        "temp_avg": 45.0,
        "process_count": 120.0,
        "battery_level": 80.0,
    }


def test_default_invariants_reject_out_of_bounds_prediction():
    twin = StubTwin({**_in_bounds_state(), "cpu_avg": 150.0})
    checker = TwinImpactChecker(twin=twin)

    result = checker.check_proposal("execute_command", {"cmd": "echo hi"})

    assert result.outcome == "reject"
    assert any("cpu_avg" in inv for inv in result.failed_invariants)
    assert result.predicted_state["cpu_avg"] == 150.0


def test_pass_when_all_invariants_hold():
    twin = StubTwin(_in_bounds_state())
    checker = TwinImpactChecker(twin=twin)

    result = checker.check_proposal("send_signal_to_self", {"signal_type": "request_resume"})

    assert result.outcome == "pass"
    assert result.failed_invariants == []


def test_twin_unavailable_is_conservative_by_default():
    checker = TwinImpactChecker(twin=None)

    result = checker.check_proposal("delete_file", {"path": "data/x"})

    assert result.outcome == "reject"
    assert result.reason.startswith("unverifiable:")


def test_unverifiable_can_be_reported_without_escalation():
    checker = TwinImpactChecker(twin=None, strict_unverifiable=False)

    result = checker.check_proposal("delete_file", {"path": "data/x"})

    assert result.outcome == "unverifiable"
    assert result.reason == "twin_unavailable"


def test_actuator_blocks_rejected_proposal_before_queueing():
    twin = StubTwin({**_in_bounds_state(), "temp_avg": 200.0})
    checker = TwinImpactChecker(twin=twin)
    actuator = EmbodiedActionActuator(impact_checker=checker)

    proposal_id = actuator.propose_action("execute_command", {"cmd": "echo hi"})

    proposal = actuator._proposals[proposal_id]
    assert proposal["status"] == "blocked"
    assert proposal["impact_check"]["outcome"] == "reject"
    assert actuator._queue == []
    history = actuator._history[-1]
    assert history["outcome"].name == "BLOCKED"
    assert "impact_check" in history["error"] or history["error"].startswith("impact_check")


def test_actuator_without_checker_keeps_previous_behavior():
    actuator = EmbodiedActionActuator()

    proposal_id = actuator.propose_action("send_signal_to_self", {"signal_type": "ping"})

    proposal = actuator._proposals[proposal_id]
    assert proposal["status"] == "proposed"
    assert "impact_check" not in proposal
    assert len(actuator._queue) == 1


def test_actuator_blocks_unverifiable_in_strict_mode():
    actuator = EmbodiedActionActuator(impact_checker=TwinImpactChecker(twin=None))

    proposal_id = actuator.propose_action("log_event", {"message": "hi"})

    assert actuator._proposals[proposal_id]["status"] == "blocked"
    assert actuator._queue == []


def test_actuator_allows_unverifiable_in_non_strict_mode():
    actuator = EmbodiedActionActuator(
        impact_checker=TwinImpactChecker(twin=None, strict_unverifiable=False),
        impact_check_strict=False,
    )

    proposal_id = actuator.propose_action("log_event", {"message": "hi"})

    proposal = actuator._proposals[proposal_id]
    assert proposal["status"] == "proposed"
    assert proposal["impact_check"]["outcome"] == "unverifiable"
    assert len(actuator._queue) == 1


def test_real_digital_twin_passes_in_bounds_proposal():
    class StubSensorArray:
        def read_all(self):
            return _in_bounds_state()

    environment = PhysicalEnvironmentModel()
    environment.update(_in_bounds_state())

    from speace_core.cellular_brain.embodiment.digital_twin_model import DigitalTwinModel

    twin = DigitalTwinModel(
        sensor_array=StubSensorArray(),
        environment_model=environment,
        data_root="data/embodiment/test_t_gov_01",
    )
    checker = TwinImpactChecker(twin=twin)
    actuator = EmbodiedActionActuator(impact_checker=checker)

    proposal_id = actuator.propose_action("send_signal_to_self", {"signal_type": "ping"})

    proposal = actuator._proposals[proposal_id]
    assert proposal["status"] == "proposed"
    assert proposal["impact_check"]["outcome"] == "pass"
    assert len(actuator._queue) == 1


def test_default_invariants_are_physical_bounds():
    ids = {inv.invariant_id for inv in DEFAULT_IMPACT_INVARIANTS}
    assert any(inv.startswith("cpu_avg") for inv in ids)
    assert any(inv.startswith("temp_avg") for inv in ids)
    assert len(DEFAULT_IMPACT_INVARIANTS) >= 4
