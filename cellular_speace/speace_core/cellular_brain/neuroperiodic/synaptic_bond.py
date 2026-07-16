from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from speace_core.cellular_brain.neuroperiodic.neural_element import (
    NeuralElement,
    ValenceState,
    ElementBlock,
    ElementPeriod,
    ElementGroup,
)


class BondType(str, Enum):
    """Chemical bond type mapped to synaptic properties.

    COVALENT   — Strong, persistent, directional (myelinated axons,
                 high-trust synapses). Like a sigma bond.
    IONIC      — Voltage-dependent, conditional (NMDA receptors,
                 gateable connections). Strength varies with depolarization.
    HYDROGEN   — Weak, modulatory, easily broken (neuromodulatory
                 connections, dopamine/serotonin). Fast to form/unform.
    METALLIC   — Diffuse, non-directional (field effects, ephaptic
                 coupling, volume transmission). Delocalized influence.
    VAN_DER_WAALS — Very weak, transient (noise-level coupling,
                    resonance synchronization). Collective phenomenon.
    """
    COVALENT = "covalent"
    IONIC = "ionic"
    HYDROGEN = "hydrogen"
    METALLIC = "metallic"
    VAN_DER_WAALS = "van_der_waals"


class BondOrder(int, Enum):
    """Redundancy / multiplicity of the synaptic connection.

    SINGLE   — One axon terminal (standard synapse)
    DOUBLE   — Two parallel terminals (reinforced pathway)
    TRIPLE   — Three+ terminals (critical pathway, high reliability)
    """
    SINGLE = 1
    DOUBLE = 2
    TRIPLE = 3


class BondPolarity(str, Enum):
    """Directionality of signal flow across the bond."""
    UNIDIRECTIONAL_FORWARD = "forward"
    UNIDIRECTIONAL_BACKWARD = "backward"
    BIDIRECTIONAL = "bidirectional"
    RECURRENT = "recurrent"


class MolecularOrbital(BaseModel):
    """Combined activation state of a bonded pair (molecular orbital analogy).

    Bonding orbital   — in-phase activation (signal amplification)
    Antibonding       — out-of-phase activation (signal cancellation)
    Non-bonding       — independent activation (no interference)
    """
    bonding_strength: float = Field(default=0.0, ge=-1.0, le=1.0)
    phase_alignment: float = Field(default=0.0, ge=-1.0, le=1.0)
    resonance_frequency: float = Field(default=10.0, ge=0.0)

    def amplification_factor(self) -> float:
        return max(0.0, 1.0 + self.bonding_strength * self.phase_alignment)

    def cancellation_factor(self) -> float:
        return max(0.0, 1.0 - abs(self.bonding_strength) * abs(self.phase_alignment))


class SynapticBond(BaseModel):
    """A connection between two NeuralElements, modeled as a chemical bond.

    Each bond is characterized by:
      - Type: how the connection works (covalent, ionic, etc.)
      - Order: how redundant it is
      - Polarity: direction of information flow
      - Energy: metabolic cost of maintaining the bond
      - Length: physical/logical distance (short vs long-range)
      - Molecule: combined orbital state for signal processing
    """
    bond_id: str = ""
    source_z: int = Field(..., description="Atomic number of presynaptic element")
    target_z: int = Field(..., description="Atomic number of postsynaptic element")
    bond_type: BondType = BondType.COVALENT
    bond_order: BondOrder = BondOrder.SINGLE
    polarity: BondPolarity = BondPolarity.UNIDIRECTIONAL_FORWARD

    bond_energy: float = Field(default=0.5, ge=0.0, le=1.0,
                                description="Synaptic weight / strength")
    bond_length: float = Field(default=0.5, ge=0.0, le=1.0,
                                description="Distance (0=local, 1=long-range)")
    plasticity: float = Field(default=0.5, ge=0.0, le=1.0,
                               description="Ability to change (STDP rate)")
    decay_rate: float = Field(default=0.01, ge=0.0, le=1.0)

    molecule: MolecularOrbital = Field(default_factory=MolecularOrbital)

    metadata: Dict[str, Any] = Field(default_factory=dict)

    # ------------------------------------------------------------------
    # Bond chemistry properties
    # ------------------------------------------------------------------

    def bond_strength(self) -> float:
        """Effective strength of this bond (weight × order × amplification)."""
        return (self.bond_energy * self.bond_order.value
                * self.molecule.amplification_factor())

    def is_strong(self) -> bool:
        return self.bond_strength() > 0.7

    def is_weak(self) -> bool:
        return self.bond_strength() < 0.3

    def is_plastic(self) -> bool:
        return self.plasticity > 0.5

    def is_long_range(self) -> bool:
        return self.bond_length > 0.6

    def is_inhibitory(self) -> bool:
        return self.bond_energy < 0.0

    def signal_delay(self) -> float:
        delay = self.bond_length * 0.5
        if self.bond_type == BondType.COVALENT:
            delay *= 0.3
        elif self.bond_type == BondType.IONIC:
            delay *= 0.7
        elif self.bond_type == BondType.HYDROGEN:
            delay *= 1.5
        elif self.bond_type == BondType.METALLIC:
            delay *= 2.0
        return max(0.01, delay)

    def energy_cost(self) -> float:
        base = self.bond_energy * 0.1
        if self.bond_type == BondType.COVALENT:
            return base * 1.5
        if self.bond_type == BondType.IONIC:
            return base * 1.2
        if self.bond_type == BondType.HYDROGEN:
            return base * 0.5
        if self.bond_type == BondType.METALLIC:
            return base * 0.3
        return base


