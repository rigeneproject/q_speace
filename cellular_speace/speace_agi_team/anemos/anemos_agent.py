"""AnemosAgent — Agente AI con accesso FS, alimentato SOLO da Kimi-K2.7-Code:cloud.

NON estende ``AgentBase`` di ``speace_agi_team``: chiama direttamente
Kimi via httpx con un'unica richiesta, senza fallback. In caso di errore
di rete/auth/timeout, l'eccezione viene propagata al chiamante.

Tool calling testuale: il modello emette blocchi ``<anemos_action .../>``
che vengono parsati, eseguiti sull'``AnemosFileSystem``, e i cui risultati
vengono restituiti al modello in un turno successivo (multi-turno con
action loop interno).

History persistente in ``data/anemos/conversation.jsonl``.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from speace_agi_team.anemos.anemos_config import AnemosConfig, create_default_config
from speace_agi_team.anemos.anemos_filesystem import AnemosFileSystem
from speace_agi_team.anemos.anemos_log import get_anemos_logger


# ── Dataclasses ─────────────────────────────────────────────────────────
@dataclass
class AnemosAction:
    """Azione parsata da un blocco <anemos_action ...>...</anemos_action>."""
    action_type: str
    attributes: Dict[str, str] = field(default_factory=dict)
    content: Optional[str] = None  # per write_file, contenuto del blocco <content>
    raw: str = ""


@dataclass
class ActionResult:
    """Risultato di un'esecuzione di azione FS."""
    action: AnemosAction
    success: bool
    result: Any = None
    error: Optional[str] = None


@dataclass
class AnemosResponse:
    """Risposta completa di un singolo turno di chat."""
    answer: str
    actions_executed: List[ActionResult] = field(default_factory=list)
    actions_failed: List[ActionResult] = field(default_factory=list)
    model: str = ""
    duration_sec: float = 0.0
    raw_actions: List[AnemosAction] = field(default_factory=list)
    error: Optional[str] = None


# ── Parsing blocchi azione ──────────────────────────────────────────────
# Pattern per estrarre blocchi <anemos_action ...>...</anemos_action> o
# self-closing <anemos_action .../>
ACTION_BLOCK_RE = re.compile(
    r'<anemos_action\s+([^>]*?)(?:/>|>(.*?)</anemos_action>)',
    re.DOTALL,
)
ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"', re.DOTALL)
CONTENT_BLOCK_RE = re.compile(
    r'<content>(.*?)</content>',
    re.DOTALL,
)


def _parse_attrs(attr_string: str) -> Dict[str, str]:
    """Parsa gli attributi di un tag da stringa raw."""
    return {m.group(1): m.group(2) for m in ATTR_RE.finditer(attr_string)}


def _parse_action_blocks(text: str) -> List[AnemosAction]:
    """Estrae tutti i blocchi <anemos_action> dal testo del modello."""
    actions: List[AnemosAction] = []
    for match in ACTION_BLOCK_RE.finditer(text):
        attr_str = match.group(1)
        inner = match.group(2) or ""
        attrs = _parse_attrs(attr_str)
        action_type = attrs.pop("type", "")
        if not action_type:
            continue
        # Estrai <content>...</content> se presente
        content_match = CONTENT_BLOCK_RE.search(inner)
        content = content_match.group(1).strip() if content_match else None
        actions.append(AnemosAction(
            action_type=action_type,
            attributes=attrs,
            content=content,
            raw=match.group(0),
        ))
    return actions


def _strip_action_blocks(text: str) -> str:
    """Rimuove i blocchi azione dal testo, lasciando solo la parte narrativa."""
    return ACTION_BLOCK_RE.sub("", text).strip()


