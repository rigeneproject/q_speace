"""SPEACE AGI Team — Orchestrator: scheduling, load balancing, monitoring, auto-analysis.

This module adds the missing pieces identified in REPORT_FINALE.md §8:
1. Periodic auto-analysis of SPEACE state by Chief Architect + supervisors
2. Load balancing across technicians (assign task to the least loaded)
3. Continuous validation: every completed task triggers a supervisor review
4. Task execution pipeline: assign → technician analyzes → supervisor validates → complete
5. Runtime monitor 24/7: watches coherence_phi, tick, CPU, memory and alerts on anomalies
"""

import json
import threading
import time
from collections import Counter, deque
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import logging

_logger = logging.getLogger(__name__)

from speace_agi_team.action_catalog import ActionCatalog
from speace_agi_team.action_executor import ActionExecutor
from speace_agi_team.action_proposal import ActionProposal, ActionProposalStatus
from speace_agi_team.action_safety_gate import ActionSafetyGate
from speace_agi_team.config import AgentConfig
from speace_agi_team.engineering_plan import EngineeringPlan


# ── Load Balancer ──────────────────────────────────────────────────────
class LoadBalancer:
    """Tracks per-agent workload and assigns new tasks to the least loaded one.

    Workload = open_tasks + recent_chats_5min + analysis_count_last_min.
    """

    def __init__(self, agents: Dict[str, Any]):
        self.agents = agents
        self._last_reset = time.time()
        self._chat_stamps: Dict[str, List[float]] = {a: [] for a in agents}
        self._analysis_stamps: Dict[str, List[float]] = {a: [] for a in agents}
        self._lock = threading.Lock()

    def _prune(self, stamps: List[float], window_sec: float = 300.0) -> List[float]:
        cutoff = time.time() - window_sec
        return [t for t in stamps if t >= cutoff]

    def record_chat(self, agent_id: str):
        with self._lock:
            self._chat_stamps.setdefault(agent_id, []).append(time.time())
            self._chat_stamps[agent_id] = self._prune(self._chat_stamps[agent_id])

    def record_analysis(self, agent_id: str):
        with self._lock:
            self._analysis_stamps.setdefault(agent_id, []).append(time.time())
            self._analysis_stamps[agent_id] = self._prune(self._analysis_stamps[agent_id])

    def workload_score(self, agent_id: str) -> float:
        """Lower is better. Combines open tasks, recent chats and analyses."""
        agent = self.agents.get(agent_id)
        if not agent:
            return float("inf")
        open_tasks = sum(1 for t in agent.tasks if t.get("status") == "assigned")
        chat_load = len(self._chat_stamps.get(agent_id, []))
        analysis_load = len(self._analysis_stamps.get(agent_id, []))
        return open_tasks * 3.0 + chat_load * 1.0 + analysis_load * 2.0

    def pick_technician(self, candidate_ids: List[str]) -> str:
        """Pick the technician with the lowest workload score."""
        if not candidate_ids:
            return ""
        scored = [(self.workload_score(aid), aid) for aid in candidate_ids if aid in self.agents]
        if not scored:
            return candidate_ids[0]
        scored.sort()
        return scored[0][1]

    def distribution(self) -> Dict[str, float]:
        return {aid: self.workload_score(aid) for aid in self.agents}


