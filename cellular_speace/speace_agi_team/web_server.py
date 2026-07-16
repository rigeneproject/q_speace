"""SPEACE AGI Team — FastAPI web server for agent management & chat."""

import sys
import io

# Forza UTF-8 su Windows per output con caratteri italiani
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import asyncio
import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from contextlib import asynccontextmanager
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
except ImportError as exc:
    raise SystemExit(
        "FastAPI is not installed.\n"
        "Install it with: pip install fastapi uvicorn websockets"
    ) from exc

from speace_agi_team.action_catalog import ActionCatalog
from speace_agi_team.action_executor import ActionExecutor
from speace_agi_team.action_proposal import ActionProposal, ActionProposalStatus
from speace_agi_team.action_safety_gate import ActionSafetyGate
from speace_agi_team.config import AgentConfig, register_agent, AGENT_REGISTRY
from speace_agi_team.agent_base import AgentBase
from speace_agi_team.supervisor_agents import (
    ChiefArchitect, BrainSupervisor, DNASupervisor,
    OrganismSupervisor, MemorySupervisor, SelfImprovementSupervisor,
    EmbodiedCognitionSupervisor, AdvancedLanguageSupervisor,
    LongTermPlanningSupervisor, SelfAwarenessSupervisor,
    register_supervisors,
)
from speace_agi_team.technical_agents import (
    NeuronTechnician, SynapseTechnician, RegionTechnician,
    GenomeTechnician, RuntimeTechnician, DefenseTechnician,
    MemoryTechnician, EvolutionTechnician, NetworkTechnician,
    EmbodimentTechnician, register_technicians,
)
from speace_agi_team.engineering_plan import EngineeringPlan
from speace_agi_team.orchestrator import Orchestrator, get_orchestrator, LoadBalancer
from speace_agi_team.web_search import DocumentFetcher, WebSearcher, research


# ── Lifespan ─────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _cached_config, _main_loop
    _main_loop = asyncio.get_event_loop()
    _cached_config = AgentConfig()
    _build_agents(_cached_config)
    # Start orchestrator: auto-analysis, health monitor, load balancer
    # Pass live runtime references for real-time context
    global _orchestrator
    runtime = getattr(app.state, "speace_runtime", None)
    brain_orchestrator = getattr(app.state, "speace_orchestrator", None)
    _orchestrator = get_orchestrator(
        _agents, _plan,
        runtime=runtime,
        brain_orchestrator=brain_orchestrator,
    )
    _orchestrator.start()
    print(f"[AGI Team] {len(_agents)} agenti inizializzati con modello {_cached_config.model} ({_cached_config.provider})")
    print("[AGI Team] Orchestrator avviato — auto-analisi e monitor attivi")
    print(f"[AGI Team] Contesto live: runtime={runtime is not None}, brain_orchestrator={brain_orchestrator is not None}")

    # ── Avvia SPEACE Anemos in background (porta 8787) ─────────────
    try:
        from speace_agi_team.anemos.anemos_server import start_anemos_server, stop_anemos_server
        if start_anemos_server(host="127.0.0.1", port=8787):
            print("[AGI Team] SPEACE Anemos attivo su http://127.0.0.1:8787")
    except Exception as e:
        print(f"[AGI Team] Anemos non avviato: {e}")

    yield
    if _orchestrator:
        _orchestrator.stop()
    try:
        stop_anemos_server()
    except Exception:
        pass


