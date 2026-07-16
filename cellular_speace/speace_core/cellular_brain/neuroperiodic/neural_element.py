from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ElementBlock(str, Enum):
    """Neurotransmitter system block (analogous to s/p/d/f blocks).

    Each block corresponds to a family of neurotransmitters with
    similar signalling properties:
      S_BLOCK  — fast ionotropic (GABA, Glycine)
      P_BLOCK  — slow ionotropic/metabotropic (Glutamate)
      D_BLOCK  — modulatory monoamines (Dopamine, Serotonin, NA, ACh)
      F_BLOCK  — slow neuromodulatory peptides (Neuropeptides, Hormones)
    """
    S_BLOCK = "s"     # GABA, Glycine — fast inhibition
    P_BLOCK = "p"     # Glutamate — excitation
    D_BLOCK = "d"     # Monoamines — modulation
    F_BLOCK = "f"     # Neuropeptides — slow neuromodulation
    G_BLOCK = "g"     # Glial — support (astrocytes, microglia, oligodendrocytes)


class ElementGroup(int, Enum):
    """Functional family groups (IUPAC-like, 1-18).

    Each group collects neuron types with similar functional valence:
      G01-G04: Sensory input      G05-G08: Association
      G09-G12: Executive/Control  G13-G16: Regulation
      G17-G18: Special/Inert
    """
    SENSORY_VISUAL = 1
    SENSORY_AUDITORY = 2
    SENSORY_SOMATOSENSORY = 3
    SENSORY_CHEMICAL = 4
    ASSOCIATION_LANGUAGE = 5
    ASSOCIATION_MEMORY = 6
    ASSOCIATION_SPATIAL = 7
    ASSOCIATION_SEMANTIC = 8
    EXECUTIVE_PFC = 9
    EXECUTIVE_LIMBIC = 10
    EXECUTIVE_DMN = 11
    EXECUTIVE_MOTOR = 12
    REGULATORY_CEREBELLAR = 13
    REGULATORY_BRAINSTEM = 14
    REGULATORY_INHIBITORY = 15
    REGULATORY_MODULATORY = 16
    GLIAL_SUPPORT = 17
    NOBLE_BACKGROUND = 18


class ElementPeriod(int, Enum):
    """Hierarchical depth level (1-7, like electron shells).

    Higher period = deeper processing / closer to output:
      P1: Sensory transduction
      P2: Feature extraction
      P3: Association & pattern recognition
      P4: Memory binding & integration
      P5: Executive planning
      P6: Motor coordination
      P7: Motor output & homeostasis
    """
    SENSORY_TRANSDUCTION = 1
    FEATURE_EXTRACTION = 2
    ASSOCIATION = 3
    INTEGRATION = 4
    EXECUTIVE = 5
    MOTOR_COORDINATION = 6
    OUTPUT_HOMEOSTASIS = 7


class ValenceState(str, Enum):
    """Excitation/inhibition balance of the element."""
    STRONG_EXCITATORY = "+2"
    EXCITATORY = "+1"
    NEUTRAL = "0"
    INHIBITORY = "-1"
    STRONG_INHIBITORY = "-2"
    MODULATORY = "±"


class OrbitalConfiguration(BaseModel):
    """Receptor expression as electron orbital configuration.

    Each orbital = a receptor type shell that can hold electrons (receptors).
    Written as a spectroscopic notation string, e.g. "1s²2s²2p⁶"
    """
    s_shell: Dict[str, float] = Field(default_factory=dict)
    p_shell: Dict[str, float] = Field(default_factory=dict)
    d_shell: Dict[str, float] = Field(default_factory=dict)
    f_shell: Dict[str, float] = Field(default_factory=dict)

    def to_notation(self) -> str:
        parts = []
        for shell, items in [("s", self.s_shell), ("p", self.p_shell),
                             ("d", self.d_shell), ("f", self.f_shell)]:
            if items:
                n = sum(1 for _ in items)
                parts.append(f"{shell}{n}")
        return " ".join(parts) if parts else "empty"

    def valence_electrons(self) -> int:
        return len(self.s_shell) + len(self.p_shell)

    def receptor_diversity(self) -> int:
        return sum(len(s) for s in [self.s_shell, self.p_shell, self.d_shell, self.f_shell])


