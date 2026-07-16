"""Lazy materialization layer for SPEACE.

The brain has billions of neurons and synapses in principle, but
typically only a small functional subset is active at any given
time. The lazy layer materializes a neuron (or synapse) only when
a signal requires its function, and unmaterializes it when no
longer active.

Public API:
  - ParametricCatalog: compact key -> function spec
  - FunctionSpec: a single (functional role, parameters) record
  - SignalKey: extraction of a function key from a DigitalSignal
  - LazyMaterializationManager: orchestrates on-demand creation
  - SignalRouter: routes signals to materialized neurons
"""

from speace_core.cellular_brain.lazy.parametric_catalog import (
    ParametricCatalog,
    FunctionSpec,
    default_catalog,
)
from speace_core.cellular_brain.lazy.signal_router import (
    SignalKey,
    SignalRouter,
)
from speace_core.cellular_brain.lazy.lazy_materialization_manager import (
    LazyMaterializationManager,
    MaterializedNeuron,
    MaterializationStats,
)

__all__ = [
    "ParametricCatalog",
    "FunctionSpec",
    "default_catalog",
    "SignalKey",
    "SignalRouter",
    "LazyMaterializationManager",
    "MaterializedNeuron",
    "MaterializationStats",
]
