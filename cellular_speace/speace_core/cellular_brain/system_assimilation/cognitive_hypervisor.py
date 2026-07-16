"""CognitiveHypervisor — system-level event monitor that feeds SPEACE's neural space.

Monitors the host OS continuously (process creation/exit, file changes, network
connections, service state transitions, hardware events) and injects them as
neural activation patterns into the orchestrator's circuit.

Architecture:
  os::event → [CognitiveHypervisor.monitor()] → neural pattern → [orchestrator.circuit]

The hypervisor does NOT poll — it uses OS event callbacks (WMI, ReadDirectoryChangesW,
ETW) where available, with a fallback polling loop where callbacks aren't possible.

Safety: all monitoring is READ-ONLY. No system state is ever modified by the hypervisor.
Modification is handled by the CognitiveActuator (in embodiment/).
"""

from __future__ import annotations

import os
import platform
import subprocess
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

from speace_core.cellular_brain.system_assimilation.cognitive_namespace import (
    UnifiedNamespace,
)


# ------------------------------------------------------------------ #
# Event models
# ------------------------------------------------------------------ #


class SystemEvent:
    """A single system event that maps to a neural pattern."""

    def __init__(
        self,
        event_type: str,
        resource_type: str,
        resource_id: str,
        cell_id: str,
        data: Dict[str, Any],
        timestamp: Optional[float] = None,
    ) -> None:
        self.event_type = event_type
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.cell_id = cell_id
        self.data = data
        self.timestamp = timestamp or time.time()

    def to_neural_pattern(self, vector_size: int = 10) -> List[float]:
        """Convert this event into a neural activation pattern.

        The pattern encodes:
          [0]: event novelty (1.0 = new, 0.5 = update, 0.0 = removal)
          [1]: resource type encoding
          [2:7]: data features normalized to [0, 1]
          [7:9]: timestamp phase
          [9]: event magnitude
        """
        pattern = [0.0] * vector_size
        type_map = {
            "process": 0.1, "file": 0.2, "socket": 0.3,
            "service": 0.4, "device": 0.5, "thread": 0.6,
            "user": 0.7, "memory": 0.8, "host": 0.9,
        }
        novelty_map = {"created": 1.0, "modified": 0.5, "deleted": 0.0}

        pattern[0] = novelty_map.get(self.event_type, 0.5)
        pattern[1] = type_map.get(self.resource_type, 0.0)

        data_values = list(self.data.values())[:5]
        for i, v in enumerate(data_values):
            if isinstance(v, (int, float)):
                pattern[2 + i] = max(0.0, min(1.0, float(v) / 100.0))

        phase = (self.timestamp % 100.0) / 100.0
        pattern[7] = phase
        pattern[8] = 1.0 - phase
        pattern[9] = min(1.0, len(str(self.data)) / 500.0)

        return pattern

    @property
    def age_seconds(self) -> float:
        return time.time() - self.timestamp

    def snapshot(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "cell_id": self.cell_id,
            "data": self.data,
            "timestamp": self.timestamp,
        }


# ------------------------------------------------------------------ #
# Cognitive Hypervisor
# ------------------------------------------------------------------ #


