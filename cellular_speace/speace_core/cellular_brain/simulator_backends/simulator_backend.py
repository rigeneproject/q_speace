"""SimulatorBackend — abstract base class for SPEACE backends.

A backend takes a description of a small neural population
(Population + Projection) and simulates it for `run(dt)` steps,
returning spike trains and continuous state where appropriate.

Backends:
  - NativeBackend: in-process, no external deps (always available).
  - Brian2Backend: optional, lazy import of brian2.
  - NESTBackend: optional, lazy import of nest.
  - NEURONBackend: optional, lazy import of NEURON (single neurons).

The design goal is *strategy compatibility* with PyNN: implement just
enough of the surface area to allow a future swap, without making any
non-native backend a hard dependency.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class BackendKind(str, Enum):
    NATIVE = "native"
    BRIAN2 = "brian2"
    NEST = "nest"
    NEURON = "neuron"


@dataclass
class BackendCapabilities:
    """What a given backend can and cannot do."""
    max_neurons: int
    supports_continuous_state: bool
    supports_synapse_plasticity: bool
    supports_single_neuron_morphology: bool
    requires_gil: bool = True
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class SimulationResult:
    """Result of a simulation run."""
    spikes: Dict[str, List[float]] = field(default_factory=dict)
    # spikes[neuron_id] = list of spike times in ms
    state: Dict[str, List[float]] = field(default_factory=dict)
    # state[neuron_id] = list of continuous state samples
    runtime_ms: float = 0.0


class SimulatorBackend(ABC):
    """Abstract base class for SPEACE simulator backends."""

    kind: BackendKind = BackendKind.NATIVE

    @abstractmethod
    def capabilities(self) -> BackendCapabilities:
        """What this backend can do."""

    @abstractmethod
    def setup(self, populations: List[Any], projections: List[Any]) -> None:
        """Prepare internal state from a list of Populations and Projections."""

    @abstractmethod
    def run(self, duration_ms: float, dt_ms: float = 0.1) -> SimulationResult:
        """Run a simulation for the given duration; return the result."""

    @abstractmethod
    def reset(self) -> None:
        """Reset internal state without re-setup."""

    def is_available(self) -> bool:
        """True if this backend can be used in the current environment."""
        return True

    def get_neurons_state(self, neuron_ids: List[str]) -> Dict[str, float]:
        """Optional hook for backends that can introspect state."""
        return {nid: 0.0 for nid in neuron_ids}

    def set_neurons_input(
        self,
        neuron_id_to_current: Dict[str, float],
    ) -> None:
        """Optional hook for backends that can inject current directly."""
        return None