class NeuralElement(BaseModel):
    """Fundamental unit of the Neural Periodic Table.

    Each NeuralElement represents a *type* of neuron or glial cell,
    classified by its fundamental computational properties — analogous
    to a chemical element in the periodic table.
    """
    atomic_number: int = Field(..., ge=1, le=200, description="Functional identity number")
    symbol: str = Field(..., min_length=1, max_length=6, pattern=r"^[A-Z][a-z]?[a-z]?$")
    name: str = Field(..., description="Full element name (e.g. 'Pyramidal')")
    period: ElementPeriod = Field(..., description="Hierarchical depth level")
    group: ElementGroup = Field(..., description="Functional family group")
    block: ElementBlock = Field(..., description="Neurotransmitter system block")
    valence: ValenceState = Field(..., description="Excitation/inhibition balance")

    electronegativity: float = Field(..., ge=0.0, le=1.0,
                                     description="Inhibition tendency (0=pure excitation, 1=pure inhibition)")
    ionization_energy: float = Field(..., ge=0.0, le=1.0,
                                     description="Activation threshold (0=easy, 1=hard)")
    atomic_radius: float = Field(..., ge=0.0, le=1.0,
                                 description="Receptive field size (0=narrow, 1=wide)")
    mass: float = Field(..., ge=0.0, le=1.0,
                        description="Metabolic cost (0=cheap, 1=expensive)")

    orbital_config: OrbitalConfiguration = Field(
        default_factory=OrbitalConfiguration,
        description="Receptor expression as electron configuration",
    )

    affinity_strengths: Dict[str, float] = Field(
        default_factory=dict,
        description="Binding affinities to other elements/groups",
    )

    cell_types: List[str] = Field(
        default_factory=list,
        description="SPEACE cell type names that map to this element",
    )

    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # T-COR — Cognitive Objective Reduction capacity
    cor_capacity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Capacity to host competing latent cognitive microstates (0=single state, 1=high superposition capacity)",
    )

    # ------------------------------------------------------------------
    # Periodic properties (computed)
    # ------------------------------------------------------------------

    def group_trend_value(self) -> float:
        """Normalized group position for trend calculations (0..1)."""
        return (self.group.value - 1) / 17.0

    def period_trend_value(self) -> float:
        """Normalized period position for trend calculations (0..1)."""
        return (self.period.value - 1) / 6.0

    def is_excitatory(self) -> bool:
        return self.valence in (ValenceState.EXCITATORY, ValenceState.STRONG_EXCITATORY)

    def is_inhibitory(self) -> bool:
        return self.valence in (ValenceState.INHIBITORY, ValenceState.STRONG_INHIBITORY)

    def is_modulatory(self) -> bool:
        return self.valence == ValenceState.MODULATORY

    def compatibility_score(self, other: "NeuralElement") -> float:
        """How likely this element forms functional connections with another.

        Based on complementary valence and group affinity.
        Higher score = more likely to connect productively.
        """
        if self.atomic_number == other.atomic_number:
            return 0.3

        valence_score = 0.0
        if self.is_excitatory() and other.is_inhibitory():
            valence_score = 0.9
        elif self.is_inhibitory() and other.is_excitatory():
            valence_score = 0.9
        elif self.is_modulatory() and not other.is_modulatory():
            valence_score = 0.7
        elif self.is_excitatory() and other.is_excitatory():
            valence_score = 0.4
        elif self.is_inhibitory() and other.is_inhibitory():
            valence_score = 0.2
        else:
            valence_score = 0.5

        affinity = self.affinity_strengths.get(other.symbol, 0.5)
        other_affinity = other.affinity_strengths.get(self.symbol, 0.5)
        affinity_score = (affinity + other_affinity) / 2.0

        period_diff = abs(self.period.value - other.period.value)
        hierarchy_score = 1.0 / (1.0 + period_diff)

        return (valence_score * 0.5 + affinity_score * 0.3 + hierarchy_score * 0.2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "z": self.atomic_number,
            "symbol": self.symbol,
            "name": self.name,
            "period": self.period.value,
            "group": self.group.value,
            "block": self.block.value,
            "valence": self.valence.value,
            "electronegativity": self.electronegativity,
            "ionization_energy": self.ionization_energy,
            "atomic_radius": self.atomic_radius,
            "mass": self.mass,
            "orbitals": self.orbital_config.to_notation(),
        }


# ------------------------------------------------------------------
# Pre-defined element catalog
# ------------------------------------------------------------------

