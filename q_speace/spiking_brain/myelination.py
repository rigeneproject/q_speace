"""Adaptive Path Myelination, Hysteretic Load Balancer & Batch Role Codec (T256-06).

Synthesized via BCEL from ``SPEACE PROTOTIPO CLAUDE`` (``myelination_engine.py``,
``neural_engine/load_balancer.py``, ``neural_parliament.py``):
- Oligodendrocyte and parliament labels are reduced to deterministic pathway priority
  weights, inter-resource variance throttling with hysteretic recovery, and single-call
  multi-role prompt/response framing.
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass
class MyelinatedPath:
    """Priority conductivity state for a directed ``(source, target)`` pathway."""

    source: str
    target: str
    weight: float = 0.10
    last_used_s: float = 0.0
    activation_count: int = 0
    phi_window: deque[float] = field(default_factory=lambda: deque(maxlen=20))


class MyelinationRegistry:
    """Coherence-driven pathway myelination with inactivity demyelination & pruning (T256-06)."""

    def __init__(
        self,
        *,
        myelination_rate: float = 0.05,
        demyelination_rate: float = 0.02,
        prune_threshold: float = 0.05,
        idle_timeout_s: float = 3600.0,
    ) -> None:
        if not (0.0 < myelination_rate <= 0.5 and 0.0 < demyelination_rate <= 0.5):
            raise ValueError("myelination_rate and demyelination_rate must be in (0, 0.5]")
        if not (0.0 <= prune_threshold < 0.5):
            raise ValueError("prune_threshold must be in [0, 0.5)")
        if not math.isfinite(idle_timeout_s) or idle_timeout_s <= 0.0:
            raise ValueError("idle_timeout_s must be finite and > 0")

        self.myelination_rate = float(myelination_rate)
        self.demyelination_rate = float(demyelination_rate)
        self.prune_threshold = float(prune_threshold)
        self.idle_timeout_s = float(idle_timeout_s)
        self._paths: dict[tuple[str, str], MyelinatedPath] = {}

    @property
    def paths(self) -> Mapping[tuple[str, str], MyelinatedPath]:
        return self._paths

    def activate(
        self,
        source: str,
        target: str,
        *,
        phi: float,
        now_s: float = 0.0,
        initial_weight: float = 0.15,
    ) -> float:
        if not source or not target or source == target:
            raise ValueError("source and target must be distinct non-empty IDs")
        if not math.isfinite(phi) or not (0.0 <= phi <= 1.0):
            raise ValueError("phi must be finite and in [0, 1]")
        if not math.isfinite(now_s) or now_s < 0.0:
            raise ValueError("now_s must be finite and >= 0")

        key = (source, target)
        path = self._paths.get(key)
        if path is None:
            path = MyelinatedPath(
                source=source,
                target=target,
                weight=float(max(0.0, min(1.0, initial_weight))),
                last_used_s=float(now_s),
            )
            self._paths[key] = path

        path.last_used_s = float(now_s)
        path.activation_count += 1
        path.phi_window.append(float(phi))

        avg_phi = sum(path.phi_window) / len(path.phi_window)
        if avg_phi > 0.70:
            path.weight = float(min(1.0, path.weight + self.myelination_rate))
        elif avg_phi < 0.40:
            path.weight = float(max(0.0, path.weight - self.demyelination_rate))
        return path.weight

    def decay_unused(self, now_s: float) -> tuple[tuple[str, str], ...]:
        """Demyelinate paths idle past ``idle_timeout_s`` and prune below ``prune_threshold``."""
        if not math.isfinite(now_s) or now_s < 0.0:
            raise ValueError("now_s must be finite and >= 0")
        pruned: list[tuple[str, str]] = []
        for key in list(self._paths.keys()):
            path = self._paths[key]
            if now_s - path.last_used_s > self.idle_timeout_s:
                path.weight = float(max(0.0, path.weight - 2.0 * self.demyelination_rate))
                if path.weight <= self.prune_threshold:
                    del self._paths[key]
                    pruned.append(key)
        return tuple(pruned)

    def top_priority_paths(self, limit: int = 5) -> tuple[tuple[str, str, float], ...]:
        if limit < 1:
            return ()
        ordered = sorted(
            self._paths.values(),
            key=lambda p: (-p.weight, -p.activation_count, p.source, p.target),
        )
        return tuple((p.source, p.target, p.weight) for p in ordered[:limit])


@dataclass(frozen=True)
class LoadSnapshot:
    """Composite multi-resource load, inter-resource balance, and throttle state."""

    level: str  # "idle" | "light" | "moderate" | "heavy" | "critical" | "overloaded"
    weighted_utilization: float
    balance_score: float
    available_capacity: float
    throttled: bool
    throttle_factor: float


class HystereticLoadBalancer:
    """Multi-resource variance balancer with safety margins & hysteretic recovery (T256-06)."""

    DEFAULT_WEIGHTS: Mapping[str, float] = {
        "cpu": 0.30,
        "memory": 0.25,
        "network": 0.20,
        "energy": 0.15,
        "attention": 0.10,
    }

    def __init__(
        self,
        *,
        weights: Mapping[str, float] = DEFAULT_WEIGHTS,
        recovery_cooldown_s: float = 30.0,
        recovery_step: float = 0.15,
    ) -> None:
        if not weights or any(w <= 0.0 or not math.isfinite(w) for w in weights.values()):
            raise ValueError("weights must be non-empty with finite positive values")
        if not math.isfinite(recovery_cooldown_s) or recovery_cooldown_s < 0.0:
            raise ValueError("recovery_cooldown_s must be finite and >= 0")
        if not math.isfinite(recovery_step) or not (0.0 < recovery_step <= 1.0):
            raise ValueError("recovery_step must be in (0, 1]")

        self._weights: dict[str, float] = {k: float(v) for k, v in weights.items()}
        self.recovery_cooldown_s = float(recovery_cooldown_s)
        self.recovery_step = float(recovery_step)
        self._throttled = False
        self._throttle_factor = 1.0
        self._last_throttle_s = 0.0

    @staticmethod
    def _safety_margin(utilization: float) -> float:
        if utilization < 0.20:
            return 0.05
        if utilization < 0.40:
            return 0.10
        if utilization < 0.60:
            return 0.15
        if utilization < 0.80:
            return 0.20
        return 0.30

    def evaluate(
        self,
        usages: Mapping[str, float],
        *,
        now_s: float = 0.0,
    ) -> LoadSnapshot:
        if not math.isfinite(now_s) or now_s < 0.0:
            raise ValueError("now_s must be finite and >= 0")

        total_w = sum(self._weights.values())
        vals: list[float] = []
        weighted = 0.0
        for name, w in self._weights.items():
            raw = float(usages.get(name, 0.0))
            if not math.isfinite(raw) or not (0.0 <= raw <= 1.0):
                raise ValueError(f"usages[{name!r}] must be finite and in [0, 1]")
            vals.append(raw)
            weighted += (raw * w) / total_w

        variance = sum((v - weighted) ** 2 for v in vals) / max(1, len(vals))
        balance_score = float(max(0.0, min(1.0, 1.0 - 2.0 * variance)))
        avail = float(max(0.0, (1.0 - weighted) - self._safety_margin(weighted)))

        if weighted < 0.20:
            level = "idle"
        elif weighted < 0.40:
            level = "light"
        elif weighted < 0.60:
            level = "moderate"
        elif weighted < 0.80:
            level = "heavy"
        elif weighted < 0.95:
            level = "critical"
        else:
            level = "overloaded"

        if level == "overloaded":
            self._throttled = True
            self._throttle_factor = 0.30
            self._last_throttle_s = float(now_s)
        elif level == "critical":
            self._throttled = True
            self._throttle_factor = min(self._throttle_factor, 0.60)
            self._last_throttle_s = float(now_s)
        elif self._throttled and (
            level in {"idle", "light"}
            and (now_s - self._last_throttle_s) >= self.recovery_cooldown_s
        ):
            self._throttle_factor = min(1.0, self._throttle_factor + self.recovery_step)
            if self._throttle_factor >= 1.0 - 1e-9:
                self._throttle_factor = 1.0
                self._throttled = False

        return LoadSnapshot(
            level=level,
            weighted_utilization=float(weighted),
            balance_score=balance_score,
            available_capacity=avail,
            throttled=self._throttled,
            throttle_factor=float(self._throttle_factor),
        )


class BatchRoleDeliberationCodec:
    """Deterministic single-call multi-role prompt builder & response parser (T256-06)."""

    DEFAULT_ROLES: Mapping[str, str] = {
        "planner": "Create a bounded step-by-step plan with explicit risk level.",
        "critic": "Identify failure modes, biases, and safety constraints.",
        "creative": "Propose alternative low-cost structural hypotheses.",
        "researcher": "Extract empirical patterns and evidence requirements.",
        "executor": "Translate approved steps into concrete verifiable actions.",
    }

    def __init__(self, roles: Mapping[str, str] = DEFAULT_ROLES) -> None:
        if not roles:
            raise ValueError("roles must be non-empty")
        self.roles: dict[str, str] = {
            k.strip().lower(): v.strip() for k, v in roles.items() if k.strip()
        }

    def build_prompt(self, query: str, *, context: Mapping[str, object] | None = None) -> str:
        if not query or not query.strip():
            raise ValueError("query must be non-empty")
        lines: list[str] = []
        if context:
            lines.append("CONTEXT:")
            for k in sorted(context.keys()):
                val_str = str(context[k])
                lines.append(f"- {k}: {val_str[:300]}")
            lines.append("")
        lines.append(f"QUERY: {query.strip()}")
        lines.append("")
        for role_name, instruction in self.roles.items():
            lines.append(f"--- {role_name.upper()} ---")
            lines.append(instruction)
        return "\n".join(lines)

    def parse_response(self, raw_text: str) -> dict[str, str]:
        """Parse ``--- ROLE ---`` sections deterministically with fallback placeholders."""
        parsed: dict[str, str] = {}
        current_role: str | None = None
        buf: list[str] = []

        for line in raw_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("---") and stripped.endswith("---") and len(stripped) > 6:
                header = stripped.strip("-").strip().lower()
                matched = (
                    header
                    if header in self.roles
                    else next((r for r in self.roles if r in header), None)
                )
                if matched is not None:
                    if current_role is not None:
                        parsed[current_role] = "\n".join(buf).strip()
                    current_role = matched
                    buf = []
                elif current_role is not None:
                    buf.append(line)
            elif current_role is not None:
                buf.append(line)

        if current_role is not None:
            parsed[current_role] = "\n".join(buf).strip()

        for role_name in self.roles:
            if not parsed.get(role_name):
                parsed[role_name] = f"[{role_name}:missing]"

        return parsed
