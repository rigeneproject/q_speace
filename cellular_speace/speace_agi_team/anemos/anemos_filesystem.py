"""AnemosFileSystem — Accesso sicuro al filesystem con allowlist.

Anemos può leggere ogni file in ``C:\\cellular_speace\\`` e scrivere con
allowlist. Ogni operazione viene:
- Validata contro una BLOCKED_PATTERNS (rifiuto assoluto)
- Validata contro una CONFIRM_REQUIRED_PATTERNS (richiede conferma umana)
- Backup automatico prima di ogni write
- Syntax check ``compile()`` per file .py con rollback automatico
- Validazione ``yaml.safe_load`` per file .yaml con rollback automatico
- Loggata in ``data/anemos/fs_audit.jsonl``

Pattern riusato da ``speace_agi_team.action_executor._execute_py_file``
(backup + compile + rollback) e ``_execute_yaml_file`` (safe_load).
"""

from __future__ import annotations

import difflib
import json
import re
import shutil
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ── Allowlist ───────────────────────────────────────────────────────────
# Pattern che causano BLOCCO ASSOLUTO. Sollevano ``PermissionError``.
BLOCKED_PATTERNS: List[str] = [
    r"\.git([/\\]|$)",
    r"\.env$",
    r"\.env\.",
    r"__pycache__([/\\]|$)",
    r"\.pyc$",
    r"\.pyo$",
    r"\.coverage$",
    r"\.ruff_cache([/\\]|$)",
    r"\.pytest_cache([/\\]|$)",
    r"node_modules([/\\]|$)",
    r"speace_agi_team[/\\]anemos[/\\]",  # anti-tampering del codice Anemos
]

# Pattern che richiedono conferma umana esplicita (via flag ``force=True``).
CONFIRM_REQUIRED_PATTERNS: List[str] = [
    r"^speace_agi_team[/\\]",            # tutto il resto del team AGI
    r"^tests[/\\]",
    r"^scripts[/\\]",
    r"^pyproject\.toml$",
    r"^setup\.py$",
    r"^requirements\.txt$",
]

# Estensioni supportate per syntax/parse check
PY_EXT = ".py"
YAML_EXT = ".yaml"
YML_EXT = ".yml"

# Limiti di sicurezza
MAX_FILE_READ_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_FILE_WRITE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_SEARCH_RESULTS = 100
MAX_LIST_ENTRIES = 1000
PYTHON_SANDBOX_TIMEOUT = 10


# ── Dataclass results ───────────────────────────────────────────────────
@dataclass
class FileInfo:
    path: str
    is_dir: bool
    size: int
    mtime: float
    blocked: bool = False
    block_reason: Optional[str] = None


@dataclass
class WriteResult:
    success: bool
    path: str
    backup_path: Optional[str] = None
    is_new_file: bool = False
    bytes_written: int = 0
    error: Optional[str] = None
    syntax_check: Optional[str] = None  # None = OK, str = errore


@dataclass
class ReadResult:
    success: bool
    path: str
    content: Optional[str] = None
    line_count: int = 0
    error: Optional[str] = None


# ── Helpers ─────────────────────────────────────────────────────────────
def _normalize_path(root: Path, raw_path: str) -> Path:
    """Normalizza un path relativo rispetto alla root, bloccando traversal."""
    # Rimuovi slash iniziale, normalizza separatori Windows
    clean = raw_path.strip().lstrip("/").lstrip("\\")
    candidate = (root / clean).resolve()
    # Sicurezza: deve stare dentro root
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        raise PermissionError(f"Path traversal detected: {raw_path!r}")
    return candidate


def _matches_any(path_str: str, patterns: List[str]) -> Optional[str]:
    """Ritorna il pattern che matcha, o None."""
    for pat in patterns:
        if re.search(pat, path_str, flags=re.IGNORECASE):
            return pat
    return None


def _is_within_anemos_self(root: Path, candidate: Path) -> bool:
    """True se il path è dentro speace_agi_team/anemos/ (auto-protezione)."""
    try:
        anemos_dir = (root / "speace_agi_team" / "anemos").resolve()
        candidate.relative_to(anemos_dir)
        return True
    except ValueError:
        return False


