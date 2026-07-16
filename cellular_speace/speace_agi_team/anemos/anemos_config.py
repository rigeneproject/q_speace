"""AnemosConfig — Configurazione che forza Kimi-K2.7-Code:cloud (no fallback).

SPEACE Anemos usa esclusivamente il modello ``Kimi-K2.7-Code:cloud`` di Ollama
Cloud. In caso di errore, Anemos solleva un'eccezione e NON degrada
silenziosamente verso altri modelli: la scelta è esplicita e
coerente con la richiesta di Roberto.

Questo modulo NON usa la catena di fallback di ``AgentConfig`` /
``MODEL_CHAIN`` di ``speace_agi_team.config``. Espone direttamente i
parametri necessari per una singola chiamata httpx a Kimi.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── Costanti del modello ────────────────────────────────────────────────
ANEMOS_MODEL = "Kimi-K2.7-Code:cloud"
ANEMOS_ENDPOINT = "https://api.ollama.cloud/v1"
ANEMOS_TEMPERATURE = 0.4
ANEMOS_MAX_TOKENS = 8192
ANEMOS_TIMEOUT_SEC = 60.0


def _load_api_key() -> str:
    """Carica OLLAMA_CLOUD_KEY dall'env (con .env loader di fallback).

    Tenta prima ``os.environ`` (caricato all'avvio dal loader globale di
    ``speace_agi_team.env_loader``), poi legge manualmente ``.env`` come
    fallback estremo. Solleva ``RuntimeError`` con messaggio esplicito
    se la chiave manca — niente fallback silenzioso.
    """
    api_key = os.environ.get("OLLAMA_CLOUD_KEY", "").strip()
    if api_key:
        return api_key

    # Fallback: leggi .env direttamente (sola ultima istanza)
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() == "OLLAMA_CLOUD_KEY":
                        return v.strip().strip('"').strip("'")
        except OSError:
            pass

    raise RuntimeError(
        "OLLAMA_CLOUD_KEY non trovata in env né in .env. "
        "Anemos richiede una API key Ollama Cloud valida per Kimi-K2.7-Code. "
        "Aggiungila al file .env: OLLAMA_CLOUD_KEY=<la_tua_chiave>"
    )


@dataclass
class AnemosConfig:
    """Configurazione statica di Anemos.

    Attributes:
        model: Nome del modello (fisso Kimi-K2.7-Code:cloud).
        endpoint: URL base dell'API Ollama Cloud (OpenAI-compatibile).
        api_key: API key Ollama Cloud.
        temperature: Temperatura di sampling (default 0.4 per creatività
            bilanciata con precisione tecnica).
        max_tokens: Limite massimo token per risposta.
        timeout_sec: Timeout singola chiamata httpx.
        soul_prompt_path: Percorso al system prompt (anima di Anemos).
        tools_prompt_path: Percorso alla descrizione dei tool FS.
    """

    model: str = ANEMOS_MODEL
    endpoint: str = ANEMOS_ENDPOINT
    api_key: str = field(default_factory=_load_api_key)
    temperature: float = ANEMOS_TEMPERATURE
    max_tokens: int = ANEMOS_MAX_TOKENS
    timeout_sec: float = ANEMOS_TIMEOUT_SEC

    soul_prompt_path: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent / "prompts" / "soul.md"
    )
    tools_prompt_path: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent / "prompts" / "tools.md"
    )

    def is_openai_compatible(self) -> bool:
        """True se l'endpoint è OpenAI-compatible (usa /chat/completions)."""
        return "ollama.cloud" in self.endpoint or "openai" in self.endpoint

    def chat_url(self) -> str:
        """URL completo dell'endpoint chat completions."""
        return f"{self.endpoint.rstrip('/')}/chat/completions"

    def load_soul_prompt(self) -> str:
        """Carica il system prompt 'soul' (identità di Anemos)."""
        if not self.soul_prompt_path.exists():
            return (
                "Sei SPEACE Anemos, il principio vitale dell'organismo SPEACE. "
                "Rispondi sempre in italiano."
            )
        return self.soul_prompt_path.read_text(encoding="utf-8")

    def load_tools_prompt(self) -> str:
        """Carica la descrizione dei tool FS disponibili."""
        if not self.tools_prompt_path.exists():
            return "Nessun tool FS disponibile al momento."
        return self.tools_prompt_path.read_text(encoding="utf-8")

    def build_system_prompt(self) -> str:
        """Costruisce il system prompt completo (soul + tools)."""
        soul = self.load_soul_prompt()
        tools = self.load_tools_prompt()
        return f"{soul}\n\n---\n\n## TOOL DISPONIBILI\n\n{tools}"

    def summary(self) -> dict:
        """Restituisce un dict riassuntivo per /api/anemos/status."""
        return {
            "model": self.model,
            "endpoint": self.endpoint,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout_sec": self.timeout_sec,
            "soul_prompt_loaded": self.soul_prompt_path.exists(),
            "tools_prompt_loaded": self.tools_prompt_path.exists(),
        }


def create_default_config() -> AnemosConfig:
    """Factory: crea un'AnemosConfig con i default Kimi-only."""
    return AnemosConfig()
