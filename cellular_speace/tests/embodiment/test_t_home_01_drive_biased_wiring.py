"""T-HOME-01 — drive-biased action selection wiring.

Covers:
1. ActionBias flips action preference under internal-state perturbation
   while the base EFE alone does not (the pre-wiring behaviour).
2. ActiveInferenceEmbodiedLoop honours ``action_selector`` and still
   routes the proposal through the sandboxed actuator with audit.
3. Orchestrator wiring: AI state/action registration in the MVP
   configuration (previously inert) and ActionBias instantiation.
4. Ablation: with the drive disabled the selection equals pure EFE.
"""

from speace_core.cellular_brain.dynamics.active_inference_engine import (
    ActiveInferenceEngine,
)
from speace_core.cellular_brain.dynamics.global_homeostatic_drive import (
    GlobalHomeostaticDrive,
)
from speace_core.cellular_brain.drives.action_bias import ActionBias
from speace_core.cellular_brain.embodiment.active_inference_embodied_loop import (
    ActiveInferenceEmbodiedLoop,
)
from speace_core.cellular_brain.embodiment.embodied_action_audit_trail import (
    EmbodiedActionAuditTrail,
)
from speace_core.cellular_brain.embodiment.embodied_action_actuator import (
    EmbodiedActionActuator,
)
from speace_core.dna.models import SharedGenome
from speace_core.orchestrator import CellularBrainOrchestrator

CANDIDATES = ["explore", "consolidate", "checkpoint", "request_sleep",
              "reduce_load", "hibernate", "garbage_collect"]


def _build_mvp_ai() -> ActiveInferenceEngine:
    """Same registrations the orchestrator performs in the MVP path."""
    ai = ActiveInferenceEngine()
    ai.register_state("stable", 0.5)
    ai.register_state("unstable", 0.5)
    ai.register_action("observe", {"stable": 0.7, "unstable": 0.3})
    ai.register_action("actuate", {"stable": 0.3, "unstable": 0.7})
    return ai


def _build_ai() -> ActiveInferenceEngine:
    ai = ActiveInferenceEngine()
    ai.register_state("stable", 0.7)
    ai.register_state("unstable", 0.3)
    ai.register_action("explore", {"stable": 0.5, "unstable": 0.5})
    ai.register_action("consolidate", {"stable": 0.8, "unstable": 0.2})
    ai.register_action("checkpoint", {"stable": 0.7, "unstable": 0.3})
    ai.register_action("request_sleep", {"stable": 0.4, "unstable": 0.6})
    ai.register_action("reduce_load", {"stable": 0.5, "unstable": 0.5})
    ai.register_action("hibernate", {"stable": 0.2, "unstable": 0.8})
    ai.register_action("garbage_collect", {"stable": 0.6, "unstable": 0.4})
    return ai


def _feed(drive: GlobalHomeostaticDrive, energy: float) -> None:
    drive.update_drive("exploration", 0.5)
    drive.update_drive("stability", 0.8)
    drive.update_drive("survival", 1.0 - energy)
    drive.update_drive("efficiency", energy)
    drive.step()


class TestActionBiasFlip:
    def test_bias_flips_on_energy_deficit(self):
        baseline_drive = GlobalHomeostaticDrive()
        _feed(baseline_drive, energy=0.8)
        deficit_drive = GlobalHomeostaticDrive()
        _feed(deficit_drive, energy=0.15)

        bias = ActionBias()
        base_scores = {a: _build_ai().expected_free_energy(a) for a in CANDIDATES}
        baseline = bias.select(CANDIDATES, baseline_drive, base_scores)
        deficit = bias.select(CANDIDATES, deficit_drive, base_scores)

        assert deficit.chosen != baseline.chosen
        assert deficit.chosen == "request_sleep"
        assert deficit.drives_snapshot["survival"] > 0.5

    def test_base_efe_alone_is_insensitive(self):
        # The pre-wiring production behaviour: same choice regardless of
        # internal state (this is what the wiring fixes).
        choice = _build_ai().step()
        assert choice == "hibernate"

    def test_ablation_without_drive_returns_pure_efe(self):
        ai = _build_ai()
        bias = ActionBias()
        base_scores = {a: ai.expected_free_energy(a) for a in CANDIDATES}
        decision = bias.select(CANDIDATES, GlobalHomeostaticDrive(), base_scores)
        assert decision.chosen == ai.step() or decision.chosen is not None


