"""Bounded execution, persistent SQLite state, and verifiable hash-chained audit (T225/T246)."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from .config import HTTPConfig


def _reject_json_constant(token: str) -> Any:
    raise ValueError(f"non_finite_json_constant:{token}")


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, sort_keys=True, indent=2, allow_nan=False).encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def _canonical_checkpoint_core(core: dict[str, Any]) -> str:
    return json.dumps(core, sort_keys=True, separators=(",", ":"), allow_nan=False)


class ServiceError(Exception):
    def __init__(self, code: str, status: int = 503) -> None:
        self.code = code
        self.status = status
        super().__init__(code)


def _verify_audit_connection(db: sqlite3.Connection) -> dict[str, Any]:
    rows = db.execute(
        "SELECT seq, payload, previous, digest FROM audit ORDER BY seq ASC"
    ).fetchall()
    if not rows:
        return {
            "valid": True,
            "row_count": 0,
            "first_seq": None,
            "last_seq": None,
            "head_digest": "",
            "failure_seq": None,
            "reason": "ok",
        }
    expected_seq = 1
    expected_prev = ""
    first_seq: int | None = None
    last_seq: int | None = None
    for seq, payload, previous, digest in rows:
        if first_seq is None:
            first_seq = int(seq)
        if seq != expected_seq:
            return {
                "valid": False,
                "row_count": len(rows),
                "first_seq": first_seq,
                "last_seq": last_seq,
                "head_digest": expected_prev,
                "failure_seq": int(seq),
                "reason": "seq_gap",
            }
        if previous != expected_prev:
            return {
                "valid": False,
                "row_count": len(rows),
                "first_seq": first_seq,
                "last_seq": last_seq,
                "head_digest": expected_prev,
                "failure_seq": int(seq),
                "reason": "previous_mismatch",
            }
        try:
            parsed = json.loads(payload, parse_constant=_reject_json_constant)
            if not isinstance(parsed, dict):
                raise ValueError("payload_not_object")
        except (ValueError, TypeError):
            return {
                "valid": False,
                "row_count": len(rows),
                "first_seq": first_seq,
                "last_seq": last_seq,
                "head_digest": expected_prev,
                "failure_seq": int(seq),
                "reason": "invalid_payload_json",
            }
        computed = hashlib.sha256((previous + payload).encode("utf-8")).hexdigest()
        if not hmac.compare_digest(computed, str(digest)):
            return {
                "valid": False,
                "row_count": len(rows),
                "first_seq": first_seq,
                "last_seq": last_seq,
                "head_digest": expected_prev,
                "failure_seq": int(seq),
                "reason": "digest_mismatch",
            }
        expected_prev = str(digest)
        last_seq = int(seq)
        expected_seq += 1
    return {
        "valid": True,
        "row_count": len(rows),
        "first_seq": first_seq,
        "last_seq": last_seq,
        "head_digest": expected_prev,
        "failure_seq": None,
        "reason": "ok",
    }


def verify_audit_chain(db_path: Path) -> dict[str, Any]:
    """Verify hash-chain continuity and SHA-256 digests of an audit SQLite DB."""
    if not db_path.exists():
        return {
            "valid": False,
            "row_count": 0,
            "first_seq": None,
            "last_seq": None,
            "head_digest": "",
            "failure_seq": None,
            "reason": "audit_db_missing",
        }
    conn = sqlite3.connect(db_path)
    try:
        return _verify_audit_connection(conn)
    except sqlite3.Error:
        return {
            "valid": False,
            "row_count": 0,
            "first_seq": None,
            "last_seq": None,
            "head_digest": "",
            "failure_seq": None,
            "reason": "audit_db_error",
        }
    finally:
        conn.close()


def verify_audit_checkpoint(
    db_path: Path,
    checkpoint: dict[str, Any],
    *,
    hmac_key: bytes | None = None,
) -> dict[str, Any]:
    """Verify an exported audit checkpoint against a SQLite audit log.

    Confirms:
    1. Checkpoint digest (and optional HMAC-SHA256) matches the checkpoint body.
    2. The full SQLite audit chain is currently intact.
    3. The log has not been truncated or rewritten prior to ``checkpoint["last_seq"]``
       (append-only growth past the checkpoint is permitted and verified).
    """
    required_keys = (
        "schema_version",
        "exported_at_ns",
        "row_count",
        "first_seq",
        "last_seq",
        "head_digest",
        "checkpoint_digest",
    )
    if any(k not in checkpoint for k in required_keys):
        return {
            "valid": False,
            "reason": "checkpoint_missing_fields",
            "checkpoint_seq": None,
            "current_row_count": 0,
            "current_head_digest": "",
        }
    core = {
        "schema_version": checkpoint["schema_version"],
        "exported_at_ns": checkpoint["exported_at_ns"],
        "row_count": checkpoint["row_count"],
        "first_seq": checkpoint["first_seq"],
        "last_seq": checkpoint["last_seq"],
        "head_digest": checkpoint["head_digest"],
    }
    try:
        canonical = _canonical_checkpoint_core(core)
    except (TypeError, ValueError):
        return {
            "valid": False,
            "reason": "checkpoint_invalid_json",
            "checkpoint_seq": None,
            "current_row_count": 0,
            "current_head_digest": "",
        }
    expected_digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(expected_digest, str(checkpoint["checkpoint_digest"])):
        return {
            "valid": False,
            "reason": "checkpoint_digest_mismatch",
            "checkpoint_seq": checkpoint["last_seq"],
            "current_row_count": 0,
            "current_head_digest": "",
        }
    if hmac_key is not None:
        if not isinstance(hmac_key, (bytes, bytearray)) or not hmac_key:
            raise ValueError("hmac_key must be non-empty bytes")
        provided_hmac = checkpoint.get("hmac_sha256")
        expected_hmac = hmac.new(
            bytes(hmac_key), canonical.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        if not isinstance(provided_hmac, str) or not hmac.compare_digest(
            expected_hmac, provided_hmac
        ):
            return {
                "valid": False,
                "reason": "checkpoint_hmac_mismatch",
                "checkpoint_seq": checkpoint["last_seq"],
                "current_row_count": 0,
                "current_head_digest": "",
            }

    chain = verify_audit_chain(db_path)
    if not chain["valid"]:
        return {
            "valid": False,
            "reason": f"chain_invalid:{chain['reason']}",
            "checkpoint_seq": checkpoint["last_seq"],
            "current_row_count": chain["row_count"],
            "current_head_digest": chain["head_digest"],
        }

    cp_count = int(checkpoint["row_count"])
    cp_last_seq = checkpoint["last_seq"]
    if chain["row_count"] < cp_count:
        return {
            "valid": False,
            "reason": "audit_truncated",
            "checkpoint_seq": cp_last_seq,
            "current_row_count": chain["row_count"],
            "current_head_digest": chain["head_digest"],
        }
    if cp_count == 0:
        if cp_last_seq is not None or checkpoint["head_digest"] != "":
            return {
                "valid": False,
                "reason": "checkpoint_empty_mismatch",
                "checkpoint_seq": cp_last_seq,
                "current_row_count": chain["row_count"],
                "current_head_digest": chain["head_digest"],
            }
        return {
            "valid": True,
            "reason": "ok",
            "checkpoint_seq": None,
            "current_row_count": chain["row_count"],
            "current_head_digest": chain["head_digest"],
        }

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT digest FROM audit WHERE seq = ?", (cp_last_seq,)).fetchone()
    finally:
        conn.close()
    if row is None or not hmac.compare_digest(str(row[0]), str(checkpoint["head_digest"])):
        return {
            "valid": False,
            "reason": "checkpoint_anchor_mismatch",
            "checkpoint_seq": cp_last_seq,
            "current_row_count": chain["row_count"],
            "current_head_digest": chain["head_digest"],
        }
    return {
        "valid": True,
        "reason": "ok",
        "checkpoint_seq": cp_last_seq,
        "current_row_count": chain["row_count"],
        "current_head_digest": chain["head_digest"],
    }


class Audit:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS audit (seq INTEGER PRIMARY KEY, payload TEXT NOT NULL, previous TEXT NOT NULL, digest TEXT NOT NULL)"
        )
        self.db.commit()
        if os.name != "nt":
            path.chmod(0o600)

    def append(self, record: dict[str, Any]) -> None:
        try:
            payload = json.dumps(
                {"schema_version": 1, "time_ns": time.time_ns(), **record},
                sort_keys=True,
                allow_nan=False,
            )
            previous_row = self.db.execute(
                "SELECT digest FROM audit ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            previous = previous_row[0] if previous_row else ""
            digest = hashlib.sha256((previous + payload).encode()).hexdigest()
            self.db.execute(
                "INSERT INTO audit(payload,previous,digest) VALUES (?,?,?)",
                (payload, previous, digest),
            )
            self.db.commit()
        except (sqlite3.Error, ValueError) as exc:
            raise ServiceError("audit_unavailable") from exc

    def verify_chain(self) -> dict[str, Any]:
        """Verify integrity of all rows currently in this audit database."""
        try:
            return _verify_audit_connection(self.db)
        except sqlite3.Error as exc:
            raise ServiceError("audit_unavailable") from exc

    def export_checkpoint(
        self,
        checkpoint_path: Path | None = None,
        *,
        hmac_key: bytes | None = None,
    ) -> dict[str, Any]:
        """Export a verified (and optionally HMAC-authenticated) checkpoint of the audit head."""
        if hmac_key is not None and (not isinstance(hmac_key, (bytes, bytearray)) or not hmac_key):
            raise ValueError("hmac_key must be non-empty bytes")
        status = self.verify_chain()
        if not status["valid"]:
            raise ServiceError("audit_chain_corrupted", 500)
        core = {
            "schema_version": 1,
            "exported_at_ns": time.time_ns(),
            "row_count": status["row_count"],
            "first_seq": status["first_seq"],
            "last_seq": status["last_seq"],
            "head_digest": status["head_digest"],
        }
        canonical = _canonical_checkpoint_core(core)
        checkpoint: dict[str, Any] = {
            **core,
            "checkpoint_digest": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        }
        if hmac_key is not None:
            checkpoint["hmac_sha256"] = hmac.new(
                bytes(hmac_key), canonical.encode("utf-8"), hashlib.sha256
            ).hexdigest()
        if checkpoint_path is not None:
            _atomic_write_json(checkpoint_path, checkpoint)
        return checkpoint


class SQLiteStateStore:
    """Durable SQLite persistence for Gateway sessions and per-principal rate buckets (T246)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS sessions ("
            "sid TEXT PRIMARY KEY, "
            "owner TEXT NOT NULL, "
            "created_at REAL NOT NULL, "
            "last_seen REAL NOT NULL)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS rates ("
            "owner TEXT PRIMARY KEY, "
            "tokens REAL NOT NULL, "
            "updated_at REAL NOT NULL)"
        )
        self.db.commit()
        if os.name != "nt":
            path.chmod(0o600)

    def load_sessions(self) -> dict[str, tuple[str, float, float]]:
        try:
            rows = self.db.execute(
                "SELECT sid, owner, created_at, last_seen FROM sessions"
            ).fetchall()
            return {
                str(sid): (str(owner), float(created_at), float(last_seen))
                for sid, owner, created_at, last_seen in rows
            }
        except sqlite3.Error as exc:
            raise ServiceError("state_store_unavailable") from exc

    def put_session(self, sid: str, owner: str, created_at: float, last_seen: float) -> None:
        try:
            self.db.execute(
                "INSERT INTO sessions(sid, owner, created_at, last_seen) VALUES (?,?,?,?) "
                "ON CONFLICT(sid) DO UPDATE SET owner=excluded.owner, "
                "created_at=excluded.created_at, last_seen=excluded.last_seen",
                (sid, owner, float(created_at), float(last_seen)),
            )
            self.db.commit()
        except sqlite3.Error as exc:
            raise ServiceError("state_store_unavailable") from exc

    def delete_session(self, sid: str) -> None:
        try:
            self.db.execute("DELETE FROM sessions WHERE sid = ?", (sid,))
            self.db.commit()
        except sqlite3.Error as exc:
            raise ServiceError("state_store_unavailable") from exc

    def delete_sessions(self, sids: list[str]) -> None:
        if not sids:
            return
        try:
            self.db.executemany("DELETE FROM sessions WHERE sid = ?", [(s,) for s in sids])
            self.db.commit()
        except sqlite3.Error as exc:
            raise ServiceError("state_store_unavailable") from exc

    def load_rates(self) -> dict[str, tuple[float, float]]:
        try:
            rows = self.db.execute("SELECT owner, tokens, updated_at FROM rates").fetchall()
            return {
                str(owner): (float(tokens), float(updated_at)) for owner, tokens, updated_at in rows
            }
        except sqlite3.Error as exc:
            raise ServiceError("state_store_unavailable") from exc

    def put_rate(self, owner: str, tokens: float, updated_at: float) -> None:
        try:
            self.db.execute(
                "INSERT INTO rates(owner, tokens, updated_at) VALUES (?,?,?) "
                "ON CONFLICT(owner) DO UPDATE SET tokens=excluded.tokens, updated_at=excluded.updated_at",
                (owner, float(tokens), float(updated_at)),
            )
            self.db.commit()
        except sqlite3.Error as exc:
            raise ServiceError("state_store_unavailable") from exc

    def prune_rates(self, min_updated_at: float) -> None:
        try:
            self.db.execute("DELETE FROM rates WHERE updated_at <= ?", (float(min_updated_at),))
            self.db.commit()
        except sqlite3.Error as exc:
            raise ServiceError("state_store_unavailable") from exc

    def close(self) -> None:
        self.db.close()


