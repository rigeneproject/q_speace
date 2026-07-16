"""SPEACE Integration — avvia il team AGI automaticamente col cervello SPEACE.

Chiamata da ``LiveOrganism.run()`` nella fase di post-accensione,
avvia in background il web server FastAPI del team AGI (porta 8686)
e lo collega al contesto vivo dell'organismo.

Ora include il collegamento del livello di esecuzione azioni:
- ActionExecutor con riferimenti a ArchitecturePatchExecutor, HardVetoRouter, ecc.
- ActionSafetyGate collegato all'infrastruttura di sicurezza esistente
- Orchestrator collegato all'ActionExecutor
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from speace_agi_team.config import _resolve_model_and_endpoint

_agi_thread: Optional[threading.Thread] = None
_server: Optional[Any] = None

logger = logging.getLogger("speace.agi_team")


def _wire_action_executor(
    runtime: Any = None,
    brain_orchestrator: Any = None,
    agi_orchestrator: Any = None,
) -> Any:
    """Wire the ActionExecutor to existing SPEACE safety infrastructure.

    Connects:
    - ArchitecturePatchExecutor (from brain orchestrator or created)
    - HardVetoRouter (MM-APR, from self_improvement module)
    - CounterfactualArchitectureSandbox (from self_improvement module)
    - SubstrateStabilityGuard (from brain dynamics)
    - SafeRegulationExecutor (from monitoring)

    Returns the ActionExecutor instance.
    """
    from speace_agi_team.action_catalog import ActionCatalog
    from speace_agi_team.action_executor import ActionExecutor
    from speace_agi_team.action_safety_gate import ActionSafetyGate

    catalog = ActionCatalog()

    # ── Try to connect to existing safety infrastructure ───────────────
    patch_executor = None
    mmapr_router = None
    counterfactual_sandbox = None
    substrate_guard = None
    safe_regulation_executor = None
    self_mod_cycle = None

    # ArchitecturePatchExecutor — from brain orchestrator
    try:
        if brain_orchestrator is not None:
            # Try to find the patch executor attached to the orchestrator
            patch_executor = getattr(brain_orchestrator, '_patch_executor', None)
            if patch_executor is None:
                from speace_core.cellular_brain.self_improvement.architecture_patch_executor import ArchitecturePatchExecutor
                patch_executor = ArchitecturePatchExecutor(orchestrator=brain_orchestrator)
    except (ImportError, Exception) as e:
        logger.info("ArchitecturePatchExecutor non disponibile: %s", e)

    # HardVetoRouter (MM-APR) — from self_improvement module
    try:
        if brain_orchestrator is not None:
            mmapr_router = getattr(brain_orchestrator, '_mmapr_router', None)
            if mmapr_router is None:
                from speace_core.cellular_brain.self_improvement.mmapr_veto_router import HardVetoRouter
                mmapr_router = HardVetoRouter()
    except (ImportError, Exception) as e:
        logger.info("HardVetoRouter non disponibile: %s", e)

    # CounterfactualArchitectureSandbox — from self_improvement module
    try:
        if brain_orchestrator is not None:
            counterfactual_sandbox = getattr(brain_orchestrator, '_sandbox', None)
    except (ImportError, Exception) as e:
        logger.info("CounterfactualArchitectureSandbox non disponibile: %s", e)

    # SubstrateStabilityGuard — from brain dynamics
    try:
        if brain_orchestrator is not None:
            substrate_guard = getattr(brain_orchestrator, '_substrate_guard', None)
            if substrate_guard is None and runtime is not None:
                substrate_guard = getattr(runtime, '_substrate_guard', None)
    except (ImportError, Exception) as e:
        logger.info("SubstrateStabilityGuard non disponibile: %s", e)

    # SafeRegulationExecutor — from monitoring
    try:
        from speace_core.monitoring.safe_regulation_executor import SafeRegulationExecutor
        safe_regulation_executor = SafeRegulationExecutor()
    except (ImportError, Exception) as e:
        logger.info("SafeRegulationExecutor non disponibile: %s", e)

    # SelfModificationCycle — from self_improvement module
    try:
        if brain_orchestrator is not None:
            from speace_core.cellular_brain.self_improvement.self_modification_cycle import SelfModificationCycle
            self_mod_cycle = SelfModificationCycle(orchestrator=brain_orchestrator)
    except (ImportError, Exception) as e:
        logger.info("SelfModificationCycle non disponibile: %s", e)

    # ── Build the safety gate and executor ─────────────────────────────
    safety_gate = ActionSafetyGate(
        catalog=catalog,
        mmapr_router=mmapr_router,
        counterfactual_sandbox=counterfactual_sandbox,
        substrate_guard=substrate_guard,
        patch_executor=patch_executor,
    )

    executor = ActionExecutor(
        catalog=catalog,
        safety_gate=safety_gate,
        patch_executor=patch_executor,
        orchestrator=brain_orchestrator,
        self_mod_cycle=self_mod_cycle,
        safe_regulation_executor=safe_regulation_executor,
    )

    logger.info(
        "ActionExecutor collegato: patch_executor=%s, mmapr=%s, sandbox=%s, substrate=%s, self_mod=%s, safe_reg=%s",
        patch_executor is not None,
        mmapr_router is not None,
        counterfactual_sandbox is not None,
        substrate_guard is not None,
        self_mod_cycle is not None,
        safe_regulation_executor is not None,
    )

    return executor


def start_agi_team(
    host: str = "127.0.0.1",
    port: int = 8686,
    runtime: Any = None,
    orchestrator: Any = None,
) -> bool:
    """Avvia il team AGI in un thread background.

    Se il server e' gia' avviato, non fa nulla.

    Args:
        host: Host per il web server.
        port: Porta per il web server.
        runtime: Riferimento al runtime engine (per contesto vivo).
        orchestrator: Riferimento all'orchestrator (per contesto vivo).

    Returns:
        True se avviato, False se gia' in esecuzione.
    """
    global _agi_thread, _server

    if _agi_thread is not None and _agi_thread.is_alive():
        logger.info("AGI Team gia' attivo su http://%s:%d", host, port)
        return False

    try:
        import uvicorn
        from speace_agi_team.web_server import app, _agents, _plan, _orchestrator as ws_orch

        # Espone il runtime e orchestrator sull'app per contesto vivo
        app.state.speace_runtime = runtime
        app.state.speace_orchestrator = orchestrator

        # ── Wire ActionExecutor to safety infrastructure ───────────────
        action_executor = _wire_action_executor(
            runtime=runtime,
            brain_orchestrator=orchestrator,
            agi_orchestrator=ws_orch,
        )

        # ── Connect to AGI orchestrator with live runtime context ──────────
        from speace_agi_team.orchestrator import get_orchestrator
        try:
            agi_orch = get_orchestrator(
                _agents, _plan,
                runtime=runtime,
                brain_orchestrator=orchestrator,
            )
            agi_orch.set_action_executor(action_executor)
            logger.info(
                "AGI Orchestrator collegato: runtime=%s, brain_orchestrator=%s",
                runtime is not None,
                orchestrator is not None,
            )
        except Exception as e:
            logger.warning("Impossibile collegare ActionExecutor all'AGI Orchestrator: %s", e)

        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=False,
        )
        server = uvicorn.Server(config)
        _server = server  # salva riferimento per stop_agi_team()

        def _run():
            try:
                server.run()
            except Exception as exc:
                logger.error("AGI Team server fallito: %s", exc)

        _agi_thread = threading.Thread(
            target=_run, name="AGI-Team", daemon=True
        )
        _agi_thread.start()
        resolved = _resolve_model_and_endpoint()
        logger.info(
            "AGI Team avviato su http://%s:%d | modello=%s | provider=%s | endpoint=%s",
            host, port,
            resolved["model"], resolved["provider"], resolved["endpoint"],
        )
        return True

    except Exception as exc:
        logger.warning("AGI Team non avviato: %s", exc)
        return False


def stop_agi_team() -> None:
    """Arresta il team AGI (se in esecuzione)."""
    global _agi_thread, _server
    if _server is not None:
        _server.should_exit = True
        _server = None
    if _agi_thread is not None and _agi_thread.is_alive():
        logger.info("Arresto AGI Team...")
        _agi_thread = None
