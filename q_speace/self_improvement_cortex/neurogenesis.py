"""NeurogenesisPipeline — automatic creation of new agents/modules (T41)."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto


class ModuleStatus(Enum):
    CREATED = auto()
    TRAINING = auto()
    CONNECTED = auto()
    TESTING = auto()
    PROMOTED = auto()
    INTEGRATED = auto()
    REJECTED = auto()


@dataclass
class NewModuleSpec:
    module_id: str = ""
    name: str = ""
    purpose: str = ""
    activity_pattern: str = ""
    module_type: str = "agent"
    status: ModuleStatus = ModuleStatus.CREATED
    created_at: float = 0.0
    metrics: dict[str, float] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        return self.status in (ModuleStatus.PROMOTED, ModuleStatus.INTEGRATED)


class NeurogenesisPipeline:
    """Pipeline for discovering and creating new cognitive modules.

    Detects recurrent uncovered activity patterns and spawns new agents.
    """

    def __init__(
        self,
        min_occurrences: int = 5,
        min_novelty: float = 0.3,
    ) -> None:
        self._activity_log: list[dict] = []
        self._modules: list[NewModuleSpec] = []
        self._min_occurrences = min_occurrences
        self._min_novelty = min_novelty

    def observe_activity(self, activity_type: str, context: dict) -> None:
        self._activity_log.append({
            "type": activity_type,
            "context": context,
            "timestamp": time.time(),
        })
        if len(self._activity_log) > 1000:
            self._activity_log.pop(0)

    def detect_recurrent_activities(self) -> list[tuple[str, int]]:
        counts: dict[str, int] = {}
        for entry in self._activity_log:
            t = entry["type"]
            counts[t] = counts.get(t, 0) + 1
        return [
            (act, count) for act, count in counts.items()
            if count >= self._min_occurrences
            and not any(m.activity_pattern == act for m in self._modules if m.is_active)
        ]

    def propose_module(self, activity_type: str, novelty: float = 0.0) -> NewModuleSpec | None:
        if novelty < self._min_novelty:
            return None
        spec = NewModuleSpec(
            module_id=uuid.uuid4().hex[:12],
            name=f"module_{activity_type}",
            purpose=f"Handle recurrent activity: {activity_type}",
            activity_pattern=activity_type,
            created_at=time.time(),
        )
        self._modules.append(spec)
        return spec

    def advance(self, module_id: str) -> ModuleStatus | None:
        for mod in self._modules:
            if mod.module_id == module_id:
                mapping = {
                    ModuleStatus.CREATED: ModuleStatus.TRAINING,
                    ModuleStatus.TRAINING: ModuleStatus.CONNECTED,
                    ModuleStatus.CONNECTED: ModuleStatus.TESTING,
                    ModuleStatus.TESTING: ModuleStatus.PROMOTED,
                    ModuleStatus.PROMOTED: ModuleStatus.INTEGRATED,
                }
                mod.status = mapping.get(mod.status, mod.status)
                return mod.status
        return None

    def reject(self, module_id: str) -> bool:
        for mod in self._modules:
            if mod.module_id == module_id:
                mod.status = ModuleStatus.REJECTED
                return True
        return False

    def active_modules(self) -> list[NewModuleSpec]:
        return [m for m in self._modules if m.is_active]

    def pipeline_status(self) -> list[NewModuleSpec]:
        return list(self._modules)
