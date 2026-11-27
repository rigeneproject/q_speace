"""Plastic regional astrocyte gap-junction syncytium & metabolic buffering (T256-01).

Synthesized via BCEL from ``SPEACE PROTOTIPO CLAUDE`` (``SPEACE_Cortex/astrocyte_network.py``,
inspired by *Nature* 2026 regional plastic astrocyte networks):
- Anatomical lobe metaphors are *accidental* and omitted.
- Bidirectional gap-junction conductances ``g_ij`` in ``[min_permeability, 1.0]`` modulated
  by regional coherence ``phi``, pruning below threshold, attenuated BFS wave propagation,
  and mass-conserving donor-floor-protected energy redistribution survive as deterministic
  mathematical operators.
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field


def _canonical_pair(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


@dataclass
class GapJunctionLink:
    """Bidirectional gap junction connecting two regional astrocyte nodes."""

    node_a: str
    node_b: str
    permeability: float = 0.50
    min_permeability: float = 0.05
    total_flux_events: int = 0

    def __post_init__(self) -> None:
        if not self.node_a or not self.node_b or self.node_a == self.node_b:
            raise ValueError("GapJunctionLink requires two distinct non-empty node IDs")
        if not math.isfinite(self.min_permeability) or not (0.0 < self.min_permeability <= 0.5):
            raise ValueError("min_permeability must be finite and in (0, 0.5]")
        if not math.isfinite(self.permeability) or not (0.0 <= self.permeability <= 1.0):
            raise ValueError("permeability must be finite and in [0, 1]")

    def flux(self, signal: Mapping[str, float]) -> dict[str, float]:
        """Transmit and scale numeric signal components by junction permeability."""
        self.total_flux_events += 1
        out: dict[str, float] = {}
        for k, v in signal.items():
            fv = float(v)
            if not math.isfinite(fv):
                raise ValueError(f"signal[{k!r}] must be finite")
            out[k] = fv * self.permeability
        return out

    def modulate(self, delta: float) -> float:
        """Adjust permeability within ``[0.0, 1.0]`` (caller prunes below threshold)."""
        if not math.isfinite(delta):
            raise ValueError("delta must be finite")
        self.permeability = float(max(0.0, min(1.0, self.permeability + delta)))
        return self.permeability


@dataclass
class RegionalAstrocyteNode:
    """Regional glial node tracking activity wave, local coherence, and metabolic reserve."""

    node_id: str
    region: str
    activity_wave: float = 0.0
    local_coherence: float = 0.70
    metabolic_reserve: float = 1.00
    history: deque[float] = field(default_factory=lambda: deque(maxlen=64))

    def __post_init__(self) -> None:
        if not self.node_id or not self.region:
            raise ValueError("node_id and region must be non-empty")
        for name, val in (
            ("activity_wave", self.activity_wave),
            ("local_coherence", self.local_coherence),
            ("metabolic_reserve", self.metabolic_reserve),
        ):
            if not math.isfinite(val) or not (0.0 <= val <= 1.0):
                raise ValueError(f"{name} must be finite and in [0, 1]")

    def activate(self, delta: float) -> float:
        if not math.isfinite(delta) or delta < 0.0:
            raise ValueError("delta must be finite and >= 0")
        self.activity_wave = float(min(1.0, self.activity_wave + delta))
        self.history.append(self.activity_wave)
        return self.activity_wave


class PlasticAstrocyteSyncytium:
    """Plastic regional astrocyte network with gap-junction reorganization & buffering (T256-01)."""

    def __init__(
        self,
        syncytium_id: str = "regional_syncytium",
        *,
        hop_attenuation: float = 0.80,
        prune_threshold: float = 0.10,
        donor_floor: float = 0.30,
    ) -> None:
        if not syncytium_id:
            raise ValueError("syncytium_id must be non-empty")
        if not math.isfinite(hop_attenuation) or not (0.0 < hop_attenuation <= 1.0):
            raise ValueError("hop_attenuation must be in (0, 1]")
        if not math.isfinite(prune_threshold) or not (0.0 <= prune_threshold < 1.0):
            raise ValueError("prune_threshold must be in [0, 1)")
        if not math.isfinite(donor_floor) or not (0.0 <= donor_floor < 1.0):
            raise ValueError("donor_floor must be in [0, 1)")

        self.syncytium_id = syncytium_id
        self.hop_attenuation = float(hop_attenuation)
        self.prune_threshold = float(prune_threshold)
        self.donor_floor = float(donor_floor)
        self._nodes: dict[str, RegionalAstrocyteNode] = {}
        self._junctions: dict[tuple[str, str], GapJunctionLink] = {}
        self._adj: dict[str, set[str]] = {}
        self._plasticity_events: deque[dict[str, int | float]] = deque(maxlen=128)

    @property
    def nodes(self) -> Mapping[str, RegionalAstrocyteNode]:
        return self._nodes

    @property
    def junctions(self) -> Mapping[tuple[str, str], GapJunctionLink]:
        return self._junctions

    def add_node(
        self,
        node_id: str,
        region: str,
        *,
        metabolic_reserve: float = 1.0,
        local_coherence: float = 0.70,
    ) -> RegionalAstrocyteNode:
        if node_id in self._nodes:
            raise ValueError(f"Duplicate astrocyte node: {node_id!r}")
        node = RegionalAstrocyteNode(
            node_id=node_id,
            region=region,
            local_coherence=local_coherence,
            metabolic_reserve=metabolic_reserve,
        )
        self._nodes[node_id] = node
        self._adj[node_id] = set()
        return node

    def connect(
        self,
        node_a: str,
        node_b: str,
        *,
        permeability: float = 0.50,
    ) -> GapJunctionLink:
        if node_a not in self._nodes or node_b not in self._nodes:
            raise KeyError("Both astrocyte nodes must exist before connecting")
        key = _canonical_pair(node_a, node_b)
        if key not in self._junctions:
            self._junctions[key] = GapJunctionLink(key[0], key[1], permeability=permeability)
            self._adj[key[0]].add(key[1])
            self._adj[key[1]].add(key[0])
        return self._junctions[key]

    def propagate_wave(self, origin_id: str, phi: float) -> dict[str, dict[str, float]]:
        """Propagate an attenuated coherence/metabolic wave from ``origin_id`` via BFS."""
        if origin_id not in self._nodes:
            raise KeyError(f"Unknown origin astrocyte: {origin_id!r}")
        if not math.isfinite(phi) or not (0.0 <= phi <= 1.0):
            raise ValueError("phi must be finite and in [0, 1]")

        origin = self._nodes[origin_id]
        origin.activate(phi)
        origin.local_coherence = float(phi)

        visited = {origin_id}
        queue: deque[str] = deque([origin_id])
        reached: dict[str, dict[str, float]] = {
            origin_id: {
                "activity_wave": origin.activity_wave,
                "local_coherence": origin.local_coherence,
                "metabolic_alert": 1.0 - origin.metabolic_reserve,
            }
        }

        while queue:
            curr_id = queue.popleft()
            curr = self._nodes[curr_id]
            for nb_id in sorted(self._adj.get(curr_id, ())):
                if nb_id in visited:
                    continue
                key = _canonical_pair(curr_id, nb_id)
                gj = self._junctions.get(key)
                if gj is None:
                    continue
                visited.add(nb_id)
                transmitted = gj.flux(
                    {
                        "wave": curr.activity_wave * self.hop_attenuation,
                        "coherence": curr.local_coherence,
                        "metabolic_alert": 1.0 - curr.metabolic_reserve,
                    }
                )
                nb = self._nodes[nb_id]
                nb.activate(transmitted["wave"])
                # Blend neighbor coherence proportionally to junction permeability
                alpha = 0.30 * gj.permeability
                nb.local_coherence = float(
                    max(
                        0.0,
                        min(1.0, (1.0 - alpha) * nb.local_coherence + alpha * curr.local_coherence),
                    )
                )
                reached[nb_id] = {
                    "activity_wave": nb.activity_wave,
                    "local_coherence": nb.local_coherence,
                    "metabolic_alert": transmitted["metabolic_alert"],
                }
                queue.append(nb_id)

        return reached

    def reorganize(
        self,
        phi_history: Sequence[float],
        *,
        high_phi: float = 0.70,
        low_phi: float = 0.40,
        step_delta: float = 0.05,
    ) -> dict[str, int]:
        """Modulate gap-junction conductances from recent ``phi_history`` and prune weak links."""
        if not phi_history:
            return {"strengthened": 0, "weakened": 0, "pruned": 0}
        window = [float(x) for x in phi_history[-10:]]
        if not all(math.isfinite(x) for x in window):
            raise ValueError("phi_history must contain only finite values")
        avg_phi = sum(window) / len(window)

        strengthened = 0
        weakened = 0
        pruned = 0

        for key in list(self._junctions.keys()):
            gj = self._junctions[key]
            if avg_phi > high_phi:
                gj.modulate(+abs(step_delta))
                strengthened += 1
            elif avg_phi < low_phi:
                new_p = gj.modulate(-abs(step_delta))
                if new_p < self.prune_threshold:
                    del self._junctions[key]
                    self._adj[key[0]].discard(key[1])
                    self._adj[key[1]].discard(key[0])
                    pruned += 1
                else:
                    weakened += 1

        summary = {"strengthened": strengthened, "weakened": weakened, "pruned": pruned}
        if strengthened or weakened or pruned:
            self._plasticity_events.append({"avg_phi": avg_phi, **summary})
        return summary

    def redistribute_reserves(
        self,
        needy_ids: Sequence[str],
        donor_ids: Sequence[str],
        *,
        max_donor_fraction: float = 0.50,
    ) -> float:
        """Transfer metabolic reserve from donors (above ``donor_floor``) to needy nodes.

        Strictly conserves ``sum(n.metabolic_reserve for n in nodes)``.
        Returns total energy transferred.
        """
        if not math.isfinite(max_donor_fraction) or not (0.0 < max_donor_fraction <= 1.0):
            raise ValueError("max_donor_fraction must be in (0, 1]")

        total_transferred = 0.0
        for nid in needy_ids:
            needy = self._nodes.get(nid)
            if needy is None:
                continue
            deficit = 1.0 - needy.metabolic_reserve
            if deficit <= 1e-9:
                continue
            for did in donor_ids:
                if did == nid:
                    continue
                donor = self._nodes.get(did)
                if donor is None:
                    continue
                surplus = donor.metabolic_reserve - self.donor_floor
                if surplus <= 1e-9:
                    continue
                transfer = min(deficit, surplus * max_donor_fraction)
                donor.metabolic_reserve = float(max(0.0, donor.metabolic_reserve - transfer))
                needy.metabolic_reserve = float(min(1.0, needy.metabolic_reserve + transfer))
                deficit -= transfer
                total_transferred += transfer
                if deficit <= 1e-9:
                    break

        return float(total_transferred)
