"""
AgenticLoop — Orchestratore del ciclo IDO (Inspect → Diagnose → Optimize).

Coordina sequenzialmente le tre fasi:
  1. Ispezione sistemica di cervello, organismo, runtime, DNA, strumenti
  2. Diagnosi delle cause radice e analisi dei pattern
  3. Ottimizzazione automatica con correzioni e proposte

Il ciclo e pensato per:
  - Esecuzione continua (run_forever) con intervallo configurabile
  - Esecuzione singola (run_once) per CI/CD o audit manuali
  - Integrazione con altri sistemi SPEACE (evolution daemon, inspector, etc.)
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import signal
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

from loop import config as cfg
from loop.diagnostician import SystemDiagnostician
from loop.inspector import BrainInspector
from loop.models import IDOCycleResult
from loop.optimizer import SystemOptimizer
from loop.reporters import IDOReporter
from loop.utils import setup_logging, short_id, save_json

logger = logging.getLogger("loop.agentic")


class AgenticLoop:
    """Ciclo continuo di Ispezione → Diagnosi → Ottimizzazione per SPEACE."""

    def __init__(
        self,
        cycle_interval: int = 300,
        auto_fix: bool = True,
        dry_run: bool = False,
        verbose: bool = False,
    ):
        self.cycle_interval = cycle_interval
        self.cycle_count = 0
        self.running = True
        self.last_health_score: Optional[float] = None

        cfg.AUTO_FIX_ENABLED = auto_fix
        cfg.DRY_RUN = dry_run

        self.inspector = BrainInspector()
        self.diagnostician = SystemDiagnostician()
        self.optimizer = SystemOptimizer()
        self.reporter = IDOReporter()

        self._history: list[IDOCycleResult] = []

        log_level = "DEBUG" if verbose else cfg.LOG_LEVEL
        setup_logging(log_level, cfg.LOG_DIR / "loop.log")
        logger.info("AgenticLoop inizializzato | interval=%ds auto_fix=%s dry_run=%s",
                     cycle_interval, auto_fix, dry_run)

    # ------------------------------------------------------------------ #
    # Ciclo completo IDO
    # ------------------------------------------------------------------ #

    def run_cycle(self) -> IDOCycleResult:
        """Esegue un ciclo completo Inspect → Diagnose → Optimize."""
        self.cycle_count += 1
        cycle_id = f"ido-{short_id()}"
        started_at = datetime.datetime.now().isoformat()
        logger.info("=" * 72)
        logger.info("CICLO IDO #%s (n.%d) avviato", cycle_id, self.cycle_count)
        logger.info("=" * 72)

        system_health_before = self.last_health_score or 1.0

        # Fase 1: Ispezione
        inspection = self.inspector.inspect_all()

        # Fase 2: Diagnosi
        diagnosis = self.diagnostician.diagnose(inspection)

        # Fase 3: Ottimizzazione
        optimization = self.optimizer.optimize(inspection, diagnosis)

        finished_at = datetime.datetime.now().isoformat()
        duration = (datetime.datetime.fromisoformat(finished_at) -
                    datetime.datetime.fromisoformat(started_at)).total_seconds()

        system_health_after = diagnosis.system_health_score
        self.last_health_score = system_health_after
        improvement = round(system_health_after - system_health_before, 4)

        result = IDOCycleResult(
            cycle_id=cycle_id,
            started_at=started_at,
            finished_at=finished_at,
            duration_sec=round(duration, 3),
            inspection=inspection,
            diagnosis=diagnosis,
            optimization=optimization,
            system_health_before=system_health_before,
            system_health_after=system_health_after,
            improvement=improvement,
        )

        self._history.append(result)
        if len(self._history) > 50:
            self._history = self._history[-50:]

        self.reporter.print_cycle_summary(result)
        self._persist_cycle(result)

        return result

    # ------------------------------------------------------------------ #
    # Esecuzione continuativa
    # ------------------------------------------------------------------ #

    def run_forever(self) -> None:
        """Esegue il ciclo IDO in loop continuo fino a richiesta di arresto."""
        logger.info("AgenticLoop avviato in modalita continua (intervallo=%ds)", self.cycle_interval)
        self._install_signal_handlers()

        while self.running:
            try:
                self.run_cycle()
            except KeyboardInterrupt:
                logger.info("Interruzione richiesta (Ctrl+C)")
                self.running = False
                break
            except Exception as e:
                logger.exception("Ciclo IDO fallito: %s", e)
                traceback.print_exc()

            if self.running:
                logger.info("Prossimo ciclo tra %d secondi...", self.cycle_interval)
                try:
                    time.sleep(self.cycle_interval)
                except KeyboardInterrupt:
                    logger.info("Interruzione durante sleep")
                    self.running = False

        logger.info("AgenticLoop arrestato. Eseguiti %d cicli.", self.cycle_count)

    # ------------------------------------------------------------------ #
    # Stato e reporting
    # ------------------------------------------------------------------ #

    def get_status(self) -> Dict[str, Any]:
        """Restituisce lo stato attuale del loop."""
        return {
            "running": self.running,
            "cycles_completed": self.cycle_count,
            "cycle_interval": self.cycle_interval,
            "auto_fix": cfg.AUTO_FIX_ENABLED,
            "dry_run": cfg.DRY_RUN,
            "last_health_score": self.last_health_score,
            "history_size": len(self._history),
        }

    def get_last_report(self) -> Optional[IDOCycleResult]:
        return self._history[-1] if self._history else None

    # ------------------------------------------------------------------ #
    # Persistenza
    # ------------------------------------------------------------------ #

    def _persist_cycle(self, result: IDOCycleResult) -> None:
        report_dir = self.reporter.report_cycle(result)
        state = self.get_status()
        state["last_cycle_id"] = result.cycle_id
        state["last_report_dir"] = str(report_dir)
        save_json(cfg.STATE_DIR / "loop_state.json", state)

    def _install_signal_handlers(self) -> None:
        def handler(*_: object) -> None:
            logger.info("Segnale di arresto ricevuto")
            self.running = False
        for sig_name in ("SIGINT", "SIGTERM", "SIGBREAK"):
            sig = getattr(signal, sig_name, None)
            if sig is not None:
                try:
                    signal.signal(sig, handler)
                except (ValueError, OSError):
                    pass

    # ------------------------------------------------------------------ #
    # Chat / CLI interattiva
    # ------------------------------------------------------------------ #

    def chat_mode(self) -> None:
        """Modalita chat interattiva per comandi manuali."""
        print("=" * 72)
        print(" LOOP IDO — Agente ispettivo-diagnostico-ottimizzativo di SPEACE")
        print("=" * 72)
        print("Comandi: /scan /status /report /history /exit")
        print()

        while self.running:
            try:
                cmd = input("[LOOP] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not cmd:
                continue
            if cmd in ("/exit", "/quit", "/esci"):
                break
            elif cmd == "/scan":
                print("[LOOP] Avvio ciclo IDO manuale...")
                result = self.run_cycle()
                print(f"[LOOP] Completato: health={result.system_health_after:.3f} "
                      f"({result.improvement:+.3f}) findings={result.inspection.total_findings}")
            elif cmd == "/status":
                s = self.get_status()
                print(f"[LOOP] Stato: running={s['running']}, "
                      f"cicli={s['cycles_completed']}, "
                      f"health={s['last_health_score']}")
            elif cmd == "/report":
                last = self.get_last_report()
                if last:
                    self.reporter.print_cycle_summary(last)
                else:
                    print("[LOOP] Nessun ciclo eseguito.")
            elif cmd == "/history":
                print(f"[LOOP] Ultimi {len(self._history)} cicli:")
                for i, r in enumerate(self._history[-10:], 1):
                    print(f"  {i}. {r.cycle_id} | health={r.system_health_after:.3f} "
                          f"({r.improvement:+.3f}) | findings={r.inspection.total_findings}")
            else:
                print("[LOOP] Comandi: /scan /status /report /history /exit")


# ------------------------------------------------------------------ #
# CLI entry point
# ------------------------------------------------------------------ #

def parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="LOOP IDO — Ciclo Ispezione → Diagnosi → Ottimizzazione per SPEACE"
    )
    p.add_argument("--once", action="store_true", help="Esegui un solo ciclo")
    p.add_argument("--interval", type=int, default=cfg.CYCLE_INTERVAL_SEC,
                   help=f"Secondi tra cicli (default {cfg.CYCLE_INTERVAL_SEC})")
    p.add_argument("--no-fix", action="store_true", help="Disabilita auto-fix")
    p.add_argument("--dry-run", action="store_true", help="Solo analisi, senza scrittura")
    p.add_argument("--chat", action="store_true", help="Modalita chat interattiva")
    p.add_argument("--verbose", "-v", action="store_true", help="Log verboso")
    return p.parse_args(argv)


def main(argv: Optional[list] = None) -> int:
    args = parse_args(argv)

    loop = AgenticLoop(
        cycle_interval=args.interval,
        auto_fix=not args.no_fix,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    if args.chat:
        loop.chat_mode()
        return 0

    if args.once:
        loop.run_cycle()
        return 0

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Interrotto da tastiera.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
