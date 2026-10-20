"""Backend selector for Q-SPEACE (mirrors cellular_speace BackendSelector)."""

from __future__ import annotations

import os
from typing import Any

from .base import NumpyBackend, QuantumBackend
from .qiskit_backend import QiskitBackend
from .quantum_inspire_backend import QuantumInspireBackend

_REGISTRY: dict[str, type[QuantumBackend]] = {
    "numpy": NumpyBackend,
    "quantum-inspire": QuantumInspireBackend,
    "qiskit": QiskitBackend,
}


def _quantum_inspire_configured() -> bool:
    if not os.environ.get("QI_TOKEN"):
        return False
    try:
        import quantum_inspire.api  # type: ignore[import-not-found]  # noqa: F401
        import quantum_inspire.credentials  # type: ignore[import-not-found]  # noqa: F401

        return True
    except ImportError:
        return False


def _qiskit_configured() -> bool:
    try:
        import qiskit  # type: ignore[import-not-found]  # noqa: F401
        import qiskit_aer  # type: ignore[import-not-found]  # noqa: F401

        return True
    except ImportError:
        return False


def build(backend_name: str = "numpy", **kwargs: Any) -> QuantumBackend:
    """Return a backend by name, falling back to numpy if unavailable."""
    name = backend_name or "numpy"
    if name == "quantum-inspire" and not _quantum_inspire_configured():
        return NumpyBackend(**kwargs)
    if name == "qiskit" and not _qiskit_configured():
        return NumpyBackend(**kwargs)
    cls = _REGISTRY.get(name, NumpyBackend)
    return cls(**kwargs)


def available() -> list[str]:
    return list(_REGISTRY.keys())
