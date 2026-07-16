"""Receptor Profile — biologically-inspired neurotransmitter receptor model.

Each neuron can express different receptor types with specific binding
affinities for each neuromodulator/neurotransmitter, implementing the
lock-and-key mechanism of synaptic transmission.
"""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ReceptorType(str, Enum):
    AMPA = "ampa"              # Glutamate, fast excitatory
    NMDA = "nmda"              # Glutamate, slow excitatory, plasticity
    GABA_A = "gaba_a"          # GABA, fast inhibitory (ionotropic)
    GABA_B = "gaba_b"          # GABA, slow inhibitory (metabotropic)
    D1 = "d1"                  # Dopamine D1, excitatory modulation
    D2 = "d2"                  # Dopamine D2, inhibitory modulation
    M1 = "m1"                  # Acetylcholine M1 (muscarinic), excitatory
    M2 = "m2"                  # Acetylcholine M2 (muscarinic), inhibitory
    NICOTINIC = "nicotinic"    # Acetylcholine, fast excitatory
    ALPHA_1 = "alpha_1"        # Noradrenaline alpha-1, excitatory
    ALPHA_2 = "alpha_2"        # Noradrenaline alpha-2, inhibitory
    BETA = "beta"              # Noradrenaline beta, excitatory
    HT_1A = "ht_1a"           # Serotonin 5-HT1A, inhibitory
    HT_2A = "ht_2a"           # Serotonin 5-HT2A, excitatory
    HT_3 = "ht_3"             # Serotonin 5-HT3, excitatory (ionotropic)


class BindingAffinity(BaseModel):
    receptor_type: ReceptorType
    affinity: float = Field(default=0.5, ge=0.0, le=1.0)
    efficacy: float = Field(default=0.5, ge=0.0, le=1.0)


class ReceptorProfile(BaseModel):
    """Receptor expression profile for a single neuron.

    Defines which receptor types are expressed and with what
    binding affinity and efficacy.
    """
    neuron_id: str = ""
    expressed_receptors: Dict[ReceptorType, BindingAffinity] = Field(default_factory=dict)

    def has_receptor(self, receptor_type: ReceptorType) -> bool:
        return receptor_type in self.expressed_receptors

    def get_affinity(self, receptor_type: ReceptorType) -> float:
        if receptor_type in self.expressed_receptors:
            return self.expressed_receptors[receptor_type].affinity
        return 0.0

    def get_efficacy(self, receptor_type: ReceptorType) -> float:
        if receptor_type in self.expressed_receptors:
            return self.expressed_receptors[receptor_type].efficacy
        return 0.0

    def bind(self, receptor_type: ReceptorType, neurotransmitter_level: float) -> float:
        """Compute the postsynaptic effect of neurotransmitter binding.

        Returns a modulation value based on:
        - neurotransmitter concentration
        - receptor binding affinity
        - receptor efficacy
        """
        if receptor_type not in self.expressed_receptors:
            return 0.0
        ba = self.expressed_receptors[receptor_type]
        occupancy = neurotransmitter_level * ba.affinity
        return occupancy * ba.efficacy

    def add_receptor(
        self,
        receptor_type: ReceptorType,
        affinity: float = 0.5,
        efficacy: float = 0.5,
    ) -> None:
        self.expressed_receptors[receptor_type] = BindingAffinity(
            receptor_type=receptor_type,
            affinity=affinity,
            efficacy=efficacy,
        )

    def remove_receptor(self, receptor_type: ReceptorType) -> None:
        self.expressed_receptors.pop(receptor_type, None)

    def list_receptors(self) -> List[ReceptorType]:
        return list(self.expressed_receptors.keys())

    # ------------------------------------------------------------------
    # Periodic table integration
    # ------------------------------------------------------------------

    def classify_block(self) -> str:
        """Classify this receptor profile into a neurotransmitter block.

        Returns: 's' (GABA/glycine), 'p' (glutamate), 'd' (monoamines),
                 'f' (neuropeptides), or 'mixed'.
        """
        has_gaba = any(self.has_receptor(r) for r in (ReceptorType.GABA_A, ReceptorType.GABA_B))
        has_glutamate = any(self.has_receptor(r) for r in (ReceptorType.AMPA, ReceptorType.NMDA))
        has_monoamine = any(
            self.has_receptor(r) for r in (
                ReceptorType.D1, ReceptorType.D2, ReceptorType.HT_1A,
                ReceptorType.HT_2A, ReceptorType.HT_3, ReceptorType.ALPHA_1,
                ReceptorType.ALPHA_2, ReceptorType.BETA, ReceptorType.M1,
                ReceptorType.M2, ReceptorType.NICOTINIC,
            )
        )

        gaba_affinity = self.get_affinity(ReceptorType.GABA_A) + self.get_affinity(ReceptorType.GABA_B)
        glut_affinity = self.get_affinity(ReceptorType.AMPA) + self.get_affinity(ReceptorType.NMDA)

        if has_gaba and not has_glutamate:
            if gaba_affinity >= 1.0:
                return "s"
            if has_monoamine:
                return "d"
            return "s"
        if has_glutamate and not has_gaba:
            if not has_monoamine:
                return "p"
            return "d" if glut_affinity < 1.0 else "p"
        if has_gaba and has_glutamate:
            if has_monoamine:
                return "d"
            return "mixed"
        if has_monoamine:
            return "d"
        return "p"

    def valence_electrons(self) -> int:
        """Number of expressed receptor types (analogous to valence electrons)."""
        return len(self.expressed_receptors)

    def receptor_formula(self) -> str:
        """Compact string representation of receptor expression."""
        parts = []
        for rt, ba in sorted(self.expressed_receptors.items(),
                             key=lambda x: x[1].affinity, reverse=True):
            parts.append(f"{rt.value}({ba.affinity:.1f})")
        return " + ".join(parts) if parts else "none"


