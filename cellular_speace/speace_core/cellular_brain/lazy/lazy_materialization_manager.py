"""LazyMaterializationManager — on-demand creation of neurons/synapses.

The manager is the *brain's lazy layer*:
  - receives a DigitalSignal and a target region
  - looks up the matching FunctionSpec in the catalog
  - materializes a DigitalNeuron *only if* no neuron for that key
    is already active
  - records synapses between materialized neurons

The full brain has potentially billions of neurons; the lazy layer
keeps in memory only those functions that are actually firing.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from speace_core.cellular_brain.base.digital_signal import DigitalSignal
from speace_core.cellular_brain.cells.digital_neuron import DigitalNeuron
from speace_core.cellular_brain.cells.digital_synapse import DigitalSynapse
from speace_core.cellular_brain.lazy.parametric_catalog import (
    FunctionSpec,
    ParametricCatalog,
    default_catalog,
)
from speace_core.cellular_brain.lazy.signal_router import (
    SignalKey,
    SignalRouter,
)


@dataclass
class MaterializedNeuron:
    """A neuron that has been materialized from a FunctionSpec."""
    neuron: DigitalNeuron
    spec: FunctionSpec
    key: str
    last_used_ts: float = field(default_factory=time.time)
    use_count: int = 0

    def touch(self) -> None:
        self.last_used_ts = time.time()
        self.use_count += 1


@dataclass
class MaterializationStats:
    """Operational statistics for the lazy manager."""
    demands: int = 0
    materializations: int = 0
    hits: int = 0  # demands that found an existing neuron
    unmaterializations: int = 0
    active_neurons: int = 0
    unique_functions: int = 0


class LazyMaterializationManager:
    """On-demand manager for SPEACE neurons."""

    def __init__(
        self,
        catalog: Optional[ParametricCatalog] = None,
        router: Optional[SignalRouter] = None,
    ) -> None:
        self._catalog = catalog or default_catalog()
        self._router = router or SignalRouter()
        self._by_key: Dict[str, MaterializedNeuron] = {}
        self._by_id: Dict[str, MaterializedNeuron] = {}
        self._stats = MaterializationStats()

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    @property
    def catalog(self) -> ParametricCatalog:
        return self._catalog

    def set_default_region(self, region: str, function: str = "processing") -> None:
        self._router.set_default(region, function)

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def demand(
        self,
        signal: DigitalSignal,
        target_region: Optional[str] = None,
    ) -> MaterializedNeuron:
        """Return a materialized neuron for the signal; create it on demand."""
        self._stats.demands += 1
        key = self._router.key_from_signal(signal, target_region)
        existing = self._by_key.get(key.key)
        if existing is not None:
            existing.touch()
            self._stats.hits += 1
            return existing
        spec = self._catalog.find_one(key.region, key.function)
        if spec is None:
            # fall back to a generic spec
            spec = self._catalog.find_one("generic", "processing")
            if spec is None:
                raise RuntimeError("catalog has no entries")
        mn = self._materialize(spec, key)
        return mn

    def demand_specific(
        self,
        region: str,
        function: str,
    ) -> MaterializedNeuron:
        """Materialize a specific function (e.g. for warm-up)."""
        key = SignalKey(region=region, function=function, key=f"{region}.{function}")
        existing = self._by_key.get(key.key)
        if existing is not None:
            existing.touch()
            return existing
        spec = self._catalog.find_one(region, function)
        if spec is None:
            spec = self._catalog.find_one("generic", "processing")
        return self._materialize(spec, key)

    def connect(
        self,
        source: MaterializedNeuron,
        target: MaterializedNeuron,
        weight: Optional[float] = None,
        delay_ms: Optional[float] = None,
    ) -> DigitalSynapse:
        """Create a DigitalSynapse between two materialized neurons."""
        if target.neuron.cell_id not in source.neuron.targets:
            source.neuron.targets.append(target.neuron.cell_id)
        w = weight if weight is not None else source.spec.weight_default
        d = delay_ms if delay_ms is not None else source.spec.delay_ms
        syn = DigitalSynapse(
            cell_id=f"syn_{source.neuron.cell_id}_{target.neuron.cell_id}",
            role="synapse",
            source=source.neuron.cell_id,
            target=target.neuron.cell_id,
            weight=w,
        )
        return syn

    def list_active(self) -> List[MaterializedNeuron]:
        return list(self._by_key.values())

    def list_active_neurons(self) -> List[DigitalNeuron]:
        return [mn.neuron for mn in self._by_key.values()]

    def get_by_id(self, cell_id: str) -> Optional[MaterializedNeuron]:
        return self._by_id.get(cell_id)

    def stats(self) -> MaterializationStats:
        s = self._stats
        s.active_neurons = len(self._by_key)
        s.unique_functions = len({mn.spec.key for mn in self._by_key.values()})
        return s

    def unmaterialize_idle(
        self,
        idle_threshold_seconds: float = 60.0,
    ) -> int:
        """Unmaterialize neurons not used in the last N seconds."""
        now = time.time()
        to_remove: List[str] = []
        for key, mn in self._by_key.items():
            if now - mn.last_used_ts > idle_threshold_seconds:
                to_remove.append(key)
        for key in to_remove:
            mn = self._by_key.pop(key)
            self._by_id.pop(mn.neuron.cell_id, None)
            self._stats.unmaterializations += 1
        return len(to_remove)

    def reset(self) -> None:
        self._by_key.clear()
        self._by_id.clear()
        self._stats = MaterializationStats()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _materialize(
        self,
        spec: FunctionSpec,
        key: SignalKey,
    ) -> MaterializedNeuron:
        cell_id = f"lazy_{key.region}_{key.function}_{uuid.uuid4().hex[:8]}"
        neuron = DigitalNeuron(
            cell_id=cell_id,
            role=spec.cell_type,
            threshold=spec.threshold,
            plasticity_rate=spec.plasticity_rate,
            region=key.region,
        )
        # Tag the neuron with the lazy function key as a layer
        neuron.layer = key.key
        neuron.cell_type = spec.cell_type
        mn = MaterializedNeuron(neuron=neuron, spec=spec, key=key.key)
        self._by_key[key.key] = mn
        self._by_id[cell_id] = mn
        self._stats.materializations += 1
        return mn
