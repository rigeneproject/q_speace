"""PropagationEngine — routes SpikeEvents through periodic bond network.

Provides:
  - emit()         — inject a SpikeEvent into a circuit, collect postsynaptic FireCandidates
  - propagate()    — propagate all spikes after a burst through their target bonds
  - apply_stdp()   — STDP update using bond-specific plasticity from the periodic table
  - signal_delay() — bond delay from SynapticBond properties
"""
from __future__ import annotations

import math
from typing import Any, List, Optional, Tuple

from pydantic import BaseModel, Field

from speace_core.cellular_brain.neuroperiodic.neural_element import NeuralElement
from speace_core.cellular_brain.neuroperiodic.neural_periodic_table import (
    NeuralPeriodicTable,
    PeriodicTableBuilder,
)
from speace_core.cellular_brain.neuroperiodic.synaptic_bond import (
    BondRegistry,
    BondType,
    SynapticBond,
)


class SpikePropagationResult(BaseModel):
    """Result of a single propagation step."""
    propagated_spikes: int = 0
    attenuated_spikes: int = 0
    dropped_spikes: int = 0
    bonds_updated: int = 0
    candidates_generated: int = 0
    mean_delay: float = 0.0


class PropagationEngine:
    """Routes spikes through the periodic bond network with STDP.

    Connects the static periodic table (element types, bond predictions)
    to the runtime burst engine by converting SpikeEvents into FireCandidates
    with bond-specific properties (delay, attenuation, plasticity).
    """

    def __init__(
        self,
        table: Optional[NeuralPeriodicTable] = None,
        bond_registry: Optional[BondRegistry] = None,
    ):
        self.table = table or PeriodicTableBuilder.build_default()
        self.bond_registry = bond_registry or BondRegistry()

    # ------------------------------------------------------------------
    # Spike emission
    # ------------------------------------------------------------------

    def emit(
        self,
        spike: Any,
        circuit: Any,
        tick: int = 0,
    ) -> List[Any]:
        """Inject a spike into a circuit; return list of FireCandidates.

        Looks up outgoing bonds from the spike's source element and
        generates a FireCandidate for each postsynaptic neuron whose
        integration threshold is exceeded.

        This is the bridge between the periodic table and the existing
        EventDrivenBurstEngine.
        """
        candidates = []
        from speace_core.cellular_brain.execution.burst_engine import FireCandidate

        bonds = self._get_outgoing_bonds(spike.source_z)
        total_delay = 0.0

        for bond in bonds:
            delay = self.signal_delay(bond)
            total_delay += delay

            tgt_element = self.table.get_by_z(bond.target_z)
            if tgt_element is None:
                continue

            thr = tgt_element.ionization_energy
            activation = spike.strength * bond.bond_strength() * (1.0 / max(delay, 0.1))
            if activation > 0.01:
                candidates.append(FireCandidate(
                    neuron_id=f"neuron_z{bond.target_z}",
                    activation=activation,
                    threshold=max(0.1, thr),
                    priority=activation - thr,
                    source=f"spike_{spike.spike_id}",
                    created_at_burst=tick,
                ))

        return candidates

    # ------------------------------------------------------------------
    # Full burst propagation
    # ------------------------------------------------------------------

    def propagate(
        self,
        spikes: List[Any],
        circuit: Any,
        tick: int = 0,
    ) -> SpikePropagationResult:
        """Propagate all spikes through their target bonds.

        For each spike, finds the bond from source_z → target_z and
        creates a propagated SpikeEvent with bond-adjusted strength and delay.
        Returns those events for the next layer.
        """
        result = SpikePropagationResult()
        propagated = []
        delays = []

        from speace_core.cellular_brain.neuroperiodic.spike_event import SpikeEvent

        for spike in spikes:
            if spike.target_z is None:
                result.dropped_spikes += 1
                continue

            bond = self._find_bond(spike.source_z, spike.target_z)
            if bond is None:
                result.dropped_spikes += 1
                continue

            delay = self.signal_delay(bond)
            delays.append(delay)

            amp = bond.molecule.amplification_factor()
            new_strength = spike.strength * amp

            if new_strength < 0.01:
                result.attenuated_spikes += 1
                continue

            propagated.append(SpikeEvent(
                source_z=spike.source_z,
                target_z=spike.target_z,
                timestamp=spike.timestamp + int(delay * 10),
                phase=(spike.phase + 0.05 * delay) % (2.0 * math.pi),
                inter_spike_interval=spike.inter_spike_interval,
                strength=new_strength,
                bond_id=bond.bond_id,
                spike_id=f"p_{spike.spike_id}",
            ))
            result.propagated_spikes += 1

        result.mean_delay = sum(delays) / max(len(delays), 1)
        return result

    # ------------------------------------------------------------------
    # Periodic-informed STDP
    # ------------------------------------------------------------------

    def apply_stdp(
        self,
        pre_spikes: List[Any],
        post_spikes: List[Any],
        tick: int = 0,
    ) -> int:
        """Apply STDP updates using bond-specific plasticity from the periodic table.

        Uses spike timing to compute Δw = A+ * exp(-Δt/τ+) for LTP (pre before post)
        and Δw = A- * exp(Δt/τ-) for LTD (post before pre).

        The maximum weight change is bounded by bond.plasticity.
        Returns count of bonds updated.
        """
        updated = 0
        for pre in pre_spikes:
            for post in post_spikes:
                bond = self._find_bond(pre.source_z, post.source_z)
                if bond is None:
                    continue

                dt = post.timestamp - pre.timestamp
                if dt == 0:
                    continue

                max_change = bond.plasticity * 0.1
                if dt > 0:
                    delta = max_change * math.exp(-dt / 5.0)
                else:
                    delta = -max_change * math.exp(dt / 5.0)

                bond.bond_energy = max(0.0, min(1.0, bond.bond_energy + delta))
                updated += 1

        return updated

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def signal_delay(self, bond: SynapticBond) -> float:
        """Return signal delay for a bond (delegates to bond's own property)."""
        return bond.signal_delay()

    def _get_outgoing_bonds(self, source_z: int) -> List[SynapticBond]:
        return [
            b for b in self.bond_registry.bonds.values()
            if b.source_z == source_z and b.polarity != "backward"
        ]

    def _find_bond(self, source_z: int, target_z: int) -> Optional[SynapticBond]:
        for b in self.bond_registry.bonds.values():
            if b.source_z == source_z and b.target_z == target_z:
                return b
        return None
