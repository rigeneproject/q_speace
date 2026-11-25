"""Fail-closed SimulatedSensorAdapter & deadlock-free async bridge isolator (T249-06).

Synthesized via BCEL from ``cellular_speace_docker`` (``simulated_sensor_adapter.py``)
and ``cellular_speace_gpt`` (``_run_async_bridge_generate``):
- "Stage-2.5 organism test body" prose is *accidental* and removed.
- Strict opt-in ``runtime_mode in {None, "simulated"}`` deterministic telemetry
  with seeded anomaly injection, append-only JSONL audit logging (aligned with
  ``docs/T217_SAFE_ASSIMILATION_LIFECYCLE_SPEC.md``), and thread-isolated
  sync-to-async execution safe inside active event loops survive.
"""

from __future__ import annotations

import asyncio
import json
import math
import threading
from collections.abc import Callable, Coroutine
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

VALID_RUNTIME_MODES: frozenset[str | None] = frozenset({None, "simulated"})


@dataclass(frozen=True)
class SimulatedSensorReading:
    """Deterministic synthetic host/environment telemetry record (no OS/hardware I/O)."""

    tick: int
    cpu_load: float
    memory_pressure: float
    thermal_ratio: float
    em_quality: float
    anomaly_injected: bool
    simulated: bool = True

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class SimulatedSensorAdapter:
    """Deterministic T217 Stage-2.5 sensor twin with optional JSONL audit logging."""

    def __init__(
        self,
        *,
        runtime_mode: str | None = "simulated",
        seed: int = 42,
        anomaly_rate: float = 0.05,
        audit_log_path: Path | None = None,
    ) -> None:
        if runtime_mode not in VALID_RUNTIME_MODES:
            raise ValueError(
                f"unsupported runtime_mode {runtime_mode!r}; allowed: None or 'simulated'"
            )
        if not math.isfinite(anomaly_rate) or not (0.0 <= anomaly_rate <= 1.0):
            raise ValueError("anomaly_rate must be finite and in [0, 1]")
        self.runtime_mode = runtime_mode
        self.seed = seed
        self.anomaly_rate = float(anomaly_rate)
        self.audit_log_path = audit_log_path
        self._rng = np.random.default_rng(seed)
        self._tick = 0

    @property
    def enabled(self) -> bool:
        return self.runtime_mode == "simulated"

    def read(self) -> SimulatedSensorReading:
        """Produce one seeded synthetic reading; fails closed if ``runtime_mode`` is None."""
        if not self.enabled:
            raise RuntimeError("SimulatedSensorAdapter is disabled (runtime_mode is None)")

        t = self._tick
        self._tick += 1
        anomaly = bool(self._rng.random() < self.anomaly_rate)

        base_cpu = 0.35 + 0.15 * math.sin(t / 5.0) + float(self._rng.normal(0.0, 0.02))
        base_mem = 0.45 + 0.10 * math.cos(t / 8.0) + float(self._rng.normal(0.0, 0.015))
        base_thm = 0.40 + 0.12 * math.sin(t / 6.0)
        base_em = 0.88 - 0.05 * abs(math.sin(t / 7.0))

        if anomaly:
            base_cpu = min(1.0, base_cpu + 0.45)
            base_thm = min(1.0, base_thm + 0.40)
            base_em = max(0.0, base_em - 0.50)

        reading = SimulatedSensorReading(
            tick=t,
            cpu_load=float(np.clip(base_cpu, 0.0, 1.0)),
            memory_pressure=float(np.clip(base_mem, 0.0, 1.0)),
            thermal_ratio=float(np.clip(base_thm, 0.0, 1.0)),
            em_quality=float(np.clip(base_em, 0.0, 1.0)),
            anomaly_injected=anomaly,
        )

        if self.audit_log_path is not None:
            self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.audit_log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(reading.to_dict(), sort_keys=True, allow_nan=False) + "\n")

        return reading


def run_coro_isolated[T](
    coro_factory: Callable[[], Coroutine[Any, Any, T]],
    *,
    timeout_s: float = 10.0,
) -> T:
    """Execute an async coroutine safely from synchronous code even inside a running event loop."""
    if not math.isfinite(timeout_s) or timeout_s <= 0.0:
        raise ValueError("timeout_s must be finite and > 0")

    async def _bounded() -> T:
        return await asyncio.wait_for(coro_factory(), timeout=timeout_s)

    try:
        asyncio.get_running_loop()
        loop_running = True
    except RuntimeError:
        loop_running = False

    if not loop_running:
        return asyncio.run(_bounded())

    box_result: list[T] = []
    box_error: list[BaseException] = []

    def _worker() -> None:
        try:
            box_result.append(asyncio.run(_bounded()))
        except BaseException as exc:
            box_error.append(exc)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(timeout=timeout_s + 1.0)
    if thread.is_alive():
        raise TimeoutError(f"isolated coroutine worker exceeded {timeout_s}s")
    if box_error:
        raise box_error[0]
    return box_result[0]
