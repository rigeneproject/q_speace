"""NeuroPeriodicIntegrator — bridges the Neural Periodic Table with SPEACE.

Maps SPEACE DigitalNeurons, DigitalSynapses, ReceptorProfiles, and
BrainRegions to their corresponding NeuralElements, SynapticBonds, and
PeriodicLaws. Provides query and transformation methods between the
existing discrete-cell model and the periodic abstraction.
"""
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from speace_core.cellular_brain.base.receptor_profile import (
    ReceptorProfile,
    ReceptorType,
)
from speace_core.cellular_brain.neuroperiodic.neural_element import (
    CATALOG,
    ElementBlock,
    ElementGroup,
    ElementPeriod,
    NeuralElement,
    ValenceState,
    build_element,
    get_element_by_cell_type,
)
from speace_core.cellular_brain.neuroperiodic.neural_periodic_table import (
    NeuralPeriodicTable,
    PeriodicTableBuilder,
)
from speace_core.cellular_brain.neuroperiodic.periodic_law import PeriodicLaw
from speace_core.cellular_brain.neuroperiodic.synaptic_bond import (
    BondFormationEngine,
    BondRegistry,
    BondType,
    SynapticBond,
)


class NeuroPeriodicIntegrator(BaseModel):
    """Integrates the Neural Periodic Table into SPEACE's neural architecture.

    Provides:
      - Lookup: cell_type → NeuralElement → periodic properties
      - Prediction: element pair → bond properties → synapse parameters
      - Classification: receptor_profile → orbital_config → element block
      - Analysis: brain_region → group/period mapping
      - Guidance: differentiation rules enhanced with periodic table
    """
    table: NeuralPeriodicTable = Field(default_factory=PeriodicTableBuilder.build_default)
    laws: PeriodicLaw = Field(default_factory=PeriodicLaw.build_default)
    bond_registry: BondRegistry = Field(default_factory=BondRegistry)

    class Config:
        arbitrary_types_allowed = True

    # Runtime dynamics (T171)
    membrane_dynamics: Any = None
    propagation_engine: Any = None

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_genome(cls, genome: Any) -> "NeuroPeriodicIntegrator":
        """Build an integrator whose periodic laws are driven by Digital DNA."""
        return cls(
            table=PeriodicTableBuilder.build_default(),
            laws=PeriodicLaw.from_genome(genome),
            bond_registry=BondRegistry(),
        )

    # ------------------------------------------------------------------
    # Runtime dynamics (T171)
    # ------------------------------------------------------------------

    def enable_runtime_dynamics(self) -> None:
        """Enable spike propagation and membrane dynamics.

        Called once during orchestrator init when the genome flag
        neuroperiodic.enable_runtime_dynamics is True.
        """
        from speace_core.cellular_brain.neuroperiodic.membrane_dynamics import (
            MembraneDynamics,
        )
        from speace_core.cellular_brain.neuroperiodic.propagation_engine import (
            PropagationEngine,
        )

        self.membrane_dynamics = MembraneDynamics()
        self.propagation_engine = PropagationEngine(
            table=self.table,
            bond_registry=self.bond_registry,
        )

    def tick(
        self,
        circuit: Any,
        tick: int = 0,
        dt: float = 1.0,
        fired_neuron_ids: list | None = None,
    ) -> dict:
        """Run one tick of periodic-informed spike propagation.

        Pipeline per tick:
        1. Convert fired neurons to SpikeEvents (using element lookup)
        2. Propagate events through bonds (delay, attenuation, amplification)
        3. Update bond states (short-term depression)
        4. Return propagation summary

        Parameters
        ----------
        circuit : NeuralCircuit
            The active neural circuit.
        tick : int
            Current tick number.
        dt : float
            Time step.
        fired_neuron_ids : list[str] | None
            Neuron IDs that fired this tick (from burst engine).

        Returns
        -------
        dict
            Propagation summary with counters.
        """
        from speace_core.cellular_brain.neuroperiodic.spike_event import SpikeEvent

        if self.membrane_dynamics is None:
            return {"error": "Runtime dynamics not enabled. Call enable_runtime_dynamics() first."}

        # 1. Convert fired neurons to SpikeEvents
        spikes: list[SpikeEvent] = []
        if fired_neuron_ids:
            for nid in fired_neuron_ids:
                element = self._guess_element_from_neuron_id(nid)
                if element is None:
                    continue
                state = self.membrane_dynamics.get_state(nid)
                spikes.append(SpikeEvent(
                    source_z=element.atomic_number,
                    target_z=None,
                    timestamp=tick,
                    phase=(tick * 0.1) % (2.0 * 3.14159),
                    inter_spike_interval=max(1, tick - state.last_spike_tick),
                    strength=1.0,
                ))

        # 2. Propagate through bonds
        result = self.propagation_engine.propagate(spikes, circuit, tick)

        # 3. Apply STDP
        if result.propagated_spikes > 0:
            updated = self.propagation_engine.apply_stdp(spikes, spikes, tick)
            result.bonds_updated = updated

        return {
            "spikes_created": len(spikes),
            "propagated": result.propagated_spikes,
            "attenuated": result.attenuated_spikes,
            "dropped": result.dropped_spikes,
            "bonds_updated": result.bonds_updated,
            "mean_delay": result.mean_delay,
        }

    def _guess_element_from_neuron_id(self, neuron_id: str) -> NeuralElement | None:
        """Try to extract element info from a neuron ID."""
        for element in self.table.elements.values():
            for ct in element.cell_types:
                if ct.lower() in neuron_id.lower():
                    return element
        return None

    # ------------------------------------------------------------------
    # Element lookup
    # ------------------------------------------------------------------

    def get_element(self, cell_type: str) -> Optional[NeuralElement]:
        return self.table.get_by_cell_type(cell_type)

    def get_element_by_symbol(self, symbol: str) -> Optional[NeuralElement]:
        return self.table.get_by_symbol(symbol)

    def get_element_by_z(self, z: int) -> Optional[NeuralElement]:
        return self.table.get_by_z(z)

    def classify_cell_type(self, cell_type: str) -> Dict[str, Any]:
        """Full periodic classification of a cell type."""
        element = self.get_element(cell_type)
        if element is None:
            return {"cell_type": cell_type, "classified": False}
        return {
            "cell_type": cell_type,
            "classified": True,
            "symbol": element.symbol,
            "element": element.symbol,
            "atomic_number": element.atomic_number,
            "period": element.period.value,
            "period_name": element.period.name,
            "group": element.group.value,
            "group_name": element.group.name,
            "block": element.block.value,
            "block_name": element.block.name,
            "valence": element.valence.value,
            "electronegativity": element.electronegativity,
            "ionization_energy": element.ionization_energy,
            "atomic_radius": element.atomic_radius,
            "mass": element.mass,
            "orbitals": element.orbital_config.to_notation(),
        }

    # ------------------------------------------------------------------
    # Receptor profile ↔ orbital configuration
    # ------------------------------------------------------------------

    def receptor_to_block(self, profile: ReceptorProfile) -> ElementBlock:
        """Classify a receptor profile into a neurotransmitter block."""
        has_gaba = any(
            profile.has_receptor(r) for r in (ReceptorType.GABA_A, ReceptorType.GABA_B)
        )
        has_glutamate = any(
            profile.has_receptor(r) for r in (ReceptorType.AMPA, ReceptorType.NMDA)
        )
        has_monoamine = any(
            profile.has_receptor(r) for r in (
                ReceptorType.D1, ReceptorType.D2,
                ReceptorType.HT_1A, ReceptorType.HT_2A, ReceptorType.HT_3,
                ReceptorType.ALPHA_1, ReceptorType.ALPHA_2, ReceptorType.BETA,
                ReceptorType.M1, ReceptorType.M2,
            )
        )
        has_neuropeptide = any(
            profile.has_receptor(r) for r in (ReceptorType.NICOTINIC,)
        )

        if has_gaba and not has_glutamate:
            return ElementBlock.S_BLOCK
        if has_glutamate and not has_gaba:
            return ElementBlock.P_BLOCK
        if has_monoamine and not (has_gaba or has_glutamate):
            return ElementBlock.D_BLOCK
        if has_glutamate and has_gaba:
            return ElementBlock.D_BLOCK if has_monoamine else ElementBlock.P_BLOCK
        return ElementBlock.P_BLOCK

    def receptor_to_orbital_config(self, profile: ReceptorProfile) -> Dict[str, Dict[str, float]]:
        """Map receptor expression to orbital configuration notation."""
        config = {"s_shell": {}, "p_shell": {}, "d_shell": {}, "f_shell": {}}
        for rt, ba in profile.expressed_receptors.items():
            if rt in (ReceptorType.GABA_A, ReceptorType.GABA_B):
                config["s_shell"][rt.value] = ba.affinity
            elif rt in (ReceptorType.AMPA, ReceptorType.NMDA):
                config["p_shell"][rt.value] = ba.affinity
            elif rt in (ReceptorType.D1, ReceptorType.D2,
                        ReceptorType.HT_1A, ReceptorType.HT_2A, ReceptorType.HT_3,
                        ReceptorType.ALPHA_1, ReceptorType.ALPHA_2, ReceptorType.BETA,
                        ReceptorType.M1, ReceptorType.M2):
                config["d_shell"][rt.value] = ba.affinity
            else:
                config["f_shell"][rt.value] = ba.affinity
        return config

    # ------------------------------------------------------------------
    # Synapse prediction
    # ------------------------------------------------------------------

    def predict_synapse_by_elements(self, src: NeuralElement,
                                    tgt: NeuralElement) -> Dict[str, Any]:
        """Predict synapse properties between two NeuralElements."""
        bond = BondFormationEngine.form_bond(src, tgt)
        bond = self.laws.apply_bond_rules(src, tgt, bond)
        self.bond_registry.register(bond)

        def _val(v):
            return v.value if hasattr(v, 'value') else v
        return {
            "source": src.symbol,
            "target": tgt.symbol,
            "bond_type": _val(bond.bond_type),
            "bond_order": _val(bond.bond_order),
            "polarity": _val(bond.polarity),
            "strength": bond.bond_strength(),
            "plasticity": bond.plasticity,
            "energy_cost": bond.energy_cost(),
            "signal_delay": bond.signal_delay(),
            "amplification": bond.molecule.amplification_factor(),
            "compatibility": src.compatibility_score(tgt),
            "applicable_rules": [r.name for r in self.laws.get_applicable_rules(src, tgt)],
        }

    def predict_synapse(self, source_cell_type: str,
                        target_cell_type: str) -> Dict[str, Any]:
        """Predict synapse properties between two cell types."""
        src = self.get_element(source_cell_type)
        tgt = self.get_element(target_cell_type)
        if src is None or tgt is None:
            return {"error": "Unknown cell type"}

        bond = BondFormationEngine.form_bond(src, tgt)
        bond = self.laws.apply_bond_rules(src, tgt, bond)
        self.bond_registry.register(bond)

        def _val(v):
            return v.value if hasattr(v, 'value') else v
        return {
            "source": src.symbol,
            "target": tgt.symbol,
            "bond_type": _val(bond.bond_type),
            "bond_order": _val(bond.bond_order),
            "polarity": _val(bond.polarity),
            "strength": bond.bond_strength(),
            "plasticity": bond.plasticity,
            "energy_cost": bond.energy_cost(),
            "signal_delay": bond.signal_delay(),
            "amplification": bond.molecule.amplification_factor(),
            "compatibility": src.compatibility_score(tgt),
            "applicable_rules": [r.name for r in self.laws.get_applicable_rules(src, tgt)],
        }

    def predict_circuit_properties(self, cell_types: List[str]) -> Dict[str, Any]:
        """Predict collective properties of a circuit from its element composition."""
        elements = []
        for ct in cell_types:
            el = self.get_element(ct)
            if el:
                elements.append(el)

        if not elements:
            return {"error": "No known elements"}

        weights = [1.0 for _ in elements]
        avg_mass = sum(e.mass * w for e, w in zip(elements, weights)) / sum(weights)
        avg_energy = sum(e.ionization_energy * w for e, w in zip(elements, weights)) / sum(weights)
        avg_radius = sum(e.atomic_radius * w for e, w in zip(elements, weights)) / sum(weights)

        blocks = set(e.block for e in elements)
        periods = sorted(set(e.period.value for e in elements))
        depth = max(periods) - min(periods) + 1 if periods else 0

        pairs = 0
        reactions = 0
        for i in range(len(elements)):
            for j in range(len(elements)):
                if i != j:
                    pairs += 1
                    pred = self.table.predict_connection(elements[i], elements[j])
                    if pred["compatibility"] > 0.4:
                        rx = self.laws.get_applicable_reactions(
                            [elements[i], elements[j]]
                        )
                        reactions += len(rx)

        return {
            "element_count": len(elements),
            "avg_metabolic_cost": avg_mass,
            "avg_activation_threshold": avg_energy,
            "avg_receptive_field": avg_radius,
            "block_diversity": len(blocks),
            "blocks": [b.value for b in blocks],
            "hierarchical_depth": depth,
            "periods": periods,
            "possible_pairs": pairs,
            "possible_reactions": reactions,
            "connectivity_potential": pairs * avg_radius,
        }

    # ------------------------------------------------------------------
    # Cell differentiation guidance
    # ------------------------------------------------------------------

    def suggest_differentiation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest cell differentiation using periodic table rules.

        Considers:
          - Region → group mapping
          - Energy → mass / ionization constraints
          - Existing cell type → element mapping
        """
        region = (context.get("region") or "").lower()
        energy = context.get("energy", 1.0)
        activation = context.get("activation", 0.0)
        fires = context.get("consecutive_fires", 0)
        role = context.get("role", "excitatory")

        period_map = {
            "sensory": ElementPeriod.SENSORY_TRANSDUCTION,
            "visual": ElementPeriod.SENSORY_TRANSDUCTION,
            "auditory": ElementPeriod.SENSORY_TRANSDUCTION,
            "hippocampus": ElementPeriod.INTEGRATION,
            "entorhinal": ElementPeriod.INTEGRATION,
            "prefrontal": ElementPeriod.EXECUTIVE,
            "pfc": ElementPeriod.EXECUTIVE,
            "limbic": ElementPeriod.EXECUTIVE,
            "motor": ElementPeriod.MOTOR_COORDINATION,
            "cerebellar": ElementPeriod.MOTOR_COORDINATION,
            "brainstem": ElementPeriod.OUTPUT_HOMEOSTASIS,
            "default_mode": ElementPeriod.EXECUTIVE,
            "language": ElementPeriod.ASSOCIATION,
            "wernicke": ElementPeriod.ASSOCIATION,
            "broca": ElementPeriod.ASSOCIATION,
        }

        group_map = {
            "sensory": ElementGroup.SENSORY_VISUAL,
            "visual": ElementGroup.SENSORY_VISUAL,
            "auditory": ElementGroup.SENSORY_AUDITORY,
            "hippocampus": ElementGroup.ASSOCIATION_MEMORY,
            "prefrontal": ElementGroup.EXECUTIVE_PFC,
            "limbic": ElementGroup.EXECUTIVE_LIMBIC,
            "motor": ElementGroup.EXECUTIVE_MOTOR,
            "cerebellar": ElementGroup.REGULATORY_CEREBELLAR,
            "brainstem": ElementGroup.REGULATORY_BRAINSTEM,
            "default_mode": ElementGroup.EXECUTIVE_DMN,
            "language": ElementGroup.ASSOCIATION_LANGUAGE,
        }

        suggested_period = period_map.get(region, ElementPeriod.ASSOCIATION)
        suggested_group = group_map.get(region, ElementGroup.NOBLE_BACKGROUND)

        # Find elements matching this position
        matches = [
            e for e in self.table.elements.values()
            if e.period == suggested_period and e.group == suggested_group
        ]

        if not matches:
            return {
                "context": context,
                "classified": False,
                "suggested_elements": [],
                "reason": "No element found for this region/period/group",
            }

        return {
            "context": context,
            "classified": True,
            "suggested_period": suggested_period.name,
            "suggested_group": suggested_group.name,
            "suggested_elements": [
                {
                    "symbol": e.symbol,
                    "name": e.name,
                    "z": e.atomic_number,
                    "cell_types": e.cell_types,
                }
                for e in matches
            ],
            "primary_suggestion": matches[0].symbol,
            "reason": f"Region '{region}' maps to period {suggested_period.value}, group {suggested_group.value}",
        }

    # ------------------------------------------------------------------
    # Analysis & reporting
    # ------------------------------------------------------------------

    def analyze_region(self, region_id: str,
                       cell_types_in_region: List[str]) -> Dict[str, Any]:
        """Analyze a brain region through the periodic table lens."""
        elements = []
        for ct in cell_types_in_region:
            el = self.get_element(ct)
            if el:
                elements.append(el)

        if not elements:
            return {"region": region_id, "elements": []}

        groups = set(e.group for e in elements)
        periods = set(e.period for e in elements)
        blocks = set(e.block for e in elements)

        internal_bonds = []
        for i in range(len(elements)):
            for j in range(i + 1, len(elements)):
                pred = self.table.predict_connection(elements[i], elements[j])
                internal_bonds.append({
                    "source": elements[i].symbol,
                    "target": elements[j].symbol,
                    "compatibility": pred["compatibility"],
                    "strength": pred["strength"],
                })

        return {
            "region": region_id,
            "element_count": len(elements),
            "elements": [e.symbol for e in elements],
            "groups": [g.name for g in groups],
            "periods": sorted(set(p.value for p in periods)),
            "blocks": [b.name for b in blocks],
            "internal_bonds": internal_bonds,
            "bond_density": len(internal_bonds) / (len(elements) ** 2 + 1),
            "hierarchical_span": max(p.value for p in periods) - min(p.value for p in periods) + 1 if periods else 0,
        }

    def compare_elements(self, symbol_a: str, symbol_b: str) -> Dict[str, Any]:
        """Compare two elements side by side."""
        a = self.table.get_by_symbol(symbol_a)
        b = self.table.get_by_symbol(symbol_b)
        if not a or not b:
            return {"error": "Element not found"}
        return {
            "element_a": a.to_dict(),
            "element_b": b.to_dict(),
            "similarity_score": self._element_similarity(a, b),
            "compatibility": a.compatibility_score(b),
            "reciprocal": b.compatibility_score(a),
            "predicted_bond": BondFormationEngine.form_bond(a, b).to_dict() if hasattr(BondFormationEngine.form_bond(a, b), 'to_dict') else {
                "type": BondFormationEngine.predict_bond_type(a, b).value,
                "energy": BondFormationEngine.predict_bond_energy(a, b),
                "order": BondFormationEngine.predict_bond_order(a, b).value,
            },
            "applicable_laws": [r.name for r in self.laws.get_applicable_rules(a, b)],
            "reactions": [r.name for r in self.laws.get_applicable_reactions([a, b])],
        }

    def _element_similarity(self, a: NeuralElement, b: NeuralElement) -> float:
        scores = [
            1.0 - abs(a.electronegativity - b.electronegativity),
            1.0 - abs(a.ionization_energy - b.ionization_energy),
            1.0 - abs(a.atomic_radius - b.atomic_radius),
            1.0 - abs(a.mass - b.mass),
            0.5 if a.period == b.period else 0.0,
            0.5 if a.group == b.group else 0.0,
            0.3 if a.block == b.block else 0.0,
        ]
        return sum(scores) / len(scores)

    def get_missing_elements(self) -> List[Tuple[int, int, str]]:
        """Report empty positions in the table (potential new discoveries)."""
        missing = []
        filled = {(e.period, e.group) for e in self.table.elements.values()}
        for p in ElementPeriod:
            for g in ElementGroup:
                if (p, g) not in filled:
                    missing.append((p.value, g.value, f"Period {p.value}, Group {g.value}"))
        return missing
