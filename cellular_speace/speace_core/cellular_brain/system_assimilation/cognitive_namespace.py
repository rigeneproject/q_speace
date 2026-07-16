"""UnifiedNamespace — maps every OS resource to a neural cell_id.

Every resource on the system (process, file, socket, service, device,
GPU thread, environment variable) has a canonical cell_id in SPEACE's
neural space. The brain does not distinguish between a thought and a
file descriptor — both are activation patterns in the same space.

Naming convention:
  os:proc:<pid>         — process
  os:file:<path_hash>   — file / directory
  os:sock:<proto>:<port> — network socket
  os:srv:<name>         — Windows service
  os:dev:<device_id>    — hardware device
  os:env:<var_name>     — environment variable
  os:thread:<tid>       — OS thread
  os:gpu:<uuid>         — GPU compute resource
  os:mem:<region>       — memory region
  os:user:<sid>         — user account
"""

import hashlib
import os as os_mod
import platform
import socket
from typing import Any, Dict, List, Optional


class UnifiedNamespace:
    """Maps system resources to canonical cell_ids for the neural space.

    Every lookup is O(1) from a local cache. The cache is refreshed
    periodically by the CognitiveHypervisor.
    """

    def __init__(self) -> None:
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._reverse_cache: Dict[str, str] = {}

    # ------------------------------------------------------------------ #
    # Cell ID generation
    # ------------------------------------------------------------------ #

    @staticmethod
    def process_cell_id(pid: int) -> str:
        return f"os:proc:{pid}"

    @staticmethod
    def file_cell_id(path: str) -> str:
        h = hashlib.sha256(path.lower().encode("utf-8")).hexdigest()[:12]
        return f"os:file:{h}"

    @staticmethod
    def socket_cell_id(proto: str, port: int, host: str = "*") -> str:
        return f"os:sock:{proto}:{host}:{port}"

    @staticmethod
    def service_cell_id(name: str) -> str:
        return f"os:srv:{name.lower().replace(' ', '_')}"

    @staticmethod
    def device_cell_id(device_id: str) -> str:
        h = hashlib.sha256(device_id.encode("utf-8")).hexdigest()[:12]
        return f"os:dev:{h}"

    @staticmethod
    def env_cell_id(var_name: str) -> str:
        return f"os:env:{var_name.upper()}"

    @staticmethod
    def thread_cell_id(tid: int) -> str:
        return f"os:thread:{tid}"

    @staticmethod
    def user_cell_id(sid: str) -> str:
        h = hashlib.sha256(sid.encode("utf-8")).hexdigest()[:12]
        return f"os:user:{h}"

    @staticmethod
    def memory_cell_id(region: str) -> str:
        return f"os:mem:{region}"

    @staticmethod
    def host_cell_id() -> str:
        return f"os:host:{socket.gethostname().lower()}"

    # ------------------------------------------------------------------ #
    # Cache management
    # ------------------------------------------------------------------ #

    def register(self, cell_id: str, resource: Dict[str, Any]) -> None:
        self._cache[cell_id] = resource
        rid = str(resource.get("id", ""))
        if rid:
            self._reverse_cache[rid] = cell_id

    def get(self, cell_id: str) -> Optional[Dict[str, Any]]:
        return self._cache.get(cell_id)

    def resolve(self, resource_id: str) -> Optional[str]:
        return self._reverse_cache.get(resource_id)

    def remove(self, cell_id: str) -> None:
        entry = self._cache.pop(cell_id, None)
        if entry:
            rid = str(entry.get("id", ""))
            self._reverse_cache.pop(rid, None)

    def clear(self) -> None:
        self._cache.clear()
        self._reverse_cache.clear()

    # ------------------------------------------------------------------ #
    # Bulk operations
    # ------------------------------------------------------------------ #

    def snapshot(self) -> Dict[str, Any]:
        return {
            "total_mappings": len(self._cache),
            "categories": self._count_categories(),
            "sample": list(self._cache.keys())[:20],
        }

    def _count_categories(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for cid in self._cache:
            prefix = cid.split(":")[1] if ":" in cid else "other"
            counts[prefix] = counts.get(prefix, 0) + 1
        return counts

    def list_by_category(self, category: str) -> List[str]:
        prefix = f"os:{category}:"
        return [cid for cid in self._cache if cid.startswith(prefix)]

    def search(self, query: str) -> List[str]:
        q = query.lower()
        return [cid for cid in self._cache if q in cid.lower()]

    @property
    def total(self) -> int:
        return len(self._cache)
