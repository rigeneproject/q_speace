"""T228 independent exact affine verifier; no proposer or corpus dependency.

Certificate covers the real affine model with the exact represented decay.
Replay checks, but does not formally prove, NumPy floating point refinement.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Literal

import numpy as np

from q_speace.spiking.plasticity import SpikePlasticity

STEP_LIMIT = Fraction(1, 4)
RULE_VERSION = "ema-affine-unit-domain-v1"


@dataclass(frozen=True)
class Witness:
    state: float
    rate: float
    expected: float
    property: str = "abs(next-state) <= 1/4"


@dataclass(frozen=True)
class Verdict:
    status: Literal["VALIDA", "INVALIDA", "INDETERMINATA"]
    reason: str
    witness: Witness | None = None


def verify(decay: float) -> Verdict:
    """Prove at all vertices; affine extrema cover [0,1]^2 continuously."""
    if not math.isfinite(decay) or not 0 < decay < 1:
        return Verdict("INDETERMINATA", "Not a finite constructor-admissible decay")
    d = Fraction.from_float(decay)
    for x in (Fraction(0), Fraction(1)):
        for rate in (Fraction(0), Fraction(1)):
            out = d * x + (1 - d) * rate
            if not 0 <= out <= 1 or abs(out - x) > STEP_LIMIT:
                return Verdict(
                    "INVALIDA",
                    "Exact affine vertex violates the declared step bound",
                    Witness(float(x), float(rate), float(out)),
                )
    return Verdict("VALIDA", "Exact affine vertex certificate on x,abs(input) in [0,1]")


def replay(decay: float, witness: Witness) -> dict[str, float | bool]:
    """Replay in the production update, restoring its private EMA snapshot."""
    kernel = SpikePlasticity(num_units=2, decay=decay)
    kernel._ema = np.full(2, witness.state, dtype=np.float64)
    observed = float(kernel.update(np.full(2, witness.rate))[0])
    return {
        "observed": observed,
        "model_gap": abs(observed - witness.expected),
        "violated": abs(observed - witness.state) > float(STEP_LIMIT),
    }
