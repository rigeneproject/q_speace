"""MemoryPressureManager — hierarchical memory pressure & consolidation for Neuro-OS.

Manages the memory hierarchy (L1 synaptic -> L2 morphological -> L3 semantic) with:
  - Access-frequency tracking for consolidation decisions
  - Memory pressure calculation (fraction of total capacity used)
  - Automatic consolidation of high-value traces
  - "Swap" of low-salience traces to disk
  - Cache eviction policy based on recency x frequency
"""

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class MemoryTier:
    """A tier in the memory hierarchy."""
    name: str
    capacity: float  # abstract capacity units
    access_cost: float  # relative cost to access
    consolidation_threshold: float  # min salience to consolidate here
    eviction_policy: str = "lru"  # lru, lfu, fifo


@dataclass
class MemoryTrace:
    """A single memory trace with access statistics."""
    trace_id: str
    content: Any = None
    salience: float = 0.0
    access_count: int = 0
    last_access_tick: int = 0
    created_at: float = field(default_factory=time.time)
    tier: str = "working"
    consolidated: bool = False

    @property
    def consolidation_score(self) -> float:
        """Score used to decide if this trace should be consolidated."""
        return self.salience * (1.0 + 0.1 * self.access_count)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "salience": self.salience,
            "access_count": self.access_count,
            "last_access_tick": self.last_access_tick,
            "tier": self.tier,
            "consolidated": self.consolidated,
            "consolidation_score": self.consolidation_score,
        }


