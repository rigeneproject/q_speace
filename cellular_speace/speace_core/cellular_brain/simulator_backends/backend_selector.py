"""BackendSelector — recommend a backend given a workload description."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from speace_core.cellular_brain.simulator_backends.optional_imports import (
    available_backends,
    is_available,
)


class BackendChoice(str, Enum):
    NATIVE = "native"
    BRIAN2 = "brian2"
    NEST = "nest"
    NEURON = "neuron"


@dataclass
class WorkloadSpec:
    """Description of the kind of simulation requested."""
    neuron_count: int = 100
    duration_ms: float = 100.0
    needs_morphology: bool = False
    needs_stdp: bool = False
    prefers_python: bool = True
    allow_external_deps: bool = True


def recommend_backend(workload: WorkloadSpec) -> BackendChoice:
    """Pick the most appropriate backend for a given workload.

    Strategy (per user spec):
      - Default: native (always works, zero deps).
      - Use Brian2 for moderate-scale when available.
      - Use NEST for very large networks when available.
      - Use NEURON for detailed morphology.
    """
    avail = available_backends()
    if workload.needs_morphology and avail.get("neuron"):
        return BackendChoice.NEURON
    if workload.neuron_count > 50_000 and avail.get("nest"):
        return BackendChoice.NEST
    if workload.allow_external_deps and avail.get("brian2") and not workload.prefers_python:
        return BackendChoice.BRIAN2
    return BackendChoice.NATIVE


class BackendSelector:
    """Memoizing selector that caches `available_backends()` and exposes `.build()`."""

    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}

    def recommend(self, neuron_count: int = 100, **kwargs: Any) -> BackendChoice:
        wl = WorkloadSpec(neuron_count=neuron_count, **kwargs)
        return recommend_backend(wl)

    def build(self, choice) -> Any:
        """Instantiate a backend by name. Cached for re-use.

        Accepts a `BackendChoice` enum or a string equivalent.
        """
        if isinstance(choice, str):
            try:
                choice = BackendChoice(choice)
            except ValueError as exc:
                raise ValueError(f"unknown backend choice: {choice!r}") from exc
        if not isinstance(choice, BackendChoice):
            raise TypeError(
                f"choice must be a BackendChoice or str, got {type(choice).__name__}"
            )
        key = choice.value
        if key in self._cache:
            cached = self._cache[key]
            if getattr(cached, "is_available", lambda: False)():
                return cached
            # Cached backend is not actually available; fall through.
        backend: Any
        if choice == BackendChoice.NATIVE:
            from speace_core.cellular_brain.simulator_backends.native_backend import (
                NativeBackend,
            )
            backend = NativeBackend()
        elif choice == BackendChoice.BRIAN2:
            from speace_core.cellular_brain.simulator_backends.brian2_backend import (
                Brian2Backend,
            )
            backend = Brian2Backend()
        elif choice == BackendChoice.NEST:
            from speace_core.cellular_brain.simulator_backends.nest_backend import (
                NESTBackend,
            )
            backend = NESTBackend()
        elif choice == BackendChoice.NEURON:
            from speace_core.cellular_brain.simulator_backends.neuron_backend import (
                NEURONBackend,
            )
            backend = NEURONBackend()
        else:
            raise ValueError(f"unknown backend: {choice}")
        if not backend.is_available():
            if choice == BackendChoice.NATIVE:
                raise RuntimeError("native backend must always be available")
            # Fallback to native backend when the requested one is missing.
            from speace_core.cellular_brain.simulator_backends.native_backend import (
                NativeBackend,
            )
            backend = NativeBackend()
            self._cache[key] = backend
            return backend
        self._cache[key] = backend
        return backend