# ── Classe principale ───────────────────────────────────────────────────
class AnemosAgent:
    """Agente AI Anemos con accesso FS, alimentato da Kimi-K2.7-Code:cloud.

    Attributes:
        config: Configurazione (modello, endpoint, API key).
        fs: AnemosFileSystem per operazioni file.
        log: Logger.
        conversation_history: Lista messaggi in formato ChatML.
        history_path: File JSONL della history persistente.
    """

    def __init__(
        self,
        config: Optional[AnemosConfig] = None,
        fs: Optional[AnemosFileSystem] = None,
    ) -> None:
        self.config = config or create_default_config()
        self.fs = fs or AnemosFileSystem()
        self.log = get_anemos_logger("agent")
        self.conversation_history: List[Dict[str, str]] = []
        self.history_path: Path = self.fs.data_dir / "conversation.jsonl"
        self._load_persistent_history()

    # ── History management ──────────────────────────────────────────
    def _load_persistent_history(self) -> None:
        """Carica la history persistente dal file JSONL."""
        if not self.history_path.exists():
            return
        try:
            lines = self.history_path.read_text(encoding="utf-8").strip().split("\n")
            for line in lines[-100:]:  # ultime 100 entries
                try:
                    entry = json.loads(line)
                    if "role" in entry and "content" in entry:
                        self.conversation_history.append({
                            "role": entry["role"],
                            "content": entry["content"],
                        })
                except json.JSONDecodeError:
                    continue
        except OSError as e:
            self.log.warning(f"Impossibile caricare history: {e}")

    def _save_to_history(self, role: str, content: str) -> None:
        """Salva un singolo messaggio in history persistente."""
        self.conversation_history.append({"role": role, "content": content})
        try:
            with self.history_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "role": role,
                    "content": content,
                }, ensure_ascii=False) + "\n")
        except OSError as e:
            self.log.warning(f"Impossibile salvare history: {e}")

    def clear_history(self) -> None:
        """Cancella la history (in-memory e persistente)."""
        self.conversation_history = []
        if self.history_path.exists():
            try:
                self.history_path.unlink()
            except OSError:
                pass
        self.log.info("History cancellata")

    def get_history(self, n: int = 50) -> List[Dict[str, Any]]:
        """Restituisce le ultime N entries della history persistente."""
        if not self.history_path.exists():
            return []
        try:
            lines = self.history_path.read_text(encoding="utf-8").strip().split("\n")
            entries = []
            for line in lines[-n:]:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return entries
        except OSError:
            return []

    def history_stats(self) -> Dict[str, int]:
        """Statistiche history per /api/anemos/status."""
        return {
            "in_memory_messages": len(self.conversation_history),
            "persistent_file_lines": (
                sum(1 for _ in self.history_path.open(encoding="utf-8"))
                if self.history_path.exists() else 0
            ),
            "history_path": str(self.history_path.relative_to(self.fs.root)),
        }

    # ── Build messages ──────────────────────────────────────────────
    def _build_messages(
        self,
        user_message: str,
        fs_context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        """Costruisce la lista di messaggi per la chiamata Kimi."""
        system = self.config.build_system_prompt()
        # Aggiungi contesto FS opzionale
        if fs_context:
            ctx_str = json.dumps(fs_context, indent=2, default=str, ensure_ascii=False)[:3000]
            system += f"\n\n## CONTESTO FILESYSTEM CORRENTE\n\n{ctx_str}"

        messages: List[Dict[str, str]] = [{"role": "system", "content": system}]
        # History: ultimi 20 messaggi per non sforare il contesto
        for msg in self.conversation_history[-20:]:
            messages.append(msg)
        messages.append({"role": "user", "content": user_message})
        return messages

    # ── Chiamata Kimi (no fallback) ──────────────────────────────────
    def _call_kimi(self, messages: List[Dict[str, str]]) -> str:
        """Chiama Kimi-K2.7-Code via Ollama Cloud. Solleva eccezioni su errori."""
        url = self.config.chat_url()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": False,
        }
        self.log.info(f"Kimi call: {len(messages)} messaggi, max_tokens={self.config.max_tokens}")

        with httpx.Client(timeout=self.config.timeout_sec) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                err_body = resp.text[:500]
                self.log.error(f"Kimi HTTP {resp.status_code}: {err_body}")
                raise RuntimeError(
                    f"Kimi-K2.7-Code:cloud ha risposto con HTTP {resp.status_code}: {err_body}"
                )
            data = resp.json()
            try:
                content = data["choices"][0]["message"]["content"]
            except (KeyError, IndexError) as e:
                self.log.error(f"Kimi response malformata: {data}")
                raise RuntimeError(f"Risposta Kimi malformata: {e}") from e
            return content

    # ── Esegui azione ───────────────────────────────────────────────
    def _execute_action(self, action: AnemosAction) -> ActionResult:
        """Esegue un'azione parsata usando AnemosFileSystem."""
        try:
            if action.action_type == "read_file":
                offset = int(action.attributes.get("offset", 0))
                limit_str = action.attributes.get("limit")
                limit = int(limit_str) if limit_str else None
                r = self.fs.read(
                    action.attributes.get("path", ""),
                    offset=offset,
                    limit=limit,
                )
                return ActionResult(
                    action=action,
                    success=r.success,
                    result={"content": r.content, "line_count": r.line_count},
                    error=r.error,
                )
            elif action.action_type == "write_file":
                force = action.attributes.get("force", "false").lower() == "true"
                r = self.fs.write(
                    action.attributes.get("path", ""),
                    action.content or "",
                    force=force,
                )
                return ActionResult(
                    action=action,
                    success=r.success,
                    result={
                        "is_new_file": r.is_new_file,
                        "bytes_written": r.bytes_written,
                        "backup_path": r.backup_path,
                        "syntax_check": r.syntax_check,
                    },
                    error=r.error,
                )
            elif action.action_type == "list_dir":
                recursive = action.attributes.get("recursive", "false").lower() == "true"
                pattern = action.attributes.get("pattern")
                items = self.fs.list_dir(
                    action.attributes.get("path", "."),
                    recursive=recursive,
                    pattern=pattern,
                )
                return ActionResult(
                    action=action,
                    success=True,
                    result={"items": [
                        {
                            "path": i.path,
                            "is_dir": i.is_dir,
                            "size": i.size,
                            "blocked": i.blocked,
                        }
                        for i in items
                    ]},
                )
            elif action.action_type == "search_files":
                files = self.fs.search_files(
                    action.attributes.get("pattern", ""),
                    path=action.attributes.get("path", "."),
                    max_results=int(action.attributes.get("max_results", 50)),
                )
                return ActionResult(action=action, success=True, result={"files": files})
            elif action.action_type == "search_content":
                results = self.fs.search_content(
                    action.attributes.get("query", ""),
                    path=action.attributes.get("path", "."),
                    max_results=int(action.attributes.get("max_results", 30)),
                )
                return ActionResult(action=action, success=True, result={"matches": results})
            elif action.action_type == "diff_backup":
                diff = self.fs.diff_backup(action.attributes.get("path", ""))
                return ActionResult(action=action, success=True, result={"diff": diff})
            elif action.action_type == "rollback_file":
                ok = self.fs.rollback(action.attributes.get("path", ""))
                return ActionResult(action=action, success=ok, error=None if ok else "rollback fallito")
            elif action.action_type == "run_python":
                timeout = int(action.attributes.get("timeout", 10))
                r = self.fs.run_python(action.content or "", timeout=timeout)
                return ActionResult(action=action, success=r.get("success", False), result=r)
            else:
                return ActionResult(
                    action=action,
                    success=False,
                    error=f"Tipo azione sconosciuto: {action.action_type!r}",
                )
        except Exception as e:
            return ActionResult(action=action, success=False, error=str(e))

    # ── Chat principale ─────────────────────────────────────────────
    def chat(
        self,
        user_message: str,
        fs_context: Optional[Dict[str, Any]] = None,
        max_action_turns: int = 5,
    ) -> AnemosResponse:
        """Invia un messaggio a Kimi e gestisce eventuali action loop.

        Algoritmo:
        1. Costruisci messaggi con system + history + user_message
        2. Chiama Kimi
        3. Se la risposta contiene <anemos_action>, eseguile, costruisci
           un messaggio di feedback con i risultati, e richiama Kimi.
           Ripeti fino a max_action_turns volte.
        4. Salva la risposta finale (senza blocchi XML) in history.

        Raises:
            RuntimeError: se Kimi non è raggiungibile (no fallback).
        """
        t0 = time.time()
        # NOTA: il messaggio utente e la risposta assistant vengono salvati
        # in history SOLO se la chat ha successo. Se Kimi fallisce, la
        # history resta pulita (no messaggi "appesi" senza risposta).
        messages = self._build_messages(user_message, fs_context)
        all_executed: List[ActionResult] = []
        all_failed: List[ActionResult] = []
        all_actions: List[AnemosAction] = []
        final_text = ""

        for turn in range(max_action_turns + 1):
            try:
                response_text = self._call_kimi(messages)
            except Exception as e:
                self.log.error(f"Chiamata Kimi fallita al turno {turn}: {e}")
                # History resta con solo il messaggio utente (risposta non arrivata)
                raise RuntimeError(
                    f"Kimi-K2.7-Code:cloud non raggiungibile. "
                    f"Anemos non esegue fallback. Errore: {e}"
                ) from e

            actions = _parse_action_blocks(response_text)
            all_actions.extend(actions)
            final_text = response_text

            if not actions or turn >= max_action_turns:
                break

            # Esegui azioni e costruisci feedback
            self.log.info(f"Turno {turn}: {len(actions)} azione(i) da eseguire")
            feedback_parts = []
            for action in actions:
                result = self._execute_action(action)
                if result.success:
                    all_executed.append(result)
                    feedback_parts.append(
                        f"<result action=\"{action.action_type}\" status=\"ok\">\n"
                        f"{json.dumps(result.result, ensure_ascii=False, default=str)[:3000]}\n"
                        f"</result>"
                    )
                else:
                    all_failed.append(result)
                    feedback_parts.append(
                        f"<result action=\"{action.action_type}\" status=\"error\">\n"
                        f"{result.error}\n"
                        f"</result>"
                    )

            # Aggiungi response assistant e feedback utente
            messages.append({"role": "assistant", "content": response_text})
            messages.append({
                "role": "user",
                "content": (
                    "Ho eseguito le azioni che hai richiesto. Ecco i risultati:\n\n"
                    + "\n\n".join(feedback_parts)
                    + "\n\nOra continua la risposta a Roberto basandoti su questi risultati."
                ),
            })

        # Salva in history: utente + assistant (senza blocchi XML)
        # Solo ora che sappiamo che la chat ha avuto successo.
        self._save_to_history("user", user_message)
        narrative = _strip_action_blocks(final_text)
        if narrative:
            self._save_to_history("assistant", narrative)

        duration = time.time() - t0
        self.log.info(
            f"Chat completata: {len(all_actions)} azioni, "
            f"{len(all_executed)} ok, {len(all_failed)} fail, {duration:.1f}s"
        )

        return AnemosResponse(
            answer=final_text,
            actions_executed=all_executed,
            actions_failed=all_failed,
            model=self.config.model,
            duration_sec=duration,
            raw_actions=all_actions,
        )

    # ── Status ──────────────────────────────────────────────────────
    def status(self) -> Dict[str, Any]:
        """Restituisce lo stato dell'agente per /api/anemos/status."""
        return {
            "status": "online",
            "model": self.config.model,
            "endpoint": self.config.endpoint,
            "config": self.config.summary(),
            "history": self.history_stats(),
            "filesystem_root": str(self.fs.root),
        }
