import json
from pathlib import Path
from typing import Dict, List, Optional

from speace_core.cellular_brain.memory.semantic.cell_assembly import (
    CellAssembly,
    SemanticMemoryMetrics,
)


class SemanticMemoryStore:
    """Persistence and retrieval layer for cell assemblies."""

    def __init__(self, storage_path: Optional[str] = None):
        self._assemblies: Dict[str, CellAssembly] = {}
        self._metrics_log: List[SemanticMemoryMetrics] = []
        self._storage_path = Path(storage_path) if storage_path else None
        if self._storage_path is not None:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            self._load()

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #

    def save(self, assembly: CellAssembly) -> None:
        self._assemblies[assembly.assembly_id] = assembly

    def get_by_id(self, assembly_id: str) -> Optional[CellAssembly]:
        return self._assemblies.get(assembly_id)

    def list_active(self) -> List[CellAssembly]:
        return [a for a in self._assemblies.values() if a.active]

    def list_consolidated(self) -> List[CellAssembly]:
        return [a for a in self._assemblies.values() if a.consolidated]

    def count(self) -> int:
        return len(self._assemblies)

    def get_best_by_strength(self, n: int = 5) -> List[CellAssembly]:
        return sorted(
            self._assemblies.values(), key=lambda a: a.strength, reverse=True
        )[:n]

    def get_recent(self, n: int = 5) -> List[CellAssembly]:
        return sorted(
            self._assemblies.values(),
            key=lambda a: a.last_activated_tick,
            reverse=True,
        )[:n]

    def persist_metrics(self, metrics: SemanticMemoryMetrics) -> None:
        self._metrics_log.append(metrics)

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #

    def _load(self) -> None:
        if self._storage_path is None or not self._storage_path.exists():
            return
        for line in self._storage_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                assembly = CellAssembly(**data)
                self._assemblies[assembly.assembly_id] = assembly
            except Exception:
                continue

    def flush(self) -> None:
        if self._storage_path is None:
            return
        lines = []
        for assembly in self._assemblies.values():
            lines.append(assembly.model_dump_json())
        self._storage_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def clear(self) -> None:
        self._assemblies.clear()
        self._metrics_log.clear()
