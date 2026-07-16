"""T172 — InformationalValueFunction (Module B of the Information Value triad).

Biological analogue
-------------------
The inverted-U relationship between arousal / stimulus intensity and
behavioural performance (Yerkes-Dodson law) and the dopamine-mediated
"reward = prediction_error minus baseline" signal. We generalize this to
informational thermodynamics: SPEACE prefers contexts that are *informative*
(structured yet not fully predictable) over contexts that are rigidly
ordered (no information) or pure noise (uncompressible).

Function
--------
``V(novelty, predictability, compressibility) ∈ [-1, +1]``

The three input axes are read as independent components of an "information
phase space":

- ``novelty``         ∈ [0, 1] — distance from prior (similar to novelty_score)
- ``predictability``  ∈ [0, 1] — 1 - prediction_error
- ``compressibility`` ∈ [0, 1] — 1 - informational_entropy (i.e. structure)

The inverted-U is realized as the product of three Gaussian "deltas"
peaked at 0.5 on each axis. The sweet spot of the function is at
(0.5, 0.5, 0.5), giving V_max ≈ 0.6 (after normalization). Pure order
(1, 1, 1) and pure noise (0, 0, 0) both give V → 0.

Mapping to DNA
--------------
This module does NOT modify the genome. It operationalizes the implicit
relationship between ``destructive_entropy_reduction`` (S_ent) and
``generative_variability_preservation`` (V_gen) by exposing a runtime
quantity that:

- is maximised when *both* S_ent is low (structure preserved) *and* V_gen
  is non-trivial (variability present),
- falls to ~0 when the system collapses to either rigid order or noise.

The exact mathematical form is encoded as a new functional constraint law
(see ``register_value_law``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass
class ValueBreakdown:
    """Decomposed value components, useful for diagnostics and Omni-RAG."""

    novelty: float
    predictability: float
    compressibility: float
    V_raw: float
    V_normalised: float
    regime: str  # "ordered" | "sweet_spot" | "chaotic" | "saturated"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "novelty": round(self.novelty, 6),
            "predictability": round(self.predictability, 6),
            "compressibility": round(self.compressibility, 6),
            "V_raw": round(self.V_raw, 6),
            "V_normalised": round(self.V_normalised, 6),
            "regime": self.regime,
        }


class InformationalValueFunction:
    """Inverted-U value function over the information phase space.

    Usage::

        vf = InformationalValueFunction()
        v, breakdown = vf.evaluate(0.6, 0.5, 0.45)
        # v ∈ [-1, +1]; breakdown.regime tells you which regime
    """

    # Sweet spot in (novelty, predictability, compressibility) phase space.
    SWEET_SPOT: Tuple[float, float, float] = (0.5, 0.5, 0.5)

    # Width of each Gaussian "bump". Smaller ⇒ narrower peak ⇒ stricter
    # preference for the sweet spot.
    DEFAULT_SIGMA: float = 0.30

    # Classification thresholds
    SWEET_BAND: float = 0.55  # above this V_normalised we are in sweet spot
    SATURATION: float = 0.95  # very high novelty + low predictability ⇒ chaos
    STARVATION: float = 0.10  # very low novelty + high predictability ⇒ boredom

    def __init__(self, sigma: float = DEFAULT_SIGMA) -> None:
        if sigma <= 0:
            raise ValueError("sigma must be positive")
        self._sigma = sigma
        self._sigma_sq_2 = 2.0 * sigma * sigma

    # ------------------------------------------------------------------ #
    # Core computation
    # ------------------------------------------------------------------ #

    @staticmethod
    def _clip01(x: float) -> float:
        if x < 0.0:
            return 0.0
        if x > 1.0:
            return 1.0
        return float(x)

    def _bump(self, x: float, center: float) -> float:
        """Gaussian bump peaked at ``center`` with width ``sigma``."""
        dx = x - center
        return math.exp(-(dx * dx) / self._sigma_sq_2)

    def V(self, novelty: float, predictability: float, compressibility: float) -> float:
        """Raw value (non-negative).

        This is the product of three Gaussian bumps. Sweet spot ⇒ ~1.0;
        edges ⇒ ~0.
        """
        n = self._clip01(novelty)
        p = self._clip01(predictability)
        c = self._clip01(compressibility)
        return (
            self._bump(n, self.SWEET_SPOT[0])
            * self._bump(p, self.SWEET_SPOT[1])
            * self._bump(c, self.SWEET_SPOT[2])
        )

    def V_normalised(self, novelty: float, predictability: float, compressibility: float) -> float:
        """Normalised value in [-1, +1].

        Sweet spot ⇒ +0.6; far edges ⇒ negative (anti-preference).
        """
        raw = self.V(novelty, predictability, compressibility)
        # Map raw ∈ [0, 1] → [-1, +1] with 0.5 as the neutral point.
        return (2.0 * raw) - 1.0

    def evaluate(
        self,
        novelty: float,
        predictability: float,
        compressibility: float,
    ) -> Tuple[float, ValueBreakdown]:
        """Evaluate and return both raw and normalised value plus regime."""
        n = self._clip01(novelty)
        p = self._clip01(predictability)
        c = self._clip01(compressibility)
        raw = self.V(n, p, c)
        v_norm = self.V_normalised(n, p, c)
        regime = self._classify(n, p, c, v_norm)
        bd = ValueBreakdown(
            novelty=n,
            predictability=p,
            compressibility=c,
            V_raw=raw,
            V_normalised=v_norm,
            regime=regime,
        )
        return v_norm, bd

    # ------------------------------------------------------------------ #
    # Regimes
    # ------------------------------------------------------------------ #

    def _classify(
        self,
        novelty: float,
        predictability: float,
        compressibility: float,
        v_norm: float,
    ) -> str:
        if v_norm >= self.SWEET_BAND:
            return "sweet_spot"
        # High novelty + low predictability + low compressibility ⇒ chaos
        if novelty > 0.7 and predictability < 0.3 and compressibility < 0.3:
            return "chaotic"
        if novelty > self.SATURATION and predictability < 0.2:
            return "saturated"
        # Low novelty + high predictability + high compressibility ⇒ rigid order
        if novelty < self.STARVATION and predictability > 0.8 and compressibility > 0.8:
            return "ordered"
        if v_norm < -0.5:
            return "anti_preferred"
        return "suboptimal"

    # ------------------------------------------------------------------ #
    # Diagnostics
    # ------------------------------------------------------------------ #

    def policy_snapshot(self) -> Dict[str, Any]:
        return {
            "sweet_spot": list(self.SWEET_SPOT),
            "sigma": self._sigma,
            "sweet_band": self.SWEET_BAND,
            "saturation_threshold": self.SATURATION,
            "starvation_threshold": self.STARVATION,
        }

    # ------------------------------------------------------------------ #
    # BCEL functional constraint registration helper
    # ------------------------------------------------------------------ #

    def as_functional_law(self) -> Dict[str, Any]:
        """Return a dict compatible with ``FunctionalConstraintLaw`` registration.

        This is consumed by :func:`speace_core.bcel.catalog.register_value_law`
        which inserts the law into the BCEL catalog so that the Omni-RAG
        bcel_collector picks it up.
        """
        return {
            "name": "inverted_u_information_value",
            "invariant": "generative_variability_preservation",
            "biological_form": (
                "Yerkes-Dodson inverted-U; dopaminergic reward prediction error; "
                "boundary between order and chaos as generative substrate"
            ),
            "target": "circuit",
            "parameters": {
                "sweet_spot": list(self.SWEET_SPOT),
                "sigma": self._sigma,
                "function_class": "InformationalValueFunction",
            },
            "enabled": True,
        }
