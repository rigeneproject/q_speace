"""T-HOME-01.7 — QH-01 post-wiring probe (in-tree re-run).

Reproduces the QH-01 end-to-end phases (§3 of
docs/QH01_dynamic_verification_2026-11-16.md) with the T-HOME-01 wiring
active, and asserts:

- the drive modulators still react to the energy deficit exactly as in the
  pre-wiring audit (no regression of the homeostatic layer);
- the new observables are live: bias decision recorded during ticks and
  active-inference beliefs non-empty in the MVP path (they were ``{}``
  pre-wiring).
"""

from __future__ import annotations

import asyncio

from speace_core.cellular_brain.regulation.homeostasis_engine import SystemMetrics
from speace_core.dna.models import SharedGenome
from speace_core.orchestrator import CellularBrainOrchestrator

TICKS_PER_PHASE = 5


def _build_orchestrator(**flags) -> CellularBrainOrchestrator:
    genome = SharedGenome(cell_type="neuron", genome_id="qh01-post")
    return CellularBrainOrchestrator(
        genome=genome,
        circuit=CellularBrainOrchestrator.build_mvp(genome).circuit,
        tick_interval=0,
        **flags,
    )


def _force_metrics(orch: CellularBrainOrchestrator, energy: float) -> None:
    """Freeze the homeostatic input the way the QH-01 probe did.

    noise=0.5, phi=0.8 as in the QH-01 §2 scenarios A/B.
    """

    def _compute(tick, neurons, astrocytes, synapse_count, pruned_count, _E=energy):
        return SystemMetrics(
            tick=tick,
            coherence_phi=0.8,
            mean_energy=_E,
            noise_level=0.5,
            active_neurons=len(neurons),
        )

    orch._homeostasis.compute_metrics = _compute  # type: ignore[method-assign]


def _run_phase(orch: CellularBrainOrchestrator, energy: float) -> dict:
    _force_metrics(orch, energy)
    asyncio.run(orch.run_ticks(TICKS_PER_PHASE))
    drive = orch._homeostatic_drive
    return {
        "energy": energy,
        "modulation": dict(drive.get_global_modulation()),
        "bias_decision": orch._last_drive_bias_decision,
        "beliefs": dict(orch._active_inference.beliefs)
        if orch._active_inference is not None
        else {},
    }


def test_qh01_post_wiring_phases():
    orch = _build_orchestrator(
        embodiment_enabled=True,
        active_inference_enabled=True,
        homeostatic_drive_enabled=True,
    )
    baseline = _run_phase(orch, energy=0.80)
    deficit = _run_phase(orch, energy=0.10)
    restore = _run_phase(orch, energy=0.90)

    # Homeostatic layer unchanged: deficit raises survival drive error and
    # suppresses plasticity exactly as measured pre-wiring (QH-01 §3).
    assert deficit["modulation"]["plasticity_multiplier"] < 0.5
    assert baseline["modulation"]["plasticity_multiplier"] > deficit[
        "modulation"
    ]["plasticity_multiplier"]
    assert (
        restore["modulation"]["plasticity_multiplier"]
        >= baseline["modulation"]["plasticity_multiplier"] * 0.9
    )

    # New observables (post-wiring): the bias decision is recorded while
    # ticking through the audited embodied loop.
    assert deficit["bias_decision"] is not None
    assert deficit["bias_decision"]["drives"]["survival"] > 0.5
    assert "scores" in deficit["bias_decision"]

    # MVP active inference is no longer inert (beliefs were {} pre-wiring).
    assert deficit["beliefs"], "AI beliefs must be populated in MVP path"

    # Actions proposed through the loop are audited (T-HOME-01.3).
    trail = orch._embodied_audit_trail
    assert trail is not None
