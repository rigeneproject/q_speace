"""Stage-1 Asynchronous Global Workspace & Memory Budget Guard (T261).

Replaces hardcoded sequential orchestration with bounded ``asyncio`` coalition
competition regulated by ``dynamic_spikes`` and ``CriticalityController``
(empirical branching ratio ``sigma ~ 1.0`` over non-zero-variance spike trains),
under fail-closed ``KillSwitch`` and ``< 250 MB`` process RSS enforcement.

BCEL note (AGENTS.md §2): "Global Workspace" is strictly an asynchronous
priority-arbitration and state-broadcast scheduler; zero consciousness claims.
"""

from __future__ import annotations

import asyncio
import ctypes
import math
import sys
import tracemalloc
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np

from ..edd_cvt import InformationalLogicalField
from ..seed.constitution import SeedGenome
from ..seed.killswitch import KillSwitch
from ..spiking.criticality import CriticalityController, CriticalityRegime
from ..spiking.encoder import dynamic_spikes


class MemoryBudgetExceededError(RuntimeError):
    """Raised when process RSS breaches the configured Stage-1 RAM ceiling."""


class _ProcessMemoryCounters(ctypes.Structure):
    """Win32 ``PROCESS_MEMORY_COUNTERS`` structure for zero-dependency RSS reads."""

    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def read_process_rss_mb() -> float:
    """Return current OS process resident working set in MiB without external deps."""
    if sys.platform == "win32":
        pmc = _ProcessMemoryCounters()
        pmc.cb = ctypes.sizeof(_ProcessMemoryCounters)
        kernel32 = ctypes.windll.kernel32
        get_proc = kernel32.GetCurrentProcess
        get_proc.argtypes = []
        get_proc.restype = ctypes.c_void_p
        handle = get_proc()
        ok = 0
        try:
            get_mem = kernel32.K32GetProcessMemoryInfo
        except AttributeError:
            get_mem = ctypes.windll.psapi.GetProcessMemoryInfo
        get_mem.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(_ProcessMemoryCounters),
            ctypes.c_ulong,
        ]
        get_mem.restype = ctypes.c_int
        ok = int(get_mem(handle, ctypes.byref(pmc), pmc.cb))
        if ok:
            return float(pmc.WorkingSetSize) / (1024.0 * 1024.0)

    # T266-06: on Linux report the *current* resident set (ru_maxrss below is the peak).
    try:
        import os

        with open("/proc/self/statm", encoding="ascii") as fh:
            resident_pages = int(fh.read().split()[1])
        return float(resident_pages * os.sysconf("SC_PAGE_SIZE")) / (1024.0 * 1024.0)
    except (OSError, ValueError, IndexError, AttributeError):
        pass

    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        raw_rss = float(usage.ru_maxrss)
        if sys.platform == "darwin":
            return raw_rss / (1024.0 * 1024.0)
        return raw_rss / 1024.0
    except (ImportError, AttributeError):
        if tracemalloc.is_tracing():
            current, _peak = tracemalloc.get_traced_memory()
            return float(current) / (1024.0 * 1024.0)
        return 0.0


@dataclass(frozen=True)
class MemorySnapshot:
    """Point-in-time process memory measurement in MiB."""

    rss_mb: float
    peak_rss_mb: float
    tracemalloc_current_mb: float
    tracemalloc_peak_mb: float
    budget_mb: float


