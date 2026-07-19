"""10 adaptive levels — Harness Update to Weight Update to Neurogenesis (T35)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class AdaptiveLevel(IntEnum):
    PROMPT = 1
    WORKFLOW = 2
    TOOL = 3
    AGENTS = 4
    MEMORY = 5
    WORLD_MODEL = 6
    DIGITAL_DNA = 7
    LORA = 8
    NEW_MODEL = 9
    NEW_NETWORK = 10


LEVEL_NAMES = {
    AdaptiveLevel.PROMPT: "Prompt",
    AdaptiveLevel.WORKFLOW: "Workflow",
    AdaptiveLevel.TOOL: "Tool",
    AdaptiveLevel.AGENTS: "Agents",
    AdaptiveLevel.MEMORY: "Memory",
    AdaptiveLevel.WORLD_MODEL: "World Model",
    AdaptiveLevel.DIGITAL_DNA: "Digital DNA",
    AdaptiveLevel.LORA: "LoRA",
    AdaptiveLevel.NEW_MODEL: "New Model",
    AdaptiveLevel.NEW_NETWORK: "New Network",
}

LEVEL_UPDATE_TYPE = {
    AdaptiveLevel.PROMPT: "harness",
    AdaptiveLevel.WORKFLOW: "harness",
    AdaptiveLevel.TOOL: "harness",
    AdaptiveLevel.AGENTS: "harness",
    AdaptiveLevel.MEMORY: "harness",
    AdaptiveLevel.WORLD_MODEL: "harness",
    AdaptiveLevel.DIGITAL_DNA: "epigenetic",
    AdaptiveLevel.LORA: "weight",
    AdaptiveLevel.NEW_MODEL: "weight",
    AdaptiveLevel.NEW_NETWORK: "neurogenesis",
}


@dataclass
class HarnessUpdate:
    level: AdaptiveLevel
    target: str
    old_value: str = ""
    new_value: str = ""
    reason: str = ""

    @property
    def description(self) -> str:
        return f"[Harness] {LEVEL_NAMES[self.level]}: {self.target}"


@dataclass
class WeightUpdate:
    level: AdaptiveLevel
    method: str  # "lora" | "finetune" | "new_architecture"
    target_model: str = ""
    hyperparams: dict[str, float] = field(default_factory=dict)
    reason: str = ""

    @property
    def description(self) -> str:
        return f"[Weight] {LEVEL_NAMES[self.level]} via {self.method}"


@dataclass
class AdaptiveLevelRegistry:
    current_level: AdaptiveLevel = AdaptiveLevel.PROMPT

    def escalate(self) -> AdaptiveLevel | None:
        next_val = self.current_level.value + 1
        if next_val > AdaptiveLevel.NEW_NETWORK.value:
            return None
        self.current_level = AdaptiveLevel(next_val)
        return self.current_level

    def reset(self) -> None:
        self.current_level = AdaptiveLevel.PROMPT

    def set_level(self, level: AdaptiveLevel) -> None:
        self.current_level = level

    def update_type(self) -> str:
        return LEVEL_UPDATE_TYPE[self.current_level]

    def level_name(self) -> str:
        return LEVEL_NAMES[self.current_level]