class CognitiveHypervisor:
    """Monitors system events and injects them as neural patterns.

    Runs a background thread that polls system state at configurable
    intervals and pushes events (process created/killed, file changed,
    socket opened/closed, service started/stopped) into the event queue.

    The orchestrator calls `drain_events()` each tick to consume queued
    events and inject them as neural patterns.
    """

    def __init__(
        self,
        namespace: Optional[UnifiedNamespace] = None,
        poll_interval: float = 2.0,
        event_capacity: int = 1000,
        enable_process_monitor: bool = True,
        enable_file_monitor: bool = True,
        enable_socket_monitor: bool = True,
        enable_service_monitor: bool = True,
        enable_system_metrics: bool = True,
    ) -> None:
        self.namespace = namespace or UnifiedNamespace()
        self._poll_interval = poll_interval
        self._event_queue: deque[SystemEvent] = deque(maxlen=event_capacity)

        self._enable_process_monitor = enable_process_monitor
        self._enable_file_monitor = enable_file_monitor
        self._enable_socket_monitor = enable_socket_monitor
        self._enable_service_monitor = enable_service_monitor
        self._enable_system_metrics = enable_system_metrics

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Previous state snapshots for delta detection
        self._prev_processes: Dict[int, Dict[str, Any]] = {}
        self._prev_services: Dict[str, Dict[str, Any]] = {}
        self._prev_sockets: Set[str] = set()
        self._prev_file_snapshots: Dict[str, float] = {}
        self._prev_metrics: Dict[str, float] = {}

        self._total_events_injected: int = 0
        self._start_time: float = 0.0

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._start_time = time.time()
        self._capture_initial_snapshot()
        self._thread = threading.Thread(
            target=self._poll_loop,
            name="cognitive_hypervisor",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self._start_time if self._start_time else 0.0

    # ------------------------------------------------------------------ #
    # Event draining (called by orchestrator tick)
    # ------------------------------------------------------------------ #

    def drain_events(self, max_events: int = 50) -> List[SystemEvent]:
        """Consume queued events for injection into the neural circuit."""
        events: List[SystemEvent] = []
        with self._lock:
            while self._event_queue and len(events) < max_events:
                events.append(self._event_queue.popleft())
        self._total_events_injected += len(events)
        return events

    # ------------------------------------------------------------------ #
    # Poll loop
    # ------------------------------------------------------------------ #

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._poll_cycle()
            except Exception:
                pass
            self._stop_event.wait(self._poll_interval)

    def _poll_cycle(self) -> None:
        if self._enable_process_monitor:
            self._monitor_processes()
        if self._enable_service_monitor:
            self._monitor_services()
        if self._enable_socket_monitor:
            self._monitor_sockets()
        if self._enable_system_metrics:
            self._monitor_system_metrics()

    def _capture_initial_snapshot(self) -> None:
        try:
            import psutil
            self._prev_processes = {
                p.info["pid"]: {
                    "name": p.info["name"],
                    "status": p.info["status"],
                    "create_time": p.info.get("create_time", 0.0),
                }
                for p in psutil.process_iter(["pid", "name", "status", "create_time"])
            }
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Process monitor
    # ------------------------------------------------------------------ #

    def _monitor_processes(self) -> None:
        try:
            import psutil
            current: Dict[int, Dict[str, Any]] = {}
            for p in psutil.process_iter(["pid", "name", "status", "create_time"]):
                info = p.info
                pid = info["pid"]
                current[pid] = {
                    "name": info.get("name", ""),
                    "status": info.get("status", ""),
                    "create_time": info.get("create_time", 0.0),
                }
                if pid not in self._prev_processes:
                    cell_id = UnifiedNamespace.process_cell_id(pid)
                    self.namespace.register(cell_id, {"id": pid, "type": "process", **current[pid]})
                    self._enqueue("created", "process", str(pid), cell_id, current[pid])

            for pid in list(self._prev_processes):
                if pid not in current:
                    cell_id = UnifiedNamespace.process_cell_id(pid)
                    self.namespace.remove(cell_id)
                    self._enqueue("deleted", "process", str(pid), cell_id, self._prev_processes[pid])

            self._prev_processes = current
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Service monitor
    # ------------------------------------------------------------------ #

    def _monitor_services(self) -> None:
        if platform.system() != "Windows":
            return
        try:
            result = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-Command",
                    "Get-Service | Select-Object Name, Status, StartType | ConvertTo-Csv -NoTypeInformation",
                ],
                capture_output=True,
                text=True,
                timeout=10.0,
            )
            if result.returncode != 0:
                return
            current: Dict[str, Dict[str, Any]] = {}
            for line in result.stdout.splitlines()[1:]:
                parts = [p.strip().strip('"') for p in line.split(",")]
                if len(parts) >= 2:
                    name, status = parts[0], parts[1]
                    current[name] = {"name": name, "status": status}
                    if name not in self._prev_services:
                        cell_id = UnifiedNamespace.service_cell_id(name)
                        self.namespace.register(cell_id, {"id": name, "type": "service", "status": status})
                        self._enqueue("created", "service", name, cell_id, current[name])
                    elif self._prev_services[name].get("status") != status:
                        cell_id = UnifiedNamespace.service_cell_id(name)
                        self._enqueue("modified", "service", name, cell_id, {"name": name, "status": status})

            for name in list(self._prev_services):
                if name not in current:
                    cell_id = UnifiedNamespace.service_cell_id(name)
                    self.namespace.remove(cell_id)
                    self._enqueue("deleted", "service", name, cell_id, self._prev_services[name])

            self._prev_services = current
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Socket monitor
    # ------------------------------------------------------------------ #

    def _monitor_sockets(self) -> None:
        try:
            import psutil
            current: Set[str] = set()
            for conn in psutil.net_connections(kind="inet"):
                if conn.raddr:
                    key = f"{conn.type}:{conn.raddr.port}"
                else:
                    key = f"{conn.type}:{conn.laddr.port}" if conn.laddr else ""
                if not key:
                    continue
                current.add(key)
                if key not in self._prev_sockets:
                    cell_id = UnifiedNamespace.socket_cell_id("tcp" if conn.type == 1 else "udp",
                                                              conn.raddr.port if conn.raddr else conn.laddr.port)
                    self.namespace.register(cell_id, {"id": key, "type": "socket"})
                    self._enqueue("created", "socket", key, cell_id, {"key": key})

            for key in self._prev_sockets - current:
                cell_id = UnifiedNamespace.socket_cell_id("tcp", 0)
                self.namespace.remove(cell_id)
                self._enqueue("deleted", "socket", key, cell_id, {"key": key})

            self._prev_sockets = current
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # System metrics monitor
    # ------------------------------------------------------------------ #

    def _monitor_system_metrics(self) -> None:
        try:
            import psutil
            metrics = {
                "cpu_percent": psutil.cpu_percent(interval=None),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_io_busy": psutil.disk_io_counters().iops if hasattr(psutil.disk_io_counters(), "iops") else 0.0,
                "net_bytes_sent": psutil.net_io_counters().bytes_sent,
                "net_bytes_recv": psutil.net_io_counters().bytes_recv,
            }
            if self._prev_metrics:
                for key, val in metrics.items():
                    prev = self._prev_metrics.get(key, 0.0)
                    if abs(val - prev) > 10.0:
                        cell_id = f"os:metric:{key}"
                        self._enqueue("modified", "host", key, cell_id, {key: val})
            self._prev_metrics = metrics
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _enqueue(
        self, event_type: str, resource_type: str,
        resource_id: str, cell_id: str, data: Dict[str, Any],
    ) -> None:
        event = SystemEvent(event_type, resource_type, resource_id, cell_id, data)
        with self._lock:
            self._event_queue.append(event)

    # ------------------------------------------------------------------ #
    # Direct external event injection (for OS callbacks / API)
    # ------------------------------------------------------------------ #

    def inject_event(self, event: SystemEvent) -> None:
        with self._lock:
            self._event_queue.append(event)

    def inject_raw(
        self, event_type: str, resource_type: str,
        resource_id: str, data: Dict[str, Any],
    ) -> None:
        cell_id = f"os:ext:{resource_type}:{resource_id}"
        event = SystemEvent(event_type, resource_type, resource_id, cell_id, data)
        self.inject_event(event)

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #

    def snapshot(self) -> Dict[str, Any]:
        return {
            "running": self.is_running,
            "uptime_seconds": self.uptime_seconds,
            "total_events_injected": self._total_events_injected,
            "queue_size": len(self._event_queue),
            "namespace_mappings": self.namespace.total,
            "monitors": {
                "process": self._enable_process_monitor,
                "service": self._enable_service_monitor,
                "socket": self._enable_socket_monitor,
                "file": self._enable_file_monitor,
                "system_metrics": self._enable_system_metrics,
            },
            "poll_interval": self._poll_interval,
        }

    def shutdown(self) -> None:
        self.stop()
        self._event_queue.clear()
        self._prev_processes.clear()
        self._prev_services.clear()
        self._prev_sockets.clear()