class MemoryBudgetGuard:
    """Enforces a hard process RSS ceiling (default ``250.0`` MiB) via ``KillSwitch``."""

    def __init__(
        self,
        *,
        max_rss_mb: float = 250.0,
        kill_switch: KillSwitch | None = None,
    ) -> None:
        if not math.isfinite(max_rss_mb) or max_rss_mb <= 16.0:
            raise ValueError("max_rss_mb must be finite and > 16.0 MiB")
        self.max_rss_mb = float(max_rss_mb)
        self._kill_switch = kill_switch
        self._peak_rss_mb = 0.0
        self._started_tracemalloc = False
        if not tracemalloc.is_tracing():
            tracemalloc.start()
            self._started_tracemalloc = True

    @property
    def peak_rss_mb(self) -> float:
        return self._peak_rss_mb

    def check(self, *, context_state: str = "WORKSPACE_TICK") -> MemorySnapshot:
        """Sample process RSS and trigger fail-closed halt if ``>= max_rss_mb``."""
        rss_mb = read_process_rss_mb()
        if rss_mb > self._peak_rss_mb:
            self._peak_rss_mb = rss_mb
        tm_cur, tm_peak = tracemalloc.get_traced_memory() if tracemalloc.is_tracing() else (0, 0)
        snap = MemorySnapshot(
            rss_mb=round(rss_mb, 3),
            peak_rss_mb=round(self._peak_rss_mb, 3),
            tracemalloc_current_mb=round(float(tm_cur) / (1024.0 * 1024.0), 3),
            tracemalloc_peak_mb=round(float(tm_peak) / (1024.0 * 1024.0), 3),
            budget_mb=self.max_rss_mb,
        )
        if rss_mb >= self.max_rss_mb:
            if self._kill_switch is not None and not self._kill_switch.is_extinguished:
                self._kill_switch.trigger(
                    authority="system:budget_exhaustion",
                    reason=(
                        f"process RSS {rss_mb:.2f} MiB reached Stage-1 cap "
                        f"{self.max_rss_mb:.2f} MiB"
                    ),
                    prior_state=context_state,
                    state_snapshot={"rss_mb": snap.rss_mb, "budget_mb": snap.budget_mb},
                )
            raise MemoryBudgetExceededError(
                f"Stage-1 RAM cap exceeded: {rss_mb:.2f} MiB >= {self.max_rss_mb:.2f} MiB"
            )
        return snap


@dataclass
class WorkspaceBlackboard:
    """Shared decaying broadcast state read by specialists and updated by winners."""

    tick: int = 0
    surface_facts: frozenset[str] = frozenset()
    episode_surface: frozenset[str] = frozenset()
    active_beliefs: frozenset[str] = frozenset()
    goal_facts: frozenset[str] = frozenset()
    probe_readings: dict[str, str] = field(default_factory=dict)
    failed_actions_in_state: set[str] = field(default_factory=set)
    clobbered_facts_last_step: frozenset[str] = frozenset()
    surprise: float = 0.0
    coherence_phi: float = 0.75
    last_winner: str = ""
    last_broadcast: dict[str, Any] = field(default_factory=dict)
    goal_achieved: bool = False
    halted: bool = False


@dataclass(frozen=True)
class CoalitionProposal:
    """Salience-weighted proposal emitted asynchronously by one specialist."""

    specialist_name: str
    intent: str
    salience_channels: tuple[float, float, float]
    confidence: float
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.specialist_name or not self.intent:
            raise ValueError("specialist_name and intent must be non-empty")
        if len(self.salience_channels) != 3:
            raise ValueError("salience_channels must contain exactly 3 finite floats")
        for v in self.salience_channels:
            if not math.isfinite(v) or v < 0.0:
                raise ValueError("salience_channels values must be finite and >= 0")
        if not math.isfinite(self.confidence) or not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be finite and in [0, 1]")

    @property
    def peak_salience(self) -> float:
        return float(max(self.salience_channels))


class WorkspaceSpecialist(Protocol):
    """Protocol implemented by concurrent asynchronous workspace modules."""

    @property
    def name(self) -> str: ...

    async def propose(self, board: WorkspaceBlackboard) -> CoalitionProposal: ...


@dataclass(frozen=True)
class WorkspaceTickTelemetry:
    """Per-tick telemetry of asynchronous competition and criticality control."""

    tick: int
    winner: str
    winner_intent: str
    num_spikes: int
    sparsity: float
    branching_ratio: float
    regime: CriticalityRegime
    updated_k: float
    coherence_phi: float
    rss_mb: float


