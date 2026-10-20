"""Foundational primitives for the q_speace_economy (T6.2).

This module provides the three core dataclasses used throughout the rest
of the package:

- :class:`J_c` — the cognitive 5-tuple ``(J, ΔS, ΔI_c, R_b, ΔC, confidence)``
  plus a ``from_telemetry`` factory. The components are independently
  measurable physical quantities; ``confidence`` reflects telemetry
  completeness, not subjective belief.
- :class:`V` — the multi-domain value vector (4 components by default,
  5 with an optional ``coherence_phi``). The ``VTEC`` controller reads
  this vector to allocate exergy.
- :class:`CME` — the 12-dimensional Capital-Multi-vector Extension,
  bounded in [0,1] per dimension. Tracks the non-fungible capital
  registry of an agent or ecosystem.

All three are pure ``numpy`` / standard library — no scipy, no torch.
They survive round-trip with the JSON Schemas in
``q_speace/economy/schemas/`` (validated by
``tests/test_economy_schemas.py``).

BCEL: the 5-tuple ``J_c`` is *not* a joule-equivalent of consciousness.
The components map cleanly to physical observables; the analogy
"metabolic intentionality" is **accidental**: the math survives, the
biological analogy does not.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# J_c — cognitive 5-tuple
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class J_c:
    """Cognitive 5-tuple ``(J, ΔS, ΔI_c, R_b, ΔC)`` with measurement confidence.

    Attributes
    ----------
    J : float
        Total useful exergy produced or conserved, in joules (>= 0).
    delta_S : float
        Entropy produced (>= 0) or destroyed (<= 0), in J/K.
    delta_I_c : float
        Change in catalytic information content (structural complexity), in
        bits (>= 0).
    R_b : float
        Regenerative budget remaining after the action, in [0, 1].
    delta_C : float
        Net change in catalytic capacity, in [-1, 1].
    confidence : float
        Telemetry completeness in [0, 1]. Reflects how much of the tuple
        was actually measured vs. imputed; **not** subjective belief.
    metadata : dict[str, Any]
        Free-form annotations (agent id, source, timestamp, units).
    """

    J: float
    delta_S: float
    delta_I_c: float
    R_b: float
    delta_C: float
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.J < 0.0:
            raise ValueError(f"J must be >= 0 (got {self.J})")
        if self.delta_S > 0.0:
            raise ValueError(f"delta_S must be <= 0 for a net-bounded action (got {self.delta_S})")
        if self.delta_I_c < 0.0:
            raise ValueError(f"delta_I_c must be >= 0 (got {self.delta_I_c})")
        if not 0.0 <= self.R_b <= 1.0:
            raise ValueError(f"R_b must be in [0, 1] (got {self.R_b})")
        if not -1.0 <= self.delta_C <= 1.0:
            raise ValueError(f"delta_C must be in [-1, 1] (got {self.delta_C})")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1] (got {self.confidence})")

    @classmethod
    def from_telemetry(
        cls,
        J: float,
        delta_S: float,
        delta_I_c: float,
        R_b: float,
        delta_C: float,
        measured_components: int,
        total_components: int = 5,
        metadata: dict[str, Any] | None = None,
    ) -> J_c:
        """Build a :class:`J_c` from raw telemetry; confidence is computed.

        ``confidence = measured_components / total_components`` clipped to
        [0, 1]. The factory exists so callers do not have to hand-roll the
        confidence value.
        """
        if total_components <= 0:
            raise ValueError("total_components must be > 0")
        if measured_components < 0:
            raise ValueError("measured_components must be >= 0")
        confidence = float(np.clip(measured_components / total_components, 0.0, 1.0))
        return cls(
            J=J,
            delta_S=delta_S,
            delta_I_c=delta_I_c,
            R_b=R_b,
            delta_C=delta_C,
            confidence=confidence,
            metadata=dict(metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable dict matching ``j_c.schema.json``."""
        d = asdict(self)
        # Schema names use ``delta_S`` (snake_case matches).
        return d


