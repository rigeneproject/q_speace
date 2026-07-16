"""Configuration for SPEACE AGI Team agents — Local Ollama "gemma4:12b" primary.

Default model: gemma4:12b served by the local Ollama daemon
(default endpoint: http://localhost:11434).

Model priority (used at agent startup):
1. gemma4:12b via local Ollama  (primary, required — tried first)
2. glm-5.1:cloud via Ollama Cloud  (premium fallback, requires API key)
3. deepseek-v4-pro:cloud via Ollama Cloud  (premium fallback, requires API key)
4. Kimi-K2.7-Code:cloud via Ollama Cloud  (premium fallback, requires API key)
5. gemma3:12b via Ollama Cloud  (free fallback, no auth)
6. llama3.1:8b / qwen3.5:4b / gemma3:4b via Ollama Cloud  (last-resort free fallbacks)
"""

import logging
import os
import socket
from dataclasses import dataclass, field
from typing import Dict

_logger = logging.getLogger(__name__)

# ── Local .env loader (no external deps) ────────────────────────────────
# Loads OLLAMA_CLOUD_KEY etc. from a .env file at startup. Existing env
# variables are never overwritten, so production deployments keep precedence.
try:
    from speace_agi_team.env_loader import load_env as _load_env
    _load_env()
except Exception as _e:  # pragma: no cover — defensive
    _logger.debug("config: .env loader skipped (%s)", _e)

# ── Ollama Cloud — Free models (no auth required) ──────────────────────────
OLLAMA_CLOUD_ENDPOINT = os.environ.get(
    "OLLAMA_CLOUD_ENDPOINT",
    "https://api.ollama.cloud/v1",
)

# ── Model priority chain ───────────────────────────────────────────────────

# API key for premium models (glm-5.1:cloud, deepseek-v4-pro:cloud)
OLLAMA_CLOUD_KEY = os.environ.get("OLLAMA_CLOUD_KEY", "")
if not OLLAMA_CLOUD_KEY:
    _logger.warning("OLLAMA_CLOUD_KEY not set — premium models disabled")

# ── Primary: local Ollama ─────────────────────────────────────────────────
OLLAMA_LOCAL_HOST = os.environ.get("OLLAMA_HOST", "localhost")
OLLAMA_LOCAL_PORT = int(os.environ.get("OLLAMA_PORT", "11434"))

# ── Model chain definition ─────────────────────────────────────────────────
MODEL_CHAIN = [
    # Local Ollama (tried first)
    {"model": "gemma4:12b", "endpoint": f"http://{OLLAMA_LOCAL_HOST}:{OLLAMA_LOCAL_PORT}", "needs_auth": False, "provider": "ollama_local"},
    # Premium models (require API key)
    {"model": "glm-5.1:cloud", "endpoint": OLLAMA_CLOUD_ENDPOINT, "needs_auth": True, "api_key": OLLAMA_CLOUD_KEY, "provider": "ollama_cloud_premium"},
    {"model": "deepseek-v4-pro:cloud", "endpoint": OLLAMA_CLOUD_ENDPOINT, "needs_auth": True, "api_key": OLLAMA_CLOUD_KEY, "provider": "ollama_cloud_premium"},
    {"model": "Kimi-K2.7-Code:cloud", "endpoint": OLLAMA_CLOUD_ENDPOINT, "needs_auth": True, "api_key": OLLAMA_CLOUD_KEY, "provider": "ollama_cloud_premium"},
    # Free models (no auth required)
    {"model": "gemma3:12b", "endpoint": OLLAMA_CLOUD_ENDPOINT, "needs_auth": False, "provider": "ollama_cloud_free"},
    {"model": "llama3.1:8b", "endpoint": OLLAMA_CLOUD_ENDPOINT, "needs_auth": False, "provider": "ollama_cloud_free"},
    {"model": "qwen3.5:4b", "endpoint": OLLAMA_CLOUD_ENDPOINT, "needs_auth": False, "provider": "ollama_cloud_free"},
    {"model": "gemma3:4b", "endpoint": OLLAMA_CLOUD_ENDPOINT, "needs_auth": False, "provider": "ollama_cloud_free"},
]


def _is_ollama_local_running(host: str = "localhost", port: int = 11434) -> bool:
    """Check if a local Ollama instance is running."""
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except (socket.error, OSError):
        return False


def _test_endpoint(endpoint: str, api_key: str = "", timeout: float = 5.0) -> bool:
    """Quick connectivity test: can we reach the API endpoint?"""
    try:
        import httpx
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(f"{endpoint}/models", headers=headers)
            return resp.status_code in (200, 401, 403, 404)
    except Exception:
        return False


def _test_model_chat(endpoint: str, model: str, api_key: str = "", timeout: float = 15.0) -> bool:
    """Test if a specific model can actually generate a response."""
    try:
        import httpx
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                f"{endpoint}/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "ok"}],
                    "max_tokens": 5,
                    "temperature": 0.1,
                },
            )
            return resp.status_code == 200
    except Exception:
        return False