@dataclass(frozen=True)
class WorkspaceTelemetrySummary:
    """Aggregate workspace telemetry verifying sigma ~ 1.0 & resource bounds."""

    total_ticks: int
    mean_branching_ratio: float
    final_branching_ratio: float
    spike_counts: tuple[int, ...]
    spike_count_variance: float
    distinct_winners: tuple[str, ...]
    winner_counts: dict[str, int]
    regime_counts: dict[str, int]
    peak_rss_mb: float
    tracemalloc_peak_mb: float
    within_critical_band: bool
    non_trivial_dynamics: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_ticks": self.total_ticks,
            "mean_branching_ratio": round(self.mean_branching_ratio, 4),
            "final_branching_ratio": round(self.final_branching_ratio, 4),
            "spike_counts": list(self.spike_counts),
            "spike_count_variance": round(self.spike_count_variance, 4),
            "distinct_winners": list(self.distinct_winners),
            "winner_counts": dict(self.winner_counts),
            "regime_counts": dict(self.regime_counts),
            "peak_rss_mb": round(self.peak_rss_mb, 3),
            "tracemalloc_peak_mb": round(self.tracemalloc_peak_mb, 3),
            "within_critical_band": self.within_critical_band,
            "non_trivial_dynamics": self.non_trivial_dynamics,
        }


def default_stage1_seed_genome() -> SeedGenome:
    """Construct immutable write-locked constitutional genome for Stage-1 sandbox."""
    return SeedGenome(
        profile_id="speace-stage1-t261",
        profile_version="1.0.0",
        autonomy_class="A5-sandbox",
        governance_roster=("human:maintainer", "operator:stage1"),
    )