# ---------------------------------------------------------------------------
# V — multi-domain value vector
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class V:
    """Multi-domain value vector ``(E_x, S_gen, I_c, R_b[, coherence_phi])``.

    Attributes
    ----------
    E_x : float
        Exergy extracted per unit time, in watts (>= 0).
    S_gen : float
        Entropy generation per unit time, in W/K (>= 0).
    I_c : float
        Catalytic information flux, in bits/s (>= 0).
    R_b : float
        Regenerative budget fraction, in [0, 1].
    coherence_phi : float, optional
        Global coherence phase, in [0, 1]. When present, the 5-component
        form is used by the VTEC controller to weight the objective.
    """

    E_x: float
    S_gen: float
    I_c: float
    R_b: float
    coherence_phi: float | None = None

    def __post_init__(self) -> None:
        if self.E_x < 0.0:
            raise ValueError(f"E_x must be >= 0 (got {self.E_x})")
        if self.S_gen < 0.0:
            raise ValueError(f"S_gen must be >= 0 (got {self.S_gen})")
        if self.I_c < 0.0:
            raise ValueError(f"I_c must be >= 0 (got {self.I_c})")
        if not 0.0 <= self.R_b <= 1.0:
            raise ValueError(f"R_b must be in [0, 1] (got {self.R_b})")
        if self.coherence_phi is not None and not 0.0 <= self.coherence_phi <= 1.0:
            raise ValueError(f"coherence_phi must be in [0, 1] (got {self.coherence_phi})")

    @property
    def n_components(self) -> int:
        """Number of components in the vector (4 or 5)."""
        return 5 if self.coherence_phi is not None else 4

    def as_array(self) -> np.ndarray:
        """Return the vector as a 1-D numpy array (4 or 5 components)."""
        if self.coherence_phi is None:
            return np.array([self.E_x, self.S_gen, self.I_c, self.R_b], dtype=np.float64)
        return np.array(
            [self.E_x, self.S_gen, self.I_c, self.R_b, self.coherence_phi],
            dtype=np.float64,
        )

    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable dict matching ``v.schema.json``."""
        d: dict[str, Any] = {
            "E_x": self.E_x,
            "S_gen": self.S_gen,
            "I_c": self.I_c,
            "R_b": self.R_b,
        }
        if self.coherence_phi is not None:
            d["coherence_phi"] = self.coherence_phi
        return d


# ---------------------------------------------------------------------------
# CME — 12-dimensional Capital-Multi-vector Extension
# ---------------------------------------------------------------------------


_CME_FIELDS: tuple[str, ...] = (
    "energy",
    "matter",
    "information",
    "time",
    "ecology",
    "resilience",
    "wellbeing",
    "innovation",
    "reversibility",
    "distribution",
    "coherence",
    "regeneration",
)


@dataclass(frozen=True)
class CME:
    """12-dimensional non-fungible capital registry.

    Each component is in [0, 1] and represents a dimensionless normalised
    stock of one capital kind. ``CME`` is the SPEACE-aligned replacement for
    scalar monetary bookkeeping: capital is never fungible across kinds.

    The 12 fields are exactly the keys in ``cme.schema.json``.
    """

    energy: float
    matter: float
    information: float
    time: float
    ecology: float
    resilience: float
    wellbeing: float
    innovation: float
    reversibility: float
    distribution: float
    coherence: float
    regeneration: float

    def __post_init__(self) -> None:
        for f in fields(self):
            v = getattr(self, f.name)
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"CME.{f.name} must be in [0, 1] (got {v})")

    def as_array(self) -> np.ndarray:
        """Return the 12 components as a numpy vector in canonical order."""
        return np.array([getattr(self, name) for name in _CME_FIELDS], dtype=np.float64)

    def to_dict(self) -> dict[str, float]:
        """JSON-serialisable dict matching ``cme.schema.json``."""
        return {name: getattr(self, name) for name in _CME_FIELDS}

    def weak_axes(self, threshold: float = 0.2) -> list[str]:
        """Return the names of axes with stock below ``threshold``."""
        return [name for name in _CME_FIELDS if getattr(self, name) < threshold]
