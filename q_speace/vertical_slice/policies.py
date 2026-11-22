"""Gate policy configurations and deterministic precedence rules (T208 §2.1 & T209.5)."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Literal

from .contracts import DecisionRecord

PolicyKind = Literal["always_answer", "confidence_gate", "energy_gate", "combined_gate"]
FallbackMode = Literal["refuse", "fallback"]
VALID_POLICY_KINDS: tuple[PolicyKind, ...] = (
    "always_answer",
    "confidence_gate",
    "energy_gate",
    "combined_gate",
)


@dataclass(frozen=True)
class PolicyConfig:
    """Stable, serializable gate policy configuration."""

    policy_id: str
    kind: PolicyKind
    min_confidence: float = 0.60
    max_energy_j: float = 80.0
    sevo_threshold: float = 1.5
    min_coherence_phi: float = 0.05
    fallback_mode: FallbackMode = "refuse"
    model_revision: str | None = None
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise ValueError("policy_id must be non-empty")
        if self.kind not in VALID_POLICY_KINDS:
            raise ValueError(f"unknown policy kind: {self.kind!r}")
        if not math.isfinite(self.min_confidence) or not (0.0 <= self.min_confidence <= 1.0):
            raise ValueError(
                f"min_confidence must be finite and in [0, 1] (got {self.min_confidence!r})"
            )
        if not math.isfinite(self.max_energy_j) or self.max_energy_j < 0.0:
            raise ValueError(f"max_energy_j must be finite and >= 0 (got {self.max_energy_j!r})")
        if not math.isfinite(self.sevo_threshold) or self.sevo_threshold < 0.0:
            raise ValueError(
                f"sevo_threshold must be finite and >= 0 (got {self.sevo_threshold!r})"
            )
        if not math.isfinite(self.min_coherence_phi) or not (0.0 <= self.min_coherence_phi <= 1.0):
            raise ValueError(
                f"min_coherence_phi must be finite and in [0, 1] (got {self.min_coherence_phi!r})"
            )
        if self.fallback_mode not in ("refuse", "fallback"):
            raise ValueError(f"invalid fallback_mode: {self.fallback_mode!r}")

    def thresholds_dict(self) -> dict[str, float]:
        return {
            "min_confidence": self.min_confidence,
            "max_energy_j": self.max_energy_j,
            "sevo_threshold": self.sevo_threshold,
            "min_coherence_phi": self.min_coherence_phi,
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_policy(kind: PolicyKind = "always_answer") -> PolicyConfig:
    """Return a canonical policy configuration for the requested kind."""
    return PolicyConfig(policy_id=f"t209-{kind}", kind=kind)


def evaluate_policy(
    policy: PolicyConfig,
    *,
    route: str,
    predicted_energy_j: float | None,
    confidence: float | None,
    sevo: float | None,
    coherence_phi: float | None,
) -> DecisionRecord:
    """Evaluate a gate policy with explicit, auditable reason precedence.

    Precedence order:
      1. ``policy_disabled`` -> falls back to ``always_answer`` behavior (opt-in rollback).
      2. ``route_non_language`` -> refuses non-language events on the instruction slice.
      3. ``energy_gate`` (for ``energy_gate`` / ``combined_gate``).
      4. ``confidence_gate`` (for ``confidence_gate`` / ``combined_gate``).
      5. ``sevo_gate`` and ``coherence_gate`` (for ``combined_gate``).
      6. ``approved``.
    """
    safe_energy = (
        predicted_energy_j
        if (predicted_energy_j is not None and math.isfinite(predicted_energy_j))
        else None
    )
    safe_conf = confidence if (confidence is not None and math.isfinite(confidence)) else None
    thresholds = policy.thresholds_dict()

    if route != "language":
        return DecisionRecord(
            route=route,
            gate_open=False,
            decision_reason="route_non_language",
            predicted_energy_j=safe_energy,
            confidence=safe_conf,
            thresholds=thresholds,
        )

    if not policy.enabled or policy.kind == "always_answer":
        reason = "always_answer" if policy.enabled else "policy_disabled_passthrough"
        return DecisionRecord(
            route=route,
            gate_open=True,
            decision_reason=reason,
            predicted_energy_j=safe_energy,
            confidence=safe_conf,
            thresholds=thresholds,
        )

    # Energy gate (fail-closed on missing/non-finite energy)
    if policy.kind in ("energy_gate", "combined_gate") and (
        safe_energy is None or safe_energy > policy.max_energy_j
    ):
        return DecisionRecord(
            route=route,
            gate_open=False,
            decision_reason="energy_gate_exceeded",
            predicted_energy_j=safe_energy,
            confidence=safe_conf,
            thresholds=thresholds,
        )

    # Confidence gate (fail-closed on missing/non-finite confidence)
    if policy.kind in ("confidence_gate", "combined_gate") and (
        safe_conf is None or safe_conf < policy.min_confidence
    ):
        return DecisionRecord(
            route=route,
            gate_open=False,
            decision_reason="confidence_gate_below_threshold",
            predicted_energy_j=safe_energy,
            confidence=safe_conf,
            thresholds=thresholds,
        )

    # Sevo + coherence checks for combined_gate
    if policy.kind == "combined_gate":
        if sevo is None or not math.isfinite(sevo) or sevo <= policy.sevo_threshold:
            return DecisionRecord(
                route=route,
                gate_open=False,
                decision_reason="sevo_gate_below_threshold",
                predicted_energy_j=safe_energy,
                confidence=safe_conf,
                thresholds=thresholds,
            )
        if (
            coherence_phi is None
            or not math.isfinite(coherence_phi)
            or coherence_phi < policy.min_coherence_phi
        ):
            return DecisionRecord(
                route=route,
                gate_open=False,
                decision_reason="coherence_gate_below_threshold",
                predicted_energy_j=safe_energy,
                confidence=safe_conf,
                thresholds=thresholds,
            )

    return DecisionRecord(
        route=route,
        gate_open=True,
        decision_reason="approved",
        predicted_energy_j=safe_energy,
        confidence=safe_conf,
        thresholds=thresholds,
    )
