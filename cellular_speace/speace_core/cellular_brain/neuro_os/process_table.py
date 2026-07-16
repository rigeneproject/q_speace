"""ProcessTable — cognitive agent/process lifecycle management for Neuro-OS.

Each cognitive process (agent, module, subroutine) is tracked with:
  - State: RUNNING, SLEEPING, BLOCKED, ZOMBIE, TERMINATED
  - Resource budget: energy, ticks, memory
  - Watchdog: max inactive ticks before forced termination
  - Priority boost from CognitiveScheduler
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ProcessState(str, Enum):
    RUNNING = "running"
    SLEEPING = "sleeping"
    BLOCKED = "blocked"
    ZOMBIE = "zombie"
    TERMINATED = "terminated"


@dataclass
class ResourceBudget:
    """Resource limits for a cognitive process."""
    max_energy_per_tick: float = 0.1
    max_ticks_before_yield: int = 50
    max_memory_mb: float = 100.0
    max_inactive_ticks: int = 500

    def snapshot(self) -> Dict[str, Any]:
        return {
            "max_energy_per_tick": self.max_energy_per_tick,
            "max_ticks_before_yield": self.max_ticks_before_yield,
            "max_memory_mb": self.max_memory_mb,
            "max_inactive_ticks": self.max_inactive_ticks,
        }


@dataclass
class ResourceUsage:
    """Current resource consumption of a process."""
    energy_consumed: float = 0.0
    ticks_executed: int = 0
    ticks_inactive: int = 0
    estimated_memory_mb: float = 0.0

    def snapshot(self) -> Dict[str, Any]:
        return {
            "energy_consumed": self.energy_consumed,
            "ticks_executed": self.ticks_executed,
            "ticks_inactive": self.ticks_inactive,
            "estimated_memory_mb": self.estimated_memory_mb,
        }


@dataclass
class ProcessEntry:
    """A cognitive process tracked by the ProcessTable."""
    process_id: str
    name: str
    category: str
    state: ProcessState = ProcessState.RUNNING
    callable_fn: Optional[Callable[[Any], Any]] = None
    budget: ResourceBudget = field(default_factory=ResourceBudget)
    usage: ResourceUsage = field(default_factory=ResourceUsage)
    priority: float = 0.5
    created_at: float = field(default_factory=time.time)
    last_active_tick: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_alive(self) -> bool:
        return self.state not in (ProcessState.ZOMBIE, ProcessState.TERMINATED)

    @property
    def is_active(self) -> bool:
        return self.state == ProcessState.RUNNING

    def snapshot(self) -> Dict[str, Any]:
        return {
            "process_id": self.process_id,
            "name": self.name,
            "category": self.category,
            "state": self.state.value,
            "priority": self.priority,
            "budget": self.budget.snapshot(),
            "usage": self.usage.snapshot(),
            "created_at": self.created_at,
            "last_active_tick": self.last_active_tick,
            "alive": self.is_alive,
            "active": self.is_active,
        }


class ProcessTable:
    """Tracks lifecycle and resource usage of cognitive processes (agents).

    Analogue to an OS process table but for cognitive agents:
      - State machine: RUNNING -> SLEEPING/BLOCKED -> ZOMBIE -> TERMINATED
      - Resource budgeting: prevents any single agent from starving the system
      - Watchdog: processes inactive too long are killed
      - Priority: can be updated by CognitiveScheduler each tick
    """

    def __init__(
        self,
        max_processes: int = 50,
        watchdog_ticks: int = 1000,
    ) -> None:
        self._processes: Dict[str, ProcessEntry] = {}
        self._max_processes = max_processes
        self._watchdog_ticks = watchdog_ticks
        self._terminated_history: List[ProcessEntry] = []
        self._max_history: int = 100

    # ------------------------------------------------------------------ #
    # Registration
    # ------------------------------------------------------------------ #

    def spawn(
        self,
        process_id: str,
        name: str,
        category: str = "agent",
        callable_fn: Optional[Callable[[Any], Any]] = None,
        priority: float = 0.5,
        budget: Optional[ResourceBudget] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProcessEntry:
        """Register a new cognitive process."""
        if process_id in self._processes:
            raise ValueError(f"Process already exists: {process_id}")
        if len(self._processes) >= self._max_processes:
            raise RuntimeError(f"Process table full ({self._max_processes})")

        entry = ProcessEntry(
            process_id=process_id,
            name=name,
            category=category,
            state=ProcessState.RUNNING,
            callable_fn=callable_fn,
            budget=budget or ResourceBudget(),
            priority=priority,
            metadata=metadata or {},
        )
        self._processes[process_id] = entry
        return entry

    def kill(self, process_id: str, reason: str = "manual") -> None:
        """Mark a process as ZOMBIE; it will be reaped later."""
        entry = self._processes.get(process_id)
        if entry is None:
            return
        entry.state = ProcessState.ZOMBIE
        entry.metadata["kill_reason"] = reason
        entry.metadata["killed_at_tick"] = time.time()

    def reap(self, process_id: str) -> Optional[ProcessEntry]:
        """Remove a ZOMBIE process and archive it."""
        entry = self._processes.pop(process_id, None)
        if entry and entry.state == ProcessState.ZOMBIE:
            entry.state = ProcessState.TERMINATED
            self._terminated_history.append(entry)
            if len(self._terminated_history) > self._max_history:
                self._terminated_history.pop(0)
            return entry
        if entry:
            self._processes[process_id] = entry
        return None

    # ------------------------------------------------------------------ #
    # Tick
    # ------------------------------------------------------------------ #

    def tick(self, current_tick: int) -> Dict[str, Any]:
        """Update all process states. Returns cleanup actions."""
        cleanup: Dict[str, Any] = {"killed": [], "reaped": []}

        for pid, entry in list(self._processes.items()):
            # Update inactive tick counter
            if entry.last_active_tick < current_tick:
                entry.usage.ticks_inactive += 1

            # Watchdog: kill processes inactive too long
            if (
                entry.is_alive
                and entry.usage.ticks_inactive > entry.budget.max_inactive_ticks
            ):
                self.kill(pid, reason="watchdog_timeout")
                cleanup["killed"].append(pid)

            # Budget check: kill processes that exceeded energy
            if (
                entry.is_alive
                and entry.usage.energy_consumed > 10.0  # arbitrary cap
            ):
                self.kill(pid, reason="energy_overuse")
                if pid not in cleanup["killed"]:
                    cleanup["killed"].append(pid)

            # Reap zombies
            if entry.state == ProcessState.ZOMBIE:
                reaped = self.reap(pid)
                if reaped:
                    cleanup["reaped"].append(pid)

        return cleanup

    def record_activity(
        self,
        process_id: str,
        tick: int,
        energy_delta: float = 0.0,
    ) -> None:
        """Record that a process executed and consumed resources."""
        entry = self._processes.get(process_id)
        if entry is None:
            return
        entry.usage.ticks_executed += 1
        entry.usage.energy_consumed += energy_delta
        entry.last_active_tick = tick
        entry.usage.ticks_inactive = 0

    # ------------------------------------------------------------------ #
    # State transitions
    # ------------------------------------------------------------------ #

    def set_state(self, process_id: str, state: ProcessState) -> bool:
        entry = self._processes.get(process_id)
        if entry is None:
            return False
        entry.state = state
        return True

    def set_priority(self, process_id: str, priority: float) -> None:
        entry = self._processes.get(process_id)
        if entry is not None:
            entry.priority = max(0.0, min(1.0, priority))

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #

    def get(self, process_id: str) -> Optional[ProcessEntry]:
        return self._processes.get(process_id)

    def list_processes(
        self,
        state: Optional[ProcessState] = None,
        category: Optional[str] = None,
    ) -> List[ProcessEntry]:
        result = list(self._processes.values())
        if state:
            result = [p for p in result if p.state == state]
        if category:
            result = [p for p in result if p.category == category]
        return result

    @property
    def alive_count(self) -> int:
        return sum(1 for p in self._processes.values() if p.is_alive)

    @property
    def running_count(self) -> int:
        return sum(1 for p in self._processes.values() if p.is_active)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "total_processes": len(self._processes),
            "alive": self.alive_count,
            "running": self.running_count,
            "terminated_history": len(self._terminated_history),
            "max_processes": self._max_processes,
            "processes": [
                p.snapshot() for p in sorted(
                    self._processes.values(),
                    key=lambda x: x.priority,
                    reverse=True,
                )[:20]
            ],
            "recently_terminated": [
                p.snapshot() for p in self._terminated_history[-10:]
            ],
        }

    def shutdown(self) -> None:
        """Terminate all running processes."""
        for pid in list(self._processes.keys()):
            self.kill(pid, reason="system_shutdown")
            self.reap(pid)
        self._terminated_history.clear()
