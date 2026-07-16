"""DashboardAPI — FastAPI application for SPEACE Local Organism Monitor.

Serves read-only HTTP endpoints and WebSocket live updates.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List

from speace_core.cli import SPEACE_VERSION
from speace_core.monitoring.alert_engine import AlertEngine
from speace_core.monitoring.anomaly_panel import AnomalyPanel
from speace_core.monitoring.human_approval_gate import HumanApprovalGate
from speace_core.monitoring.longitudinal_memory import LongitudinalMemory
from speace_core.monitoring.metrics_bus import MetricsBus
from speace_core.monitoring.organism_state_collector import OrganismStateCollector
from speace_core.cellular_brain.language.dialogue_manager import DialogueManager
from speace_core.monitoring.multi_node_aggregator import MultiNodeAggregator
from speace_core.monitoring.regulation_proposal_builder import RegulationProposalBuilder
from speace_core.monitoring.safety_status import SafetyStatus
from speace_core.monitoring.websocket_server import create_websocket_router
from speace_core.cellular_brain.experience.relational_memory import RelationalMemory
from speace_core.cellular_brain.experience.temporal_narrative_engine import TemporalNarrativeEngine
from speace_core.cellular_brain.experience.session_continuity_manager import SessionContinuityManager
from speace_core.cellular_brain.experience.adaptive_preference_model import AdaptivePreferenceModel
from speace_core.cellular_brain.experience.experiential_snapshot_store import ExperientialSnapshotStore
from speace_core.dna.parser import load_genome
from speace_core.orchestrator import CellularBrainOrchestrator
from speace_core.runtime.continuous_runtime_engine import ContinuousRuntimeEngine

from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles

    _HAS_FASTAPI = True
except Exception:  # pragma: no cover
    _HAS_FASTAPI = False
    FastAPI = Any  # type: ignore[misc,assignment]
    StaticFiles = Any  # type: ignore[misc,assignment]

# --------------------------------------------------------------------------- #
# Bootstrap
# --------------------------------------------------------------------------- #
_start_time = time.time()

_data_root = Path("data")
_collector = OrganismStateCollector(data_root=str(_data_root))
_safety = SafetyStatus(data_root=str(_data_root))
_anomaly = AnomalyPanel()
_alert_engine = AlertEngine()
_longitudinal_memory = LongitudinalMemory(health_score_func=_alert_engine.health_score)
_regulation_builder = RegulationProposalBuilder()
_approval_gate = HumanApprovalGate(builder=_regulation_builder)
_multi_node_aggregator = MultiNodeAggregator()
_dialogue_manager = DialogueManager()

# T108 — Persistent Experiential Continuity
_relational_memory = RelationalMemory()
_narrative_engine = TemporalNarrativeEngine()
_session_continuity = SessionContinuityManager()
_preference_model = AdaptivePreferenceModel()
_experiential_snapshot_store = ExperientialSnapshotStore()

# T109 — Controlled Continuous Runtime (optional, lazy-init)
_runtime_engine: Any = None

# Load genome thresholds if available
_genome_path = Path(__file__).resolve().parent.parent / "dna" / "genome" / "monitoring_dashboard.yaml"
if _genome_path.exists():
    try:
        import yaml

        _cfg = yaml.safe_load(_genome_path.read_text(encoding="utf-8"))
        _md = _cfg.get("monitoring_dashboard", {})
        _thresh = _md.get("anomaly_thresholds", {})
        if _thresh:
            _anomaly = AnomalyPanel(
                coherence_phi_min=_thresh.get("coherence_phi_min", 0.1),
                energy_min=_thresh.get("energy_min", 0.2),
                severity_max=_thresh.get("severity_max", 2.0),
                branching_ratio_deviation=_thresh.get("branching_ratio_deviation", 0.3),
            )
        _alert_thresh = _md.get("alert_thresholds", {})
        if _alert_thresh:
            _alert_engine = AlertEngine(thresholds=_alert_thresh)
    except Exception:
        pass

def _post_process(state: Dict[str, Any]) -> Dict[str, Any]:
    try:
        state["anomaly_panel"] = _anomaly.analyze(state)
    except Exception:
        state["anomaly_panel"] = {"anomalies": [], "overall_status": "unknown", "anomaly_count": 0}
    try:
        alerts = _alert_engine.evaluate(state)
        state["alert_engine"] = {
            "alerts": alerts,
            "recent_alerts": _alert_engine.recent_alerts(limit=20),
            "health_score": _alert_engine.health_score(state),
        }
        # T104: build regulation proposals from critical/warning alerts
        try:
            proposals = _regulation_builder.build_from_alerts(alerts, state)
            state["regulation_proposals"] = {
                "pending_count": len([p for p in proposals if p.get("status") == "pending"]),
                "latest": proposals[:5],
            }
        except Exception:
            state["regulation_proposals"] = {"pending_count": 0, "latest": []}
    except Exception:
        state["alert_engine"] = {"alerts": [], "recent_alerts": [], "health_score": 0.0}
        state["regulation_proposals"] = {"pending_count": 0, "latest": []}
    try:
        _longitudinal_memory.record(state)
    except Exception:
        pass
    return state


_metrics_bus = MetricsBus(collector=_collector, interval_ms=1000.0, post_process=_post_process)

_static_dir = Path(__file__).resolve().parent.parent.parent / "web" / "dashboard"
if not _static_dir.exists():
    # Fallback for editable installs where cwd might differ
    _static_dir = Path("web") / "dashboard"

# --------------------------------------------------------------------------- #
# Guard
# --------------------------------------------------------------------------- #
if not _HAS_FASTAPI:
    raise ImportError(
        "FastAPI / Uvicorn are not installed.\n"
        "Install with: pip install \"speace-core[monitoring]\"\n"
        "or:          pip install fastapi uvicorn websockets"
    )

# --------------------------------------------------------------------------- #
# Lifecycle
# --------------------------------------------------------------------------- #


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    _metrics_bus.start()
    yield
    if _runtime_engine is not None:
        try:
            await _runtime_engine.stop()
        except Exception:
            pass
    _metrics_bus.stop()


app = FastAPI(
    title="SPEACE Local Organism Monitor",
    description="T101 — Read-only organismic monitoring dashboard",
    version=SPEACE_VERSION,
    lifespan=_lifespan,
)


# --------------------------------------------------------------------------- #
# API — read-only granular endpoints
# --------------------------------------------------------------------------- #


@app.get("/api/health")
async def api_health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - _start_time),
        "speace_version": SPEACE_VERSION,
    }


@app.get("/api/state")
async def api_state() -> Dict[str, Any]:
    state = _metrics_bus.latest()
    if not state:
        state = _collector.collect_all()
        state["timestamp"] = time.time()
    if "alert_engine" not in state:
        try:
            alerts = _alert_engine.evaluate(state)
            state["alert_engine"] = {
                "alerts": alerts,
                "recent_alerts": _alert_engine.recent_alerts(limit=20),
                "health_score": _alert_engine.health_score(state),
            }
        except Exception:
            state["alert_engine"] = {"alerts": [], "recent_alerts": [], "health_score": 0.0}
    anomalies = _anomaly.analyze(state)
    return {
        **state,
        "anomaly_panel": anomalies,
    }


@app.get("/api/body")
async def api_body() -> Dict[str, Any]:
    return _collector.collect_body()


@app.get("/api/cognition")
async def api_cognition() -> Dict[str, Any]:
    return _collector.collect_cognition()


@app.get("/api/dynamics")
async def api_dynamics() -> Dict[str, Any]:
    return _collector.collect_dynamics()


@app.get("/api/identity")
async def api_identity() -> Dict[str, Any]:
    return _collector.collect_identity()


@app.get("/api/drives")
async def api_drives() -> Dict[str, Any]:
    return _collector.collect_drives()


@app.get("/api/safety")
async def api_safety() -> Dict[str, Any]:
    safety = _safety.evaluate()
    safety["governance_mode"] = "observation_only"
    safety["allow_actuator_commands"] = False
    return safety


# --------------------------------------------------------------------------- #
# T102 — Alerts and Health Score
# --------------------------------------------------------------------------- #


@app.get("/api/alerts")
async def api_alerts(limit: int = 20) -> Dict[str, Any]:
    state = _metrics_bus.latest()
    if not state:
        state = _collector.collect_all()
        state["timestamp"] = time.time()
    alerts = _alert_engine.evaluate(state)
    recent = _alert_engine.recent_alerts(limit=limit)
    return {
        "alerts": alerts,
        "recent_alerts": recent,
        "health_score": _alert_engine.health_score(state),
        "timestamp": time.time(),
    }


@app.get("/api/health_score")
async def api_health_score() -> Dict[str, Any]:
    state = _metrics_bus.latest()
    if not state:
        state = _collector.collect_all()
        state["timestamp"] = time.time()
    return {
        "health_score": _alert_engine.health_score(state),
        "timestamp": time.time(),
    }


# --------------------------------------------------------------------------- #
# T103 — Observer Report
# --------------------------------------------------------------------------- #

@app.get("/api/report")
async def api_report(lookback: int = 24) -> Dict[str, Any]:
    from speace_core.monitoring.observer_report_generator import ObserverReportGenerator

    generator = ObserverReportGenerator()
    report = generator.generate(lookback_hours=lookback)
    return report.model_dump(mode="json")


# --------------------------------------------------------------------------- #
# T105 — Longitudinal Memory
# --------------------------------------------------------------------------- #

@app.get("/api/history/snapshot")
async def api_history_snapshot(hours: int = 24, limit: int = 100) -> Dict[str, Any]:
    now = time.time()
    cutoff = now - (hours * 3600)
    snapshots: List[Dict[str, Any]] = []
    path = _longitudinal_memory.history_path
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if entry.get("timestamp", 0) >= cutoff:
                        snapshots.append(entry)
        except OSError:
            pass
    if limit:
        snapshots = snapshots[-limit:]
    return {"hours": hours, "snapshots": snapshots}


@app.get("/api/history/{metric}")
async def api_history(metric: str, hours: int = 24, limit: int = 100) -> Dict[str, Any]:
    data = _longitudinal_memory.get_history(metric, hours=hours, limit=limit)
    return {"metric": metric, "hours": hours, "data": data}


@app.get("/api/history/trend/{metric}")
async def api_history_trend(metric: str, hours: int = 24) -> Dict[str, Any]:
    trend = _longitudinal_memory.get_trend(metric, hours=hours)
    return {"metric": metric, "hours": hours, **trend}


# --------------------------------------------------------------------------- #
# T104 — Regulation Proposals
# --------------------------------------------------------------------------- #

@app.get("/api/regulation/proposals")
async def api_regulation_proposals(status: str = "pending", limit: int = 100) -> Dict[str, Any]:
    proposals = _approval_gate.list_pending(limit=limit) if status == "pending" else _approval_gate.list_all(limit=limit)
    return {"status": status, "count": len(proposals), "proposals": proposals}


@app.post("/api/regulation/approve/{proposal_id}")
async def api_regulation_approve(proposal_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    reviewer = body.get("reviewer", "anonymous")
    health = _alert_engine.health_score(_metrics_bus.latest() or {})
    result = _approval_gate.approve(proposal_id, reviewer=reviewer, current_health=health)
    return result


@app.post("/api/regulation/reject/{proposal_id}")
async def api_regulation_reject(proposal_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    reviewer = body.get("reviewer", "anonymous")
    result = _approval_gate.reject(proposal_id, reviewer=reviewer)
    return result


# --------------------------------------------------------------------------- #
# T106 — Multi-node Monitoring
# --------------------------------------------------------------------------- #

@app.get("/api/nodes")
async def api_nodes() -> Dict[str, Any]:
    agg = _multi_node_aggregator.aggregate()
    return agg


@app.get("/api/nodes/{node_id}/state")
async def api_node_state(node_id: str) -> Dict[str, Any]:
    return _multi_node_aggregator._states.get(node_id, {"error": "node_not_found"})


@app.get("/api/distributed/divergence")
async def api_distributed_divergence() -> Dict[str, Any]:
    drift = _multi_node_aggregator._compute_personality_drift()
    return {
        "personality_drift": drift,
        "node_count": len(_multi_node_aggregator._states),
    }


# --------------------------------------------------------------------------- #
# T107 — Dialogue
# --------------------------------------------------------------------------- #

@app.post("/api/dialogue/message")
async def api_dialogue_message(body: Dict[str, Any]) -> Dict[str, Any]:
    msg = body.get("message", "")
    if not msg:
        return {"error": "empty_message"}
    response = _dialogue_manager.receive(msg)
    return response


@app.get("/api/dialogue/history")
async def api_dialogue_history(limit: int = 20) -> Dict[str, Any]:
    turns = _dialogue_manager.history(limit=limit)
    return {"turns": turns, "state": _dialogue_manager.state}


@app.post("/api/dialogue/speak")
async def api_dialogue_speak() -> Dict[str, Any]:
    result = _dialogue_manager.speak_last_response()
    return result


# --------------------------------------------------------------------------- #
# T108 — Persistent Experiential Continuity
# --------------------------------------------------------------------------- #

@app.get("/api/experience/state")
async def api_experience_state() -> Dict[str, Any]:
    humans = _relational_memory.list_humans()
    latest_snapshot = _experiential_snapshot_store.latest()
    continuity = _session_continuity.load()
    preferences = _preference_model.summary()
    return {
        "relational_humans": humans,
        "relational_human_count": len(humans),
        "latest_snapshot": latest_snapshot,
        "session_continuity": continuity,
        "preferences": preferences,
        "resume_narrative": _session_continuity.build_resume_narrative(),
    }


@app.get("/api/experience/timeline")
async def api_experience_timeline(hours: float = 168, limit: int = 50) -> Dict[str, Any]:
    events = _narrative_engine.recent(hours=hours, limit=limit)
    summary = _narrative_engine.get_narrative_summary(hours=hours)
    return {
        "events": events,
        "summary": summary,
        "hours": hours,
        "count": len(events),
    }


@app.post("/api/experience/snapshot")
async def api_experience_snapshot(body: Dict[str, Any]) -> Dict[str, Any]:
    state = body.get("state", {})
    human_id = body.get("human_id")
    narrative_position = body.get("narrative_position")
    snapshot = _experiential_snapshot_store.save(
        state=state, human_id=human_id, narrative_position=narrative_position
    )
    return {"snapshot": snapshot}


# --------------------------------------------------------------------------- #
# T109 — Controlled Continuous Runtime
# --------------------------------------------------------------------------- #


def _build_runtime_from_genome(genome_path: Optional[str] = None) -> ContinuousRuntimeEngine:
    if genome_path:
        genome = load_genome(Path(genome_path))
    else:
        default = Path(__file__).resolve().parent.parent / "dna" / "genome" / "default_genome.yaml"
        genome = load_genome(default)
    orchestrator = CellularBrainOrchestrator.build_mvp(genome)
    # Load runtime config from monitoring_dashboard genome if present
    runtime_cfg: Dict[str, Any] = {}
    md_path = Path(__file__).resolve().parent.parent / "dna" / "genome" / "monitoring_dashboard.yaml"
    if md_path.exists():
        try:
            import yaml
            md_cfg = yaml.safe_load(md_path.read_text(encoding="utf-8"))
            runtime_cfg = md_cfg.get("monitoring_dashboard", {}).get("continuous_runtime", {})
        except Exception:
            pass
    return ContinuousRuntimeEngine(
        orchestrator=orchestrator,
        tick_interval=runtime_cfg.get("tick_interval", 1.0),
        checkpoint_interval_seconds=runtime_cfg.get("checkpoint_interval_seconds", 300.0),
        awake_duration=runtime_cfg.get("circadian", {}).get("awake_duration_seconds", 300.0),
        sleep_duration=runtime_cfg.get("circadian", {}).get("sleep_duration_seconds", 60.0),
        runtime_health_config=runtime_cfg.get("runtime_health", {}),
        emergency_halt_config=runtime_cfg.get("emergency_halt", {}),
        degradation_config=runtime_cfg.get("degradation", {}),
    )


@app.post("/api/runtime/start")
async def api_runtime_start(body: Dict[str, Any]) -> Dict[str, Any]:
    global _runtime_engine
    if _runtime_engine is not None:
        return {"error": "runtime_already_running", "state": _runtime_engine.snapshot()}
    genome_path = body.get("genome_path")
    _runtime_engine = _build_runtime_from_genome(genome_path)
    result = await _runtime_engine.start()
    return {"status": "started", **result}


@app.post("/api/runtime/control")
async def api_runtime_control(body: Dict[str, Any]) -> Dict[str, Any]:
    global _runtime_engine
    if _runtime_engine is None:
        return {"error": "runtime_not_running"}
    action = body.get("action", "")
    if action == "pause":
        await _runtime_engine.pause()
    elif action == "resume":
        await _runtime_engine.resume()
    elif action == "halt":
        await _runtime_engine.halt()
    elif action == "checkpoint":
        cp = await _runtime_engine.force_checkpoint()
        return {"status": "checkpoint_forced", "checkpoint": cp}
    else:
        return {"error": "unknown_action", "allowed": ["pause", "resume", "halt", "checkpoint"]}
    return {"status": "ok", "state": _runtime_engine.snapshot()}


@app.get("/api/runtime/state")
async def api_runtime_state() -> Dict[str, Any]:
    if _runtime_engine is None:
        return {"status": "not_running"}
    return _runtime_engine.snapshot()


@app.get("/api/runtime/health")
async def api_runtime_health() -> Dict[str, Any]:
    if _runtime_engine is None:
        return {"status": "not_running"}
    return _runtime_engine.health_monitor.snapshot()


@app.get("/api/runtime/checkpoints")
async def api_runtime_checkpoints(limit: int = 10) -> Dict[str, Any]:
    if _runtime_engine is None:
        return {"checkpoints": []}
    return {"checkpoints": _runtime_engine.checkpoint_manager.list_checkpoints(limit=limit)}


# --------------------------------------------------------------------------- #
# WebSocket
# --------------------------------------------------------------------------- #

app.include_router(create_websocket_router(_metrics_bus))

# --------------------------------------------------------------------------- #
# Static frontend (mounted last so API routes take precedence)
# --------------------------------------------------------------------------- #

if _static_dir.exists():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="dashboard")
