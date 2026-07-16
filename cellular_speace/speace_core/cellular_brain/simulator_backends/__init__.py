"""Simulator backends for SPEACE — pluggable backends for neuron/synapse simulation.

This package implements a PyNN-like abstraction over different
simulators, with a native (in-process) backend as the always-available
default. Optional backends (Brian2, NEST, NEURON) are loaded lazily so
they are not required dependencies.

Public API:
  - SimulatorBackend (ABC)
  - NativeBackend (default, no external deps)
  - Brian2Backend / NESTBackend / NEURONBackend (optional, import-lazy)
  - BackendSelector (automatic backend recommendation)
  - Population / Projection (PyNN-like adapters)
"""

from speace_core.cellular_brain.simulator_backends.simulator_backend import (
    SimulatorBackend,
    BackendCapabilities,
)
from speace_core.cellular_brain.simulator_backends.optional_imports import (
    optional_import,
    is_available,
    available_backends,
)
from speace_core.cellular_brain.simulator_backends.native_backend import (
    NativeBackend,
)
from speace_core.cellular_brain.simulator_backends.population import (
    Population,
    Projection,
    NeuronSpec,
    ConnectionSpec,
)
from speace_core.cellular_brain.simulator_backends.backend_selector import (
    BackendSelector,
    BackendChoice,
    WorkloadSpec,
    recommend_backend,
)

__all__ = [
    "SimulatorBackend",
    "BackendCapabilities",
    "NativeBackend",
    "Population",
    "Projection",
    "NeuronSpec",
    "ConnectionSpec",
    "BackendSelector",
    "BackendChoice",
    "WorkloadSpec",
    "recommend_backend",
    "optional_import",
    "is_available",
    "available_backends",
]
