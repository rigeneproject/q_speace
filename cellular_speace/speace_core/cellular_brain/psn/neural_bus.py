from __future__ import annotations
from typing import Dict, Optional, Tuple

from speace_core.cellular_brain.psn.models import SynapseKey, SynapseCleft, ReceptorProfile


class NeuralBus:
    """Fast, volatile, point-to-point neurotransmitter signalling.

    Synapses are cleared every tick (reuptake). Supports masking
    for temporary desensitisation/habituation.
    """

    def __init__(self, receptors: Optional[Dict[str, Dict[str, ReceptorProfile]]] = None):
        self._synapses: Dict[SynapseKey, SynapseCleft] = {}
        self._receptors: Dict[str, Dict[str, ReceptorProfile]] = receptors or {}
        self._current_tick: int = 0

    @property
    def synapse_count(self) -> int:
        return len(self._synapses)

    @property
    def current_tick(self) -> int:
        return self._current_tick

    def set_tick(self, tick: int) -> None:
        self._current_tick = tick

    def synapse(
        self,
        molecule: str,
        value: float,
        source: str,
        target: str,
        receptor: str,
        confidence: float = 0.9,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Fire a neurotransmitter pulse across a specific synapse."""
        key = (molecule, source, target, receptor)
        existing = self._synapses.get(key)

        if existing and existing.masked and existing.mask_until_tick >= self._current_tick:
            return

        self._synapses[key] = SynapseCleft(
            molecule=molecule,
            value=max(0.0, min(1.0, value)),
            source=source,
            target=target,
            receptor=receptor,
            confidence=min(1.0, max(0.0, confidence)),
            timestamp=self._current_tick,
            metadata=metadata or {},
            masked=existing.masked if existing else False,
            mask_until_tick=existing.mask_until_tick if existing else 0,
        )

    def read(self, target: str, molecule: str, receptor: str) -> Optional[float]:
        """Read the current concentration at a specific synapse.

        Returns None if no signal is present.
        """
        best: Optional[float] = None
        best_confidence: float = 0.0

        for key, cleft in self._synapses.items():
            mol, src, tgt, rec = key
            if tgt == target and mol == molecule and rec == receptor:
                if cleft.masked and cleft.mask_until_tick >= self._current_tick:
                    continue
                if best is None or cleft.confidence > best_confidence:
                    best = cleft.value
                    best_confidence = cleft.confidence

        return best

    def read_synapse(self, key: SynapseKey) -> Optional[SynapseCleft]:
        """Read the full cleft at a specific synapse."""
        cleft = self._synapses.get(key)
        if cleft and cleft.masked and cleft.mask_until_tick >= self._current_tick:
            return None
        return cleft

    def clear_all(self) -> None:
        """Reuptake: clear all synapses at end of tick."""
        self._synapses.clear()

    def reuptake(self, molecule: str, synapse: SynapseKey) -> None:
        """Clear a specific synapse immediately."""
        if synapse in self._synapses:
            del self._synapses[synapse]

    def mask(
        self,
        molecule: str,
        source: str,
        target: str,
        receptor: str,
        duration_ticks: int = 10,
    ) -> None:
        """Temporarily block a specific synapse."""
        key = (molecule, source, target, receptor)
        if key in self._synapses:
            self._synapses[key].masked = True
            self._synapses[key].mask_until_tick = self._current_tick + duration_ticks
        else:
            cleft = SynapseCleft(
                molecule=molecule,
                value=0.0,
                source=source,
                target=target,
                receptor=receptor,
                timestamp=self._current_tick,
                masked=True,
                mask_until_tick=self._current_tick + duration_ticks,
            )
            self._synapses[key] = cleft

    def unmask(self, molecule: str, source: str, target: str, receptor: str) -> None:
        """Remove a mask from a synapse."""
        key = (molecule, source, target, receptor)
        if key in self._synapses:
            self._synapses[key].masked = False
            self._synapses[key].mask_until_tick = 0

    def snapshot(self) -> Dict[SynapseKey, float]:
        """Return current synapse values (unmasked only)."""
        result = {}
        for key, cleft in self._synapses.items():
            if not (cleft.masked and cleft.mask_until_tick >= self._current_tick):
                result[key] = cleft.value
        return result