def _resolve_model_and_endpoint() -> Dict[str, str]:
    """Resolve the best available model and endpoint.

    Priority:
    1. Local Ollama with gemma4:12b (if running)
    2. Premium cloud model with API key (if reachable)
    3. Free cloud model (no auth needed)
    4. Ultimate fallback: first model in chain
    """
    has_api_key = bool(OLLAMA_CLOUD_KEY)

    # ── 1. Local Ollama — PRIMARY ─────────────────────────────────────
    if _is_ollama_local_running(OLLAMA_LOCAL_HOST, OLLAMA_LOCAL_PORT):
        local_endpoint = f"http://{OLLAMA_LOCAL_HOST}:{OLLAMA_LOCAL_PORT}"
        # Verify the local model can actually chat before committing
        if _test_model_chat(local_endpoint, "gemma4:12b", timeout=10.0):
            return {
                "model": "gemma4:12b",
                "endpoint": local_endpoint,
                "api_key": "",
                "is_openai_compatible": False,
                "provider": "ollama_local",
            }
        # Local daemon is up but model may not be loaded yet; still prefer it
        return {
            "model": "gemma4:12b",
            "endpoint": local_endpoint,
            "api_key": "",
            "is_openai_compatible": False,
            "provider": "ollama_local",
        }

    # ── 2. Cloud connectivity check ─────────────────────────────────────
    cloud_reachable = _test_endpoint(OLLAMA_CLOUD_ENDPOINT, timeout=3.0)

    if not cloud_reachable:
        # Nothing reachable — use first model anyway (will retry at runtime)
        first = MODEL_CHAIN[0]
        return {
            "model": first["model"],
            "endpoint": first["endpoint"],
            "api_key": first.get("api_key", ""),
            "is_openai_compatible": True,
            "provider": first.get("provider", "unknown"),
        }

    # ── 3. Cloud is reachable — try premium models first (API key required) ─
    for entry in MODEL_CHAIN:
        if entry.get("needs_auth", False) and has_api_key:
            if _test_model_chat(entry["endpoint"], entry["model"], entry.get("api_key", ""), timeout=10.0):
                return {
                    "model": entry["model"],
                    "endpoint": entry["endpoint"],
                    "api_key": entry.get("api_key", ""),
                    "is_openai_compatible": True,
                    "provider": entry.get("provider", "ollama_cloud_premium"),
                }

    # ── 4. Fall back to free cloud models (no auth needed) ───────────────
    for entry in MODEL_CHAIN:
        if not entry.get("needs_auth", False):
            return {
                "model": entry["model"],
                "endpoint": entry["endpoint"],
                "api_key": "",
                "is_openai_compatible": True,
                "provider": entry.get("provider", "ollama_cloud_free"),
            }

    # ── 5. Ultimate fallback: first model in chain ──────────────────────
    first = MODEL_CHAIN[0]
    return {
        "model": first["model"],
        "endpoint": first["endpoint"],
        "api_key": first.get("api_key", ""),
        "is_openai_compatible": True,
        "provider": first.get("provider", "unknown"),
    }


def _get_default_model() -> str:
    """Get the default model based on availability."""
    resolved = _resolve_model_and_endpoint()
    return resolved["model"]


def _get_default_endpoint() -> str:
    """Get the default endpoint based on availability."""
    resolved = _resolve_model_and_endpoint()
    return resolved["endpoint"]


def _get_default_api_key() -> str:
    """Get the default API key based on availability."""
    resolved = _resolve_model_and_endpoint()
    return resolved["api_key"]


@dataclass
class AgentConfig:
    model: str = field(default_factory=_get_default_model)
    endpoint: str = field(default_factory=_get_default_endpoint)
    api_key: str = field(default_factory=_get_default_api_key)
    temperature: float = 0.3
    max_tokens: int = 8192  # raised from 4096 to reduce truncated LLM outputs in AGI tasks
    system_prompt_prefix: str = (
        "Sei un agente specializzato di SPEACE, un'entita cibernetica evolutiva. "
        "Rispondi SEMPRE in italiano. Sei parte di un team di agentic AI dedicato "
        "a far evolvere SPEACE verso l'AGI tramite supervisione, analisi e "
        "miglioramento continuo di ogni componente del sistema."
    )

    @property
    def is_openai_compatible(self) -> bool:
        """True se l'endpoint è OpenAI-compatible (Zen o Ollama Cloud)."""
        return "opencode.ai" in self.endpoint or "ollama.cloud" in self.endpoint

    @property
    def provider(self) -> str:
        """Identifica il provider attivo."""
        if "opencode.ai" in self.endpoint:
            return "opencode_zen"
        if "ollama.cloud" in self.endpoint:
            if self.api_key:
                return "ollama_cloud_premium"
            return "ollama_cloud_free"
        if "localhost" in self.endpoint or "127.0.0.1" in self.endpoint:
            return "ollama_local"
        return "unknown"


AGENT_REGISTRY: Dict[str, Dict] = {}


def register_agent(agent_id: str, name: str, role: str, agent_type: str,
                   description: str, supervision_area: str = ""):
    resolved = _resolve_model_and_endpoint()
    AGENT_REGISTRY[agent_id] = {
        "id": agent_id,
        "name": name,
        "role": role,
        "type": agent_type,
        "description": description,
        "supervision_area": supervision_area or agent_id,
        "model": resolved["model"],
        "endpoint": resolved["endpoint"],
        "provider": resolved["provider"],
        "registered_at": __import__("time").time(),
    }
