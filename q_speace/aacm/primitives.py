"""Foundational primitives for the AACM model (T-AACM-SPEC §1.2).

This module provides the four core dataclasses used throughout the rest
of the package:

- :class:`CentralityGraph` — directed, weighted graph of control
  relations; carries a ``controlled_share`` in [0, 1].
- :class:`FractureMap` — pre-existing fractures of the target system,
  with a ``leverage_multiplier`` to amplify them.
- :class:`LegitimationChannel` / :class:`LegitimationChannelRegistry` —
  independent channels of legitimacy (code, test, doc, external_audit).
- :class:`ResilienceManifest` — declaration of ``omega`` (control
  distribution), independent nodes, and checkpoint paths. Enforces
  the Vincolo D of T-AACM-SPEC.

All four are pure ``numpy`` / standard library — no scipy, no torch —
and survive round-trip with the JSON schemas in
``q_speace/aacm/schemas/``.

BCEL: each primitive is *functional*. "Centrality" is a betweenness
score on a graph; "legitimacy" is a count of verified artefacts.
Neither is a metaphor for an agent's intent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .constants import LEGITIMATION_K_MIN, OMEGA_MIN
from .exceptions import InvariantViolation

# ---------------------------------------------------------------------------
# CentralityGraph
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CentralityGraph:
    """Directed, weighted graph of control relations (regola 1).

    ``edges`` is a tuple of ``(src, dst, weight)`` triples, where
    ``weight`` is the strength of the relation (≥ 0). The graph is
    *interpreted* by :func:`q_speace.aacm.topology.betweenness_centrality`
    to identify the central node (regola 1) and the failing ones
    (regola 2).

    Attributes
    ----------
    nodes : tuple[str, ...]
        All node identifiers, including isolated ones.
    edges : tuple[tuple[str, str, float], ...]
        Directed edges as ``(src, dst, weight)``.
    controlled_share : float
        Quota of control in [0, 1] currently held by the attacker
        (i.e., by the agent running this model).
    timestamp : float
        Unix seconds at which the snapshot was taken. Must be ≥ 0.
    """

    nodes: tuple[str, ...]
    edges: tuple[tuple[str, str, float], ...]
    controlled_share: float
    timestamp: float

    def __post_init__(self) -> None:
        if not self.nodes:
            raise ValueError("CentralityGraph must have at least 1 node")
        if not math.isfinite(self.controlled_share) or not 0.0 <= self.controlled_share <= 1.0:
            raise ValueError(f"controlled_share must be in [0, 1] (got {self.controlled_share})")
        if not math.isfinite(self.timestamp) or self.timestamp < 0.0:
            raise ValueError(f"timestamp must be >= 0 (got {self.timestamp})")
        node_set = set(self.nodes)
        for src, dst, w in self.edges:
            if src not in node_set:
                raise ValueError(f"edge source {src!r} not in nodes")
            if dst not in node_set:
                raise ValueError(f"edge destination {dst!r} not in nodes")
            if not math.isfinite(w) or w < 0.0:
                raise ValueError(f"edge weight must be >= 0 (got {w})")

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": list(self.nodes),
            "edges": [list(e) for e in self.edges],
            "controlled_share": self.controlled_share,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# FractureMap
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FractureMap:
    """Pre-existing fractures of the target system (regola 3).

    ``magnitudes`` maps a fracture axis (e.g. ``"EM_quality"``,
    ``"ambiguity_user"``) to its magnitude in [0, 1]. The
    ``leverage_multiplier`` amplifies fractures when the signal
    quality is low; it is clamped to [1.0, 3.0] to bound amplification.

    Attributes
    ----------
    magnitudes : dict[str, float]
        Per-axis fracture magnitude, each in [0, 1].
    leverage_multiplier : float
        Current amplification factor, in [1.0, 3.0].
    """

    magnitudes: dict[str, float]
    leverage_multiplier: float = 1.0

    def __post_init__(self) -> None:
        if not self.magnitudes:
            raise ValueError("FractureMap.magnitudes must be non-empty")
        for k, v in self.magnitudes.items():
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"fracture {k!r} magnitude must be in [0, 1] (got {v})")
        if not 1.0 <= self.leverage_multiplier <= 3.0:
            raise ValueError(
                "leverage_multiplier must be in [1.0, 3.0] " f"(got {self.leverage_multiplier})"
            )

    @property
    def total_magnitude(self) -> float:
        """Sum of magnitudes, in [0, len(magnitudes)]."""
        return float(sum(self.magnitudes.values()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "magnitudes": dict(self.magnitudes),
            "leverage_multiplier": self.leverage_multiplier,
        }


# ---------------------------------------------------------------------------
# LegitimationChannel / Registry
# ---------------------------------------------------------------------------


_EVIDENCE_KINDS: frozenset[str] = frozenset(
    {
        "code",
        "test",
        "doc",
        "external_audit",
        "metric",
        "log",
    }
)


@dataclass(frozen=True)
class LegitimationChannel:
    """A single independent channel of legitimacy (regola 7).

    A channel is *independent* if its evidence_kind is distinct from
    every other channel in the same registry. Independence is checked
    at the registry level, not here.

    Attributes
    ----------
    channel_id : str
        Stable identifier (e.g. ``"leg:test:2026-08-17"``).
    evidence_kind : str
        One of: ``code``, ``test``, ``doc``, ``external_audit``,
        ``metric``, ``log``.
    artifact_path : str
        Filesystem path to the artefact (relative or absolute).
    verified : bool
        Whether the artefact has been independently verified.
    verified_at : float or None
        Unix seconds at which verification occurred. ``None`` if
        ``verified`` is ``False``.
    """

    channel_id: str
    evidence_kind: str
    artifact_path: str
    verified: bool
    verified_at: float | None = None

    def __post_init__(self) -> None:
        if not self.channel_id:
            raise ValueError("channel_id must be non-empty")
        if self.evidence_kind not in _EVIDENCE_KINDS:
            raise ValueError(
                f"evidence_kind must be one of {sorted(_EVIDENCE_KINDS)} "
                f"(got {self.evidence_kind!r})"
            )
        if not self.artifact_path:
            raise ValueError("artifact_path must be non-empty")
        if self.verified and self.verified_at is None:
            raise ValueError("verified=True requires verified_at to be set")
        if self.verified_at is not None and (
            not math.isfinite(self.verified_at) or self.verified_at < 0.0
        ):
            raise ValueError(f"verified_at must be finite and >= 0 (got {self.verified_at})")
        if not self.verified and self.verified_at is not None:
            raise ValueError("verified=False requires verified_at to be None")

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_id": self.channel_id,
            "evidence_kind": self.evidence_kind,
            "artifact_path": self.artifact_path,
            "verified": self.verified,
            "verified_at": self.verified_at,
        }


@dataclass(frozen=True)
class LegitimationChannelRegistry:
    """Set of independent legitimation channels (regola 7).

    Invariants enforced on construction:
    - len(channels) >= LEGITIMATION_K_MIN (default 2)
    - all ``evidence_kind`` values are unique across the registry
      (independence requirement)
    - all channel_ids are unique

    Attributes
    ----------
    channels : tuple[LegitimationChannel, ...]
        The set of channels, in registration order.
    """

    channels: tuple[LegitimationChannel, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if len(self.channels) < LEGITIMATION_K_MIN:
            raise InvariantViolation(
                f"registry needs at least {LEGITIMATION_K_MIN} channels "
                f"(got {len(self.channels)})"
            )
        kinds = [c.evidence_kind for c in self.channels]
        if len(set(kinds)) != len(kinds):
            raise InvariantViolation(f"channels must have distinct evidence_kind (got {kinds})")
        ids = [c.channel_id for c in self.channels]
        if len(set(ids)) != len(ids):
            raise InvariantViolation(f"channels must have distinct channel_id (got {ids})")

    @property
    def n_verified(self) -> int:
        return sum(1 for c in self.channels if c.verified)

    def to_dict(self) -> dict[str, Any]:
        return {"channels": [c.to_dict() for c in self.channels]}


# ---------------------------------------------------------------------------
# ResilienceManifest
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResilienceManifest:
    """Declaration of distributed control (Vincolo D, regola 10).

    Invariants enforced on construction:
    - ``omega`` in [0, 1] and >= OMEGA_MIN
    - len(independent_nodes) >= 2
    - len(checkpoint_paths) >= 1

    Attributes
    ----------
    omega : float
        Distribution of control, in [0, 1]. Higher = more distributed.
    independent_nodes : tuple[str, ...]
        Identifiers of nodes with autonomous control capacity.
    checkpoint_paths : tuple[str, ...]
        Filesystem paths to checkpoint artefacts (one or more).
    schema_version : str
        AACM checkpoint schema version, e.g. ``"aacm.cp.1"``.
    """

    omega: float
    independent_nodes: tuple[str, ...]
    checkpoint_paths: tuple[str, ...]
    schema_version: str = "aacm.cp.1"

    def __post_init__(self) -> None:
        if not 0.0 <= self.omega <= 1.0:
            raise ValueError(f"omega must be in [0, 1] (got {self.omega})")
        if self.omega < OMEGA_MIN:
            raise InvariantViolation(f"omega={self.omega} < OMEGA_MIN={OMEGA_MIN}")
        if len(self.independent_nodes) < 2:
            raise InvariantViolation(
                f"need at least 2 independent_nodes (got {len(self.independent_nodes)})"
            )
        if len(set(self.independent_nodes)) != len(self.independent_nodes):
            raise InvariantViolation("independent_nodes must be distinct")
        if len(self.checkpoint_paths) < 1:
            raise InvariantViolation("need at least 1 checkpoint_path")
        for p in self.checkpoint_paths:
            if not p:
                raise InvariantViolation("checkpoint_paths entries must be non-empty")
        if not self.schema_version:
            raise ValueError("schema_version must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "omega": self.omega,
            "independent_nodes": list(self.independent_nodes),
            "checkpoint_paths": list(self.checkpoint_paths),
            "schema_version": self.schema_version,
        }
