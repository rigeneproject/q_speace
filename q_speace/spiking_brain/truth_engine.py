"""SHA-256 epistemic provenance, structural cycle surprise & action degradation gate (T249-03).

Synthesized via BCEL from ``GTP SPEACE`` v3.20.15
(``safety/truth_engine.py``, ``brain/predictive_coding.py``, ``brain/basal_ganglia.py``):
- Prefrontal/basal-ganglia anatomical labels are *accidental* and removed.
- Canonical SHA-256 observation digests, epistemic classification, negation-aware
  anti-overclaim screening, symmetric-difference module prediction error, and
  cost/reversibility degradation survive as deterministic software gates.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

EpistemicClass = Literal["fact", "tool_observation", "inference", "hypothesis_guarded"]
ActionMode = Literal["execute", "plan", "refuse"]

_WORD_RE = re.compile(r"[a-z0-9_àèéìòù]+")

_DEFAULT_OVERCLAIM_PHRASES: tuple[str, ...] = (
    "quantum consciousness",
    "coscienza reale",
    "coscienza quantistica",
    "sono senziente",
    "senziente",
    "sentient",
    "true agi",
    "full agi",
    "guaranteed 100%",
    "garantito al 100%",
    "infallible",
    "infallibile",
)

_NEGATION_TOKENS: frozenset[str] = frozenset(
    {"no", "not", "never", "non", "nessuna", "nessun", "senza", "neither", "zero"}
)


def _canonical_sha256(payload: Any) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ObservationDigest:
    """Cryptographic provenance record binding a tool/sensor observation (T249-03)."""

    tool: str
    verifiable: bool
    arguments_digest: str
    result_digest: str
    supports_claims: bool = True


@dataclass(frozen=True)
class EpistemicAssessment:
    """Result of epistemic classification & anti-overclaim screening."""

    epistemic_class: EpistemicClass
    adjusted_confidence: float
    overclaim_detected: bool
    matched_overclaims: tuple[str, ...]
    observation_digests: tuple[str, ...]
    approved: bool
    reason: str


class TruthEngine:
    """Epistemic provenance classifier & negation-aware anti-overclaim gate."""

    def __init__(
        self,
        *,
        overclaim_phrases: Sequence[str] = _DEFAULT_OVERCLAIM_PHRASES,
        overclaim_penalty: float = 0.50,
        reject_on_overclaim: bool = True,
        negation_window: int = 3,
    ) -> None:
        if not math.isfinite(overclaim_penalty) or not (0.0 <= overclaim_penalty <= 1.0):
            raise ValueError("overclaim_penalty must be finite and in [0, 1]")
        if negation_window < 1:
            raise ValueError("negation_window must be >= 1")
        self.overclaim_phrases: tuple[str, ...] = tuple(
            p.strip().lower() for p in overclaim_phrases if p.strip()
        )
        self.overclaim_penalty = float(overclaim_penalty)
        self.reject_on_overclaim = reject_on_overclaim
        self.negation_window = negation_window

    @staticmethod
    def tool_observation(
        tool: str,
        arguments: Mapping[str, Any],
        result: Any,
        *,
        verifiable: bool = True,
        supports_claims: bool = True,
    ) -> ObservationDigest:
        """Create a canonical SHA-256 provenance digest for one tool/sensor observation."""
        if not tool or not tool.strip():
            raise ValueError("tool name must be non-empty")
        return ObservationDigest(
            tool=tool.strip(),
            verifiable=verifiable,
            arguments_digest=_canonical_sha256(dict(arguments)),
            result_digest=_canonical_sha256(result),
            supports_claims=supports_claims,
        )

    def _find_unnegated_overclaims(self, text: str) -> tuple[str, ...]:
        lowered = text.lower()
        tokens = _WORD_RE.findall(lowered)
        found: list[str] = []
        for phrase in self.overclaim_phrases:
            idx = lowered.find(phrase)
            if idx < 0:
                continue
            # Check preceding words before the match for explicit negation
            prefix_tokens = _WORD_RE.findall(lowered[:idx])
            recent = prefix_tokens[-self.negation_window :]
            if any(tok in _NEGATION_TOKENS for tok in recent):
                continue
            # Single-word checks avoid substring false positives (e.g. "sentient" vs "non-sentient")
            phrase_tokens = _WORD_RE.findall(phrase)
            if len(phrase_tokens) == 1 and phrase_tokens[0] not in tokens:
                continue
            found.append(phrase)
        return tuple(dict.fromkeys(found))

    def assess(
        self,
        text: str,
        *,
        observations: Sequence[ObservationDigest] = (),
        base_confidence: float = 0.5,
        verified_fact: bool = False,
    ) -> EpistemicAssessment:
        """Classify epistemic grounding and screen ``text`` for unnegated overclaims."""
        if not math.isfinite(base_confidence) or not (0.0 <= base_confidence <= 1.0):
            raise ValueError(
                f"base_confidence must be finite and in [0, 1] (got {base_confidence!r})"
            )

        matched = self._find_unnegated_overclaims(text)
        overclaim = len(matched) > 0
        supporting = [o for o in observations if o.verifiable and o.supports_claims]

        if overclaim:
            epi_class: EpistemicClass = "hypothesis_guarded"
            adj_conf = max(0.0, float(base_confidence) * (1.0 - self.overclaim_penalty))
            approved = not self.reject_on_overclaim
            reason = f"overclaim_detected:{','.join(matched)}"
        elif verified_fact and supporting:
            epi_class = "fact"
            adj_conf = min(1.0, float(base_confidence) + 0.05)
            approved = True
            reason = "verified_fact_with_provenance"
        elif supporting:
            epi_class = "tool_observation"
            adj_conf = float(base_confidence)
            approved = True
            reason = "grounded_in_tool_observation"
        elif float(base_confidence) >= 0.65:
            epi_class = "inference"
            adj_conf = float(base_confidence)
            approved = True
            reason = "bounded_inference"
        else:
            epi_class = "hypothesis_guarded"
            adj_conf = float(base_confidence)
            approved = True
            reason = "low_confidence_hypothesis"

        return EpistemicAssessment(
            epistemic_class=epi_class,
            adjusted_confidence=adj_conf,
            overclaim_detected=overclaim,
            matched_overclaims=matched,
            observation_digests=tuple(o.result_digest for o in supporting),
            approved=approved,
            reason=reason,
        )


@dataclass(frozen=True)
class CyclePrediction:
    """Pre-tick structural expectation over action, risk, energy mode & active modules."""

    expected_action: str
    expected_risk: str
    expected_energy_mode: str
    expected_modules: frozenset[str]
    confidence: float = 0.7

    def __post_init__(self) -> None:
        if not math.isfinite(self.confidence) or not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be finite and in [0, 1]")


@dataclass(frozen=True)
class CycleObservation:
    """Post-tick observed execution outcome."""

    actual_action: str
    actual_risk: str
    actual_energy_mode: str
    active_modules: frozenset[str]


@dataclass(frozen=True)
class CycleSurprise:
    """Composite structural prediction error and confidence-weighted surprise."""

    module_error: float
    composite_error: float
    surprise: float


class StructuralPredictiveCoder:
    """Cycle-level structural prediction error & surprise evaluator (T249-03)."""

    def evaluate(self, pred: CyclePrediction, obs: CycleObservation) -> CycleSurprise:
        union_mods = pred.expected_modules | obs.active_modules
        sym_diff = pred.expected_modules ^ obs.active_modules
        mod_err = min(1.0, len(sym_diff) / max(1, len(union_mods)))

        act_err = 0.0 if pred.expected_action == obs.actual_action else 1.0
        risk_err = 0.0 if pred.expected_risk == obs.actual_risk else 1.0
        energy_err = 0.0 if pred.expected_energy_mode == obs.actual_energy_mode else 1.0

        comp = 0.40 * act_err + 0.20 * risk_err + 0.20 * energy_err + 0.20 * mod_err
        surprise = comp * (0.75 + 0.50 * pred.confidence)
        return CycleSurprise(
            module_error=float(mod_err),
            composite_error=float(comp),
            surprise=float(surprise),
        )


class ActionDegradationGate:
    """Cost, risk & reversibility selector ('execute' -> 'plan' -> 'refuse', T249-03)."""

    def __init__(
        self,
        *,
        max_risk: float = 0.75,
        cost_margin: float = 0.20,
    ) -> None:
        if not math.isfinite(max_risk) or not (0.0 <= max_risk <= 1.0):
            raise ValueError("max_risk must be finite and in [0, 1]")
        if not math.isfinite(cost_margin) or cost_margin < 0.0:
            raise ValueError("cost_margin must be finite and >= 0")
        self.max_risk = float(max_risk)
        self.cost_margin = float(cost_margin)

    def select(
        self,
        *,
        value_score: float,
        energy_cost: float,
        risk: float,
        reversible: bool = True,
    ) -> ActionMode:
        for name, val in (
            ("value_score", value_score),
            ("energy_cost", energy_cost),
            ("risk", risk),
        ):
            if not math.isfinite(val):
                raise ValueError(f"{name} must be finite")
        if value_score < 0.0 or energy_cost < 0.0 or not (0.0 <= risk <= 1.0):
            raise ValueError("value_score >= 0, energy_cost >= 0, and risk in [0, 1] required")

        if risk > self.max_risk or (not reversible and risk > 0.5 * self.max_risk):
            return "refuse"
        if energy_cost > value_score + self.cost_margin or not reversible:
            return "plan"
        return "execute"
