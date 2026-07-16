"""
Simple launch script for the SPEACE brain.

This script demonstrates how to start the SPEACE brain using:
  - parametric representation (DNA-driven cell factory)
  - hierarchical organization (genome regions, periodic table)
  - lazy on-demand activation (FunctionalActivationGate)
  - optional COR collapse dynamics
  - optional pluggable simulator backend

It is not a real consciousness; it is a running simulation of a
digital-neural organism.
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any, Dict, List

from speace_core.dna.parser import load_genome
from speace_core.orchestrator import CellularBrainOrchestrator
from speace_core.cellular_brain.base.digital_signal import DigitalSignal


def run_speace_brain(
    ticks: int = 50,
    enable_cor: bool = True,
    enable_simulator_backend: bool = True,
    enable_functional_activation: bool = True,
) -> Dict[str, Any]:
    """Build and run the SPEACE brain for a number of ticks."""
    genome_path = Path(r"C:\cellular_speace\speace_core\dna\genome\default_genome.yaml")
    genome = load_genome(genome_path)

    # Build the orchestrator (MVP circuit + all standard subsystems)
    orch = CellularBrainOrchestrator.build_mvp(
        genome,
        ilf_enabled=True,
        energy_field_enabled=True,
        homeostatic_drive_enabled=True,
        criticality_monitor_enabled=True,
        systemic_harmony_enabled=True,
    )

    # Enable new mechanisms
    if enable_cor:
        orch.cor_enabled = True
        orch.cor_phi_threshold_factor = 0.55
        orch.cor_min_latent_states = 2
        orch.cor_max_hypotheses = 4

    if enable_simulator_backend:
        orch.simulator_backend_enabled = True
        orch.simulator_backend_name = "native"
        orch.simulator_backend_interval_ticks = 10

    # Re-initialize so the new flags take effect
    orch.model_post_init(None)

    # Seed latent superpositions in a subset of hidden neurons
    for idx, n in enumerate(orch.circuit.hidden_neurons[:5]):
        if enable_functional_activation:
            n.functional_activation_gate.rules = [
                r.model_copy() for r in genome.functional_activation.rules
            ]
        n.update_latent_states({
            "explore": 0.3,
            "exploit": 0.7,
        })
        n.cor_pressure = 0.2

    history: List[Dict[str, Any]] = []
    t0 = time.perf_counter()

    async def _loop() -> None:
        for tick in range(ticks):
            # Inject a simple rotating sensory pattern
            pattern = [0.0] * 10
            pattern[tick % 10] = 0.8
            orch.inject(pattern)

            # Send one semantic signal to trigger lazy activation
            target_id = orch.circuit.hidden_neurons[5].cell_id
            sig = DigitalSignal(
                source="launcher",
                target=target_id,
                strength=0.6,
                meaning="word",
            )
            target = orch.circuit._find_neuron(target_id)
            if target is not None:
                await target.receive(sig)

            await orch._tick()

            m = orch.latest_metrics
            history.append({
                "tick": orch.current_tick,
                "coherence_phi": getattr(m, "coherence_phi", None),
                "mean_energy": getattr(m, "mean_energy", None),
                "active_neurons": getattr(m, "active_neurons", None),
                "cor_collapsed": (
                    orch._last_cor_result.collapsed
                    if orch._last_cor_result else False
                ),
            })

    asyncio.run(_loop())
    elapsed = time.perf_counter() - t0

    final = history[-1] if history else {}
    return {
        "ticks_executed": ticks,
        "elapsed_seconds": elapsed,
        "ticks_per_second": ticks / elapsed if elapsed > 0 else 0.0,
        "final_coherence_phi": final.get("coherence_phi"),
        "final_mean_energy": final.get("mean_energy"),
        "final_active_neurons": final.get("active_neurons"),
        "any_cor_collapse": any(h.get("cor_collapsed") for h in history),
        "simulator_backend_log_size": len(orch._simulator_backend_log),
        "history_sample": history[:5],
    }


if __name__ == "__main__":
    report = run_speace_brain(ticks=30)
    print("SPEACE brain run report:")
    for key, value in report.items():
        print(f"  {key}: {value}")