class Execution:
    def __init__(self, config: HTTPConfig) -> None:
        self.config = config
        self.active: dict[str, int] = {}
        self.total = 0

    async def compute(self, owner: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if (
            self.total >= self.config.total_workers
            or self.active.get(owner, 0) >= self.config.principal_workers
        ):
            raise ServiceError("workers_exhausted", 429)
        self.total += 1
        self.active[owner] = self.active.get(owner, 0) + 1
        process = None
        home = tempfile.TemporaryDirectory(prefix="qspeace-worker-")
        try:
            env = {
                k: v for k, v in os.environ.items() if k in {"SYSTEMROOT", "PATH", "TEMP", "TMP"}
            }
            env.update(HOME=home.name, USERPROFILE=home.name, TEMP=home.name, TMP=home.name)
            env.update(
                OPENBLAS_NUM_THREADS="1",
                OMP_NUM_THREADS="1",
                MKL_NUM_THREADS="1",
                PYTHONHASHSEED="0",
            )
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                str(Path(__file__).with_name("worker.py")),
                cwd=Path(__file__).resolve().parents[2],
                env=env,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            payload = json.dumps({"name": name, "arguments": arguments}, allow_nan=False).encode()
            output, _ = await asyncio.wait_for(
                process.communicate(payload), self.config.worker_seconds
            )
            if process.returncode != 0 or len(output) > 256 * 1024:
                raise ServiceError("worker_failed")
            result = json.loads(output)
            if not result.get("ok"):
                raise ServiceError("invalid_arguments_or_computation", 400)
            return dict(result["result"])
        except TimeoutError as exc:
            raise ServiceError("worker_timeout", 504) from exc
        except (ValueError, KeyError, OSError) as exc:
            raise ServiceError("worker_failed") from exc
        finally:
            if process is not None and process.returncode is None:
                process.kill()
                await asyncio.shield(process.wait())
            home.cleanup()
            self.total -= 1
            self.active[owner] -= 1
            if self.active[owner] == 0:
                del self.active[owner]
