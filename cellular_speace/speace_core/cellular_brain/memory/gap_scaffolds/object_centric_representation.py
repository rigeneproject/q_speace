"""Object-centric representation scaffolding.

A simple 'slot-based' scene description for compositional reasoning.
Each scene is a small dict of ObjectSlot(name, features) that downstream
modules (FSPI, planning, world model) can compose with bind/unbind operations.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass
class ObjectSlot:
    name: str
    features: Dict[str, Any] = field(default_factory=dict)

    def bind(self, other: "ObjectSlot") -> "ObjectSlot":
        return ObjectSlot(name=f"{self.name}__{other.name}",
                         features={**self.features, **other.features})


@dataclass
class SceneDescription:
    slots: List[ObjectSlot] = field(default_factory=list)
    relations: List[Tuple[str, str, str]] = field(default_factory=list)  # (subj, rel, obj)

    def add(self, slot: ObjectSlot) -> None:
        self.slots.append(slot)

    def relate(self, subj: str, relation: str, obj: str) -> None:
        self.relations.append((subj, relation, obj))

    def get(self, name: str) -> Optional[ObjectSlot]:
        for s in self.slots:
            if s.name == name:
                return s
        return None

    def compose(self, names: Iterable[str]) -> Optional[ObjectSlot]:
        cur: Optional[ObjectSlot] = None
        for n in names:
            slot = self.get(n)
            if slot is None:
                return None
            cur = slot if cur is None else cur.bind(slot)
        return cur


class ObjectCentricRepresentation:
    """Lightweight store of SceneDescription indexed by scene_id."""

    def __init__(self) -> None:
        self._scenes: Dict[str, SceneDescription] = {}

    def create(self, scene_id: str) -> SceneDescription:
        sc = SceneDescription()
        self._scenes[scene_id] = sc
        return sc

    def get(self, scene_id: str) -> Optional[SceneDescription]:
        return self._scenes.get(scene_id)

    def slots(self, scene_id: str) -> List[ObjectSlot]:
        sc = self._scenes.get(scene_id)
        return list(sc.slots) if sc else []

    def stats(self) -> Dict[str, Any]:
        return {
            "scenes": len(self._scenes),
            "slots_total": sum(len(s.slots) for s in self._scenes.values()),
            "relations_total": sum(len(s.relations) for s in self._scenes.values()),
        }