CATALOG: Dict[int, Dict[str, Any]] = {
    # ═══════════════════════════════════════════════════════════════
    # PERIOD 1 — Sensory transduction
    # ═══════════════════════════════════════════════════════════════
    1: dict(symbol="Ph", name="Photoreceptor", period=ElementPeriod.SENSORY_TRANSDUCTION,
            group=ElementGroup.SENSORY_VISUAL, block=ElementBlock.P_BLOCK,
            valence=ValenceState.EXCITATORY, electronegativity=0.2, ionization_energy=0.1,
            atomic_radius=0.1, mass=0.2, cell_types=["sensory_neuron", "input"],
            orbital_config=OrbitalConfiguration(p_shell={"ampa": 0.9, "nmda": 0.7})),
    2: dict(symbol="Hc", name="HairCell", period=ElementPeriod.SENSORY_TRANSDUCTION,
            group=ElementGroup.SENSORY_AUDITORY, block=ElementBlock.P_BLOCK,
            valence=ValenceState.EXCITATORY, electronegativity=0.2, ionization_energy=0.15,
            atomic_radius=0.15, mass=0.2, cell_types=["auditory_neuron"],
            orbital_config=OrbitalConfiguration(p_shell={"ampa": 0.95, "nmda": 0.6})),
    3: dict(symbol="Mc", name="Mechanoreceptor", period=ElementPeriod.SENSORY_TRANSDUCTION,
            group=ElementGroup.SENSORY_SOMATOSENSORY, block=ElementBlock.P_BLOCK,
            valence=ValenceState.EXCITATORY, electronegativity=0.25, ionization_energy=0.12,
            atomic_radius=0.3, mass=0.15, cell_types=["sensory_neuron"],
            orbital_config=OrbitalConfiguration(p_shell={"ampa": 0.85, "nmda": 0.5})),
    4: dict(symbol="Ch", name="Chemoreceptor", period=ElementPeriod.SENSORY_TRANSDUCTION,
            group=ElementGroup.SENSORY_CHEMICAL, block=ElementBlock.P_BLOCK,
            valence=ValenceState.EXCITATORY, electronegativity=0.3, ionization_energy=0.2,
            atomic_radius=0.2, mass=0.2, cell_types=["sensory_neuron"],
            orbital_config=OrbitalConfiguration(p_shell={"ampa": 0.8, "nmda": 0.6})),
    # ═══════════════════════════════════════════════════════════════
    # PERIOD 2 — Feature extraction
    # ═══════════════════════════════════════════════════════════════
    5: dict(symbol="Sc", name="SimpleCell", period=ElementPeriod.FEATURE_EXTRACTION,
            group=ElementGroup.SENSORY_VISUAL, block=ElementBlock.P_BLOCK,
            valence=ValenceState.EXCITATORY, electronegativity=0.3, ionization_energy=0.25,
            atomic_radius=0.15, mass=0.3, cell_types=["generic_neuron"],
            orbital_config=OrbitalConfiguration(p_shell={"ampa": 0.8, "nmda": 0.6})),
    6: dict(symbol="Cc", name="ComplexCell", period=ElementPeriod.FEATURE_EXTRACTION,
            group=ElementGroup.SENSORY_VISUAL, block=ElementBlock.P_BLOCK,
            valence=ValenceState.EXCITATORY, electronegativity=0.3, ionization_energy=0.3,
            atomic_radius=0.25, mass=0.35, cell_types=["generic_neuron"],
            orbital_config=OrbitalConfiguration(p_shell={"ampa": 0.75, "nmda": 0.7})),
    # ═══════════════════════════════════════════════════════════════
    # PERIOD 3 — Association and pattern recognition
    # ═══════════════════════════════════════════════════════════════
    7: dict(symbol="Au", name="Auditory", period=ElementPeriod.ASSOCIATION,
            group=ElementGroup.ASSOCIATION_LANGUAGE, block=ElementBlock.P_BLOCK,
            valence=ValenceState.EXCITATORY, electronegativity=0.35, ionization_energy=0.4,
            atomic_radius=0.4, mass=0.4, cell_types=["auditory_neuron"],
            orbital_config=OrbitalConfiguration(p_shell={"ampa": 0.8, "nmda": 0.7})),
    8: dict(symbol="We", name="Wernicke", period=ElementPeriod.ASSOCIATION,
            group=ElementGroup.ASSOCIATION_LANGUAGE, block=ElementBlock.P_BLOCK,
            valence=ValenceState.EXCITATORY, electronegativity=0.3, ionization_energy=0.45,
            atomic_radius=0.5, mass=0.5, cell_types=["wernicke_neuron"],
            orbital_config=OrbitalConfiguration(p_shell={"ampa": 0.7, "nmda": 0.8},
                                                d_shell={"ht_2a": 0.4})),
    9: dict(symbol="Br", name="Broca", period=ElementPeriod.ASSOCIATION,
            group=ElementGroup.ASSOCIATION_LANGUAGE, block=ElementBlock.P_BLOCK,
            valence=ValenceState.EXCITATORY, electronegativity=0.35, ionization_energy=0.5,
            atomic_radius=0.45, mass=0.5, cell_types=["broca_neuron"],
            orbital_config=OrbitalConfiguration(p_shell={"ampa": 0.75, "nmda": 0.75},
                                                d_shell={"d1": 0.5})),
    10: dict(symbol="Sp", name="SemanticPointer", period=ElementPeriod.ASSOCIATION,
             group=ElementGroup.ASSOCIATION_SEMANTIC, block=ElementBlock.P_BLOCK,
             valence=ValenceState.EXCITATORY, electronegativity=0.3, ionization_energy=0.5,
             atomic_radius=0.6, mass=0.55, cell_types=["semantic_pointer_neuron"],
             orbital_config=OrbitalConfiguration(p_shell={"ampa": 0.6, "nmda": 0.85},
                                                 d_shell={"ht_2a": 0.5, "d1": 0.4})),
    11: dict(symbol="Hp", name="Hippocampal", period=ElementPeriod.ASSOCIATION,
             group=ElementGroup.ASSOCIATION_MEMORY, block=ElementBlock.P_BLOCK,
             valence=ValenceState.EXCITATORY, electronegativity=0.25, ionization_energy=0.35,
             atomic_radius=0.5, mass=0.45, cell_types=["hippocampal_neuron"],
             orbital_config=OrbitalConfiguration(p_shell={"ampa": 0.8, "nmda": 0.9},
                                                 d_shell={"d1": 0.6})),
    # ═══════════════════════════════════════════════════════════════
    # PERIOD 4 — Integration
    # ═══════════════════════════════════════════════════════════════
    12: dict(symbol="En", name="Entorhinal", period=ElementPeriod.INTEGRATION,
             group=ElementGroup.ASSOCIATION_SPATIAL, block=ElementBlock.P_BLOCK,
             valence=ValenceState.EXCITATORY, electronegativity=0.3, ionization_energy=0.4,
             atomic_radius=0.55, mass=0.5, cell_types=["hippocampal_neuron"],
             orbital_config=OrbitalConfiguration(p_shell={"ampa": 0.7, "nmda": 0.8})),
    13: dict(symbol="Dg", name="DentateGyrus", period=ElementPeriod.INTEGRATION,
             group=ElementGroup.ASSOCIATION_MEMORY, block=ElementBlock.P_BLOCK,
             valence=ValenceState.EXCITATORY, electronegativity=0.25, ionization_energy=0.3,
             atomic_radius=0.35, mass=0.4, cell_types=["hippocampal_neuron"],
             orbital_config=OrbitalConfiguration(p_shell={"ampa": 0.85, "nmda": 0.75})),
    # ═══════════════════════════════════════════════════════════════
    # PERIOD 5 — Executive planning
    # ═══════════════════════════════════════════════════════════════
    14: dict(symbol="Pf", name="Prefrontal", period=ElementPeriod.EXECUTIVE,
             group=ElementGroup.EXECUTIVE_PFC, block=ElementBlock.P_BLOCK,
             valence=ValenceState.EXCITATORY, electronegativity=0.4, ionization_energy=0.6,
             atomic_radius=0.7, mass=0.7, cell_types=["prefrontal_neuron"],
             orbital_config=OrbitalConfiguration(p_shell={"ampa": 0.7, "nmda": 0.8},
                                                 d_shell={"d1": 0.7, "d2": 0.5, "ht_2a": 0.5})),
    15: dict(symbol="Lb", name="Limbic", period=ElementPeriod.EXECUTIVE,
             group=ElementGroup.EXECUTIVE_LIMBIC, block=ElementBlock.D_BLOCK,
             valence=ValenceState.MODULATORY, electronegativity=0.5, ionization_energy=0.5,
             atomic_radius=0.6, mass=0.6, cell_types=["limbic_neuron"],
             orbital_config=OrbitalConfiguration(p_shell={"ampa": 0.5, "nmda": 0.6},
                                                 d_shell={"d1": 0.8, "d2": 0.7, "ht_1a": 0.6, "ht_2a": 0.7})),
    16: dict(symbol="Dm", name="DefaultMode", period=ElementPeriod.EXECUTIVE,
             group=ElementGroup.EXECUTIVE_DMN, block=ElementBlock.D_BLOCK,
             valence=ValenceState.MODULATORY, electronegativity=0.45, ionization_energy=0.55,
             atomic_radius=0.65, mass=0.65, cell_types=["default_mode_neuron"],
             orbital_config=OrbitalConfiguration(p_shell={"ampa": 0.5, "nmda": 0.7},
                                                 d_shell={"ht_1a": 0.7, "d1": 0.5})),
    # ═══════════════════════════════════════════════════════════════
    # PERIOD 6 — Motor coordination
    # ═══════════════════════════════════════════════════════════════
    17: dict(symbol="Mo", name="Motor", period=ElementPeriod.MOTOR_COORDINATION,
             group=ElementGroup.EXECUTIVE_MOTOR, block=ElementBlock.P_BLOCK,
             valence=ValenceState.EXCITATORY, electronegativity=0.35, ionization_energy=0.45,
             atomic_radius=0.5, mass=0.55, cell_types=["motor_neuron", "output"],
             orbital_config=OrbitalConfiguration(p_shell={"ampa": 0.8, "nmda": 0.6})),
    18: dict(symbol="Cb", name="Cerebellar", period=ElementPeriod.MOTOR_COORDINATION,
             group=ElementGroup.REGULATORY_CEREBELLAR, block=ElementBlock.P_BLOCK,
             valence=ValenceState.INHIBITORY, electronegativity=0.6, ionization_energy=0.5,
             atomic_radius=0.5, mass=0.45, cell_types=["cerebellar_neuron"],
             orbital_config=OrbitalConfiguration(p_shell={"ampa": 0.7, "nmda": 0.6},
                                                 s_shell={"gaba_a": 0.8, "gaba_b": 0.6})),
    # ═══════════════════════════════════════════════════════════════
    # PERIOD 7 — Output & homeostasis
    # ═══════════════════════════════════════════════════════════════
    19: dict(symbol="Bs", name="Brainstem", period=ElementPeriod.OUTPUT_HOMEOSTASIS,
             group=ElementGroup.REGULATORY_BRAINSTEM, block=ElementBlock.D_BLOCK,
             valence=ValenceState.MODULATORY, electronegativity=0.55, ionization_energy=0.6,
             atomic_radius=0.4, mass=0.35, cell_types=["brainstem_neuron"],
             orbital_config=OrbitalConfiguration(d_shell={"d1": 0.5, "d2": 0.5, "ht_1a": 0.7})),
    20: dict(symbol="In", name="InhibitoryInterneuron", period=ElementPeriod.OUTPUT_HOMEOSTASIS,
             group=ElementGroup.REGULATORY_INHIBITORY, block=ElementBlock.S_BLOCK,
             valence=ValenceState.STRONG_INHIBITORY, electronegativity=0.9, ionization_energy=0.3,
             atomic_radius=0.3, mass=0.25, cell_types=["inhibitory_neuron"],
             orbital_config=OrbitalConfiguration(s_shell={"gaba_a": 0.95, "gaba_b": 0.7})),
    21: dict(symbol="Dp", name="Dopaminergic", period=ElementPeriod.OUTPUT_HOMEOSTASIS,
             group=ElementGroup.REGULATORY_MODULATORY, block=ElementBlock.D_BLOCK,
             valence=ValenceState.MODULATORY, electronegativity=0.5, ionization_energy=0.5,
             atomic_radius=0.5, mass=0.4, cell_types=["generic_neuron"],
             orbital_config=OrbitalConfiguration(d_shell={"d1": 0.9, "d2": 0.8})),
    22: dict(symbol="Sr", name="Serotonergic", period=ElementPeriod.OUTPUT_HOMEOSTASIS,
             group=ElementGroup.REGULATORY_MODULATORY, block=ElementBlock.D_BLOCK,
             valence=ValenceState.MODULATORY, electronegativity=0.55, ionization_energy=0.55,
             atomic_radius=0.5, mass=0.4, cell_types=["generic_neuron"],
             orbital_config=OrbitalConfiguration(d_shell={"ht_1a": 0.9, "ht_2a": 0.8, "ht_3": 0.6})),
    # ═══════════════════════════════════════════════════════════════
    # Noble — Glial cells (Period-independent)
    # ═══════════════════════════════════════════════════════════════
    23: dict(symbol="As", name="Astrocyte", period=ElementPeriod.OUTPUT_HOMEOSTASIS,
             group=ElementGroup.GLIAL_SUPPORT, block=ElementBlock.G_BLOCK,
             valence=ValenceState.NEUTRAL, electronegativity=0.5, ionization_energy=0.9,
             atomic_radius=0.8, mass=0.3, cell_types=["digital_astrocyte"],
             orbital_config=OrbitalConfiguration()),
    24: dict(symbol="Mg", name="Microglia", period=ElementPeriod.OUTPUT_HOMEOSTASIS,
             group=ElementGroup.GLIAL_SUPPORT, block=ElementBlock.G_BLOCK,
             valence=ValenceState.NEUTRAL, electronegativity=0.7, ionization_energy=0.95,
             atomic_radius=0.3, mass=0.2, cell_types=["digital_microglia"],
             orbital_config=OrbitalConfiguration()),
    25: dict(symbol="Ol", name="Oligodendrocyte", period=ElementPeriod.OUTPUT_HOMEOSTASIS,
             group=ElementGroup.GLIAL_SUPPORT, block=ElementBlock.G_BLOCK,
             valence=ValenceState.NEUTRAL, electronegativity=0.4, ionization_energy=0.95,
             atomic_radius=0.4, mass=0.15, cell_types=["digital_oligodendrocyte"],
             orbital_config=OrbitalConfiguration()),
    26: dict(symbol="Rg", name="Regulatory", period=ElementPeriod.OUTPUT_HOMEOSTASIS,
             group=ElementGroup.REGULATORY_INHIBITORY, block=ElementBlock.S_BLOCK,
             valence=ValenceState.INHIBITORY, electronegativity=0.6, ionization_energy=0.5,
             atomic_radius=0.4, mass=0.3, cell_types=["regulatory_neuron"],
             orbital_config=OrbitalConfiguration(s_shell={"gaba_a": 0.7, "gaba_b": 0.6})),
    27: dict(symbol="Gn", name="GenericNeuron", period=ElementPeriod.ASSOCIATION,
             group=ElementGroup.NOBLE_BACKGROUND, block=ElementBlock.P_BLOCK,
             valence=ValenceState.NEUTRAL, electronegativity=0.5, ionization_energy=0.5,
             atomic_radius=0.5, mass=0.5, cell_types=["generic_neuron"],
             orbital_config=OrbitalConfiguration(p_shell={"ampa": 0.5, "nmda": 0.5})),
}


