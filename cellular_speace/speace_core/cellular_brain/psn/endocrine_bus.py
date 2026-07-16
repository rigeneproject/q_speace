from __future__ import annotations
from typing import Dict, List, Optional

from speace_core.cellular_brain.psn.models import HormonePool


class EndocrineBus:
    """Slow, persistent, broadcast hormone signalling.

    Hormones accumulate on re-secretion and decay via molecule-specific
    clearance rates. Supports both stream (continuous) and event (spike)
    modes.
    """

    def __init__(self):
        self._pools: Dict[str, HormonePool] = {}
        self._current_tick: int = 0

    @property
    def current_tick(self) -> int:
        return self._current_tick

    def set_tick(self, tick: int) -> None:
        self._current_tick = tick

    def register_pool(
        self,
        molecule: str,
        clearance_rate: float = 0.92,
        delay_ticks: int = 2,
        max_concentration: float = 1.0,
        baseline: float = 0.0,
        stream: bool = True,
        event_mode: bool = False,
        event_duration: int = 0,
        event_decay: float = 0.80,
    ) -> None:
        """Register a hormone pool, typically from the Physiome at startup."""
        self._pools[molecule] = HormonePool(
            molecule=molecule,
            clearance_rate=clearance_rate,
            delay_ticks=delay_ticks,
            max_concentration=max_concentration,
            baseline=baseline,
            stream=stream,
            event_mode=event_mode,
            event_duration=event_duration,
            event_decay=event_decay,
        )

    def secrete(
        self,
        hormone: str,
        concentration: float,
        source: str = "",
        clearance_rate: Optional[float] = None,
        delay_ticks: Optional[int] = None,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Broadcast hormone into systemic circulation.

        If the pool doesn't exist, it is auto-registered with defaults.
        """
        if hormone not in self._pools:
            self.register_pool(hormone)

        pool = self._pools[hormone]
        if clearance_rate is not None:
            pool.clearance_rate = clearance_rate
        if delay_ticks is not None:
            pool.delay_ticks = delay_ticks

        pool.concentration = min(
            pool.max_concentration,
            pool.concentration + max(0.0, concentration),
        )
        pool.last_secretion_tick = self._current_tick
        pool.last_secretion_source = source

    def secrete_event(
        self,
        hormone: str,
        intensity: float,
        source: str = "",
        duration: int = 0,
        decay: float = 0.80,
    ) -> None:
        """Broadcast a discrete hormone event (e.g., adrenaline spike)."""
        if hormone not in self._pools:
            self.register_pool(hormone)

        pool = self._pools[hormone]
        pool.event_mode = True
        pool.event_duration = duration
        pool.event_decay = decay
        pool.event_onset_tick = self._current_tick
        pool.event_intensity = intensity
        pool.concentration = min(
            pool.max_concentration,
            pool.concentration + max(0.0, intensity),
        )
        pool.last_secretion_tick = self._current_tick
        pool.last_secretion_source = source

    def read(self, hormone: str) -> Optional[float]:
        """Read current systemic concentration."""
        pool = self._pools.get(hormone)
        return pool.concentration if pool is not None else None

    def decay_all(self) -> None:
        """Apply metabolism-based clearance to all hormones."""
        for pool in self._pools.values():
            if pool.event_mode:
                self._decay_event(pool)
            else:
                self._decay_stream(pool)

    def _decay_stream(self, pool: HormonePool) -> None:
        pool.concentration *= pool.clearance_rate
        if pool.baseline > 0.0:
            drift = (pool.baseline - pool.concentration) * 0.05
            pool.concentration += drift
        pool.concentration = max(0.0, min(pool.max_concentration, pool.concentration))

    def _decay_event(self, pool: HormonePool) -> None:
        elapsed = self._current_tick - pool.event_onset_tick
        if elapsed <= pool.event_duration:
            pool.concentration = pool.event_intensity
        else:
            pool.concentration *= pool.event_decay
            if pool.concentration < 0.01:
                pool.concentration = 0.0
                pool.event_mode = False

    def clear(self, hormone: str, amount: float = 1.0) -> None:
        """Accelerate clearance of a specific hormone."""
        if hormone in self._pools:
            pool = self._pools[hormone]
            pool.concentration = max(0.0, pool.concentration - amount)

    def snapshot(self) -> Dict[str, float]:
        """Return current hormone concentrations."""
        return {h: p.concentration for h, p in self._pools.items()}

    @property
    def active_hormones(self) -> List[str]:
        return [h for h, p in self._pools.items() if p.concentration > 0.01]