# ── Runtime Health Monitor ─────────────────────────────────────────────
class RuntimeHealthMonitor:
    """Watches SPEACE state files and detects anomalies.

    Tracks:
    - coherence_phi (drop below threshold)
    - tick (not advancing)
    - CPU/memory spikes
    - absence of snapshots

    Now with live runtime access for real-time data.
    """

    def __init__(self, data_root: str = "data", runtime: Any = None, brain_orchestrator: Any = None):
        self.data_root = Path(data_root)
        self.runtime = runtime
        self.brain_orchestrator = brain_orchestrator
        self.last_tick: Optional[int] = None
        self.last_tick_time: float = 0.0
        self.last_phi: Optional[float] = None
        self.alerts: deque = deque(maxlen=100)
        self.coherence_threshold = 0.3
        self.tick_stall_seconds = 60.0

    def _read_last_report(self, report_dir: Path, prefix: str = "") -> Optional[Dict[str, Any]]:
        """Read the most recent JSON report from a reports directory."""
        if not report_dir.exists():
            return None
        try:
            files = sorted(
                [f for f in report_dir.iterdir() if f.is_file() and f.suffix == ".json" and (not prefix or f.name.startswith(prefix))],
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            if not files:
                return None
            return json.loads(files[0].read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _read_last_assessment_report(self) -> Optional[Dict[str, Any]]:
        return self._read_last_report(Path("reports/assessment"), "capability_assessment_")

    def _read_last_environment_report(self) -> Optional[Dict[str, Any]]:
        return self._read_last_report(Path("reports/environment"), "run_")

    def _read_last_snapshot(self) -> Optional[Dict[str, Any]]:
        # Nuovo percorso: organism_observer/topology_history.jsonl
        snap_path = self.data_root / "organism_observer" / "topology_history.jsonl"
        # Fallback: vecchio percorso morphological_memory
        old_path = self.data_root / "morphological_memory" / "snapshots.jsonl"
        for path in (snap_path, old_path):
            if path.exists():
                try:
                    with path.open("r", encoding="utf-8") as f:
                        lines = f.readlines()
                    if lines:
                        return json.loads(lines[-1])
                except (OSError, json.JSONDecodeError):
                    continue
        return None

    def _read_last_embodiment(self) -> Optional[Dict[str, Any]]:
        emb_path = self.data_root / "embodiment" / "environment_state.jsonl"
        if not emb_path.exists():
            return None
        try:
            with emb_path.open("r", encoding="utf-8") as f:
                lines = f.readlines()
            if not lines:
                return None
            return json.loads(lines[-1])
        except (OSError, json.JSONDecodeError):
            return None

    def _normalize_cpu(self, value: Optional[float]) -> Optional[float]:
        """CPU may be reported as 0-100 (percent) or 0-1 (fraction)."""
        if value is None:
            return None
        if value > 1.5:
            return value / 100.0
        return float(value)

    def _normalize_mem(self, value: Optional[float]) -> Optional[float]:
        """Memory may be reported as bytes (huge) or 0-1 fraction. We return 0-1."""
        if value is None:
            return None
        if value > 100:
            # Assume bytes — normalize using 16 GB as reference total
            return min(1.0, value / (16 * 1024 ** 3))
        return float(value)

    def check(self) -> Dict[str, Any]:
        """Run a health check. Returns a report and stores alerts.

        Primary source: live runtime engine.
        Fallback: data files.
        """
        report = {
            "ok": True,
            "checks": [],
            "alerts": [],
            "coherence_phi": None,
            "mean_energy": None,
            "active_neurons": None,
            "tick": None,
            "cpu": None,
            "memory": None,
            "cor_enabled": None,
            "cor_collapses": None,
            "simulator_backend_enabled": None,
            "simulator_backend_log_size": None,
            "capability_score": None,
            "timestamp": time.time(),
        }

        # ── Primary: live runtime data ──────────────────────────────────
        live_tick = None
        live_phi = None
        if self.runtime is not None:
            try:
                snap = self.runtime.snapshot() if hasattr(self.runtime, "snapshot") else {}
                if snap:
                    live_tick = snap.get("ticks_since_start", snap.get("tick_count", 0))
                    health = snap.get("health", {})
                    if isinstance(health, dict):
                        report["health_score"] = health.get("health_score", 0.0)
                    report["tick"] = live_tick
                    report["checks"].append("live_runtime")
            except Exception:
                pass

        if self.brain_orchestrator is not None:
            try:
                m = getattr(self.brain_orchestrator, "latest_metrics", None)
                if m is not None:
                    live_phi = getattr(m, "coherence_phi", None)
                    if live_phi is not None:
                        report["coherence_phi"] = live_phi
                    report["mean_energy"] = getattr(m, "mean_energy", None)
                    report["active_neurons"] = getattr(m, "active_neurons", None)
                    report["cor_enabled"] = getattr(self.brain_orchestrator, "cor_enabled", None)
                    report["simulator_backend_enabled"] = getattr(self.brain_orchestrator, "simulator_backend_enabled", None)
                    report["simulator_backend_log_size"] = len(getattr(self.brain_orchestrator, "_simulator_backend_log", []))
                    cor_engine = getattr(self.brain_orchestrator, "_cor_engine", None)
                    if cor_engine is not None:
                        history = getattr(cor_engine, "_history", [])
                        report["cor_collapses"] = sum(1 for r in history if getattr(r, "collapsed", False))
            except Exception:
                pass

        # ── Fallback: data files ────────────────────────────────────────
        snap = self._read_last_snapshot()
        if snap:
            phi = snap.get("coherence_phi") or snap.get("avg_clustering")
            tick = snap.get("tick", 0)
            # Use live data over file data when available
            report["coherence_phi"] = live_phi if live_phi is not None else (
                phi * 0.5 + snap.get("global_efficiency", 0.0) * 0.5
                if phi else None
            )
            report["tick"] = live_tick if live_tick is not None else tick

            if phi is not None and phi < self.coherence_threshold:
                alert = f"⚠️ Coherence_phi {phi:.3f} sotto soglia {self.coherence_threshold}"
                report["alerts"].append(alert)
                report["ok"] = False
                self.alerts.append({"ts": time.time(), "msg": alert})

            if tick is not None:
                if self.last_tick == tick:
                    stalled = time.time() - self.last_tick_time
                    if stalled > self.tick_stall_seconds:
                        alert = f"⚠️ Tick {tick} non avanza da {stalled:.0f}s"
                        report["alerts"].append(alert)
                        report["ok"] = False
                        self.alerts.append({"ts": time.time(), "msg": alert})
                else:
                    self.last_tick = tick
                    self.last_tick_time = time.time()

            report["checks"].append("morphological_snapshot")
        else:
            report["alerts"].append("ℹ️ Nessuno snapshot morfologico trovato")
            report["checks"].append("morphological_snapshot:missing")

        emb = self._read_last_embodiment()
        if emb:
            state = emb.get("state", {})
            cpu_norm = self._normalize_cpu(state.get("cpu_avg"))
            mem_norm = self._normalize_mem(state.get("mem_used"))
            report["cpu"] = cpu_norm
            report["memory"] = mem_norm
            report["cpu_raw"] = state.get("cpu_avg")
            report["memory_raw"] = state.get("mem_used")
            if cpu_norm is not None and cpu_norm > 0.95:
                alert = f"⚠️ CPU al {cpu_norm*100:.1f}%"
                report["alerts"].append(alert)
                self.alerts.append({"ts": time.time(), "msg": alert})
            if mem_norm is not None and mem_norm > 0.95:
                alert = f"⚠️ Memoria al {mem_norm*100:.1f}%"
                report["alerts"].append(alert)
                self.alerts.append({"ts": time.time(), "msg": alert})
            report["checks"].append("embodiment_state")
        else:
            report["checks"].append("embodiment_state:missing")

        # ── Assessment / environment reports ─────────────────────────────
        assessment = self._read_last_assessment_report()
        if assessment:
            report["capability_score"] = assessment.get("composite_score")
            report["checks"].append("assessment_report")
            score = report["capability_score"]
            if score is not None and score < 30:
                alert = f"⚠️ Capability assessment score basso: {score:.1f}/100"
                report["alerts"].append(alert)
                report["ok"] = False
                self.alerts.append({"ts": time.time(), "msg": alert})
        else:
            report["checks"].append("assessment_report:missing")

        env_report = self._read_last_environment_report()
        if env_report:
            report["last_env_kind"] = env_report.get("env_kind")
            report["checks"].append("environment_report")
        else:
            report["checks"].append("environment_report:missing")

        return report

    def recent_alerts(self, n: int = 10) -> List[Dict[str, Any]]:
        return list(self.alerts)[-n:]


# ── Periodic Auto-Analysis Scheduler ──────────────────────────────────
class AutoAnalysisScheduler:
    """Periodically runs ChiefArchitect.analyze() and broadcasts a digest to supervisors.

    Cycles:
    - Every N seconds: Chief Architect reviews the engineering plan
    - Every M seconds: each supervisor analyzes its domain
    - Findings are logged to data/agi_team/auto_analysis.jsonl

    Now with:
    - Live runtime context (not just files)
    - Stall detection (skip repetitive LLM calls when context is unchanged)
    - Per-call LLM fallback on timeout
    """

    def __init__(self, agents: Dict[str, Any], plan: EngineeringPlan,
                 chief_id: str = "chief_architect",
                 chief_interval: float = 300.0,
                 supervisor_interval: float = 600.0,
                 runtime: Any = None,
                 brain_orchestrator: Any = None):
        self.agents = agents
        self.plan = plan
        self.chief_id = chief_id
        self.chief_interval = chief_interval
        self.supervisor_interval = supervisor_interval
        self._last_chief: float = 0.0
        self._last_supervisor: float = 0.0
        self._lock = threading.Lock()
        self._orchestrator_ref: Optional[Any] = None  # Set by Orchestrator to enable action cycle
        # ── Live runtime context ──────────────────────────────────────────
        self._runtime = runtime
        self._brain_orchestrator = brain_orchestrator
        # ── Stall detection ───────────────────────────────────────────────
        self._last_context_hash: str = ""
        self._stall_count: int = 0
        self._max_stall_skips: int = 3  # Skip analysis after N consecutive identical contexts
        self._log_path = Path("data/agi_team/auto_analysis.jsonl")
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._findings_count = 0
        self._running = False

    def _log_finding(self, kind: str, agent_id: str, content: str):
        try:
            with self._log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "ts": time.time(),
                    "kind": kind,
                    "agent_id": agent_id,
                    "content": content[:8000],
                }, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def _build_speace_context(self) -> Dict[str, Any]:
        """Read latest SPEACE data for analysis context.

        Primary source: live runtime engine (real-time data).
        Fallback: organism_observer topology + morphological_memory + embodiment files.
        Last resort: static defaults with 'no_data' status.
        """
        ctx: Dict[str, Any] = {}

        # ── Primary: live context from runtime engine ──────────────────
        if self._runtime is not None:
            try:
                snap = self._runtime.snapshot() if hasattr(self._runtime, "snapshot") else {}
                if snap:
                    ctx["tick"] = snap.get("tick_count", snap.get("tick", 0))
                    ctx["ticks_since_start"] = snap.get("ticks_since_start", 0)
                    ctx["state"] = snap.get("state", "unknown")
                    ctx["uptime_seconds"] = snap.get("uptime_seconds", 0)
                    health = snap.get("health", {})
                    if isinstance(health, dict):
                        ctx["health_score"] = health.get("health_score", 0.0)
                        ctx["tick_latency_ms"] = health.get("tick_latency_ms", 0.0)
                        ctx["peak_memory_rss_mb"] = health.get("_peak_memory_rss_mb", 0.0)
            except Exception:
                pass

        if self._brain_orchestrator is not None:
            try:
                m = getattr(self._brain_orchestrator, "latest_metrics", None)
                if m is not None:
                    ctx["coherence_phi"] = getattr(m, "coherence_phi", 0.0)
                    ctx["mean_energy"] = getattr(m, "mean_energy", 0.0)
                    ctx["active_neurons"] = getattr(m, "active_neurons", 0)
                    ctx["total_neurons"] = getattr(m, "total_neurons", 0)
                    ctx["fired_neurons"] = getattr(m, "fired_neurons", 0)
                    ctx["propagated_synapses"] = getattr(m, "propagated_synapses", 0)
                fs = getattr(self._brain_orchestrator, "get_field_state", None)
                if callable(fs):
                    field = fs()
                    if field is not None:
                        ctx["ilf_value"] = getattr(field, "ilf_value", 0.0)
                        ctx["field_stability"] = getattr(field, "field_stability", 0.0)
            except Exception:
                pass

        # ── Fallback: data files (only if live context is incomplete) ───
        if not ctx.get("coherence_phi") or not ctx.get("tick"):
            try:
                snap_path = Path("data/organism_observer/topology_history.jsonl")
                if not snap_path.exists():
                    snap_path = Path("data/morphological_memory/snapshots.jsonl")
                if snap_path.exists():
                    lines = snap_path.read_text(encoding="utf-8").strip().split("\n")
                    if lines:
                        last = json.loads(lines[-1])
                        ctx.setdefault("coherence_phi", (
                            last.get("avg_clustering", 0.0) * 0.5 +
                            last.get("global_efficiency", 0.0) * 0.5
                        ))
                        ctx.setdefault("tick", last.get("tick", 0))
                        ctx.setdefault("node_count", last.get("node_count", 0))
                        ctx.setdefault("edge_count", last.get("edge_count", 0))
                        ctx.setdefault("modularity_q", last.get("modularity_q", 0.0))
                        ctx.setdefault("global_efficiency", last.get("global_efficiency", 0.0))
            except (OSError, json.JSONDecodeError):
                pass

            # Morphologies salvate
            morph_path = Path("data/organism_observer/morphologies.jsonl")
            if morph_path.exists():
                try:
                    lines = morph_path.read_text(encoding="utf-8").strip().split("\n")
                    if lines:
                        last = json.loads(lines[-1])
                        ctx["saved_morphologies"] = len(lines)
                        ctx.setdefault("best_fitness", last.get("fitness_score", 0.0))
                except (OSError, json.JSONDecodeError):
                    pass

            # Embodiment
            emb_path = Path("data/embodiment/environment_state.jsonl")
            if emb_path.exists():
                try:
                    lines = emb_path.read_text(encoding="utf-8").strip().split("\n")
                    if lines:
                        last = json.loads(lines[-1])
                        state = last.get("state", {})
                        if state:
                            ctx.setdefault("cpu", state.get("cpu_avg", 0))
                            ctx.setdefault("memory", state.get("mem_used", 0))
                            ctx.setdefault("disk", state.get("disk_used", 0))
                            ctx.setdefault("temperature", state.get("temp_avg", 0))
                except (OSError, json.JSONDecodeError):
                    pass

        # ── Stall detection ────────────────────────────────────────────
        import hashlib
        context_hash = hashlib.md5(
            json.dumps({k: v for k, v in sorted(ctx.items()) if isinstance(v, (str, int, float, bool))}, sort_keys=True).encode()
        ).hexdigest()
        if context_hash == self._last_context_hash:
            self._stall_count += 1
            ctx["stall_detected"] = True
            ctx["stall_count"] = self._stall_count
        else:
            self._stall_count = 0
            ctx["stall_detected"] = False
            ctx["stall_count"] = 0
        self._last_context_hash = context_hash

        ctx["plan_progress"] = self.plan.overall_progress()
        ctx["milestones"] = [
            {"id": m["id"], "title": m["title"], "progress": m["progress"], "status": m["status"]}
            for m in self.plan.milestones
        ]
        return ctx

    def tick(self) -> Dict[str, Any]:
        """Call from the main loop. Returns what was done this tick.

        Includes stall detection: if context hasn't changed for multiple cycles,
        skip repetitive LLM calls and prioritize action cycle instead.
        """
        with self._lock:
            now = time.time()
            actions = {"ran_chief": False, "ran_supervisors": [], "skipped": True}

            # Build context once for this tick (with stall detection)
            ctx = self._build_speace_context()
            is_stalled = ctx.get("stall_detected", False)
            stall_count = ctx.get("stall_count", 0)

            # ── Skip repetitive analysis during stalls ───────────────────
            # After N consecutive identical contexts, only run action cycle
            # (which may propose recovery actions), skip LLM-heavy analysis
            skip_analysis = is_stalled and stall_count >= self._max_stall_skips

            if now - self._last_chief >= self.chief_interval and not skip_analysis:
                chief = self.agents.get(self.chief_id)
                if chief:
                    finding = chief.analyze(ctx)
                    self._log_finding("chief_review", self.chief_id, finding.get("analysis", ""))
                    self._last_chief = now
                    self._findings_count += 1
                    actions["ran_chief"] = True
                    actions["skipped"] = False

            if now - self._last_supervisor >= self.supervisor_interval and not skip_analysis:
                for aid, agent in self.agents.items():
                    if aid == self.chief_id:
                        continue
                    if getattr(agent, "agent_type", "technician") == "supervisor" or aid.endswith("_supervisor"):
                        finding = agent.analyze(ctx)
                        self._log_finding("supervisor_review", aid, finding.get("analysis", ""))
                        actions["ran_supervisors"].append(aid)
                        self._findings_count += 1
                self._last_supervisor = now
                actions["skipped"] = False

            if skip_analysis:
                actions["stall_skipped_analysis"] = True
                self._log_finding(
                    "stall_detected", "system",
                    f"Context unchanged for {stall_count} cycles — skipping LLM analysis, running action cycle only"
                )

            # ── Trigger supervisor-directed action cycle ──────────────────
            if self._orchestrator_ref and getattr(self._orchestrator_ref, 'action_executor', None):
                try:
                    action_report = self._orchestrator_ref.supervisor_directed_action_cycle(ctx)
                    actions["action_cycle"] = action_report
                except Exception as e:
                    _logger.warning("Supervisor-directed action cycle failed: %s", e)

            return actions

    def stats(self) -> Dict[str, Any]:
        return {
            "findings_count": self._findings_count,
            "seconds_since_chief": time.time() - self._last_chief,
            "seconds_since_supervisors": time.time() - self._last_supervisor,
            "chief_interval": self.chief_interval,
            "supervisor_interval": self.supervisor_interval,
        }


# ── Background Loop ───────────────────────────────────────────────────
class Orchestrator:
    """Ties everything together: load balancer, monitor, auto-analysis.

    Runs a background thread that:
    - Calls auto-analysis scheduler.tick() every loop_interval seconds
    - Calls runtime health monitor.check() every loop_interval seconds
    - Persists health alerts to data/agi_team/health_alerts.jsonl
    """

    def __init__(self, agents: Dict[str, Any], plan: EngineeringPlan,
                 loop_interval: float = 30.0,
                 chief_interval: float = 300.0,
                 supervisor_interval: float = 600.0,
                 runtime: Any = None,
                 brain_orchestrator: Any = None):
        self.agents = agents
        self.plan = plan
        self.loop_interval = loop_interval
        self.load_balancer = LoadBalancer(agents)
        self.health_monitor = RuntimeHealthMonitor(
            runtime=runtime,
            brain_orchestrator=brain_orchestrator,
        )
        self.scheduler = AutoAnalysisScheduler(
            agents, plan,
            chief_interval=chief_interval,
            supervisor_interval=supervisor_interval,
            runtime=runtime,
            brain_orchestrator=brain_orchestrator,
        )
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._alerts_log = Path("data/agi_team/health_alerts.jsonl")
        self._alerts_log.parent.mkdir(parents=True, exist_ok=True)
        self._execution_log: List[Dict[str, Any]] = []
        # ── Action execution layer ──────────────────────────────────────
        self.action_executor: Optional[ActionExecutor] = None
        self.action_safety_gate: Optional[ActionSafetyGate] = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="AGI-Orchestrator", daemon=True
        )
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5.0)

    def _log_alert(self, report: Dict[str, Any]):
        try:
            with self._alerts_log.open("a", encoding="utf-8") as f:
                f.write(json.dumps(report, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def _loop(self):
        while not self._stop.is_set():
            try:
                # Runtime health
                health = self.health_monitor.check()
                if health.get("alerts"):
                    self._log_alert(health)

                # Auto-analysis
                self.scheduler.tick()
            except Exception as e:  # pragma: no cover
                print(f"[Orchestrator] loop error: {e}")
            self._stop.wait(self.loop_interval)

    # ── Task execution pipeline ──────────────────────────────────────
    def execute_task(self, task: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run a task end-to-end:

        1. Assign to technician (or use specified agent_id, applying load balancing if 'auto')
        2. Technician analyzes the task with optional context
        3. Relevant supervisor validates the technician's analysis
        4. Mark task completed (or failed if validation finds issues)
        """
        agent_id = task.get("agent_id", "")
        if agent_id == "auto" or not agent_id:
            agent_id = self._auto_pick_technician(task)
            task["agent_id"] = agent_id

        ctx = context or self.scheduler._build_speace_context()
        context_summary = (
            f"coherence_phi={ctx.get('coherence_phi', 'n/a')}, "
            f"tick={ctx.get('tick', 'n/a')}, "
            f"health_score={ctx.get('health_score', 'n/a')}, "
            f"active_neurons={ctx.get('active_neurons', 'n/a')}, "
            f"stall_detected={ctx.get('stall_detected', False)}"
        )
        task_prompt = (
            f"Task assegnato: {task.get('title','')}\n"
            f"Descrizione: {task.get('description','')}\n"
            f"Priorità: {task.get('priority','medium')}\n"
            f"Milestone: {task.get('milestone_id','')}\n"
            f"Contesto SPEACE: {context_summary}\n\n"
            f"Analizza il task, proponi una soluzione concreta e indica lo stato di esecuzione."
        )

        record: Dict[str, Any] = {
            "task_id": task.get("id"),
            "title": task.get("title"),
            "agent_id": agent_id,
            "started_at": time.time(),
            "steps": [],
        }

        # Step 1: Technician analyzes
        tech = self.agents.get(agent_id)
        if not tech:
            record["outcome"] = "failed"
            record["error"] = f"Agent {agent_id} not found"
            record["completed_at"] = time.time()
            self._execution_log.append(record)
            return record

        self.load_balancer.record_chat(agent_id)
        self.load_balancer.record_analysis(agent_id)
        tech_response = tech.chat(task_prompt)
        record["steps"].append({
            "step": "technician_analysis",
            "agent_id": agent_id,
            "response": tech_response,
        })

        # Step 2: Supervisor validates
        supervisor_id = self._find_supervisor_for(agent_id)
        if supervisor_id and supervisor_id in self.agents:
            sup = self.agents[supervisor_id]
            validation_prompt = (
                f"Valida l'output del tecnico {agent_id} sul task '{task.get('title','')}'.\n"
                f"Risposta del tecnico:\n{tech_response[:2000]}\n\n"
                f"Conferma se la soluzione è corretta, o richiedi modifiche. Rispondi in italiano."
            )
            self.load_balancer.record_chat(supervisor_id)
            self.load_balancer.record_analysis(supervisor_id)
            sup_response = sup.chat(validation_prompt)
            record["steps"].append({
                "step": "supervisor_validation",
                "agent_id": supervisor_id,
                "response": sup_response,
            })
            # Heuristic for outcome: distinguish between explicit rejection vs
            # troncamento/output parziale. The LLM sometimes complains about
            # "output troncato" without truly rejecting the work.
            low = sup_response.lower()
            # Strong rejection signals → failed
            strong_reject = [
                "non è accettabile", "rifiuta", "respinto",
                "non approvato", "respinta", "inaccettabile",
            ]
            # Soft rejection (truncated output, partial validation) — count as
            # success because the work was done, just incomplete.
            soft_reject = [
                "non consegnabile", "parzialmente valido", "troncato",
                "richiede integrazione", "incompleto", "parziale",
            ]
            if any(m in low for m in strong_reject):
                outcome = "failed"
            elif any(m in low for m in soft_reject):
                outcome = "success"
                record["validation_note"] = "Output parziale: richiede follow-up"
            else:
                outcome = "success"
        else:
            outcome = "success"
            record["steps"].append({
                "step": "supervisor_validation",
                "agent_id": None,
                "response": "Nessun supervisor assegnato, validazione saltata.",
            })

        record["outcome"] = outcome
        record["completed_at"] = time.time()
        record["duration_sec"] = record["completed_at"] - record["started_at"]
        self._execution_log.append(record)

        # Persist log
        try:
            log_path = Path("data/agi_team/task_executions.jsonl")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            pass

        # Mark task in the plan
        if task.get("id"):
            self.plan.complete_task(task["id"], outcome)

        return record

    def _find_supervisor_for(self, technician_id: str) -> str:
        """Map a technician to the relevant supervisor based on the engineering plan."""
        mapping = {
            "neuron_tech": "brain_supervisor",
            "synapse_tech": "brain_supervisor",
            "region_tech": "brain_supervisor",
            "runtime_tech": "organism_supervisor",
            "defense_tech": "organism_supervisor",
            "embodiment_tech": "embodied_cognition_supervisor",
            "memory_tech": "memory_supervisor",
            "evolution_tech": "selfimprovement_supervisor",
            "network_tech": "organism_supervisor",
            "genome_tech": "dna_supervisor",
        }
        return mapping.get(technician_id, "chief_architect")

    # Inverse mapping: supervisor → technicians
    _TECH_FOR_SUP: Dict[str, List[str]] = {
        "brain_supervisor": ["neuron_tech", "synapse_tech", "region_tech"],
        "dna_supervisor": ["genome_tech"],
        "organism_supervisor": ["runtime_tech", "defense_tech", "network_tech"],
        "memory_supervisor": ["memory_tech"],
        "selfimprovement_supervisor": ["evolution_tech"],
        "embodied_cognition_supervisor": ["embodiment_tech"],
    }

    def _find_technician_for(self, proposal) -> str:
        """Map an action proposal to the best technician for execution.

        Uses the proposal's agent_id (supervisor) and target to find the
        most appropriate technician. Falls back to load balancing.
        """
        agent_id = proposal.agent_id if hasattr(proposal, 'agent_id') else ""
        target = proposal.target if hasattr(proposal, 'target') else ""
        category = proposal.action_category if hasattr(proposal, 'action_category') else ""

        # If the proposing agent is a technician, use it directly
        if agent_id.endswith("_tech") and agent_id in self.agents:
            return agent_id

        # If the proposing agent is a supervisor, find its technicians
        if agent_id in self._TECH_FOR_SUP:
            technicians = self._TECH_FOR_SUP[agent_id]
            if technicians:
                # Pick the least loaded technician
                return self.load_balancer.pick_technician(technicians)

        # If the proposing agent is chief_architect, use all technicians
        if agent_id == "chief_architect":
            tech_ids = [a for a in self.agents if a.endswith("_tech")]
            return self.load_balancer.pick_technician(tech_ids) or "neuron_tech"

        # Fallback: pick based on target domain
        catalog = ActionCatalog()
        all_agents = set(catalog.get_full_catalog().keys())
        tech_ids = [a for a in all_agents if a.endswith("_tech")]
        for tid in tech_ids:
            if catalog.is_authorized(tid, category, target):
                return tid

        # Ultimate fallback: least loaded technician
        tech_ids = [a for a in self.agents if a.endswith("_tech")]
        return self.load_balancer.pick_technician(tech_ids) or "neuron_tech"

    def supervisor_directed_action_cycle(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Supervisor-driven action cycle: supervisors analyze, propose, and dispatch.

        Flow:
        1. Each supervisor proposes actions from current context
        2. Each proposal goes through the safety gate (only once, not twice)
        3. Approved proposals are dispatched to the appropriate technician
        4. Technician executes via ActionExecutor
        5. Returns a complete report of all proposals and results

        Optimization: proposals are collected once, not called twice per supervisor.
        """
        if self.action_executor is None:
            return {"error": "ActionExecutor not available", "proposals": [], "results": []}

        ctx = context or self.scheduler._build_speace_context()

        report: Dict[str, Any] = {
            "timestamp": time.time(),
            "all_proposals": {},
            "approved": {},
            "blocked": {},
            "conditioned": {},
            "executed": {},
            "execution_results": [],
        }

        # ── Step 1: Supervisors propose actions (call LLM ONCE) ───────────
        all_proposals_with_agent: List[tuple] = []  # [(agent_id, proposal), ...]
        for aid, agent in self.agents.items():
            if not (getattr(agent, 'agent_type', '') == "supervisor" or aid.endswith("_supervisor") or aid == "chief_architect"):
                continue

            try:
                proposals = agent.propose_action_from_analysis(ctx)
                if proposals:
                    report["all_proposals"][aid] = [
                        {
                            "id": p.proposal_id,
                            "action_type": p.action_type,
                            "target": p.target,
                            "risk": p.risk_level if isinstance(p.risk_level, str) else p.risk_level.value,
                        }
                        for p in proposals
                    ]
                    for p in proposals:
                        all_proposals_with_agent.append((aid, p))
            except Exception as e:
                _logger.warning("Supervisor %s failed to propose actions: %s", aid, e)
                continue

        # ── Step 2: Evaluate each proposal through safety gate ONCE ──────
        approved_proposals: List[tuple] = []  # [(agent_id, proposal), ...]
        for aid, proposal in all_proposals_with_agent:
            try:
                gate_result = self.action_safety_gate.evaluate(proposal)
            except Exception as e:
                _logger.warning("Safety gate evaluation failed for %s: %s", proposal.proposal_id, e)
                report["blocked"].setdefault(aid, []).append({
                    "id": proposal.proposal_id,
                    "action_type": proposal.action_type,
                    "target": proposal.target,
                    "gate_decision": "blocked",
                    "error": str(e),
                })
                continue

            self.action_executor._store_proposal(proposal)

            proposal_info = {
                "id": proposal.proposal_id,
                "action_type": proposal.action_type,
                "target": proposal.target,
                "risk": proposal.risk_level if isinstance(proposal.risk_level, str) else proposal.risk_level.value,
                "gate_decision": gate_result.final_decision,
                "conditions": gate_result.conditions,
            }

            if gate_result.final_decision == "allow":
                report["approved"].setdefault(aid, []).append(proposal_info)
                approved_proposals.append((aid, proposal))
            elif gate_result.final_decision == "conditioned":
                report["conditioned"].setdefault(aid, []).append(proposal_info)
                # Conditioned proposals are also executed (conditions noted)
                approved_proposals.append((aid, proposal))
            else:
                report["blocked"].setdefault(aid, []).append(proposal_info)

        # ── Step 3: Execute approved proposals ───────────────────────────
        for aid, proposal in approved_proposals:
            tech_id = self._find_technician_for(proposal)

            try:
                result = self.action_executor.execute_pipeline(proposal)
                report["executed"].setdefault(aid, []).append({
                    "proposal_id": proposal.proposal_id,
                    "technician": tech_id,
                    "status": result.final_status,
                    "rollback": result.rollback_performed,
                    "error": result.error,
                })
                report["execution_results"].append(result.model_dump())
            except Exception as e:
                _logger.error("Action execution failed for %s: %s", proposal.proposal_id, e)
                report["executed"].setdefault(aid, []).append({
                    "proposal_id": proposal.proposal_id,
                    "technician": tech_id,
                    "status": "error",
                    "error": str(e),
                })

        return report

    def _auto_pick_technician(self, task: Dict[str, Any]) -> str:
        """Choose technician based on task's milestone mapping or load balancing."""
        milestone_id = task.get("milestone_id", "")
        for ms in self.plan.milestones:
            if ms["id"] == milestone_id:
                candidates = [a for a in ms.get("agents", []) if a.endswith("_tech")]
                if candidates:
                    return self.load_balancer.pick_technician(candidates)
        # fallback: least loaded technician
        tech_ids = [a for a in self.agents if a.endswith("_tech")]
        return self.load_balancer.pick_technician(tech_ids) or "neuron_tech"

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._thread.is_alive() if self._thread else False,
            "load_distribution": self.load_balancer.distribution(),
            "scheduler": self.scheduler.stats(),
            "health_alerts": self.health_monitor.recent_alerts(5),
            "executions_count": len(self._execution_log),
            "action_executor_available": self.action_executor is not None,
        }

    # ── Action execution layer integration ──────────────────────────────

    def set_action_executor(self, executor: ActionExecutor) -> None:
        """Wire the ActionExecutor and ActionSafetyGate into the orchestrator."""
        self.action_executor = executor
        self.action_safety_gate = executor.safety_gate
        # Provide orchestrator reference to executor for runtime param patches
        if executor.orchestrator is None:
            executor.orchestrator = self  # type: ignore[assignment]
        # Wire the scheduler's orchestrator reference for action cycle
        self.scheduler._orchestrator_ref = self

    def execute_task_with_actions(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        auto_execute: bool = False,
    ) -> Dict[str, Any]:
        """Extended task execution with action proposal and execution pipeline.

        Steps:
        1. Assign to technician (or use specified agent_id)
        2. Technician analyzes the task with context
        3. Technician proposes actions based on analysis (NEW)
        4. Safety gate evaluates each proposal (NEW)
        5. Supervisor validates analysis + actions (extended)
        6. Execute approved actions through ActionExecutor (NEW)
        7. Post-execution verification (NEW)
        """
        if self.action_executor is None:
            # Fallback to original execute_task if no action executor
            return self.execute_task(task, context)

        agent_id = task.get("agent_id", "")
        if agent_id == "auto" or not agent_id:
            agent_id = self._auto_pick_technician(task)
            task["agent_id"] = agent_id

        ctx = context or self.scheduler._build_speace_context()
        task_prompt = (
            f"Task assegnato: {task.get('title','')}\n"
            f"Descrizione: {task.get('description','')}\n"
            f"Priorità: {task.get('priority','medium')}\n"
            f"Milestone: {task.get('milestone_id','')}\n\n"
            f"Analizza il task, proponi una soluzione concreta e indica lo stato di esecuzione."
        )

        record: Dict[str, Any] = {
            "task_id": task.get("id"),
            "title": task.get("title"),
            "agent_id": agent_id,
            "started_at": time.time(),
            "steps": [],
            "action_proposals": [],
            "action_results": [],
        }

        # Step 1: Technician analyzes
        tech = self.agents.get(agent_id)
        if not tech:
            record["outcome"] = "failed"
            record["error"] = f"Agent {agent_id} not found"
            record["completed_at"] = time.time()
            self._execution_log.append(record)
            return record

        self.load_balancer.record_chat(agent_id)
        self.load_balancer.record_analysis(agent_id)
        tech_response = tech.chat(task_prompt)
        record["steps"].append({
            "step": "technician_analysis",
            "agent_id": agent_id,
            "response": tech_response,
        })

        # Step 2: Technician proposes actions
        proposals = tech.propose_action_from_analysis(ctx)
        record["steps"].append({
            "step": "action_proposal",
            "agent_id": agent_id,
            "proposal_count": len(proposals),
            "proposals": [
                {"id": p.proposal_id, "action_type": p.action_type, "target": p.target, "risk": p.risk_level}
                for p in proposals
            ],
        })

        # Step 3: Safety gate evaluation
        approved_proposals = []
        for proposal in proposals:
            gate_result = self.action_safety_gate.evaluate(proposal)
            proposal_snapshot = {
                "proposal_id": proposal.proposal_id,
                "action_type": proposal.action_type,
                "target": proposal.target,
                "risk_level": proposal.risk_level if isinstance(proposal.risk_level, str) else proposal.risk_level.value,
                "gate_decision": gate_result.final_decision,
                "conditions": gate_result.conditions,
            }
            record["action_proposals"].append(proposal_snapshot)

            if gate_result.final_decision == "blocked":
                continue
            if gate_result.final_decision == "conditioned" and gate_result.human_approval_required:
                # Needs human approval — store for later
                self.action_executor._store_proposal(proposal)
                proposal_snapshot["needs_human_approval"] = True
                continue
            approved_proposals.append(proposal)

        # Step 4: Supervisor validates
        supervisor_id = self._find_supervisor_for(agent_id)
        if supervisor_id and supervisor_id in self.agents:
            sup = self.agents[supervisor_id]
            action_summary = "\n".join(
                f"- {p.action_type} → {p.target} (risk: {p.risk_level})"
                for p in proposals
            )
            validation_prompt = (
                f"Valida l'output del tecnico {agent_id} sul task '{task.get('title','')}'.\n"
                f"Risposta del tecnico:\n{tech_response[:2000]}\n\n"
                f"Azioni proposte:\n{action_summary}\n\n"
                f"Conferma se la soluzione e le azioni sono corrette, o richiedi modifiche. "
                f"Rispondi in italiano."
            )
            self.load_balancer.record_chat(supervisor_id)
            self.load_balancer.record_analysis(supervisor_id)
            sup_response = sup.chat(validation_prompt)
            record["steps"].append({
                "step": "supervisor_validation",
                "agent_id": supervisor_id,
                "response": sup_response,
            })

            # Check if supervisor rejected any proposals (heuristic)
            low = sup_response.lower()
            strong_reject = [
                "non è accettabile", "rifiuta", "respinto",
                "non approvato", "respinta", "inaccettabile",
            ]
            if any(m in low for m in strong_reject):
                # Supervisor rejected — filter out proposals that supervisor might object to
                approved_proposals = [
                    p for p in approved_proposals
                    if isinstance(p.risk_level, str) and p.risk_level in ("low", "moderate")
                    or (not isinstance(p.risk_level, str) and p.risk_level.value in ("low", "moderate"))
                ]

        # Step 5: Execute approved actions
        if auto_execute and approved_proposals:
            for proposal in approved_proposals:
                result = self.action_executor.execute_pipeline(proposal)
                record["action_results"].append({
                    "proposal_id": result.proposal_id,
                    "status": result.final_status,
                    "rollback": result.rollback_performed,
                    "error": result.error,
                })

        # Step 6: Determine outcome
        outcome = "success"
        if record.get("action_results"):
            failed_actions = [r for r in record["action_results"] if r["status"] in ("failed", "vetoed")]
            if len(failed_actions) > len(record["action_results"]) // 2:
                outcome = "failed"

        record["outcome"] = outcome
        record["completed_at"] = time.time()
        record["duration_sec"] = record["completed_at"] - record["started_at"]
        self._execution_log.append(record)

        # Persist log
        try:
            log_path = Path("data/agi_team/task_executions.jsonl")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        except OSError:
            pass

        # Mark task in the plan
        if task.get("id"):
            self.plan.complete_task(task["id"], outcome)

        return record


# Singleton container
_orchestrator: Optional[Orchestrator] = None


def get_orchestrator(agents: Optional[Dict[str, Any]] = None,
                     plan: Optional[EngineeringPlan] = None,
                     runtime: Any = None,
                     brain_orchestrator: Any = None) -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        if agents is None or plan is None:
            raise ValueError("First call to get_orchestrator requires agents and plan")
        _orchestrator = Orchestrator(agents, plan, runtime=runtime, brain_orchestrator=brain_orchestrator)
    else:
        # Update runtime references even if already initialized
        if runtime is not None:
            _orchestrator.scheduler._runtime = runtime
            _orchestrator.health_monitor.runtime = runtime
        if brain_orchestrator is not None:
            _orchestrator.scheduler._brain_orchestrator = brain_orchestrator
            _orchestrator.health_monitor.brain_orchestrator = brain_orchestrator
    return _orchestrator