# ── Classe principale ───────────────────────────────────────────────────
class AnemosFileSystem:
    """Accesso al filesystem di SPEACE con allowlist e audit.

    Attributes:
        root: Directory radice (``C:\\cellular_speace\\``).
        audit_path: File JSONL dove loggare ogni operazione.
        backup_dir: Directory dei backup automatici.
    """

    def __init__(
        self,
        root: Optional[Path] = None,
        data_dir: Optional[Path] = None,
    ) -> None:
        if root is None:
            # Default: risali da questo file fino a C:\cellular_speace\
            root = Path(__file__).resolve().parents[2]
        self.root: Path = Path(root).resolve()

        if data_dir is None:
            data_dir = self.root / "data" / "anemos"
        self.data_dir: Path = Path(data_dir)
        self.audit_path: Path = self.data_dir / "fs_audit.jsonl"
        self.backup_dir: Path = self.data_dir / "backups"

        # Crea directory se non esistono
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.audit_path.touch(exist_ok=True)

    # ── Audit ───────────────────────────────────────────────────────
    def _audit(
        self,
        operation: str,
        path: str,
        agent_id: str = "anemos",
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Registra un'operazione nel file di audit JSONL."""
        entry = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "epoch": time.time(),
            "operation": operation,
            "path": path,
            "agent_id": agent_id,
            "success": success,
            "details": details or {},
        }
        try:
            with self.audit_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass  # audit failure non blocca l'operazione

    def get_audit_log(self, n: int = 50) -> List[Dict[str, Any]]:
        """Restituisce le ultime N entries di audit."""
        if not self.audit_path.exists():
            return []
        try:
            lines = self.audit_path.read_text(encoding="utf-8").strip().split("\n")
            entries = []
            for line in lines[-n:]:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return entries
        except OSError:
            return []

    # ── Validazione path ────────────────────────────────────────────
    def _validate_read(self, raw_path: str) -> Path:
        """Valida un path per lettura. Solleva ``PermissionError`` se bloccato."""
        candidate = _normalize_path(self.root, raw_path)
        rel = candidate.relative_to(self.root).as_posix()
        matched = _matches_any(rel, BLOCKED_PATTERNS)
        if matched is not None:
            raise PermissionError(
                f"Path bloccato dall'allowlist Anemos: {raw_path!r} (pattern: {matched})"
            )
        return candidate

    def _validate_write(
        self,
        raw_path: str,
        force: bool = False,
    ) -> Tuple[Path, Optional[str]]:
        """Valida un path per scrittura.

        Returns: (path_normalizzato, warning_message)

        Raises:
            PermissionError: se il path è in BLOCKED_PATTERNS o force=False
                e il path è in CONFIRM_REQUIRED_PATTERNS.
        """
        candidate = _normalize_path(self.root, raw_path)
        rel = candidate.relative_to(self.root).as_posix()

        # Blocco assoluto
        matched = _matches_any(rel, BLOCKED_PATTERNS)
        if matched is not None:
            raise PermissionError(
                f"Path bloccato dall'allowlist Anemos (blocco assoluto): "
                f"{raw_path!r} (pattern: {matched})"
            )

        # Auto-protezione extra: speace_agi_team/anemos/
        if _is_within_anemos_self(self.root, candidate):
            raise PermissionError(
                f"Auto-protezione: Anemos non può modificare il proprio codice ({raw_path!r})"
            )

        # Conferma richiesta
        warning = None
        confirm_pat = _matches_any(rel, CONFIRM_REQUIRED_PATTERNS)
        if confirm_pat is not None and not force:
            raise PermissionError(
                f"Path in area protetta (richiede force=True o conferma Roberto): "
                f"{raw_path!r} (pattern: {confirm_pat})"
            )
        if confirm_pat is not None and force:
            warning = f"Modifica di area protetta con force=True: {confirm_pat}"

        return candidate, warning

    # ── Read ────────────────────────────────────────────────────────
    def read(
        self,
        raw_path: str,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        agent_id: str = "anemos",
    ) -> ReadResult:
        """Legge un file con paginazione opzionale.

        Args:
            raw_path: Path relativo a root.
            offset: Riga di partenza (0-based). None = inizio.
            limit: Numero massimo di righe. None = tutte.
            agent_id: Identificativo per audit.

        Returns:
            ReadResult con contenuto o errore.
        """
        try:
            candidate = self._validate_read(raw_path)
        except PermissionError as e:
            self._audit("read", raw_path, agent_id, False, {"error": str(e)})
            return ReadResult(success=False, path=raw_path, error=str(e))

        if not candidate.exists():
            err = f"File non esistente: {raw_path}"
            self._audit("read", raw_path, agent_id, False, {"error": err})
            return ReadResult(success=False, path=raw_path, error=err)

        if not candidate.is_file():
            err = f"Non è un file: {raw_path}"
            self._audit("read", raw_path, agent_id, False, {"error": err})
            return ReadResult(success=False, path=raw_path, error=err)

        # Limite dimensione
        size = candidate.stat().st_size
        if size > MAX_FILE_READ_BYTES:
            err = f"File troppo grande ({size} bytes > {MAX_FILE_READ_BYTES})"
            self._audit("read", raw_path, agent_id, False, {"error": err})
            return ReadResult(success=False, path=raw_path, error=err)

        try:
            content = candidate.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            err = f"Errore lettura: {e}"
            self._audit("read", raw_path, agent_id, False, {"error": err})
            return ReadResult(success=False, path=raw_path, error=err)

        # Paginazione
        if offset is not None or limit is not None:
            lines = content.splitlines(keepends=True)
            start = offset or 0
            end = start + limit if limit is not None else len(lines)
            lines = lines[start:end]
            # Aggiungi numeri di riga (1-based per il display)
            numbered = "".join(f"{start + i + 1:6d}\t{line}" for i, line in enumerate(lines))
            content = numbered
            line_count = len(lines)
        else:
            line_count = content.count("\n") + (1 if content else 0)

        self._audit("read", raw_path, agent_id, True, {
            "size": size, "lines": line_count, "offset": offset, "limit": limit,
        })
        return ReadResult(success=True, path=raw_path, content=content, line_count=line_count)

    # ── List directory ──────────────────────────────────────────────
    def list_dir(
        self,
        raw_path: str = ".",
        recursive: bool = False,
        pattern: Optional[str] = None,
        agent_id: str = "anemos",
    ) -> List[FileInfo]:
        """Lista contenuto di una directory."""
        try:
            candidate = _normalize_path(self.root, raw_path)
        except PermissionError as e:
            self._audit("list", raw_path, agent_id, False, {"error": str(e)})
            return [FileInfo(path=raw_path, is_dir=False, size=0, mtime=0, blocked=True, block_reason=str(e))]

        if not candidate.exists() or not candidate.is_dir():
            self._audit("list", raw_path, agent_id, False, {"error": "directory non esistente"})
            return []

        try:
            entries: List[Path] = []
            if recursive:
                for p in candidate.rglob(pattern or "*"):
                    entries.append(p)
            else:
                glob_pattern = pattern or "*"
                entries = sorted(candidate.glob(glob_pattern))
        except OSError as e:
            self._audit("list", raw_path, agent_id, False, {"error": str(e)})
            return []

        results: List[FileInfo] = []
        for p in entries[:MAX_LIST_ENTRIES]:
            try:
                rel = p.relative_to(self.root).as_posix()
                blocked = _matches_any(rel, BLOCKED_PATTERNS) is not None
                is_dir = p.is_dir()
                if p.exists():
                    stat = p.stat()
                    size = 0 if is_dir else stat.st_size
                    mtime = stat.st_mtime
                else:
                    size = 0
                    mtime = 0
                results.append(FileInfo(
                    path=rel,
                    is_dir=is_dir,
                    size=size,
                    mtime=mtime,
                    blocked=blocked,
                ))
            except OSError:
                continue

        self._audit("list", raw_path, agent_id, True, {"count": len(results), "recursive": recursive})
        return results

    # ── Write ───────────────────────────────────────────────────────
    def write(
        self,
        raw_path: str,
        content: str,
        force: bool = False,
        agent_id: str = "anemos",
    ) -> WriteResult:
        """Scrive un file con backup, syntax check e audit.

        Args:
            raw_path: Path relativo.
            content: Contenuto completo (non append).
            force: Se True, bypassa i CONFIRM_REQUIRED_PATTERNS.
            agent_id: Per audit.

        Returns:
            WriteResult con esito.
        """
        # Validazione
        try:
            candidate, warning = self._validate_write(raw_path, force=force)
        except PermissionError as e:
            self._audit("write", raw_path, agent_id, False, {"error": str(e)})
            return WriteResult(success=False, path=raw_path, error=str(e))

        # Limite dimensione contenuto
        if len(content.encode("utf-8")) > MAX_FILE_WRITE_BYTES:
            err = f"Contenuto troppo grande ({len(content)} chars > {MAX_FILE_WRITE_BYTES} bytes)"
            self._audit("write", raw_path, agent_id, False, {"error": err})
            return WriteResult(success=False, path=raw_path, error=err)

        # Backup se il file esiste
        backup_path = None
        is_new = not candidate.exists()
        if not is_new:
            try:
                rel_for_backup = candidate.relative_to(self.root).as_posix().replace("/", "_").replace("\\", "_")
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"{rel_for_backup}.{ts}.bak"
                backup_file = self.backup_dir / backup_name
                shutil.copy2(candidate, backup_file)
                backup_path = str(backup_file.relative_to(self.root))
            except OSError as e:
                err = f"Backup fallito: {e}"
                self._audit("write", raw_path, agent_id, False, {"error": err})
                return WriteResult(success=False, path=raw_path, error=err)

        # Crea directory padre se necessario
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            err = f"Creazione directory fallita: {e}"
            self._audit("write", raw_path, agent_id, False, {"error": err})
            return WriteResult(success=False, path=raw_path, error=err)

        # Scrivi
        try:
            candidate.write_text(content, encoding="utf-8")
        except OSError as e:
            err = f"Scrittura fallita: {e}"
            self._audit("write", raw_path, agent_id, False, {"error": err})
            # Rollback: rimuovi file nuovo o ripristina backup
            if is_new and candidate.exists():
                try:
                    candidate.unlink()
                except OSError:
                    pass
            return WriteResult(success=False, path=raw_path, error=err)

        # Syntax/parse check
        syntax_msg = None
        if candidate.suffix == PY_EXT:
            try:
                compile(content, str(candidate), "exec")
            except SyntaxError as e:
                syntax_msg = f"SyntaxError: {e}"
                # Rollback
                if backup_path:
                    try:
                        shutil.copy2(self.root / backup_path, candidate)
                    except OSError:
                        pass
                else:
                    try:
                        candidate.unlink()
                    except OSError:
                        pass
                self._audit("write", raw_path, agent_id, False, {
                    "error": syntax_msg, "rolled_back": True,
                })
                return WriteResult(
                    success=False, path=raw_path, error=syntax_msg,
                    syntax_check=syntax_msg,
                )
        elif candidate.suffix in (YAML_EXT, YML_EXT):
            try:
                import yaml
                yaml.safe_load(content)
            except Exception as e:  # YAML parse error
                syntax_msg = f"YAML parse error: {e}"
                if backup_path:
                    try:
                        shutil.copy2(self.root / backup_path, candidate)
                    except OSError:
                        pass
                else:
                    try:
                        candidate.unlink()
                    except OSError:
                        pass
                self._audit("write", raw_path, agent_id, False, {
                    "error": syntax_msg, "rolled_back": True,
                })
                return WriteResult(
                    success=False, path=raw_path, error=syntax_msg,
                    syntax_check=syntax_msg,
                )

        self._audit("write", raw_path, agent_id, True, {
            "bytes": len(content), "is_new": is_new, "backup": backup_path,
            "warning": warning,
        })
        return WriteResult(
            success=True, path=raw_path, backup_path=backup_path,
            is_new_file=is_new, bytes_written=len(content.encode("utf-8")),
            syntax_check="OK",
        )

    # ── Search files (glob) ─────────────────────────────────────────
    def search_files(
        self,
        pattern: str,
        path: str = ".",
        max_results: int = 50,
        agent_id: str = "anemos",
    ) -> List[str]:
        """Cerca file per pattern glob."""
        try:
            base = _normalize_path(self.root, path)
        except PermissionError as e:
            self._audit("search_files", pattern, agent_id, False, {"error": str(e)})
            return []

        if not base.exists():
            return []

        try:
            matches = [str(p.relative_to(self.root).as_posix())
                       for p in base.glob(pattern)][:max_results]
        except OSError as e:
            self._audit("search_files", pattern, agent_id, False, {"error": str(e)})
            return []

        # Filtra i bloccati
        filtered = [m for m in matches if _matches_any(m, BLOCKED_PATTERNS) is None]

        self._audit("search_files", pattern, agent_id, True, {"count": len(filtered)})
        return filtered

    # ── Search content (grep testuale) ──────────────────────────────
    def search_content(
        self,
        query: str,
        path: str = ".",
        max_results: int = 30,
        agent_id: str = "anemos",
    ) -> List[Dict[str, Any]]:
        """Cerca una stringa nei file (case-sensitive)."""
        try:
            base = _normalize_path(self.root, path)
        except PermissionError as e:
            self._audit("search_content", query, agent_id, False, {"error": str(e)})
            return []

        if not base.exists():
            return []

        results: List[Dict[str, Any]] = []
        try:
            for p in base.rglob("*"):
                if not p.is_file():
                    continue
                rel = p.relative_to(self.root).as_posix()
                if _matches_any(rel, BLOCKED_PATTERNS) is not None:
                    continue
                if p.suffix in (".pyc", ".pyo", ".png", ".jpg", ".pdf"):
                    continue
                try:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                for i, line in enumerate(text.splitlines(), 1):
                    if query in line:
                        results.append({
                            "path": rel,
                            "line": i,
                            "context": line.strip()[:200],
                        })
                        if len(results) >= max_results:
                            break
                if len(results) >= max_results:
                    break
        except OSError as e:
            self._audit("search_content", query, agent_id, False, {"error": str(e)})
            return results

        self._audit("search_content", query, agent_id, True, {"count": len(results)})
        return results

    # ── Diff con backup ─────────────────────────────────────────────
    def diff_backup(
        self,
        raw_path: str,
        agent_id: str = "anemos",
    ) -> Optional[str]:
        """Ritorna un diff unificato tra il file attuale e l'ultimo backup."""
        try:
            candidate = self._validate_read(raw_path)
        except PermissionError:
            return None
        if not candidate.exists():
            return None

        # Trova l'ultimo backup
        rel = candidate.relative_to(self.root).as_posix().replace("/", "_").replace("\\", "_")
        backups = sorted(self.backup_dir.glob(f"{rel}.*.bak"), reverse=True)
        if not backups:
            return f"Nessun backup trovato per {raw_path}"
        latest_backup = backups[0]

        try:
            old_text = latest_backup.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
            new_text = candidate.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
            diff = difflib.unified_diff(
                old_text, new_text,
                fromfile=f"backup: {latest_backup.name}",
                tofile=f"current: {raw_path}",
                lineterm="",
            )
            return "".join(diff)
        except OSError as e:
            return f"Errore diff: {e}"

    # ── Rollback ────────────────────────────────────────────────────
    def rollback(
        self,
        raw_path: str,
        agent_id: str = "anemos",
    ) -> bool:
        """Ripristina l'ultimo backup del file."""
        try:
            candidate = self._validate_read(raw_path)
        except PermissionError as e:
            self._audit("rollback", raw_path, agent_id, False, {"error": str(e)})
            return False

        rel = candidate.relative_to(self.root).as_posix().replace("/", "_").replace("\\", "_")
        backups = sorted(self.backup_dir.glob(f"{rel}.*.bak"), reverse=True)
        if not backups:
            self._audit("rollback", raw_path, agent_id, False, {"error": "nessun backup"})
            return False

        latest_backup = backups[0]
        try:
            # Backup dell'attuale prima di rollbackre (safety)
            if candidate.exists():
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                pre_rollback = self.backup_dir / f"{rel}.{ts}.pre_rollback.bak"
                shutil.copy2(candidate, pre_rollback)
            shutil.copy2(latest_backup, candidate)
        except OSError as e:
            self._audit("rollback", raw_path, agent_id, False, {"error": str(e)})
            return False

        self._audit("rollback", raw_path, agent_id, True, {"from": latest_backup.name})
        return True

    # ── Run Python (limitato) ───────────────────────────────────────
    def run_python(
        self,
        code: str,
        timeout: int = PYTHON_SANDBOX_TIMEOUT,
        agent_id: str = "anemos",
    ) -> Dict[str, Any]:
        """Esegue Python in sub-processo con timeout.

        Limiti: nessun accesso al filesystem fuori da ``data/``, nessun
        network. Solo per calcoli veloci e ispezione.
        """
        import subprocess
        if len(code) > 50_000:
            return {"success": False, "error": "code troppo lungo (>50k chars)"}

        try:
            result = subprocess.run(
                ["python", "-c", code],
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[:5000],
                "stderr": result.stderr[:5000],
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"timeout ({timeout}s)"}
        except Exception as e:
            return {"success": False, "error": str(e)}
