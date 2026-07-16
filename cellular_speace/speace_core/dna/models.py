from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from speace_core.dna.tft_gene import TFTPspGeneSet


class GenomeIdentity(BaseModel):
    entity_name: str = "SPEACE"
    nature: str = "cybernetic_evolutionary_entity"
    core_function: str = "increase_systemic_coherence"
    substrate: str = "digital_physical_hybrid"
    continuity_principle: str = "preserve_identity_through_adaptive_change"


class GenomeMorphology(BaseModel):
    allowed_cell_types: List[str] = []
    allowed_tissues: List[str] = []
    organs: List[str] = []


class CellExpressionRules(BaseModel):
    role: str
    express: List[str] = []
    threshold_defaults: Dict[str, float] = Field(default_factory=dict)


class HomeostasisParams(BaseModel):
    default_threshold: float = 0.5
    default_plasticity_rate: float = 0.05
    max_energy: float = 1.0
    overload_threshold: float = 0.85
    noise_suppression_rate: float = 0.2
    energy_recovery_rate: float = 0.01


class ImmuneParams(BaseModel):
    prune_threshold: float = 0.1
    quarantine_error_limit: int = 10
    myelination_success_threshold: float = 0.8
    latency_reduction: float = 0.3


class CellDifferentiationRule(BaseModel):
    regions: List[str] = []
    role: str = ""
    threshold_modifier: float = 0.0
    plasticity_modifier: float = 1.0
    energy_profile: str = "normal"
    signal_sign: int = 1
    refractory_period: int = 0
    memory_affinity: float = 0.0
    inhibition_affinity: float = 0.0


class DynamicsParams(BaseModel):
    temporal_dynamics: Dict[str, Any] = Field(default_factory=dict)
    neural_oscillator: Dict[str, Any] = Field(default_factory=dict)
    phase_coupling: Dict[str, Any] = Field(default_factory=dict)
    energy_field: Dict[str, Any] = Field(default_factory=dict)
    predictive_coding: Dict[str, Any] = Field(default_factory=dict)
    active_inference: Dict[str, Any] = Field(default_factory=dict)
    homeostatic_drive: Dict[str, Any] = Field(default_factory=dict)
    criticality_monitor: Dict[str, Any] = Field(default_factory=dict)


class PeriodicTrendGene(BaseModel):
    """DNA-serializable description of a periodic trend function.

    The ``across_period`` and ``down_group`` fields are Python expression
    strings using the normalized variables ``g`` (0..1 across group) and
    ``p`` (0..1 down period). They are evaluated safely by PeriodicLaw.
    """
    name: str
    description: str = ""
    across_period: str = "g"
    down_group: str = "1.0 - p"
    noise_amplitude: float = 0.05


class ValenceRuleGene(BaseModel):
    """DNA-serializable valence rule for the Neural Periodic Table."""
    name: str
    description: str = ""
    condition: str
    result: Dict[str, Any] = Field(default_factory=dict)


class ReactionRuleGene(BaseModel):
    """DNA-serializable neural 'chemical reaction' rule."""
    name: str
    description: str = ""
    reactants: List[str] = Field(default_factory=list)
    products: List[str] = Field(default_factory=list)
    catalyst: Optional[str] = None
    energy_barrier: float = 0.5
    rate_constant: float = 0.1


class PeriodicTableGeneSet(BaseModel):
    """Genetic blueprint for the Neural Periodic Table laws.

    Allows the Digital DNA to drive periodic trends, valence rules and
    reaction rules instead of keeping them hard-coded in Python.
    """
    enabled: bool = True
    trends: Dict[str, PeriodicTrendGene] = Field(default_factory=dict)
    valence_rules: List[ValenceRuleGene] = Field(default_factory=list)
    reaction_rules: List[ReactionRuleGene] = Field(default_factory=list)
    default_bond_energy: float = 0.5
    default_bond_plasticity: float = 0.5
    affinity_strengths: Dict[str, Dict[str, float]] = Field(default_factory=dict)


class ConnectomeGeneSet(BaseModel):
    """Geni che controllano le proprietà topologiche del connettoma.

    Ogni gene agisce come parametro epigenetico per la formazione
    della struttura reticolare: più alto è il valore, più il tratto
    è espresso nel fenotipo connettomico.
    """
    connectivity_density: float = 0.3
    hub_formation: float = 0.5
    modularity: float = 0.5
    plasticity: float = 0.7
    long_range_connections: float = 0.4
    memory_consolidation: float = 0.5
    small_world_bias: float = 0.6
    redundancy: float = 0.3
    exploration: float = 0.5


class SystemAssimilationRule(BaseModel):
    path_prefix: str
    allowed_permissions: List[str] = ["read"]
    requires_approval: bool = False
    approved: bool = False


class SystemAssimilationParams(BaseModel):
    enable_vfs: bool = True
    enable_assimilation: bool = True
    root_mount_point: str = "C:\\"
    access_rules: List[SystemAssimilationRule] = Field(default_factory=lambda: [
        SystemAssimilationRule(path_prefix="C:\\", allowed_permissions=["read"], requires_approval=False),
        SystemAssimilationRule(path_prefix="C:\\cellular_speace", allowed_permissions=["read", "write"], requires_approval=False),
        SystemAssimilationRule(path_prefix="C:\\Windows\\System32", allowed_permissions=["read"], requires_approval=True),
        SystemAssimilationRule(path_prefix="C:\\Program Files", allowed_permissions=["read"], requires_approval=False),
    ])




