"""Dynamic Allocation Token (DAT) for the q_speace_economy (T6.4).

Implements :class:`DAT`, the token type described in
``docs/q_speace_economy.md`` §4.4.3. A DAT carries:

- an ``amount`` that halves every ``decay_half_life`` seconds,
- a routing key ``bound_to`` that scopes where the token may be spent,
- a ``mint_time`` anchor (Unix seconds).

Spending against a non-matching ``bound_to`` raises :class:`ValueError`;
over-spending (i.e. requesting more than the current value) raises
:class:`ValueError` with a precise message.

The exponential decay function is:

    value(t) = amount * 2 ** (-(t - mint_time) / decay_half_life)

This is the "decoherence-as-interest" interpretation noted in §11 of the
paper (the environment's decoherence rate effectively sets the discount
factor). The function is intentionally a pure Python implementation: no
numpy, no scipy — keeps the token logic portable and testable.

BCEL: the decay curve is *functional*: it is a deterministic exponential
that any agent can recompute. It is not a biological metabolism rate, and
the token itself is not an "energy quanta" of any conscious entity.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DAT:
    """Dynamic Allocation Token with exponential decay.

    Attributes
    ----------
    amount : float
        Initial amount at mint time. Must be > 0.
    bound_to : str
        Routing key for valid spending targets. Must be non-empty.
    decay_half_life : float
        Time in seconds for the amount to halve. Must be > 0.
    mint_time : float
        Mint timestamp (Unix seconds, float). Must be >= 0.
    metadata : dict[str, Any]
        Free-form annotations (issuer id, lineage, tags).
    """

    amount: float
    bound_to: str
    decay_half_life: float
    mint_time: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.amount <= 0.0:
            raise ValueError(f"amount must be > 0 (got {self.amount})")
        if not self.bound_to:
            raise ValueError("bound_to must be a non-empty string")
        if self.decay_half_life <= 0.0:
            raise ValueError(f"decay_half_life must be > 0 (got {self.decay_half_life})")
        if self.mint_time < 0.0:
            raise ValueError(f"mint_time must be >= 0 (got {self.mint_time})")

    # ------------------------------------------------------------------
    # value at time t
    # ------------------------------------------------------------------

    def value_at(self, t: float) -> float:
        """Return the decayed amount at time ``t``.

        Parameters
        ----------
        t : float
            Unix timestamp (seconds, float).
        """
        if t < self.mint_time:
            raise ValueError(f"t ({t}) is before mint_time ({self.mint_time})")
        elapsed = (t - self.mint_time) / self.decay_half_life
        v: float = self.amount * (2.0**-elapsed)
        return v

    def age(self, t: float) -> float:
        """Return elapsed seconds since mint."""
        if t < self.mint_time:
            raise ValueError(f"t ({t}) is before mint_time ({self.mint_time})")
        return t - self.mint_time

    def fraction_remaining(self, t: float) -> float:
        """Return the fraction of the original amount still available at ``t``.

        The fraction is in (0, 1]; at ``t = mint_time`` it is exactly 1.0.
        """
        if t < self.mint_time:
            raise ValueError(f"t ({t}) is before mint_time ({self.mint_time})")
        elapsed = (t - self.mint_time) / self.decay_half_life
        f: float = 2.0**-elapsed
        return f

    # ------------------------------------------------------------------
    # spending
    # ------------------------------------------------------------------

    def spend(self, amount: float, target: str, t: float) -> SpendReceipt:
        """Spend ``amount`` against ``target`` at time ``t``.

        Returns a :class:`SpendReceipt`. Raises :class:`ValueError` if:

        - ``target != bound_to`` (binding violation),
        - ``amount > value_at(t)`` (over-spend).
        """
        if amount <= 0.0:
            raise ValueError(f"spend amount must be > 0 (got {amount})")
        if target != self.bound_to:
            raise ValueError(
                f"bound violation: token is bound to {self.bound_to!r}, "
                f"cannot spend against {target!r}"
            )
        current = self.value_at(t)
        if amount > current:
            raise ValueError(f"over-spend: requested {amount} > available {current}")
        # Reduce the value so the remaining budget under the same
        # half-life (anchored at the new mint time ``t``) equals
        # ``current - amount``.
        new_amount = current - amount
        receipt = SpendReceipt(
            spent=amount,
            target=target,
            t=t,
            new_amount=new_amount,
            new_mint_time=t,
            decay_half_life=self.decay_half_life,
        )
        # In-place mutation so the caller sees the new state.
        self.amount = new_amount
        self.mint_time = t
        return receipt


@dataclass(frozen=True)
class SpendReceipt:
    """Immutable record of a successful :meth:`DAT.spend` call."""

    spent: float
    target: str
    t: float
    new_amount: float
    new_mint_time: float
    decay_half_life: float

    def remaining_value_at(self, t: float) -> float:
        """Value of the post-spend token at a future time ``t``."""
        if t < self.new_mint_time:
            raise ValueError(f"t ({t}) is before new_mint_time ({self.new_mint_time})")
        elapsed = (t - self.new_mint_time) / self.decay_half_life
        v: float = self.new_amount * (2.0**-elapsed)
        return v


def half_life_for_target_lifespan(target_lifespan_s: float) -> float:
    """Convenience: half-life so that value halves once per target lifetime.

    If you want the token to halve after the *full* target lifespan,
    pass the lifespan; if you want it to halve once per ``k`` lifespans,
    multiply by ``k``.
    """
    if target_lifespan_s <= 0.0:
        raise ValueError("target_lifespan_s must be > 0")
    return float(target_lifespan_s)


def rate_to_half_life(rate_per_s: float) -> float:
    """Convert an exponential rate (per second) to a half-life (seconds).

    ``value(t) = exp(-rate * t) = 2**(-t/half_life)`` implies
    ``half_life = ln(2) / rate``.
    """
    if rate_per_s <= 0.0:
        raise ValueError("rate_per_s must be > 0")
    return math.log(2.0) / rate_per_s