class MemoryPressureManager:
    """Manages memory hierarchy pressure and consolidation.

    Tiers (matching SPEACE memory architecture):
      L1 (working/synaptic): fast, volatile, limited capacity
      L2 (morphological/episodic): medium, persistent
      L3 (semantic/causal): slow, durable, near-infinite
    """

    DEFAULT_TIERS: List[MemoryTier] = [
        MemoryTier("L1_working", capacity=1000.0, access_cost=1.0, consolidation_threshold=0.3),
        MemoryTier("L2_morphological", capacity=10000.0, access_cost=5.0, consolidation_threshold=0.5),
        MemoryTier("L3_semantic", capacity=100000.0, access_cost=20.0, consolidation_threshold=0.7),
    ]

    def __init__(
        self,
        tiers: Optional[List[MemoryTier]] = None,
        auto_consolidate: bool = True,
        swap_dir: str = "data/memory_swap",
    ) -> None:
        self._tiers = tiers or list(self.DEFAULT_TIERS)
        self._traces: Dict[str, MemoryTrace] = {}
        self._auto_consolidate = auto_consolidate
        self._swap_dir = swap_dir
        self._consolidation_count: int = 0
        self._swap_count: int = 0
        self._pressure_history: List[float] = []
        self._max_pressure_history: int = 100

    # ------------------------------------------------------------------ #
    # Trace management
    # ------------------------------------------------------------------ #

    def store(
        self,
        trace_id: str,
        content: Any = None,
        salience: float = 0.5,
        tier: str = "L1_working",
    ) -> MemoryTrace:
        trace = MemoryTrace(
            trace_id=trace_id,
            content=content,
            salience=salience,
            tier=tier,
        )
        self._traces[trace_id] = trace
        return trace

    def access(self, trace_id: str, tick: int) -> Optional[MemoryTrace]:
        trace = self._traces.get(trace_id)
        if trace is None:
            return None
        trace.access_count += 1
        trace.last_access_tick = tick
        return trace

    def remove(self, trace_id: str) -> bool:
        return self._traces.pop(trace_id, None) is not None

    # ------------------------------------------------------------------ #
    # Pressure
    # ------------------------------------------------------------------ #

    def get_pressure(self) -> Dict[str, float]:
        """Return memory pressure [0, 1] per tier."""
        pressure: Dict[str, float] = {}
        for tier in self._tiers:
            tier_traces = [t for t in self._traces.values() if t.tier == tier.name]
            if tier.capacity > 0:
                pressure[tier.name] = min(1.0, len(tier_traces) / tier.capacity)
            else:
                pressure[tier.name] = 0.0
        return pressure

    def get_aggregate_pressure(self) -> float:
        """Weighted aggregate across all tiers."""
        pressures = self.get_pressure()
        if not pressures:
            return 0.0
        weights = {t.name: 1.0 / len(self._tiers) for t in self._tiers}
        return sum(pressures.get(k, 0.0) * w for k, w in weights.items())

    # ------------------------------------------------------------------ #
    # Consolidation
    # ------------------------------------------------------------------ #

    def consolidate(self, tick: int) -> Dict[str, Any]:
        """Run one consolidation cycle.

        Moves high-salience traces up the hierarchy and evicts
        low-salience traces from full tiers.
        """
        stats: Dict[str, Any] = {
            "consolidated": 0,
            "evicted": 0,
            "swapped": 0,
            "pressure": self.get_pressure(),
        }

        for tier in self._tiers:
            tier_traces = [
                t for t in self._traces.values()
                if t.tier == tier.name and not t.consolidated
            ]
            tier_pressure = len(tier_traces) / tier.capacity if tier.capacity > 0 else 0.0

            if tier_pressure > 0.7:
                # Sort by consolidation score (ascending -> evict low scorers)
                tier_traces.sort(key=lambda t: t.consolidation_score)

                # Evict bottom 10% of low-salience traces
                evict_count = max(1, int(len(tier_traces) * 0.1))
                for trace in tier_traces[:evict_count]:
                    if trace.consolidation_score < tier.consolidation_threshold:
                        self._evict(trace)
                        stats["evicted"] += 1

                # Consolidate top traces to next tier
                tier_idx = next(i for i, t in enumerate(self._tiers) if t.name == tier.name)
                if tier_idx < len(self._tiers) - 1:
                    next_tier = self._tiers[tier_idx + 1]
                    consolidate_candidates = [
                        t for t in tier_traces[evict_count:]
                        if t.consolidation_score >= next_tier.consolidation_threshold
                    ]
                    # Consolidate top 20%
                    consolidate_count = max(1, int(len(consolidate_candidates) * 0.2))
                    for trace in consolidate_candidates[:consolidate_count]:
                        trace.tier = next_tier.name
                        trace.consolidated = True
                        stats["consolidated"] += 1
                        self._consolidation_count += 1

        # Record pressure history
        agg = self.get_aggregate_pressure()
        self._pressure_history.append(agg)
        if len(self._pressure_history) > self._max_pressure_history:
            self._pressure_history.pop(0)

        return stats

    # ------------------------------------------------------------------ #
    # Eviction & Swap
    # ------------------------------------------------------------------ #

    def _evict(self, trace: MemoryTrace) -> None:
        """Evict a trace from active memory, optionally swapping to disk."""
        if trace.salience > 0.2:
            self._swap_out(trace)
            self._swap_count += 1
        self._traces.pop(trace.trace_id, None)

    def _swap_out(self, trace: MemoryTrace) -> None:
        """Write trace to disk (swap). Recoverable via swap_in()."""
        os.makedirs(self._swap_dir, exist_ok=True)
        path = os.path.join(self._swap_dir, f"{trace.trace_id}.json")
        try:
            with open(path, "w") as f:
                json.dump({
                    "trace_id": trace.trace_id,
                    "salience": trace.salience,
                    "access_count": trace.access_count,
                    "created_at": trace.created_at,
                    "tier": trace.tier,
                }, f)
        except OSError:
            pass

    def swap_in(self, trace_id: str) -> Optional[MemoryTrace]:
        """Recover a swapped-out trace."""
        path = os.path.join(self._swap_dir, f"{trace_id}.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path) as f:
                data = json.load(f)
            trace = MemoryTrace(
                trace_id=data["trace_id"],
                salience=data["salience"],
                access_count=data["access_count"],
                created_at=data["created_at"],
                tier=data["tier"],
            )
            self._traces[trace_id] = trace
            os.remove(path)
            return trace
        except (OSError, json.JSONDecodeError):
            return None

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #

    def snapshot(self) -> Dict[str, Any]:
        return {
            "total_traces": len(self._traces),
            "tiers": {t.name: {"capacity": t.capacity, "access_cost": t.access_cost} for t in self._tiers},
            "pressure": self.get_pressure(),
            "aggregate_pressure": self.get_aggregate_pressure(),
            "consolidation_count": self._consolidation_count,
            "swap_count": self._swap_count,
            "pressure_trend": self._pressure_history[-20:] if self._pressure_history else [],
            "traces_sample": [
                t.snapshot() for t in sorted(
                    self._traces.values(),
                    key=lambda x: x.consolidation_score,
                    reverse=True,
                )[:10]
            ],
        }

    def shutdown(self) -> None:
        self._traces.clear()
        self._pressure_history.clear()