# Default receptor profiles for common cell types

def default_excitatory_neuron_profile(neuron_id: str = "") -> ReceptorProfile:
    return ReceptorProfile(
        neuron_id=neuron_id,
        expressed_receptors={
            ReceptorType.AMPA: BindingAffinity(
                receptor_type=ReceptorType.AMPA, affinity=0.8, efficacy=0.9
            ),
            ReceptorType.NMDA: BindingAffinity(
                receptor_type=ReceptorType.NMDA, affinity=0.6, efficacy=0.7
            ),
            ReceptorType.HT_2A: BindingAffinity(
                receptor_type=ReceptorType.HT_2A, affinity=0.3, efficacy=0.4
            ),
            ReceptorType.BETA: BindingAffinity(
                receptor_type=ReceptorType.BETA, affinity=0.4, efficacy=0.5
            ),
        },
    )


def default_inhibitory_neuron_profile(neuron_id: str = "") -> ReceptorProfile:
    return ReceptorProfile(
        neuron_id=neuron_id,
        expressed_receptors={
            ReceptorType.GABA_A: BindingAffinity(
                receptor_type=ReceptorType.GABA_A, affinity=0.9, efficacy=0.9
            ),
            ReceptorType.GABA_B: BindingAffinity(
                receptor_type=ReceptorType.GABA_B, affinity=0.5, efficacy=0.6
            ),
            ReceptorType.HT_1A: BindingAffinity(
                receptor_type=ReceptorType.HT_1A, affinity=0.5, efficacy=0.5
            ),
            ReceptorType.M2: BindingAffinity(
                receptor_type=ReceptorType.M2, affinity=0.4, efficacy=0.4
            ),
        },
    )


def default_dopaminergic_neuron_profile(neuron_id: str = "") -> ReceptorProfile:
    return ReceptorProfile(
        neuron_id=neuron_id,
        expressed_receptors={
            ReceptorType.D1: BindingAffinity(
                receptor_type=ReceptorType.D1, affinity=0.8, efficacy=0.8
            ),
            ReceptorType.D2: BindingAffinity(
                receptor_type=ReceptorType.D2, affinity=0.6, efficacy=0.5
            ),
            ReceptorType.NMDA: BindingAffinity(
                receptor_type=ReceptorType.NMDA, affinity=0.5, efficacy=0.6
            ),
            ReceptorType.HT_2A: BindingAffinity(
                receptor_type=ReceptorType.HT_2A, affinity=0.4, efficacy=0.3
            ),
        },
    )


def default_sensory_neuron_profile(neuron_id: str = "") -> ReceptorProfile:
    return ReceptorProfile(
        neuron_id=neuron_id,
        expressed_receptors={
            ReceptorType.AMPA: BindingAffinity(
                receptor_type=ReceptorType.AMPA, affinity=0.9, efficacy=0.95
            ),
            ReceptorType.NMDA: BindingAffinity(
                receptor_type=ReceptorType.NMDA, affinity=0.4, efficacy=0.5
            ),
            ReceptorType.ALPHA_1: BindingAffinity(
                receptor_type=ReceptorType.ALPHA_1, affinity=0.5, efficacy=0.5
            ),
            ReceptorType.NICOTINIC: BindingAffinity(
                receptor_type=ReceptorType.NICOTINIC, affinity=0.6, efficacy=0.6
            ),
        },
    )
