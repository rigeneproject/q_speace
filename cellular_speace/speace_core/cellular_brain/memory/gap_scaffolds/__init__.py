"""Scaffolding for memory capability gaps.

Modules:
- failure_memory: structured log of task/cognitive failures with retrieval-by-context
- object_centric_representation: simple object-centric feature store for compositional reasoning
"""
from .failure_memory import FailureMemory, FailureRecord
from .object_centric_representation import (
    ObjectCentricRepresentation,
    ObjectSlot,
    SceneDescription,
)

__all__ = [
    "FailureMemory",
    "FailureRecord",
    "ObjectCentricRepresentation",
    "ObjectSlot",
    "SceneDescription",
]