class AsyncGlobalWorkspace:
    """Event-driven asynchronous specialist workspace with closed-loop criticality."""

    def __init__(
        self,
        specialists: Sequence[WorkspaceSpecialist],
        *,
        initial_k: float = 2.2,
        target_sigma: float = 1.0,
        kp: float = 0.35,
        refractory_damping: float = 0.62,
        max_rss_mb: float = 250.0,
        genome: SeedGenome | None = None,
    ) -> None:
        if len(specialists) < 2:
            raise ValueError("AsyncGlobalWorkspace requires at least 2 specialists")
        if not math.isfinite(initial_k) or initial_k <= 0.0:
            raise ValueError("initial_k must be finite and > 0")
        if not math.isfinite(refractory_damping) or not (0.1 <= refractory_damping <= 1.0):
            raise ValueError("refractory_damping must be finite and in [0.1, 1.0]")

        self._specialists: tuple[WorkspaceSpecialist, ...] = tuple(specialists)
        self.current_k = float(initial_k)
        self.refractory_damping = float(refractory_damping)
        self._genome = genome or default_stage1_seed_genome()
        self.kill_switch = KillSwitch(self._genome)
        self.memory_guard = MemoryBudgetGuard(max_rss_mb=max_rss_mb, kill_switch=self.kill_switch)
        self.criticality = CriticalityController(
            target_sigma=target_sigma,
            kp=kp,
            k_min=0.8,
            k_max=6.0,
            low_band=0.85,
            high_band=1.15,
            window=16,
        )
        self.ilf = InformationalLogicalField(q_star_ema=0.35, coherence_phi_ema=0.35)
        for sp in self._specialists:
            self.ilf.register_agent(sp.name, weight=1.0)
        self._history: list[WorkspaceTickTelemetry] = []
        self._last_mem_snap: MemorySnapshot | None = None

    @property
    def history(self) -> tuple[WorkspaceTickTelemetry, ...]:
        return tuple(self._history)

    async def step(
        self, board: WorkspaceBlackboard
    ) -> tuple[CoalitionProposal, WorkspaceTickTelemetry]:
        """Gather concurrent specialist proposals, encode spikes, arbitrate, and update ``k``."""
        if self.kill_switch.is_extinguished:
            raise RuntimeError("AsyncGlobalWorkspace halted by KillSwitch")

        mem_snap = self.memory_guard.check(context_state=f"TICK_{board.tick}")
        self._last_mem_snap = mem_snap

        proposals = list(await asyncio.gather(*(sp.propose(board) for sp in self._specialists)))

        channel_values: list[float] = []
        effective_scores: list[float] = []
        for idx, prop in enumerate(proposals):
            damping = self.refractory_damping if prop.specialist_name == board.last_winner else 1.0
            phase_mod = 1.0 + 0.06 * math.sin(0.9 * float(board.tick + 1) + 0.7 * float(idx))
            ch0, ch1, ch2 = prop.salience_channels
            eff0 = ch0 * damping * phase_mod
            eff1 = ch1 * damping
            eff2 = ch2 * (0.85 + 0.30 * min(1.0, board.surprise))
            channel_values.extend((eff0, eff1, eff2))
            spike_bonus = eff0 * (0.70 + 0.30 * prop.confidence)
            effective_scores.append(spike_bonus)

        salience_vec = np.asarray(channel_values, dtype=np.float64)
        for prop in proposals:
            self.ilf.set_belief(
                prop.specialist_name,
                np.asarray(prop.salience_channels, dtype=np.float64) + 1e-4,
            )
        self.ilf.compute_q_star()
        phi = float(np.clip(self.ilf.coherence_phi, 0.1, 1.0))

        spike_res = dynamic_spikes(
            salience_vec,
            k=self.current_k,
            coherence_phi=phi,
            beta=0.20,
        )
        crit_state = self.criticality.step(spike_res.num_spikes, self.current_k)
        self.current_k = crit_state.updated_k

        # Weight each specialist's score by its local spike count + salience tie-breaker
        best_idx = 0
        best_rank = -1.0
        for idx, score in enumerate(effective_scores):
            local_spikes = float(np.sum(np.abs(spike_res.spikes[3 * idx : 3 * idx + 3])))
            rank = score * (1.0 + 0.35 * local_spikes)
            if rank > best_rank:
                best_rank = rank
                best_idx = idx

        winner = proposals[best_idx]
        board.coherence_phi = phi
        board.last_winner = winner.specialist_name
        board.last_broadcast = {
            "winner": winner.specialist_name,
            "intent": winner.intent,
            "payload": dict(winner.payload),
            "tick": board.tick,
        }

        tel = WorkspaceTickTelemetry(
            tick=board.tick,
            winner=winner.specialist_name,
            winner_intent=winner.intent,
            num_spikes=spike_res.num_spikes,
            sparsity=spike_res.sparsity,
            branching_ratio=crit_state.branching_ratio,
            regime=crit_state.regime,
            updated_k=crit_state.updated_k,
            coherence_phi=phi,
            rss_mb=mem_snap.rss_mb,
        )
        self._history.append(tel)
        board.tick += 1
        return winner, tel

    def summarize_telemetry(self) -> WorkspaceTelemetrySummary:
        """Aggregate recorded workspace telemetry across all executed ticks."""
        if not self._history:
            return WorkspaceTelemetrySummary(
                total_ticks=0,
                mean_branching_ratio=1.0,
                final_branching_ratio=1.0,
                spike_counts=(),
                spike_count_variance=0.0,
                distinct_winners=(),
                winner_counts={},
                regime_counts={},
                peak_rss_mb=self.memory_guard.peak_rss_mb,
                tracemalloc_peak_mb=(
                    self._last_mem_snap.tracemalloc_peak_mb
                    if self._last_mem_snap is not None
                    else 0.0
                ),
                within_critical_band=True,
                non_trivial_dynamics=False,
            )

        sigmas = [h.branching_ratio for i, h in enumerate(self._history) if i >= 1] or [
            self._history[0].branching_ratio
        ]
        mean_sigma = float(sum(sigmas) / len(sigmas))
        final_sigma = self._history[-1].branching_ratio
        counts = tuple(h.num_spikes for h in self._history)
        var_spikes = float(np.var(np.asarray(counts, dtype=np.float64)))
        win_counter = Counter(h.winner for h in self._history)
        reg_counter = Counter(h.regime for h in self._history)
        distinct = tuple(dict.fromkeys(h.winner for h in self._history))
        tm_peak = (
            self._last_mem_snap.tracemalloc_peak_mb if self._last_mem_snap is not None else 0.0
        )

        return WorkspaceTelemetrySummary(
            total_ticks=len(self._history),
            mean_branching_ratio=mean_sigma,
            final_branching_ratio=final_sigma,
            spike_counts=counts,
            spike_count_variance=var_spikes,
            distinct_winners=distinct,
            winner_counts=dict(win_counter),
            regime_counts={str(k): int(v) for k, v in reg_counter.items()},
            peak_rss_mb=self.memory_guard.peak_rss_mb,
            tracemalloc_peak_mb=tm_peak,
            within_critical_band=(0.85 <= mean_sigma <= 1.15),
            non_trivial_dynamics=(var_spikes > 0.0 and len(distinct) >= 3),
        )
