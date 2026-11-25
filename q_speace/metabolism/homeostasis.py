"""Homeostatic restorative ODE, convex urgency field & diffusive budget sharing (T249-01).

Synthesized via BCEL from ``speaceorganismocibernetico`` M5
(``HomeostaticController``, ``ValueField``, ``ConstraintLayer``) and
``speace_ds`` (``AstrocyteLayer``):
- Survival/hunger teleology and glial glucose narratives are *accidental* and removed.
- Bounded Euler restorative-tracking ODEs, deadband viability, soft-constraint
  penalties, convex urgency gradients, and graph-diffusive energy sharing within
  a hard global power cap survive as pure mathematical control primitives.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class HomeostaticChannel:
    """Configuration of one bounded state variable h_d in [0, 1]."""

    name: str
    setpoint: float = 0.75
    deadband: float = 0.05
    k_restore: float = 0.15
    k_input: float = 0.35
    weight: float = 1.0
    initial_value: float | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("channel name must be non-empty")
        for label, val in (
            ("setpoint", self.setpoint),
            ("deadband", self.deadband),
            ("k_restore", self.k_restore),
            ("k_input", self.k_input),
            ("weight", self.weight),
        ):
            if not math.isfinite(val):
                raise ValueError(f"{label} must be finite (got {val!r})")
        if not (0.0 <= self.setpoint <= 1.0):
            raise ValueError("setpoint must be in [0, 1]")
        if not (0.0 <= self.deadband < 1.0):
            raise ValueError("deadband must be in [0, 1)")
        if self.k_restore < 0.0 or self.k_input < 0.0 or self.weight < 0.0:
            raise ValueError("k_restore, k_input, and weight must be >= 0")
        if self.initial_value is not None and (
            not math.isfinite(self.initial_value) or not (0.0 <= self.initial_value <= 1.0)
        ):
            raise ValueError("initial_value must be finite and in [0, 1]")


@dataclass(frozen=True)
class HomeostaticSnapshot:
    """Immutable telemetry emitted by one homeostatic ODE step."""

    state: dict[str, float]
    viability: float
    urgency: dict[str, float]
    value_gradient: dict[str, float]
    dominant_channel: str | None


class HomeostaticODEController:
    """Multi-channel restorative-tracking Euler ODE with soft constraints & urgency field."""

    def __init__(
        self,
        channels: Sequence[HomeostaticChannel],
        *,
        urgency_exponent: float = 2.0,
        max_dt: float = 10.0,
    ) -> None:
        if not channels:
            raise ValueError("at least one HomeostaticChannel is required")
        if not math.isfinite(urgency_exponent) or urgency_exponent < 1.0:
            raise ValueError("urgency_exponent must be finite and >= 1.0")
        if not math.isfinite(max_dt) or max_dt <= 0.0:
            raise ValueError("max_dt must be finite and > 0")

        self._channels: dict[str, HomeostaticChannel] = {}
        self._state: dict[str, float] = {}
        for ch in channels:
            if ch.name in self._channels:
                raise ValueError(f"duplicate channel name: {ch.name!r}")
            self._channels[ch.name] = ch
            self._state[ch.name] = (
                float(ch.initial_value) if ch.initial_value is not None else float(ch.setpoint)
            )
        self.urgency_exponent = float(urgency_exponent)
        self.max_dt = float(max_dt)

    @property
    def state(self) -> dict[str, float]:
        return dict(self._state)

    def apply_soft_constraints(
        self,
        penalties: Mapping[str, tuple[float, float]],
    ) -> dict[str, float]:
        """Apply soft constraint feedback ``h_d <- clip(h_d - lambda_c * severity_c, 0, 1)``."""
        for name, (lam, severity) in penalties.items():
            if name not in self._state:
                raise KeyError(f"unknown homeostatic channel: {name!r}")
            if not (math.isfinite(lam) and math.isfinite(severity)):
                raise ValueError("constraint lambda and severity must be finite")
            if lam < 0.0 or not (0.0 <= severity <= 1.0):
                raise ValueError("lambda must be >= 0 and severity in [0, 1]")
            self._state[name] = float(
                max(0.0, min(1.0, self._state[name] - float(lam) * float(severity)))
            )
        return dict(self._state)

    def step(
        self,
        receptors: Mapping[str, float] | None = None,
        *,
        dt: float = 1.0,
        constraint_penalties: Mapping[str, tuple[float, float]] | None = None,
    ) -> HomeostaticSnapshot:
        """Advance all channels by one clamped Euler step and return viability/urgency metrics."""
        if not math.isfinite(dt) or dt < 0.0:
            raise ValueError(f"dt must be finite and >= 0 (got {dt!r})")
        eff_dt = min(float(dt), self.max_dt)
        rec = dict(receptors) if receptors is not None else {}
        for k, v in rec.items():
            if k not in self._channels:
                raise KeyError(f"unknown receptor channel: {k!r}")
            if not math.isfinite(v) or not (0.0 <= v <= 1.0):
                raise ValueError(f"receptor[{k!r}] must be finite and in [0, 1]")

        for name, ch in self._channels.items():
            h = self._state[name]
            r = float(rec.get(name, h))
            dh_dt = -ch.k_restore * (h - ch.setpoint) + ch.k_input * (r - h)
            self._state[name] = float(max(0.0, min(1.0, h + eff_dt * dh_dt)))

        if constraint_penalties:
            self.apply_soft_constraints(constraint_penalties)

        return self.snapshot()

    def snapshot(self) -> HomeostaticSnapshot:
        viabilities: list[float] = []
        urgency: dict[str, float] = {}
        gradient: dict[str, float] = {}

        for name, ch in self._channels.items():
            h = self._state[name]
            err = abs(h - ch.setpoint)
            excess = max(0.0, err - ch.deadband)
            v_d = max(0.0, 1.0 - excess / max(1.0 - ch.deadband, 1e-9))
            viabilities.append(v_d)

            d_max = max(ch.setpoint, 1.0 - ch.setpoint, 1e-6)
            urgency[name] = float((excess / d_max) ** self.urgency_exponent)

            diff = ch.setpoint - h
            sign = 0.0 if abs(diff) <= ch.deadband else (1.0 if diff > 0.0 else -1.0)
            gradient[name] = float(ch.weight * sign / d_max)

        dominant = max(urgency, key=lambda k: urgency[k]) if urgency else None
        if dominant is not None and urgency[dominant] <= 0.0:
            dominant = None

        return HomeostaticSnapshot(
            state=dict(self._state),
            viability=float(sum(viabilities) / len(viabilities)),
            urgency=urgency,
            value_gradient=gradient,
            dominant_channel=dominant,
        )


class DiffusiveBudgetAllocator:
    """Graph-diffusive subsystem energy allocator under a hard global cap (T249-01).

    Prevents single-subsystem starvation while letting low-load neighbors lend
    surplus power to active neighbors without ever exceeding ``total_budget_w``.
    """

    def __init__(
        self,
        nodes: Sequence[str],
        edges: Sequence[tuple[str, str]] = (),
        *,
        min_share_ratio: float = 0.05,
        diffusion_rate: float = 0.25,
    ) -> None:
        unique_nodes = list(dict.fromkeys(nodes))
        if not unique_nodes or any(not n for n in unique_nodes):
            raise ValueError("nodes must be non-empty strings")
        if not math.isfinite(min_share_ratio) or not (0.0 <= min_share_ratio <= 1.0):
            raise ValueError("min_share_ratio must be finite and in [0, 1]")
        if not math.isfinite(diffusion_rate) or not (0.0 <= diffusion_rate <= 0.5):
            raise ValueError("diffusion_rate must be finite and in [0, 0.5]")

        node_set = set(unique_nodes)
        adj: dict[str, set[str]] = {n: set() for n in unique_nodes}
        for u, v in edges:
            if u not in node_set or v not in node_set:
                raise ValueError(f"edge ({u!r}, {v!r}) references unknown node")
            if u != v:
                adj[u].add(v)
                adj[v].add(u)

        self._nodes: tuple[str, ...] = tuple(unique_nodes)
        self._adj: dict[str, tuple[str, ...]] = {n: tuple(sorted(adj[n])) for n in unique_nodes}
        self.min_share_ratio = float(min_share_ratio)
        self.diffusion_rate = float(diffusion_rate)

    def allocate(
        self,
        total_budget_w: float,
        activations: Mapping[str, float],
        loads: Mapping[str, float] | None = None,
    ) -> dict[str, float]:
        """Distribute ``total_budget_w`` across nodes with load damping + neighbor diffusion."""
        if not math.isfinite(total_budget_w) or total_budget_w < 0.0:
            raise ValueError(f"total_budget_w must be finite and >= 0 (got {total_budget_w!r})")
        if total_budget_w == 0.0:
            return dict.fromkeys(self._nodes, 0.0)

        n = len(self._nodes)
        load_map = dict(loads) if loads is not None else {}
        raw: dict[str, float] = {}
        for node in self._nodes:
            act = float(activations.get(node, 1.0))
            ld = float(load_map.get(node, 0.0))
            if not (math.isfinite(act) and math.isfinite(ld)):
                raise ValueError("activations and loads must be finite")
            if act < 0.0 or not (0.0 <= ld <= 1.0):
                raise ValueError("activations must be >= 0 and loads in [0, 1]")
            support = max(0.1, 1.0 - 0.7 * ld)
            raw[node] = max(1e-6, act * support)

        raw_sum = sum(raw.values())
        alloc = {node: total_budget_w * (raw[node] / raw_sum) for node in self._nodes}

        # One synchronous mass-conserving Laplacian diffusion step across graph neighbors
        if self.diffusion_rate > 0.0:
            deltas: dict[str, float] = dict.fromkeys(self._nodes, 0.0)
            for u in self._nodes:
                nbrs = self._adj[u]
                if not nbrs:
                    continue
                deg = len(nbrs)
                for v in nbrs:
                    flow = (self.diffusion_rate / max(deg, len(self._adj[v]))) * (
                        alloc[v] - alloc[u]
                    )
                    deltas[u] += flow
            for u in self._nodes:
                alloc[u] = max(0.0, alloc[u] + deltas[u])

        # Enforce minimum floor per node without exceeding total_budget_w
        floor_w = (total_budget_w / n) * self.min_share_ratio
        boosted = {u: max(floor_w, alloc[u]) for u in self._nodes}
        boost_sum = sum(boosted.values())
        return {u: float(total_budget_w * (boosted[u] / boost_sum)) for u in self._nodes}
