"""
loop — Agente ispettivo-diagnostico-ottimizzativo autonomo per SPEACE.

Ciclo IDO (Inspect → Diagnose → Optimize):
  1. Ispettore sistemico: scansiona cervello, organismo, runtime, DNA, strumenti.
  2. Diagnosta: analizza cause radice, correla issues, prioritizza.
  3. Ottimizzatore: applica correzioni, propone refactoring, monitora outcome.
"""

__version__ = "1.0.0"

from loop.agentic_loop import AgenticLoop

__all__ = ["AgenticLoop"]
