"""Tests for simulator backend integration in the orchestrator."""
import asyncio

import pytest

from speace_core.orchestrator import CellularBrainOrchestrator
from speace_core.dna.models import SharedGenome


def test_orchestrator_initializes_native_backend():
    genome = SharedGenome()
    orch = CellularBrainOrchestrator.build_mvp(genome=genome)
    orch.simulator_backend_enabled = True
    orch.simulator_backend_name = "native"
    orch.simulator_backend_interval_ticks = 1
    orch.model_post_init(None)
    assert orch._simulator_backend is not None
    assert orch._simulator_backend_selector is not None


def test_orchestrator_runs_native_backend_step():
    genome = SharedGenome()
    orch = CellularBrainOrchestrator.build_mvp(genome=genome)
    orch.simulator_backend_enabled = True
    orch.simulator_backend_name = "native"
    orch.simulator_backend_interval_ticks = 1
    orch.model_post_init(None)

    # Activate a few input neurons
    for n in orch.circuit.input_neurons[:3]:
        n.activation = 0.9

    asyncio.run(orch._tick())
    assert orch._simulator_backend_last_tick == orch.current_tick
    assert len(orch._simulator_backend_log) >= 1
    log = orch._simulator_backend_log[-1]
    assert "backend" in log
    assert log["backend"] == "native"


def test_backend_choice_auto_selects_native_when_no_deps():
    genome = SharedGenome()
    orch = CellularBrainOrchestrator.build_mvp(genome=genome)
    orch.simulator_backend_enabled = True
    orch.simulator_backend_name = "auto"
    orch.model_post_init(None)
    # If no external simulators are installed, auto should fall back to native.
    from speace_core.cellular_brain.simulator_backends import NativeBackend
    assert isinstance(orch._simulator_backend, NativeBackend)