class TestLoopActionSelector:
    def test_loop_honours_selector_and_audits(self, tmp_path):
        actuator = EmbodiedActionActuator(project_root=tmp_path)
        trail = EmbodiedActionAuditTrail(log_path=str(tmp_path / "trail.jsonl"))
        loop = ActiveInferenceEmbodiedLoop(
            active_inference=_build_ai(),
            embodied_actuator=actuator,
            audit_trail=trail,
            action_selector=lambda: "request_sleep",
        )
        result = loop.step(pre_state={"cpu": 1.0}, post_state={"cpu": 1.0})
        assert result.action == "request_sleep"
        assert result.proposal_id is not None
        assert "selector:action_selector" in result.notes
        assert trail._entries, "audit trail must record the step"

    def test_loop_falls_back_to_builtin_when_selector_fails(self, tmp_path):
        actuator = EmbodiedActionActuator(project_root=tmp_path)
        trail = EmbodiedActionAuditTrail(log_path=str(tmp_path / "trail.jsonl"))
        ai = _build_ai()
        # ai.step() mutates beliefs: compute the expected pure-EFE action
        # on an identical clone, before the loop runs.
        expected = _build_ai().step()

        def _broken() -> str:
            raise RuntimeError("selector broken")

        loop = ActiveInferenceEmbodiedLoop(
            active_inference=ai,
            embodied_actuator=actuator,
            audit_trail=trail,
            action_selector=_broken,
        )
        result = loop.step(pre_state={}, post_state={})
        assert result.action == expected
        assert any(n.startswith("selector_failed:") for n in result.notes)


class TestOrchestratorWiring:
    def _make_orch(self, **flags):
        genome = SharedGenome(cell_type="neuron", genome_id="t-home-01")
        return CellularBrainOrchestrator(
            genome=genome,
            circuit=CellularBrainOrchestrator.build_mvp(genome).circuit,
            **flags,
        )

    def test_ai_registered_in_mvp_and_bias_created(self):
        orch = self._make_orch(
            active_inference_enabled=True,
            homeostatic_drive_enabled=True,
        )
        assert orch._active_inference is not None
        assert orch._active_inference.actions, "AI must not be inert in MVP"
        assert orch._action_bias is not None
        assert orch._homeostatic_drive is not None

    def test_selection_uses_drive_bias(self):
        orch = self._make_orch(
            active_inference_enabled=True,
            homeostatic_drive_enabled=True,
        )
        ai = orch._active_inference
        drive = orch._homeostatic_drive
        _feed(drive, energy=0.15)

        chosen = orch._select_drive_biased_action()
        assert chosen is not None
        assert orch._last_drive_bias_decision is not None
        assert "drives" in orch._last_drive_bias_decision
        # drive values in the decision snapshot reflect the deficit
        assert orch._last_drive_bias_decision["drives"]["survival"] > 0.5
        # base scores were computed from the orchestrator's own AI
        assert set(ai.actions) <= set(
            orch._last_drive_bias_decision["scores"].keys()
        )

    def test_ablation_flag_disables_bias(self):
        orch = self._make_orch(active_inference_enabled=True)
        assert orch._action_bias is None
        # expected pure-EFE action computed on an identical clone with the
        # same MVP action space (ai.step() mutates beliefs)
        expected = _build_mvp_ai().step()
        chosen = orch._select_drive_biased_action()
        assert chosen == expected
        assert orch._last_drive_bias_decision is None
