"""Backend selector for Q-SPEACE (mirrors cellular_speace BackendSelector)."""

from __future__ import annotations

import os
from typing import Any

from ...genome.quantum_genes import REAL_BACKENDS, QuantumGeneSet
from .base import NumpyBackend, QuantumBackend
from .qiskit_backend import QiskitBackend
from .quantum_inspire_backend import QuantumInspireBackend

_REGISTRY: dict[str, type[QuantumBackend]] = {
    "numpy": NumpyBackend,
    "quantum-inspire": QuantumInspireBackend,
    "qiskit": QiskitBackend,
    "qiskit-aer": QiskitBackend,
}


def validate_real_backend_gate(
    genome: QuantumGeneSet | None,
    *,
    energy_gate_passed: bool = False,
    sevo_passed: bool = False,
) -> None:
    """Enforce AGENTS.md §2 and T208 §3.5 before any real quantum backend runs.

    Requires a validated ``QuantumGeneSet`` with a non-ideal ``noise_model``
    and explicit ``energy_gate_passed`` and ``sevo_passed`` approvals.
    """
    if genome is None:
        raise ValueError("real quantum backend requires a configured QuantumGeneSet")
    genome.validate()
    if genome.noise_model == "ideal":
        raise ValueError(
            "real quantum backend requires a non-ideal QuantumGeneSet.noise_model "
            "('surface-code' or 'depolarizing')"
        )
    if not energy_gate_passed:
        raise ValueError("real quantum backend blocked: energy gate not satisfied")
    if not sevo_passed:
        raise ValueError("real quantum backend blocked: Sevo gate not satisfied")


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


def build(
    backend_name: str = "numpy",
    *,
    genome: QuantumGeneSet | None = None,
    energy_gate_passed: bool = False,
    sevo_passed: bool = False,
    **kwargs: Any,
) -> QuantumBackend:
    """Return a backend by name, falling back to numpy if unavailable.

    When a real quantum backend (``qiskit``, ``qiskit-aer``, ``quantum-inspire``)
    is installed and configured, AGENTS.md §2 requires a validated
    ``QuantumGeneSet`` with a non-ideal ``noise_model`` plus explicit energy
    and Sevo gate approval before instantiating it.
    """
    name = backend_name or "numpy"
    if genome is not None:
        genome.validate()
    if name == "quantum-inspire" and not _quantum_inspire_configured():
        return NumpyBackend(**kwargs)
    if name in ("qiskit", "qiskit-aer") and not _qiskit_configured():
        return NumpyBackend(**kwargs)
    if name in REAL_BACKENDS:
        validate_real_backend_gate(
            genome,
            energy_gate_passed=energy_gate_passed,
            sevo_passed=sevo_passed,
        )
    cls = _REGISTRY.get(name, NumpyBackend)
    return cls(**kwargs)


def available() -> list[str]:
    return list(_REGISTRY.keys())
