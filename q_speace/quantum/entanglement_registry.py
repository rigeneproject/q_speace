"""EntanglementRegistry — track entangled (entity, entity) pairs.

Mirrors ``cellular_speace/.../entanglement_registry.py``. Entanglement is
used in Q-SPEACE as a *computational resource for information binding*
(not as a communication channel — see the no-communication theorem).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class EntangledPair:
    """A bidirectional entanglement between two entities."""

    entity_a: str
    entity_b: str
    fidelity: float = 0.0
    created_at: float = field(default_factory=time.time)
    label: str = ""
    metadata: dict[str, str] = field(default_factory=dict)

    def involves(self, entity_id: str) -> bool:
        return entity_id in (self.entity_a, self.entity_b)

    def other(self, entity_id: str) -> str:
        if entity_id == self.entity_a:
            return self.entity_b
        if entity_id == self.entity_b:
            return self.entity_a
        raise KeyError(f"entity {entity_id} not in pair")


class EntanglementRegistry:
    """Registry of entangled entity pairs with graph queries."""

    def __init__(self) -> None:
        self._pairs: list[EntangledPair] = []
        self._by_entity: dict[str, list[int]] = {}

    def entangle(
        self,
        entity_a: str,
        entity_b: str,
        fidelity: float = 0.0,
        label: str = "",
        metadata: dict[str, str] | None = None,
    ) -> EntangledPair:
        if entity_a == entity_b:
            raise ValueError("cannot entangle an entity with itself")
        pair = EntangledPair(
            entity_a=entity_a,
            entity_b=entity_b,
            fidelity=float(fidelity),
            label=label,
            metadata=metadata or {},
        )
        self._pairs.append(pair)
        idx = len(self._pairs) - 1
        self._by_entity.setdefault(entity_a, []).append(idx)
        self._by_entity.setdefault(entity_b, []).append(idx)
        return pair

    def disentangle(self, entity_a: str, entity_b: str) -> bool:
        removed = False
        for i in range(len(self._pairs) - 1, -1, -1):
            p = self._pairs[i]
            if {p.entity_a, p.entity_b} == {entity_a, entity_b}:
                self._pairs.pop(i)
                removed = True
        if removed:
            self._by_entity.clear()
            for j, p in enumerate(self._pairs):
                self._by_entity.setdefault(p.entity_a, []).append(j)
                self._by_entity.setdefault(p.entity_b, []).append(j)
        return removed

    def pairs_of(self, entity_id: str) -> list[EntangledPair]:
        return [self._pairs[i] for i in self._by_entity.get(entity_id, [])]

    def partners_of(self, entity_id: str) -> set[str]:
        return {p.other(entity_id) for p in self.pairs_of(entity_id)}

    def degree(self, entity_id: str) -> int:
        return len(self._by_entity.get(entity_id, []))

    def is_entangled(self, entity_a: str, entity_b: str) -> bool:
        return any(
            {p.entity_a, p.entity_b} == {entity_a, entity_b} for p in self._pairs
        )

    def all_pairs(self) -> list[EntangledPair]:
        return list(self._pairs)

    def connected_components(self) -> list[set[str]]:
        nodes: set[str] = set()
        for p in self._pairs:
            nodes.add(p.entity_a)
            nodes.add(p.entity_b)
        visited: set[str] = set()
        comps: list[set[str]] = []
        for n in nodes:
            if n in visited:
                continue
            stack = [n]
            comp: set[str] = set()
            while stack:
                cur = stack.pop()
                if cur in visited:
                    continue
                visited.add(cur)
                comp.add(cur)
                for nb in self.partners_of(cur):
                    if nb not in visited:
                        stack.append(nb)
            comps.append(comp)
        return comps

    def count(self) -> int:
        return len(self._pairs)

    def clear(self) -> None:
        self._pairs.clear()
        self._by_entity.clear()
