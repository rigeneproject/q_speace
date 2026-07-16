import numpy as np
import pytest

from speace_core.cellular_brain.memory.morphology_events import MorphologyEventType
from speace_core.dna.models import SharedGenome
from speace_core.orchestrator import CellularBrainOrchestrator


@pytest.fixture
def genome():
    return SharedGenome()


def build_enabled_orchestrator(genome):
    """Return an orchestrator with salience-related subsystems enabled."""
    orch = CellularBrainOrchestrator.build_mvp(genome=genome)
    orch.salience_network_enabled = True
    orch.noradrenergic_modulation_enabled = True
    orch.cholinergic_modulation_enabled = True
    orch.dmn_switching_enabled = True
    orch.thalamic_relay_enabled = True
    orch.functional_resonance_enabled = True
    orch.predictive_coding_enabled = True
    orch.global_workspace_enabled = True
    orch.model_post_init(None)
    return orch


@pytest.mark.asyncio
async def test_salience_network_initializes_when_enabled(genome):
    orch = CellularBrainOrchestrator.build_mvp(genome=genome)
    orch.salience_network_enabled = True
    orch.model_post_init(None)
    assert orch._salience_network is not None
    assert isinstance(orch._last_global_salience, float)


@pytest.mark.asyncio
async def test_tick_with_salience_network_runs(genome):
    orch = build_enabled_orchestrator(genome)
    await orch._tick()
    assert orch._salience_network is not None
    assert 0.0 <= orch._last_global_salience <= 1.0


@pytest.mark.asyncio
async def test_salience_drives_dmn_switching(genome):
    orch = build_enabled_orchestrator(genome)
    # Inject a non-trivial prediction error by updating the sensory layer
    if orch._predictive_coding is not None:
        sensory_dim = orch._predictive_coding.layers["sensory"]["dim"]
        orch._predictive_coding.update(
            "sensory",
            np.full(sensory_dim, 1.0),
        )
    await orch._tick()
    assert orch._dmn_switching is not None
    assert orch._dmn_switching.state.salience_signal == orch._last_global_salience


@pytest.mark.asyncio
async def test_salience_modulates_thalamic_attention(genome):
    orch = build_enabled_orchestrator(genome)
    # Force moderate NE and a high salience signal so that the thalamus
    # moves out of BURST mode.
    if orch._noradrenergic_modulator is not None:
        orch._noradrenergic_modulator.state.noradrenaline_level = 0.5
    if orch._predictive_coding is not None:
        sensory_dim = orch._predictive_coding.layers["sensory"]["dim"]
        orch._predictive_coding.update(
            "sensory",
            np.full(sensory_dim, 1.0),
        )
    await orch._tick()
    assert orch._thalamic_relay is not None
    # With salience, the effective attention focus should increase,
    # pushing the relay at least into tonic or gated mode.
    assert orch._thalamic_relay.state.mode.value != "burst"


@pytest.mark.asyncio
async def test_salience_broadcast_to_workspace(genome):
    orch = build_enabled_orchestrator(genome)
    if orch._predictive_coding is not None:
        sensory_dim = orch._predictive_coding.layers["sensory"]["dim"]
        orch._predictive_coding.update(
            "sensory",
            np.full(sensory_dim, 1.0),
        )
    await orch._tick()
    assert orch._global_workspace is not None
    # The workspace step consumes the queue, but the module should still
    # be recorded in the activity history used by attention routing.
    assert "salience_network" in orch._global_workspace._module_activity_history


@pytest.mark.asyncio
async def test_salience_events_persisted(genome):
    orch = build_enabled_orchestrator(genome)
    if orch._predictive_coding is not None:
        sensory_dim = orch._predictive_coding.layers["sensory"]["dim"]
        orch._predictive_coding.update(
            "sensory",
            np.full(sensory_dim, 2.0),
        )
    # Max out NE arousal and activate circuit neurons to push all
    # salience channels above the burst threshold.
    if orch._noradrenergic_modulator is not None:
        orch._noradrenergic_modulator.state.noradrenaline_level = 1.0
    for n in (
        orch.circuit.input_neurons
        + orch.circuit.hidden_neurons
        + orch.circuit.output_neurons
    ):
        n.activation = 1.0
    await orch._tick()
    event_types = [e.event_type for e in orch._memory.events]
    assert MorphologyEventType.SALIENCE_BURST in event_types


@pytest.mark.asyncio
async def test_salience_without_workspace_does_not_crash(genome):
    orch = CellularBrainOrchestrator.build_mvp(genome=genome)
    orch.salience_network_enabled = True
    orch.noradrenergic_modulation_enabled = True
    orch.dmn_switching_enabled = True
    orch.model_post_init(None)
    await orch._tick()
    assert orch._salience_network is not None
    assert 0.0 <= orch._last_global_salience <= 1.0


@pytest.mark.asyncio
async def test_salience_context_propagated(genome):
    orch = build_enabled_orchestrator(genome)
    await orch._tick()
    ctx = orch._build_subsystem_context()
    assert ctx.tick_state.last_global_salience == orch._last_global_salience