class FunctionalActivationRule(BaseModel):
    """DNA rule for lazy on-demand activation of neural sub-functions."""
    rule_id: str
    description: str = ""
    trigger_meanings: List[str] = Field(default_factory=list)
    trigger_tags: List[str] = Field(default_factory=list)
    min_strength: float = 0.0
    activate_latent_state: Optional[str] = None
    latent_state_weight: float = 0.5
    activate_receptor_profile: Optional[str] = None
    enable_wave: bool = False
    wave_frequency: float = 10.0
    threshold_delta: float = 0.0
    plasticity_delta: float = 0.0


class FunctionalActivationParams(BaseModel):
    """Collection of functional-activation rules in the genome."""
    enabled: bool = True
    rules: List[FunctionalActivationRule] = Field(default_factory=list)




class QuantumGeneSet(BaseModel):
    """Digital DNA parameters for the quantum-inspired layer.

    These genes configure the optional quantum bridge. They do not claim
    to implement real quantum coherence in neurons; they only tune the
    classical emulation.
    """
    enabled: bool = False
    qubits_per_neuron: int = 1
    default_initial_state: int = 0
    entanglement_fidelity_threshold: float = 0.5
    gate_noise: float = 0.0
    periodic_element_qubit_map: Dict[str, int] = Field(default_factory=lambda: {
        "s": 1,  # fast inhibition: small state space
        "p": 2,  # excitatory association: richer superposition
        "d": 2,  # modulation
        "f": 1,  # slow neuropeptides
        "g": 1,  # glial support
    })




class CORGeneSet(BaseModel):
    """Digital DNA parameters for Cognitive Objective Reduction (COR).

    COR is a functional, informational analog of Orch-OR. These genes
    tune the collapse threshold and the structural conditions required
    to trigger a metacognitive collapse.
    """
    enabled: bool = False
    phi_threshold_factor: float = 0.55
    min_latent_states: int = 2
    max_hypotheses: int = 8
    collapse_refractory_ticks: int = 10
    reconfigure_on_collapse: bool = True
    safety_invariants: List[str] = Field(default_factory=list)

class SharedGenome(BaseModel):
    identity: GenomeIdentity = Field(default_factory=GenomeIdentity)
    morphology: GenomeMorphology = Field(default_factory=GenomeMorphology)
    expression_rules: Dict[str, CellExpressionRules] = Field(default_factory=dict)
    homeostasis: HomeostasisParams = Field(default_factory=HomeostasisParams)
    immune: ImmuneParams = Field(default_factory=ImmuneParams)
    dynamics: DynamicsParams = Field(default_factory=DynamicsParams)
    ilf_core: Dict[str, Any] = Field(default_factory=dict)
    edd_cvt_core: Dict[str, Any] = Field(default_factory=dict)
    cell_differentiation_rules: Dict[str, CellDifferentiationRule] = Field(
        default_factory=dict
    )
    brain_regions: Dict[str, Any] = Field(default_factory=dict)
    periodic_table: Dict[str, Any] = Field(default_factory=dict)
    monitoring_dashboard: Dict[str, Any] = Field(default_factory=dict)
    system_assimilation: SystemAssimilationParams = Field(default_factory=SystemAssimilationParams)
    neuro_os: Dict[str, Any] = Field(default_factory=dict)
    connectome_genes: ConnectomeGeneSet = Field(default_factory=ConnectomeGeneSet)
    periodic_table_genes: PeriodicTableGeneSet = Field(default_factory=PeriodicTableGeneSet)
    functional_activation: FunctionalActivationParams = Field(default_factory=FunctionalActivationParams)
    quantum_genes: QuantumGeneSet = Field(default_factory=QuantumGeneSet)
    cor_genes: CORGeneSet = Field(default_factory=CORGeneSet)
    tftpsp_genes: TFTPspGeneSet = Field(default_factory=TFTPspGeneSet)

    def get_genes_for_role(self, role: str) -> List[str]:
        rules = self.expression_rules.get(role)
        if rules is None:
            return []
        return list(rules.express)

    def get_differentiation_rule(self, cell_type: str) -> CellDifferentiationRule | None:
        return self.cell_differentiation_rules.get(cell_type)

    def get_effective_connectome_genes(self, epigenome_modifier: float = 1.0) -> "ConnectomeGeneSet":
        """Restituisce i geni del connettoma modulati da epigenetica."""
        cg = self.connectome_genes.model_copy()
        cg.connectivity_density = max(0.0, min(1.0, cg.connectivity_density * epigenome_modifier))
        cg.hub_formation = max(0.0, min(1.0, cg.hub_formation * epigenome_modifier))
        cg.modularity = max(0.0, min(1.0, cg.modularity * epigenome_modifier))
        cg.plasticity = max(0.0, min(1.0, cg.plasticity * epigenome_modifier))
        cg.long_range_connections = max(0.0, min(1.0, cg.long_range_connections * epigenome_modifier))
        cg.memory_consolidation = max(0.0, min(1.0, cg.memory_consolidation * epigenome_modifier))
        cg.small_world_bias = max(0.0, min(1.0, cg.small_world_bias * epigenome_modifier))
        cg.redundancy = max(0.0, min(1.0, cg.redundancy * epigenome_modifier))
        cg.exploration = max(0.0, min(1.0, cg.exploration * epigenome_modifier))
        return cg

