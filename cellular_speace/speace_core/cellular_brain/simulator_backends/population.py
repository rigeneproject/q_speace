"""Population / Projection — PyNN-style adapters for SPEACE backends.

These are simple in-process containers. Backends consume them
differently: NativeBackend drives them directly; Brian2Backend would
materialize Brian2.NeuronGroup / Synapses.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class NeuronSpec:
    """Specification of a single neuron for a backend."""
    neuron_id: str
    cell_type: str = "generic_neuron"
    threshold: float = 0.5
    reset: float = 0.0
    resting: float = 0.0
    tau_ms: float = 10.0
    refractory_ms: float = 2.0
    initial_voltage: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Population:
    """A PyNN-like population of neurons.

    The population is *declarative* — it stores specs and lets backends
    materialize them as they see fit. It is also *iterable* for
    NativeBackend's convenience.
    """

    def __init__(
        self,
        label: str,
        neurons: Optional[List[NeuronSpec]] = None,
        cell_type: str = "generic_neuron",
        size: int = 0,
    ) -> None:
        self.label = label
        self.cell_type = cell_type
        if neurons is None:
            neurons = []
            for i in range(size):
                neurons.append(
                    NeuronSpec(
                        neuron_id=f"{label}_{i}",
                        cell_type=cell_type,
                    )
                )
        self.neurons: List[NeuronSpec] = neurons
        self._index: Dict[str, int] = {n.neuron_id: i for i, n in enumerate(neurons)}

    def add(self, spec: NeuronSpec) -> None:
        if spec.neuron_id in self._index:
            raise ValueError(f"neuron_id {spec.neuron_id} already in population")
        self.neurons.append(spec)
        self._index[spec.neuron_id] = len(self.neurons) - 1

    def get(self, neuron_id: str) -> NeuronSpec:
        return self.neurons[self._index[neuron_id]]

    def __len__(self) -> int:
        return len(self.neurons)

    def __iter__(self):
        return iter(self.neurons)

    def ids(self) -> List[str]:
        return [n.neuron_id for n in self.neurons]

    def describe(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "cell_type": self.cell_type,
            "size": len(self.neurons),
            "neuron_ids": self.ids(),
        }


@dataclass
class ConnectionSpec:
    """Specification of a single connection in a Projection."""
    source_id: str
    target_id: str
    weight: float = 0.5
    delay_ms: float = 1.0
    synapse_type: str = "static"
    metadata: Dict[str, Any] = field(default_factory=dict)


class Projection:
    """A PyNN-like projection connecting two populations (or subset of them)."""

    def __init__(
        self,
        source: Population,
        target: Population,
        label: str = "proj",
        synapse_type: str = "static",
    ) -> None:
        self.source = source
        self.target = target
        self.label = label
        self.synapse_type = synapse_type
        self.connections: List[ConnectionSpec] = []
        self._conns_by_target: Dict[str, List[int]] = {}

    def connect(
        self,
        source_id: str,
        target_id: str,
        weight: float = 0.5,
        delay_ms: float = 1.0,
        synapse_type: Optional[str] = None,
    ) -> ConnectionSpec:
        if source_id not in self.source._index:
            raise KeyError(f"source_id {source_id} not in source population")
        if target_id not in self.target._index:
            raise KeyError(f"target_id {target_id} not in target population")
        spec = ConnectionSpec(
            source_id=source_id,
            target_id=target_id,
            weight=weight,
            delay_ms=delay_ms,
            synapse_type=synapse_type or self.synapse_type,
        )
        self.connections.append(spec)
        self._conns_by_target.setdefault(target_id, []).append(len(self.connections) - 1)
        return spec

    def connect_all(
        self,
        weight: float = 0.5,
        delay_ms: float = 1.0,
        density: float = 1.0,
    ) -> int:
        """Connect every source to every target, with optional density."""
        import random
        n_added = 0
        for src in self.source.neurons:
            for tgt in self.target.neurons:
                if random.random() > density:
                    continue
                self.connect(
                    source_id=src.neuron_id,
                    target_id=tgt.neuron_id,
                    weight=weight,
                    delay_ms=delay_ms,
                )
                n_added += 1
        return n_added

    def incoming_to(self, target_id: str) -> List[ConnectionSpec]:
        idxs = self._conns_by_target.get(target_id, [])
        return [self.connections[i] for i in idxs]

    def __len__(self) -> int:
        return len(self.connections)
