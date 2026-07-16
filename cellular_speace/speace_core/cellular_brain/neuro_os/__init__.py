"""Neuro-OS: organic operating system layer for SPEACE.

Unifies drive-based priority arbitration, circadian rhythm, process
management, and adaptive scheduling into a single neuro-evolutionary
layer. The OS is not centralised — it emerges from local scheduling
decisions synchronised by the ILF field.

Components:
  - CognitiveScheduler: adaptive module priority scheduling
  - ProcessTable: cognitive agent/process lifecycle management
  - MemoryPressureManager: hierarchical memory pressure & consolidation
"""

from speace_core.cellular_brain.neuro_os.cognitive_scheduler import (
    CognitiveScheduler,
    SchedulingDecision,
    ModulePriority,
)
from speace_core.cellular_brain.neuro_os.process_table import (
    ProcessTable,
    ProcessEntry,
    ProcessState,
    ResourceBudget,
)
from speace_core.cellular_brain.neuro_os.memory_pressure import (
    MemoryPressureManager,
    MemoryTier,
    MemoryTrace,
)

__all__ = [
    "CognitiveScheduler",
    "SchedulingDecision",
    "ModulePriority",
    "ProcessTable",
    "ProcessEntry",
    "ProcessState",
    "ResourceBudget",
    "MemoryPressureManager",
    "MemoryTier",
    "MemoryTrace",
]
