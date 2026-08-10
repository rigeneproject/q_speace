"""T204 runtime wiring tests for opt-in pseudo-spiking cost."""

from __future__ import annotations

import numpy as np
import pytest

from q_speace.orchestrator import QuantumOrchestrator
from q_speace.quantum import QuantumNeuralBridge


def test_spikes_are_off_by_default() -> None:
    reports = QuantumOrchestrator(neurons=["a", "b"], seed=3).run(3)
    assert all(r.num_spikes == 0 and r.sparsity == 1.0 for r in reports)


def test_spikes_add_runtime_energy_cost() -> None:
    base = QuantumOrchestrator(neurons=["a", "b", "c"], seed=3).run(1)[0]
    enabled = QuantumOrchestrator(neurons=["a", "b", "c"], seed=3, enable_spikes=True).run(1)[0]
    assert enabled.num_spikes > 0
    assert enabled.mean_energy_w > base.mean_energy_w


def test_bridge_activity_is_normalised_and_validated() -> None:
    bridge = QuantumNeuralBridge()
    bridge.register("a")
    bridge.register("b")
    bridge.set_activity(np.array([1.0, 3.0]))
    assert bridge.activity.sum() == pytest.approx(1.0)
    with pytest.raises(ValueError):
        bridge.set_activity(np.array([1.0]))
