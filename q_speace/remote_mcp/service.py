"""Bounded execution and local hash-only audit. Staging promotion remains separate."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from .config import HTTPConfig


class ServiceError(Exception):
    def __init__(self, code: str, status: int = 503) -> None:
        self.code = code
        self.status = status
        super().__init__(code)


class Audit:
    def __init__(self, path: Path) -> None:
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

