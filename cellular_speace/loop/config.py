from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path("C:/cellular_speace")

LOOP_DIR = Path(__file__).resolve().parent

DATA_DIR = PROJECT_ROOT / "data" / "loop"
LOG_DIR = DATA_DIR / "logs"
REPORT_DIR = DATA_DIR / "reports"
STATE_DIR = DATA_DIR / "state"
BACKUP_DIR = DATA_DIR / "backups"
DIAGNOSIS_DIR = DATA_DIR / "diagnoses"

for d in (DATA_DIR, LOG_DIR, REPORT_DIR, STATE_DIR, BACKUP_DIR, DIAGNOSIS_DIR):
    d.mkdir(parents=True, exist_ok=True)

INSPECTION_TARGETS = [
    {"path": PROJECT_ROOT / "speace_core", "label": "Speace Core (Cervello + Organismo)", "depth": "full"},
    {"path": PROJECT_ROOT / "speace_core" / "cellular_brain", "label": "Cervello Cellulare", "depth": "full"},
    {"path": PROJECT_ROOT / "speace_core" / "cellular_brain" / "cells", "label": "Cellule", "depth": "full"},
    {"path": PROJECT_ROOT / "speace_core" / "cellular_brain" / "regulation", "label": "Regolazione", "depth": "full"},
    {"path": PROJECT_ROOT / "speace_core" / "cellular_brain" / "regions", "label": "Regioni Cerebrali", "depth": "full"},
    {"path": PROJECT_ROOT / "speace_core" / "cellular_brain" / "memory", "label": "Memoria", "depth": "full"},
    {"path": PROJECT_ROOT / "speace_core" / "cellular_brain" / "cognition", "label": "Cognizione", "depth": "full"},
    {"path": PROJECT_ROOT / "speace_core" / "cellular_brain" / "dynamics", "label": "Dinamiche Neurali", "depth": "full"},
    {"path": PROJECT_ROOT / "speace_core" / "cellular_brain" / "autonomic", "label": "Sistema Autonomo", "depth": "full"},
    {"path": PROJECT_ROOT / "speace_core" / "cellular_brain" / "self_improvement", "label": "Auto-miglioramento", "depth": "full"},
    {"path": PROJECT_ROOT / "speace_core" / "cellular_brain" / "immune", "label": "Sistema Immune", "depth": "full"},
    {"path": PROJECT_ROOT / "speace_core" / "cellular_brain" / "metabolism", "label": "Metabolismo", "depth": "full"},
    {"path": PROJECT_ROOT / "speace_core" / "cellular_brain" / "sleep", "label": "Sonno", "depth": "full"},
    {"path": PROJECT_ROOT / "speace_core" / "cellular_brain" / "dna", "label": "DNA/Genoma", "depth": "full"},
    {"path": PROJECT_ROOT / "speace_core" / "organism", "label": "Organismo", "depth": "full"},
    {"path": PROJECT_ROOT / "speace_core" / "runtime", "label": "Runtime Continuo", "depth": "full"},
    {"path": PROJECT_ROOT / "speace_core" / "monitoring", "label": "Monitoraggio", "depth": "full"},
    {"path": PROJECT_ROOT / "speace_core" / "organism_observer", "label": "Osservatore Organismo", "depth": "full"},
    {"path": PROJECT_ROOT / "speace_core" / "evolution", "label": "Evoluzione", "depth": "full"},
    {"path": PROJECT_ROOT / "speace_core" / "ilf", "label": "Campo ILF", "depth": "full"},
    {"path": PROJECT_ROOT / "evolution_daemon", "label": "Evolution Daemon", "depth": "full"},
    {"path": PROJECT_ROOT / "speace_agi_team", "label": "AGI Team", "depth": "full"},
    {"path": PROJECT_ROOT / "scripts", "label": "Scripts", "depth": "full"},
    {"path": PROJECT_ROOT / "tests", "label": "Tests", "depth": "full"},
    {"path": PROJECT_ROOT / "docs", "label": "Documentazione", "depth": "full"},
    {"path": PROJECT_ROOT / "data", "label": "Dati", "depth": "shallow"},
    {"path": PROJECT_ROOT / "reports", "label": "Reports", "depth": "shallow"},
    {"path": PROJECT_ROOT / "ispettore_manutentore_neurologico_organismico_di_speace", "label": "Ispettore Esistente", "depth": "full"},
]

LOG_LEVEL = os.environ.get("LOOP_LOG_LEVEL", "INFO").upper()
MAX_WORKERS = int(os.environ.get("LOOP_MAX_WORKERS", "8"))
SCAN_TIMEOUT = int(os.environ.get("LOOP_SCAN_TIMEOUT", "300"))
MAX_FILE_SIZE_CHARS = int(os.environ.get("LOOP_MAX_FILE_CHARS", "80000"))
MAX_FILES_PER_COMPONENT = int(os.environ.get("LOOP_MAX_FILES", "200"))
CYCLE_INTERVAL_SEC = int(os.environ.get("LOOP_CYCLE_INTERVAL", "300"))
AUTO_FIX_ENABLED = os.environ.get("LOOP_AUTO_FIX", "true").lower() == "true"
BACKUP_ENABLED = os.environ.get("LOOP_BACKUP", "true").lower() == "true"
DRY_RUN = os.environ.get("LOOP_DRY_RUN", "false").lower() == "true"