app = FastAPI(title="SPEACE AGI Team", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ── Pydantic request/response models ─────────────────────────────────────
class ChatRequest(BaseModel):
    message: str = ""


class BroadcastRequest(BaseModel):
    message: str = ""


class TaskRequest(BaseModel):
    title: str = "Untitled"
    description: str = ""
    agent_id: str = "chief_architect"
    milestone_id: str = ""
    priority: str = "medium"


class CompleteTaskRequest(BaseModel):
    outcome: str = "success"


class MilestoneRequest(BaseModel):
    progress: float = 0.0
    status: Optional[str] = None


class ExecuteTaskRequest(BaseModel):
    task_id: Optional[str] = None
    title: str = "Untitled"
    description: str = ""
    agent_id: str = "auto"
    milestone_id: str = ""
    priority: str = "medium"


class AnalyzeAllRequest(BaseModel):
    sample: bool = False  # If True, run only on supervisors


class WebSearchRequest(BaseModel):
    query: str
    max_results: int = 5


class FetchRequest(BaseModel):
    url: str


class ResearchRequest(BaseModel):
    query: str
    max_results: int = 5
    fetch_top: int = 2
    fetch_max_chars: int = 6000


class AgentResearchRequest(BaseModel):
    query: str
    max_results: int = 5
    fetch_top: int = 2
    fetch_max_chars: int = 6000
    synthesis: bool = True  # If True, have the agent synthesize the results


# ── Action Execution Request/Response models ─────────────────────────────

class ActionProposeRequest(BaseModel):
    agent_id: str = ""
    action_type: str = ""
    target: str = ""
    new_value: Any = None
    operation: str = "set"
    justification: str = ""
    evidence: Optional[Dict[str, Any]] = None
    old_value: Any = None


class HumanApprovalRequest(BaseModel):
    approver: str = ""
    notes: str = ""


class HumanRejectRequest(BaseModel):
    rejector: str = ""
    reason: str = ""


class AnalyzeAndActRequest(BaseModel):
    agent_id: str = ""
    auto_execute: bool = False
    context: Optional[Dict[str, Any]] = None


# ── Agent Singleton Registry ─────────────────────────────────────────────
_agents: Dict[str, AgentBase] = {}
_plan = EngineeringPlan()
_ws_connections: List[WebSocket] = []
_orchestrator: Optional[Orchestrator] = None
_llm_lock = threading.Lock()
_main_loop: Optional[asyncio.AbstractEventLoop] = None


def _build_agents(config: AgentConfig):
    global _agents
    supervisors = {
        "chief_architect": ChiefArchitect(config),
        "brain_supervisor": BrainSupervisor(config),
        "dna_supervisor": DNASupervisor(config),
        "organism_supervisor": OrganismSupervisor(config),
        "memory_supervisor": MemorySupervisor(config),
        "selfimprovement_supervisor": SelfImprovementSupervisor(config),
        "embodied_cognition_supervisor": EmbodiedCognitionSupervisor(config),
        "advanced_language_supervisor": AdvancedLanguageSupervisor(config),
        "longterm_planning_supervisor": LongTermPlanningSupervisor(config),
        "self_awareness_supervisor": SelfAwarenessSupervisor(config),
    }
    technicians = {
        "neuron_tech": NeuronTechnician(config),
        "synapse_tech": SynapseTechnician(config),
        "region_tech": RegionTechnician(config),
        "genome_tech": GenomeTechnician(config),
        "runtime_tech": RuntimeTechnician(config),
        "defense_tech": DefenseTechnician(config),
        "memory_tech": MemoryTechnician(config),
        "evolution_tech": EvolutionTechnician(config),
        "network_tech": NetworkTechnician(config),
        "embodiment_tech": EmbodimentTechnician(config),
    }
    _agents = {**supervisors, **technicians}

    register_supervisors()
    register_technicians()


def _get_speace_context() -> Dict[str, Any]:
    """Read live SPEACE state from runtime + organism_observer data files.

    Primary source: runtime engine live state (passed via app.state).
    Fallback: organism_observer topology_history + embodiment files.
    """
    ctx: Dict[str, Any] = {}

    # ── Primary: live context from runtime engine ────────────────────
    runtime = getattr(app.state, "speace_runtime", None)
    orchestrator = getattr(app.state, "speace_orchestrator", None)

    if runtime is not None:
        try:
            snap = runtime.snapshot() if hasattr(runtime, "snapshot") else {}
            ctx["tick"] = snap.get("tick", 0)
            ctx["state"] = snap.get("state", "unknown")
            ctx["phase"] = snap.get("circadian_phase", "unknown")
            ctx["health_score"] = snap.get("health_score", 0.0)
        except Exception:
            pass

    if orchestrator is not None:
        try:
            m = orchestrator.latest_metrics if hasattr(orchestrator, "latest_metrics") else None
            if m is not None:
                phi = getattr(m, "coherence_phi", 0.0) or 0.0
                mean_energy = getattr(m, "mean_energy", 0.0) or 0.0
                ctx["coherence_phi"] = phi
                ctx["mean_energy"] = mean_energy
                ctx["active_neurons"] = getattr(m, "active_neurons", 0)
                energy_efficiency = max(0.0, min(1.0, mean_energy))
                ctx["energy_efficiency"] = energy_efficiency
                ctx["cognitive_score"] = max(0.0, min(1.0, 0.55 * phi + 0.35 * energy_efficiency + 0.10))
            fs = orchestrator.get_field_state() if hasattr(orchestrator, "get_field_state") else None
            if fs is not None:
                ctx["ilf_value"] = getattr(fs, "ilf_value", 0.0)
                ctx["field_stability"] = getattr(fs, "field_stability", 0.0)
        except Exception:
            pass

    # ── Fallback: organism_observer topology_history ────────────────
    if not ctx:
        data_root = Path("data")
        topo_path = data_root / "organism_observer" / "topology_history.jsonl"
        if topo_path.exists():
            try:
                lines = topo_path.read_text(encoding="utf-8").strip().split("\n")
                if lines:
                    last = json.loads(lines[-1])
                    ctx["tick"] = last.get("tick", 0)
                    ctx["node_count"] = last.get("node_count", 0)
                    ctx["edge_count"] = last.get("edge_count", 0)
                    ctx["modularity_q"] = last.get("modularity_q", 0.0)
                    ctx["small_world_sigma"] = last.get("small_world_sigma", 0.0)
            except (json.JSONDecodeError, OSError):
                pass

        # Morphologies salvate
        morph_path = data_root / "organism_observer" / "morphologies.jsonl"
        if morph_path.exists():
            try:
                lines = morph_path.read_text(encoding="utf-8").strip().split("\n")
                if lines:
                    last = json.loads(lines[-1])
                    ctx["best_fitness"] = last.get("fitness_score", 0.0)
                    ctx["best_ilf"] = last.get("ilf_value", 0.0)
            except (json.JSONDecodeError, OSError):
                pass

        # Embodiment
        emb_path = data_root / "embodiment" / "environment_state.jsonl"
        if emb_path.exists():
            try:
                lines = emb_path.read_text(encoding="utf-8").strip().split("\n")
                if lines:
                    last = json.loads(lines[-1])
                    state = last.get("state", {})
                    if state:
                        ctx["cpu"] = state.get("cpu_avg", 0)
                        ctx["memory"] = state.get("mem_used", 0)
                        ctx["disk"] = state.get("disk_used", 0)
                        ctx["temperature"] = state.get("temp_avg", 0)
            except (json.JSONDecodeError, OSError):
                pass

    # Genoma (sempre disponibile)
    ctx.setdefault("speace_version", "0.9.0")
    ctx.setdefault("cell_types", [
        "digital_neuron", "auditory", "broca", "wernicke",
        "semantic_pointer", "astrocyte", "microglia", "oligodendrocyte",
        "sensor", "actuator", "energy",
    ])
    ctx.setdefault("brain_regions", [
        "sensory", "limbic", "hippocampus", "default_mode",
        "prefrontal", "cerebellar", "motor", "brainstem_homeostatic",
    ])

    if not ctx or not ctx.get("cell_types") or not ctx.get("brain_regions"):
        ctx["status"] = "no_data"
        ctx["message"] = "SPEACE runtime not connected. Start SPEACE brain first."

    return ctx


async def _broadcast(msg: Dict):
    dead = []
    for ws in _ws_connections:
        try:
            await ws.send_json(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_connections.remove(ws)


# ── REST API ─────────────────────────────────────────────────────────────

_cached_config: Optional[AgentConfig] = None


@app.get("/api/status")
def api_status():
    global _cached_config
    if _cached_config is None:
        _cached_config = AgentConfig()
    return {
        "status": "online",
        "agents_count": len(_agents),
        "plan_progress": _plan.overall_progress(),
        "model": _cached_config.model,
    }


@app.get("/api/agents")
def api_list_agents(type_filter: Optional[str] = None):
    result = []
    for aid, agent in _agents.items():
        s = agent.get_status_summary()
        if type_filter and s.get("role") and type_filter not in str(s.get("role")).lower():
            continue
        result.append(s)
    return {"agents": result}


@app.get("/api/agents/{agent_id}")
def api_agent_detail(agent_id: str):
    agent = _agents.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent {agent_id} not found")
    return agent.get_status_summary()


@app.get("/api/agents/{agent_id}/conversation")
def api_agent_conversation(agent_id: str):
    agent = _agents.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent {agent_id} not found")
    return {"conversation": agent.get_conversation()}


@app.post("/api/agents/{agent_id}/chat")
async def api_agent_chat(agent_id: str, body: ChatRequest):
    agent = _agents.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent {agent_id} not found")
    message = body.message
    if not message:
        raise HTTPException(400, "Message is required")
    response = agent.chat(message)
    await _broadcast({
        "type": "agent_chat",
        "agent_id": agent_id,
        "message": message,
        "response": response,
    })
    return {"response": response}


@app.post("/api/agents/{agent_id}/analyze")
async def api_agent_analyze(agent_id: str):
    agent = _agents.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent {agent_id} not found")
    context = _get_speace_context()
    finding = agent.analyze(context)
    await _broadcast({
        "type": "agent_analysis",
        "agent_id": agent_id,
        "finding": finding,
    })
    return finding


@app.post("/api/agents/{agent_id}/clear")
def api_agent_clear(agent_id: str):
    agent = _agents.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent {agent_id} not found")
    agent.clear_conversation()
    return {"status": "cleared"}


# ── All-Agent Broadcast ──────────────────────────────────────────────────
@app.post("/api/broadcast")
async def api_broadcast(body: BroadcastRequest):
    """Send the same message to every agent in parallel.

    Uses asyncio.to_thread to offload each blocking LLM chat to a worker
    thread, so the 20-agent broadcast finishes in roughly the time of a
    single chat rather than 20x serial. Per-agent timing is included in
    the response payload so callers can compute per-agent latency.
    """
    message = body.message
    if not message:
        raise HTTPException(400, "Message is required")
    t0 = time.perf_counter()

    async def _one(aid: str, agent):
        s = time.perf_counter()
        try:
            chat_fn = getattr(agent, "_chat_with_retry", None) or agent.chat
            resp = await asyncio.to_thread(chat_fn, message)
            return aid, {"response": resp, "duration_sec": round(time.perf_counter() - s, 3), "ok": True}
        except Exception as exc:
            return aid, {"response": "ERRORE: " + repr(exc), "duration_sec": round(time.perf_counter() - s, 3), "ok": False}

    pairs = await asyncio.gather(*(_one(aid, agent) for aid, agent in _agents.items()))
    responses = {aid: payload for aid, payload in pairs}
    total_sec = round(time.perf_counter() - t0, 3)
    await _broadcast({
        "type": "broadcast",
        "message": message,
        "responses": responses,
        "total_sec": total_sec,
        "agent_count": len(responses),
    })
    return {"responses": responses, "total_sec": total_sec, "agent_count": len(responses)}


# ── SPEACE Context & Metrics ──────────────────────────────────────────────
@app.get("/api/speace/context")
def api_speace_context():
    return _get_speace_context()


@app.get("/api/metrics")
def api_metrics():
    """Organism-level metrics: phi, energy, cognitive_score, health_score."""
    ctx = _get_speace_context()
    return {
        "coherence_phi": ctx.get("coherence_phi", 0.0),
        "mean_energy": ctx.get("mean_energy", 0.0),
        "energy_efficiency": ctx.get("energy_efficiency", 0.0),
        "cognitive_score": ctx.get("cognitive_score", 0.0),
        "health_score": ctx.get("health_score", 0.0),
        "ilf_value": ctx.get("ilf_value", 0.0),
        "field_stability": ctx.get("field_stability", 0.0),
        "active_neurons": ctx.get("active_neurons", 0),
        "tick": ctx.get("tick", 0),
    }


# ── Engineering Plan ─────────────────────────────────────────────────────
@app.get("/api/plan")
def api_get_plan():
    return _plan.get_milestone_progress_report()


@app.get("/api/plan/tasks")
def api_list_tasks():
    return {"tasks": _plan.tasks}


@app.post("/api/plan/task")
async def api_add_task(body: TaskRequest):
    task = _plan.add_task(
        title=body.title,
        description=body.description,
        agent_id=body.agent_id,
        milestone_id=body.milestone_id,
        priority=body.priority,
    )
    await _broadcast({"type": "plan_task_added", "task": task})
    return task


@app.post("/api/plan/task/{task_id}/complete")
async def api_complete_task(task_id: str, body: CompleteTaskRequest):
    outcome = body.outcome
    success = _plan.complete_task(task_id, outcome)
    if not success:
        raise HTTPException(404, f"Task {task_id} not found")
    await _broadcast({
        "type": "plan_task_completed",
        "task_id": task_id,
        "outcome": outcome,
    })
    return {"status": "ok"}


@app.post("/api/plan/milestone/{milestone_id}")
async def api_update_milestone(milestone_id: str, body: MilestoneRequest):
    progress = body.progress
    status = body.status
    success = _plan.update_milestone(milestone_id, progress, status)
    if not success:
        raise HTTPException(404, f"Milestone {milestone_id} not found")
    await _broadcast({
        "type": "plan_milestone_updated",
        "milestone_id": milestone_id,
        "progress": progress,
        "status": status,
    })
    return {"status": "ok"}


# ── Orchestrator Endpoints (REPORT_FINALE §8) ──────────────────────────
@app.get("/api/orchestrator/status")
def api_orchestrator_status():
    if not _orchestrator:
        return {"running": False, "message": "Orchestrator not started"}
    return _orchestrator.get_status()


@app.post("/api/orchestrator/tick")
async def api_orchestrator_tick():
    """Force a single orchestrator tick (bypasses the wait timer).

    Runs in a background thread to avoid blocking the API while the LLM responds.
    """
    if not _orchestrator:
        raise HTTPException(503, "Orchestrator not started")

    def _do_tick():
        with _llm_lock:
            try:
                actions = _orchestrator.scheduler.tick()
                health = _orchestrator.health_monitor.check()
                if health.get("alerts") and _main_loop is not None:
                    try:
                        asyncio.run_coroutine_threadsafe(
                            _broadcast({"type": "health_alerts", "alerts": health["alerts"]}),
                            _main_loop,
                        )
                    except Exception:
                        pass
            except Exception as e:
                print(f"[orchestrator tick] error: {e}")

    threading.Thread(target=_do_tick, daemon=True).start()
    return {"status": "started", "message": "Tick in esecuzione in background"}


@app.get("/api/orchestrator/health")
def api_health():
    if not _orchestrator:
        raise HTTPException(503, "Orchestrator not started")
    return _orchestrator.health_monitor.check()


@app.get("/api/orchestrator/load")
def api_load():
    if not _orchestrator:
        return {"distribution": {}}
    return {"distribution": _orchestrator.load_balancer.distribution()}


@app.post("/api/plan/task/{task_id}/execute")
async def api_execute_task(task_id: str, body: Optional[ExecuteTaskRequest] = None):
    """End-to-end execution: technician analyzes + supervisor validates."""
    if not _orchestrator:
        raise HTTPException(503, "Orchestrator not started")

    # Look up existing task
    task = next((t for t in _plan.tasks if t["id"] == task_id), None)
    if not task:
        # Allow creating ad-hoc task via body
        if not body:
            raise HTTPException(404, f"Task {task_id} not found and no body provided")
        task = {
            "id": task_id,
            "title": body.title,
            "description": body.description,
            "agent_id": body.agent_id,
            "milestone_id": body.milestone_id,
            "priority": body.priority,
        }
    else:
        # Allow override via body
        if body and body.title != "Untitled":
            task = {**task, "title": body.title, "description": body.description,
                    "agent_id": body.agent_id or task.get("agent_id", "auto"),
                    "milestone_id": body.milestone_id or task.get("milestone_id", "")}

    record = _orchestrator.execute_task(task)
    await _broadcast({
        "type": "task_executed",
        "task_id": task_id,
        "outcome": record.get("outcome"),
        "agent_id": record.get("agent_id"),
    })
    return record


@app.post("/api/plan/task/{task_id}/auto-assign")
def api_auto_assign(task_id: str):
    """Apply load balancing to suggest the best technician for this task."""
    task = next((t for t in _plan.tasks if t["id"] == task_id), None)
    if not task:
        raise HTTPException(404, f"Task {task_id} not found")
    suggested = _orchestrator._auto_pick_technician(task)
    task["agent_id"] = suggested
    _plan.save()
    return {"task_id": task_id, "assigned_to": suggested}


# ── Action Execution Endpoints ───────────────────────────────────────────

def _get_action_executor() -> ActionExecutor:
    """Get the action executor from the orchestrator, or raise 503."""
    if not _orchestrator or not _orchestrator.action_executor:
        raise HTTPException(503, "Action executor not available. Start the AGI team with action support first.")
    return _orchestrator.action_executor


@app.post("/api/actions/propose")
def api_action_propose(body: ActionProposeRequest):
    """Create a new action proposal from an agent."""
    executor = _get_action_executor()
    agent = _agents.get(body.agent_id)
    if not agent:
        raise HTTPException(404, f"Agent {body.agent_id} not found")

    proposal = agent.propose_action(
        action_type=body.action_type,
        target=body.target,
        new_value=body.new_value,
        operation=body.operation,
        justification=body.justification,
        evidence=body.evidence or {},
        old_value=body.old_value,
    )
    if proposal is None:
        raise HTTPException(403, f"Agent {body.agent_id} not authorized for {body.action_type}:{body.target}")

    # Evaluate through safety gate
    gate_result = executor.safety_gate.evaluate(proposal)
    executor._store_proposal(proposal)

    return {
        "proposal": proposal.model_dump(),
        "gate_result": {
            "decision": gate_result.final_decision,
            "conditions": gate_result.conditions,
            "blocked_reason": gate_result.blocked_reason,
            "human_approval_required": gate_result.human_approval_required,
        },
    }


@app.post("/api/actions/{proposal_id}/execute")
async def api_action_execute(proposal_id: str):
    """Execute a proposal through the full safety pipeline."""
    executor = _get_action_executor()
    proposal = executor.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(404, f"Proposal {proposal_id} not found")

    result = executor.execute_pipeline(proposal)
    await _broadcast({
        "type": "action_executed",
        "proposal_id": proposal_id,
        "status": result.final_status,
    })
    return result.model_dump()


@app.post("/api/actions/{proposal_id}/rollback")
def api_action_rollback(proposal_id: str):
    """Rollback an executed action proposal."""
    executor = _get_action_executor()
    proposal = executor.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(404, f"Proposal {proposal_id} not found")

    success = executor._rollback(proposal)
    if success:
        proposal.transition_to(ActionProposalStatus.ROLLED_BACK, reason="manual_rollback")
        executor._store_proposal(proposal)
    return {"proposal_id": proposal_id, "rollback_success": success}


@app.get("/api/actions/proposals")
def api_action_proposals(status: Optional[str] = None, agent_id: Optional[str] = None, limit: int = 100):
    """List action proposals, optionally filtered by status or agent."""
    executor = _get_action_executor()
    proposals = executor.list_proposals(status=status, agent_id=agent_id, limit=limit)
    return {"proposals": [p.model_dump() for p in proposals]}


@app.get("/api/actions/catalog")
def api_action_catalog(agent_id: Optional[str] = None):
    """Get the action catalog, optionally filtered by agent."""
    catalog = ActionCatalog()
    if agent_id:
        return {"agent_id": agent_id, "actions": catalog.get_actions_for(agent_id)}
    return {"catalog": catalog.get_full_catalog()}


@app.post("/api/actions/{proposal_id}/approve")
def api_action_approve(proposal_id: str, body: HumanApprovalRequest):
    """Human approval for HIGH/CRITICAL actions."""
    executor = _get_action_executor()
    proposal = executor.approve_proposal(proposal_id, approver=body.approver, notes=body.notes)
    if not proposal:
        raise HTTPException(404, f"Proposal {proposal_id} not found or not in HUMAN_REVIEW status")
    return {"proposal": proposal.model_dump()}


@app.post("/api/actions/{proposal_id}/reject")
def api_action_reject(proposal_id: str, body: HumanRejectRequest):
    """Human rejection for an action proposal."""
    executor = _get_action_executor()
    proposal = executor.reject_proposal(proposal_id, rejector=body.rejector, reason=body.reason)
    if not proposal:
        raise HTTPException(404, f"Proposal {proposal_id} not found")
    return {"proposal": proposal.model_dump()}


@app.get("/api/actions/audit")
def api_action_audit(n: int = 50):
    """Read the last N entries from the action audit trail."""
    audit_path = Path("data/agi_team/action_audit.jsonl")
    if not audit_path.exists():
        return {"entries": []}
    try:
        lines = audit_path.read_text(encoding="utf-8").strip().split("\n")
        entries = []
        for line in lines[-n:]:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return {"entries": entries}
    except OSError:
        return {"entries": []}


@app.post("/api/agents/{agent_id}/analyze-and-act")
async def api_agent_analyze_and_act(agent_id: str, body: AnalyzeAndActRequest):
    """Analyze SPEACE context and propose actions. Optionally auto-execute."""
    agent = _agents.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent {agent_id} not found")

    context = body.context or _get_speace_context()
    proposals = agent.propose_action_from_analysis(context)

    results = []
    if body.auto_execute and _orchestrator and _orchestrator.action_executor:
        for proposal in proposals:
            result = _orchestrator.action_executor.execute_pipeline(proposal)
            results.append(result.model_dump())
    else:
        # Just return the proposals without executing
        for proposal in proposals:
            if _orchestrator and _orchestrator.action_executor:
                _orchestrator.action_executor._store_proposal(proposal)
            results.append({"proposal": proposal.model_dump(), "executed": False})

    await _broadcast({
        "type": "agent_analyze_and_act",
        "agent_id": agent_id,
        "proposal_count": len(proposals),
    })

    return {
        "agent_id": agent_id,
        "proposal_count": len(proposals),
        "results": results,
    }


@app.post("/api/actions/supervisor-cycle")
async def api_supervisor_cycle():
    """Run a supervisor-directed action cycle: supervisors propose, technicians execute."""
    if not _orchestrator or not _orchestrator.action_executor:
        raise HTTPException(503, "Orchestrator or ActionExecutor not available")

    def _do_cycle():
        with _llm_lock:
            try:
                ctx = _get_speace_context()
                return _orchestrator.supervisor_directed_action_cycle(ctx)
            except Exception as e:
                return {"error": str(e)}

    # Run in background thread since LLM calls are blocking
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as pool:
        future = pool.submit(_do_cycle)
        try:
            result = future.result(timeout=300)  # 5 min timeout
        except concurrent.futures.TimeoutError:
            raise HTTPException(504, "Supervisor cycle timed out")

    await _broadcast({
        "type": "supervisor_cycle_completed",
        "timestamp": time.time(),
    })
    return result


@app.get("/api/actions/pending-human-review")
def api_pending_human_review():
    """List proposals that are pending human review."""
    if not _orchestrator or not _orchestrator.action_executor:
        raise HTTPException(503, "ActionExecutor not available")

    proposals = _orchestrator.action_executor.list_proposals(
        status=ActionProposalStatus.HUMAN_REVIEW.value
    )
    return {
        "pending": [
            {
                "proposal_id": p.proposal_id,
                "agent_id": p.agent_id,
                "action_type": p.action_type,
                "target": p.target,
                "risk_level": p.risk_level if isinstance(p.risk_level, str) else p.risk_level.value,
                "justification": p.justification,
                "created_at": p.created_at,
            }
            for p in proposals
        ],
        "count": len(proposals),
    }


@app.post("/api/agents/analyze-all")
async def api_analyze_all(body: AnalyzeAllRequest = AnalyzeAllRequest()):
    """Run analyze() across multiple agents, with load balancing. Runs in background."""
    if not _orchestrator:
        raise HTTPException(503, "Orchestrator not started")

    ctx = _get_speace_context()
    results = []
    targets = [a for a in _agents.values()
               if (a.agent_id.endswith("_supervisor") or a.agent_id == "chief_architect")]
    if not body.sample:
        targets = list(_agents.values())

    def _do_analyze():
        completed = 0
        for agent in sorted(targets, key=lambda a: _orchestrator.load_balancer.workload_score(a.agent_id)):
            _orchestrator.load_balancer.record_analysis(agent.agent_id)
            with _llm_lock:
                try:
                    f = agent.analyze(ctx)
                    with agent._findings_lock:
                        agent.findings.append({
                            "agent_id": agent.agent_id,
                            "name": agent.name,
                            "preview": f.get("analysis", "")[:500],
                            "ts": time.time(),
                        })
                except Exception as e:
                    with agent._findings_lock:
                        agent.findings.append({
                            "agent_id": agent.agent_id,
                            "error": str(e),
                            "ts": time.time(),
                        })
            completed += 1

    threading.Thread(target=_do_analyze, daemon=True).start()
    return {"status": "started", "total": len(targets), "message": f"Analisi di {len(targets)} agenti in background"}


# ── Auto-Analysis Findings ──────────────────────────────────────────────
@app.get("/api/auto-analysis/recent")
def api_auto_analysis_recent(n: int = 20):
    log_path = Path("data/agi_team/auto_analysis.jsonl")
    if not log_path.exists():
        return {"findings": []}
    try:
        lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        findings = []
        for line in lines[-n:]:
            try:
                findings.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return {"findings": findings}
    except OSError:
        return {"findings": []}


@app.get("/api/health/alerts")
def api_health_alerts(n: int = 20):
    log_path = Path("data/agi_team/health_alerts.jsonl")
    if not log_path.exists():
        return {"alerts": []}
    try:
        lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        alerts = []
        for line in lines[-n:]:
            try:
                alerts.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return {"alerts": alerts}
    except OSError:
        return {"alerts": []}


# ── Web Search & Document Fetch ───────────────────────────────────────
@app.post("/api/web/search")
async def api_web_search(body: WebSearchRequest):
    """Direct web search via DuckDuckGo. No agent involved."""
    s = WebSearcher()
    results = s.search(body.query, max_results=body.max_results)
    return {"query": body.query, "results": results, "count": len(results)}


@app.post("/api/web/fetch")
async def api_web_fetch(body: FetchRequest):
    """Fetch and extract text from a URL."""
    f = DocumentFetcher()
    doc = f.fetch(body.url)
    return doc


@app.post("/api/web/research")
async def api_web_research(body: ResearchRequest):
    """Combined search + fetch: returns top results with extracted text."""
    data = research(body.query, max_results=body.max_results,
                    fetch_top=body.fetch_top, fetch_max_chars=body.fetch_max_chars)
    return data


@app.post("/api/agents/{agent_id}/research")
async def api_agent_research(agent_id: str, body: AgentResearchRequest):
    """Let a specific agent run a web research and synthesize the results.

    The agent's LLM is queried with the research summary as context.
    """
    agent = _agents.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent {agent_id} not found")

    # Run the research (synchronous; cached after first call)
    research_data = agent.research_web(
        body.query, max_results=body.max_results,
        fetch_top=body.fetch_top, fetch_max_chars=body.fetch_max_chars,
    )
    history = agent.get_research_history(5)

    response_payload: Dict[str, Any] = {
        "agent_id": agent_id,
        "query": body.query,
        "results": research_data.get("results", []),
        "documents": research_data.get("documents", []),
        "synthesis": None,
        "research_history": history,
    }

    if body.synthesis:
        summary = agent.research_summary(
            body.query, fetch_top=body.fetch_top, fetch_max_chars=body.fetch_max_chars,
        )
        prompt = (
            f"Hai effettuato la seguente ricerca web per migliorare SPEACE:\n\n"
            f"Query: {body.query}\n\n"
            f"Risultati trovati:\n{summary}\n\n"
            f"Basandoti SOLO su queste fonti, fornisci una sintesi strutturata in italiano:\n"
            f"1. Sintesi dei punti chiave emersi dalla letteratura\n"
            f"2. Raccomandazioni concrete per SPEACE (cervello digitale neurocellulare)\n"
            f"3. Citazioni o riferimenti specifici dai documenti analizzati\n"
            f"4. Eventuali limitazioni o gap informativi riscontrati"
        )
        synthesis = agent.chat(prompt)
        response_payload["synthesis"] = synthesis
        await _broadcast({
            "type": "agent_research",
            "agent_id": agent_id,
            "query": body.query,
            "synthesis_preview": synthesis[:300],
        })

    return response_payload


@app.get("/api/agents/{agent_id}/research-history")
def api_agent_research_history(agent_id: str, n: int = 20):
    agent = _agents.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent {agent_id} not found")
    return {"agent_id": agent_id, "history": agent.get_research_history(n)}


# ── Websocket ────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _ws_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        _ws_connections.remove(websocket)
    except Exception:
        if websocket in _ws_connections:
            _ws_connections.remove(websocket)


# ── Frontend ─────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = static_dir / "index.html"
    if index_path.exists():
        return HTMLResponse(index_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>SPEACE AGI Team</h1><p>Frontend not found</p>")


# ── Runner ───────────────────────────────────────────────────────────────
def run_server(host: str = "127.0.0.1", port: int = 8686):
    import uvicorn
    print("\n" + "="*50)
    print("  SPEACE AGI TEAM - Dashboard & Chat")
    print(f"  URL: http://{host}:{port}")
    print(f"  Modello: {AgentConfig().model}")
    print("  Agenti: 20 (10 supervisor + 10 tecnici)")
    print("="*50 + "\n")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