class BondFormationEngine(BaseModel):
    """Determines bond type and properties between two NeuralElements.

    Applies chemical-bond-style rules to determine how two neural
    elements connect based on their periodic properties.
    """

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def predict_bond_type(cls, source: NeuralElement,
                          target: NeuralElement) -> BondType:
        """Predict bond type from element properties.

        Rules:
          - Same block + opposite valence → COVALENT (strong, directional)
          - Excitatory→Inhibitory within same period → IONIC (conditional)
          - Modulatory element → HYDROGEN (weak, modulatory)
          - Same group + different period → METALLIC (diffuse influence)
          - Both noble/glial → VAN_DER_WAALS (very weak)
        """
        if source.block == target.block:
            if source.is_excitatory() and target.is_inhibitory():
                return BondType.COVALENT
            if source.is_inhibitory() and target.is_excitatory():
                return BondType.COVALENT
            if source.is_modulatory() or target.is_modulatory():
                return BondType.HYDROGEN

        if source.period == target.period:
            if source.is_excitatory() and target.is_inhibitory():
                return BondType.IONIC
            if source.is_inhibitory() and target.is_excitatory():
                return BondType.IONIC

        if source.group == target.group:
            return BondType.METALLIC

        if source.block == ElementBlock.G_BLOCK or target.block == ElementBlock.G_BLOCK:
            return BondType.VAN_DER_WAALS

        return BondType.COVALENT

    @classmethod
    def predict_bond_energy(cls, source: NeuralElement,
                            target: NeuralElement) -> float:
        """Predict bond energy (synaptic weight) from compatibility."""
        return source.compatibility_score(target)

    @classmethod
    def predict_bond_order(cls, source: NeuralElement,
                           target: NeuralElement) -> BondOrder:
        """Predict bond order from element properties.

        Higher order = more redundancy, for critical pathways.
        """
        compatibility = source.compatibility_score(target)
        if compatibility > 0.8:
            return BondOrder.TRIPLE
        if compatibility > 0.6:
            return BondOrder.DOUBLE
        return BondOrder.SINGLE

    @classmethod
    def predict_polarity(cls, source: NeuralElement,
                         target: NeuralElement) -> BondPolarity:
        """Predict signal directionality."""
        if source.period.value < target.period.value:
            return BondPolarity.UNIDIRECTIONAL_FORWARD
        if source.period.value > target.period.value:
            return BondPolarity.UNIDIRECTIONAL_BACKWARD
        if source.group == target.group:
            return BondPolarity.RECURRENT
        return BondPolarity.BIDIRECTIONAL

    @classmethod
    def predict_plasticity(cls, source: NeuralElement,
                           target: NeuralElement) -> float:
        """Predict plasticity from element properties.

        Higher in association areas, lower in sensory/motor.
        """
        p = source.period.value + target.period.value
        base = p / 14.0
        modulation = 0.0
        if ElementBlock.D_BLOCK in (source.block, target.block):
            modulation += 0.2
        if source.group == ElementGroup.ASSOCIATION_MEMORY:
            modulation += 0.15
        if target.group == ElementGroup.ASSOCIATION_MEMORY:
            modulation += 0.15
        return min(1.0, base + modulation)

    @classmethod
    def form_bond(cls, source: NeuralElement,
                  target: NeuralElement,
                  bond_id: str = "") -> SynapticBond:
        """Form a complete bond between two elements."""
        bond_type = cls.predict_bond_type(source, target)
        bond_energy = cls.predict_bond_energy(source, target)
        bond_order = cls.predict_bond_order(source, target)
        polarity = cls.predict_polarity(source, target)
        plasticity = cls.predict_plasticity(source, target)

        phase = 1.0 if polarity == BondPolarity.UNIDIRECTIONAL_FORWARD else -0.5
        orbital = MolecularOrbital(
            bonding_strength=bond_energy * 0.8,
            phase_alignment=phase,
            resonance_frequency=(source.mass + target.mass) * 50.0,
        )

        return SynapticBond(
            bond_id=bond_id,
            source_z=source.atomic_number,
            target_z=target.atomic_number,
            bond_type=bond_type,
            bond_order=bond_order,
            polarity=polarity,
            bond_energy=bond_energy,
            plasticity=plasticity,
            molecule=orbital,
        )


class BondRegistry(BaseModel):
    """Registry of all known bonds between elements."""
    bonds: Dict[str, SynapticBond] = Field(default_factory=dict)
    by_source: Dict[int, List[str]] = Field(default_factory=dict)
    by_target: Dict[int, List[str]] = Field(default_factory=dict)

    def register(self, bond: SynapticBond) -> None:
        bid = bond.bond_id or f"{bond.source_z}→{bond.target_z}"
        bond.bond_id = bid
        self.bonds[bid] = bond
        self.by_source.setdefault(bond.source_z, []).append(bid)
        self.by_target.setdefault(bond.target_z, []).append(bid)

    def get_outgoing(self, z: int) -> List[SynapticBond]:
        return [self.bonds[bid] for bid in self.by_source.get(z, [])]

    def get_incoming(self, z: int) -> List[SynapticBond]:
        return [self.bonds[bid] for bid in self.by_target.get(z, [])]

    def get_bond(self, source_z: int, target_z: int) -> Optional[SynapticBond]:
        for bid in self.by_source.get(source_z, []):
            b = self.bonds[bid]
            if b.target_z == target_z:
                return b
        return None
