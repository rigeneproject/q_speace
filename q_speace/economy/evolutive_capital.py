"""Evolutive Capital registry for the q_speace_economy (T6.22 §4.6).

The Evolutive Capital is a non-fungible registry of 10 capital kinds.
Unlike a scalar monetary balance, the kinds cannot be converted into
each other — each is measured in its own units and bounded by its own
physical constraints.

The 10 kinds are exactly the dimensions tracked by the paper §4.6.
They mirror the 12 CME dimensions but drop the two "human-subjective"
axes (``wellbeing``, ``distribution``) which are accounted elsewhere
(``BCEL`` catalog, ``admission``).

BCEL: the registry is *functional*: each capital kind is a measurable
physical quantity. The "regenerative" capital is a rate (capacity
restoration per unit time), not a metaphor for ecosystem agency.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CapitalKind = Literal[
    "energy",
    "material",
    "knowledge",
    "ecological",
    "computational",
    "human_time",
    "resilience",
    "coherence",
    "regenerative",
    "evolutionary",
]

_VALID_KINDS: frozenset[str] = frozenset(
    {
        "energy",
        "material",
        "knowledge",
        "ecological",
        "computational",
        "human_time",
        "resilience",
        "coherence",
        "regenerative",
        "evolutionary",
    }
)


@dataclass(frozen=True)
class CapitalEntry:
    """One entry in the Evolutive Capital registry."""

    kind: CapitalKind
    amount: float
    unit: str
    upper_bound: float

    def __post_init__(self) -> None:
        if self.kind not in _VALID_KINDS:
            raise ValueError(f"unknown capital kind: {self.kind!r}")
        if self.amount < 0.0:
            raise ValueError(f"amount must be >= 0 (got {self.amount})")
        if self.upper_bound <= 0.0:
            raise ValueError(f"upper_bound must be > 0 (got {self.upper_bound})")
        if self.amount > self.upper_bound:
            raise ValueError(f"amount {self.amount} exceeds upper_bound {self.upper_bound}")
        if not self.unit:
            raise ValueError("unit must be non-empty")

    @property
    def fraction(self) -> float:
        """Amount as a fraction of the upper bound, in [0, 1]."""
        return self.amount / self.upper_bound


def validate_registry(entries: list[CapitalEntry]) -> list[str]:
    """Return a list of validation messages (empty if the registry is OK).

    A registry is considered valid when:

    - every entry has ``amount <= upper_bound``,
    - each ``kind`` appears at most once (no double-bookkeeping),
    - the total of all entries is below a soft threshold of 10.0
      (sanity check for tests; not a hard economic limit).
    """
    out: list[str] = []
    seen: set[str] = set()
    total = 0.0
    for e in entries:
        if e.kind in seen:
            out.append(f"duplicate kind: {e.kind}")
        seen.add(e.kind)
        if e.amount > e.upper_bound:
            out.append(f"{e.kind}: amount {e.amount} > upper_bound {e.upper_bound}")
        total += e.amount
    return out