def build_element(atomic_number: int) -> NeuralElement:
    """Build a NeuralElement from the catalog by atomic number."""
    if atomic_number not in CATALOG:
        raise ValueError(f"Unknown element z={atomic_number}")
    params = CATALOG[atomic_number].copy()
    affinities = params.pop("affinity_strengths", {})

    # T-COR — default superposition capacity by block/period if not explicit.
    if "cor_capacity" not in params:
        block = params.get("block")
        period = params.get("period")
        if block == ElementBlock.P_BLOCK:
            base = 0.7  # excitatory associative elements support many hypotheses
        elif block == ElementBlock.D_BLOCK:
            base = 0.5  # modulatory elements gate hypotheses
        elif block == ElementBlock.S_BLOCK:
            base = 0.3  # inhibitory elements collapse fast
        elif block == ElementBlock.F_BLOCK:
            base = 0.4  # slow neuropeptide modulation
        else:
            base = 0.2
        # Deeper periods can sustain richer superpositions.
        depth_factor = ((period.value if period else 3) - 1) / 6.0 * 0.2
        params["cor_capacity"] = min(1.0, base + depth_factor)

    element = NeuralElement(atomic_number=atomic_number, **params)
    element.affinity_strengths = affinities
    return element


def get_element_by_cell_type(cell_type: str) -> Optional[NeuralElement]:
    """Find the NeuralElement that corresponds to a SPEACE cell type."""
    for z, params in CATALOG.items():
        if cell_type in params.get("cell_types", []):
            return build_element(z)
    return None


