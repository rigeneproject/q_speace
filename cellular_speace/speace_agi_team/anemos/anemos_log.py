"""Anemos Logger — Dual output (file + console) with rotation.

Mantiene i log in ``data/logs/anemos/`` con un file per sessione
(formato ``anemos_YYYYMMDD_HHMMSS.log``) e stampa su console con
prefisso ``[ANEMOS]``. Riusa la directory log esistente.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

# ── Paths ────────────────────────────────────────────────────────────────
_DEFAULT_LOG_DIR = Path("data/logs/anemos")
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOG_DIR = _PROJECT_ROOT / "data" / "logs" / "anemos"


class _AnemosFormatter(logging.Formatter):
    """Formatter che produce output compatti con prefisso [ANEMOS]."""

    def __init__(self, with_prefix: bool = True) -> None:
        prefix = "[ANEMOS] " if with_prefix else ""
        super().__init__(f"%(asctime)s [%(levelname)s] {prefix}%(message)s",
                         datefmt="%Y-%m-%d %H:%M:%S")


_singleton_logger: Optional[logging.Logger] = None


def get_anemos_logger(name: str = "anemos") -> logging.Logger:
    """Restituisce il logger singleton di Anemos.

    Configura un RotatingFileHandler (max 5 MB × 3 backup) nella directory
    ``data/logs/anemos/`` e un StreamHandler per la console. Entrambi
    condividono lo stesso formato compatto.

    La prima chiamata crea i file handler; le successive sono no-op
    per evitare log duplicati durante i reimport.
    """
    global _singleton_logger
    if _singleton_logger is not None:
        return _singleton_logger

    logger = logging.getLogger(f"speace.anemos.{name}")
    logger.setLevel(logging.INFO)
    logger.propagate = False  # non propagare al root logger

    # Evita di aggiungere handler due volte
    if logger.handlers:
        return logger

    # Crea directory log
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    # File handler con rotazione
    log_filename = f"anemos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_path = _LOG_DIR / log_filename
    try:
        file_handler = RotatingFileHandler(
            str(file_path),
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(_AnemosFormatter(with_prefix=False))
        logger.addHandler(file_handler)
    except (OSError, PermissionError):
        # Se la directory non è scrivibile, fallback silenzioso
        pass

    # Console handler (solo se non siamo in modalità silenziosa)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(_AnemosFormatter(with_prefix=True))
    logger.addHandler(console_handler)

    _singleton_logger = logger
    return logger


def get_log_dir() -> Path:
    """Restituisce la directory dei log Anemos."""
    return _LOG_DIR
