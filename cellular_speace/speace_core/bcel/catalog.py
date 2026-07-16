"""Catalog of biological-to-digital equivalences used by the BCEL.

Each entry records the function, the likely accidental constraints, and the
functional constraints that must be preserved as mathematical rules.
"""

from typing import Dict, List

from speace_core.bcel.models import BiologicalComponent, CyberneticEquivalent, FunctionalConstraint


def _dna_rna_equivalent() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="DNA-RNA expression",
        preserved_function="stable source code + isolated execution copy",
        removed_constraints=[
            "chemical instability of RNA",
            "macromolecular transport slowness",
            "transcription enzyme overhead",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="source_protection",
                invariant="identity_preservation_through_change",
                biological_form="DNA stays in nucleus; RNA is the disposable working copy",
                mathematical_form="immutable SharedGenome + volatile Transcriptome",
                parameters={"genome_write_governance": True},
            ),
            FunctionalConstraint(
                name="amplification_control",
                invariant="generative_variability_preservation",
                biological_form="thousands of mRNA copies from one gene",
                mathematical_form="context-dependent expression profiles; rate limiting",
                parameters={"max_expression_rate": 1.0},
            ),
        ],
        digital_implementation="Digital DNA -> Digital RNA -> Workspace",
        configuration={"rna_volatility": True, "dna_immutable": True},
    )


def _synapse_equivalent() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="chemical synapse",
        preserved_function="directed, weighted, adaptive signal transmission",
        removed_constraints=[
            "neurotransmitter diffusion delay",
            "vesicle depletion",
            "thermal noise in ion channels",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="delay_as_lowpass_filter",
                invariant="coherence_preservation",
                biological_form="1-2 ms synaptic delay",
                mathematical_form="leaky integrator + rate limiter",
                parameters={"tau_ms": 5.0, "max_rate_hz": 100.0},
                stability_test="network_does_not_oscillate_when_delay_removed",
            ),
            FunctionalConstraint(
                name="short_term_depression",
                invariant="destructive_entropy_reduction",
                biological_form="vesicle depletion reduces gain on repeated firing",
                mathematical_form="activity-dependent synaptic gain decay",
                parameters={"decay_per_spike": 0.05, "recovery_tau": 10.0},
                stability_test="prevents_runaway_excitation",
            ),
        ],
        digital_implementation="SynapticBond regulated by PeriodicLaw",
        configuration={"bond_type": "weighted_directed"},
    )




def _homeostasis_equivalent() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="biological homeostasis",
        preserved_function="maintain stable internal state despite perturbations",
        removed_constraints=[
            "slow hormonal diffusion through bloodstream",
            "limited sensor coverage of the body",
            "allostatic wear and tear",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="negative_feedback_loop",
                invariant="coherence_preservation",
                biological_form="homeostatic set-points with negative feedback",
                mathematical_form="target tracking PID / error-correcting controller",
                parameters={"set_point": 0.5, "gain": 0.1, "decay": 0.9},
                stability_test="system_returns_to_set_point_after_perturbation",
            )
        ],
        digital_implementation="HomeostasisEngine with target tracking",
        configuration={"feedback_type": "negative"},
    )


def _immune_response_equivalent() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="immune response",
        preserved_function="detect and neutralize threats while preserving self",
        removed_constraints=[
            "physical cell migration through tissue",
            "antibody production latency",
            "inflammation side-effects",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="self_nonself_discrimination",
                invariant="identity_preservation_through_change",
                biological_form="immune system distinguishes self from non-self",
                mathematical_form="allow-list / signature-based anomaly detection",
                parameters={"tolerance_threshold": 0.1, "quarantine_after_errors": 10},
                stability_test="does_not_attack_legitimate_components",
            ),
            FunctionalConstraint(
                name="controlled_inflammation",
                invariant="destructive_entropy_reduction",
                biological_form="localized inflammation isolates damage",
                mathematical_form="quarantine + resource throttling for misbehaving agents",
                parameters={"quarantine_duration_ticks": 50},
            ),
        ],
        digital_implementation="ImmuneEngine + quarantine policies",
        configuration={"detection": "signature_and_anomaly"},
    )


def _metabolism_equivalent() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="cellular metabolism",
        preserved_function="allocate energy and resources to functions that need them",
        removed_constraints=[
            "ATP synthesis bottleneck",
            "mitochondrial spatial distribution",
            "limited substrate diffusion",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="resource_allocation_by_demand",
                invariant="interconnection_efficiency",
                biological_form="metabolism preferentially fuels active tissues",
                mathematical_form="energy budget allocator weighted by activity and coherence",
                parameters={"baseline_budget": 0.3, "activity_weight": 0.5, "coherence_weight": 0.2},
                stability_test="active_modules_receive_resources_without_starvation",
            )
        ],
        digital_implementation="MetabolismCoordinator / EnergyControlAgent",
        configuration={"allocator": "demand_weighted"},
    )


def _apoptosis_equivalent() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="apoptosis",
        preserved_function="remove damaged or unnecessary components safely",
        removed_constraints=[
            "lysosomal enzyme cascade",
            "phagocyte cleanup latency",
            "irreversibility of cell death",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="programmed_removal_threshold",
                invariant="destructive_entropy_reduction",
                biological_form="cells self-destruct when damage exceeds a threshold",
                mathematical_form="prune components when error rate > threshold with audit trail",
                parameters={"damage_threshold": 0.8, "grace_period_ticks": 20},
                stability_test="removal_reduces_instead_of_creating_entropy",
            )
        ],
        digital_implementation="ApoptosisEngine with rollback-capable pruning",
        configuration={"rollback_enabled": True},
    )


def _refractory_period_equivalent() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="neural refractory period",
        preserved_function="limit firing rate to prevent runaway excitation",
        removed_constraints=[
            "ion-channel recovery time",
            "sodium-potassium pump refractoriness",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="rate_limiter",
                invariant="coherence_preservation",
                biological_form="neuron cannot fire again immediately after a spike",
                mathematical_form="digital neuron enforces minimum inter-spike interval",
                parameters={"min_inter_spike_ticks": 2},
                stability_test="firing_rate_stays_bounded",
            )
        ],
        digital_implementation="DigitalNeuron refractory counter",
        configuration={"refractory_ticks": 2},
    )

def _omni_rag_equivalent() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="corpus callosum (cognitive integration)",
        preserved_function="unified information integration across distributed cognitive modules",
        removed_constraints=[
            "slow axonal conduction velocity",
            "limited bandwidth (~200M fibers)",
            "physical space constraints in the skull",
            "myelination delay",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="bidirectional_integration",
                invariant="coherence_preservation",
                biological_form="corpus callosum enables bidirectional communication between hemispheres",
                mathematical_form="cognitive graph with typed edges and layer-specific collectors",
                parameters={"max_query_depth": 5, "relation_types": 22},
                stability_test="query_returns_multi_layer_results",
            ),
            FunctionalConstraint(
                name="modulatory_gating",
                invariant="generative_variability_preservation",
                biological_form="callosal transfer is modulated by attention/context",
                mathematical_form="layer filters and query parameters control which information crosses",
                parameters={"default_layers": "all", "max_results": 50},
                stability_test="layer_filter_works_correctly",
            ),
            FunctionalConstraint(
                name="coherence_preserving_integration",
                invariant="identity_preservation_through_change",
                biological_form="integrated information maintains hemispheric identity",
                mathematical_form="deduplication by node ID, cross-layer correlation scoring",
                parameters={"dedup_by": "node_id", "merge_strategy": "correlate_and_rank"},
                stability_test="no_duplicate_nodes_across_layers",
            ),
        ],
        digital_implementation="Omni-RAG cognitive graph -> layer collectors -> multi-layer query engine",
        configuration={
            "layers": ["semantic", "arch", "dna", "bcel", "runtime"],
            "storage": "JSONL",
            "query_engine": "graph_traversal + keyword",
        },
    )


def _cognitive_self_observatory_equivalent() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="cognitive self observatory (meta-cognition)",
        preserved_function="self-observation, self-modeling, narrative memory, coherence tracking, and metacognitive evaluation",
        removed_constraints=[
            "limited introspective access in biological brains",
            "confabulation and memory distortion",
            "slow cognitive reappraisal (seconds/minutes)",
            "emotional bias in self-assessment",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="layered_self_observation",
                invariant="coherence_preservation",
                biological_form="biological meta-cognition operates in nested loops (perception→evaluation→adjustment)",
                mathematical_form="8-level cognitive observatory pipeline (L1-L8) with configurable depth",
                parameters={"levels": 8, "max_trace_depth": 10, "cci_dimensions": 6},
                stability_test="on_tick_returns_coherent_cci",
            ),
            FunctionalConstraint(
                name="causal_attribution",
                invariant="identity_preservation_through_change",
                biological_form="humans construct narrative explanations for their own behavior",
                mathematical_form="causal evolution graph with genome→expression→decision→outcome→ILF→learning→mutation chains",
                parameters={"max_chain_depth": 7, "causal_relations": 14},
                stability_test="causal_trace_returns_complete_chain",
            ),
            FunctionalConstraint(
                name="coherence_driven_adaptation",
                invariant="generative_variability_preservation",
                biological_form="meta-cognitive discomfort (dissonance) motivates learning",
                mathematical_form="CCI trend triggers self-interpretation and narrative re-evaluation when below threshold",
                parameters={"cci_alert_threshold": 0.3, "trend_window": 20},
                stability_test="cci_decline_generates_interpretation",
            ),
        ],
        digital_implementation="CognitiveSelfObservatory orchestrator (CognitiveStateGraph → SelfModel → NarrativeMemory → CoherenceEngine → MetacognitiveEngine → CausalEvolutionGraph → SelfInterpretationEngine)",
        configuration={
            "store": "JSONL in data/cognitive_observatory",
            "tick_integration": "on_tick",
            "self_model_auto_update": True,
        },
    )


def _identity_vector_equivalent() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="identity vector / self-nonself boundary",
        preserved_function="distinguish self from non-self; maintain stable organism identity",
        removed_constraints=[
            "MHC polymorphism",
            "clonal selection latency",
            "physical antigen presentation",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="identity_preservation_through_change",
                invariant="identity_preservation_through_change",
                biological_form="immune system recognizes self antigens",
                mathematical_form="Euclidean distance < threshold on 10D identity vector",
                parameters={"vector_dimensions": 10, "self_threshold": 0.15},
                stability_test="identical_vectors_recognized_as_self",
            ),
            FunctionalConstraint(
                name="nonlocal_decoherence_tolerance",
                invariant="nonlocal_decoherence_tolerance",
                biological_form="self-recognition tolerates minor variations",
                mathematical_form="distance threshold allows drift within bound",
                parameters={"drift_tolerance": 0.15},
            ),
        ],
        digital_implementation="Organism.identity_vector + is_self() + self_distance()",
        configuration={"vector_size": 10, "threshold": 0.15},
    )


def _metabolic_cycle_equivalent() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="metabolic cycle",
        preserved_function="extract, transform, and allocate energy resources",
        removed_constraints=[
            "ATP yield per glucose molecule",
            "enzyme kinetics",
            "mitochondrial spatial distribution",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="resource_allocation_by_demand",
                invariant="interconnection_efficiency",
                biological_form="metabolism preferentially fuels active tissues",
                mathematical_form="energy acquisition weighted by neural/episodic/assembly activity",
                parameters={"base_energy": 1.0, "neuron_energy": 0.001, "episode_energy": 0.002, "assembly_energy": 0.001},
                stability_test="active_modules_receive_energy",
            )
        ],
        digital_implementation="MetabolicCycle.tick() -> acquire + transform + waste + store",
        configuration={"energy_capacity": 100.0},
    )


def _waste_clearance_equivalent() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="waste clearance",
        preserved_function="remove metabolic byproducts that would poison the system",
        removed_constraints=[
            "slow lysosomal enzyme degradation",
            "limited lysosome capacity per cell",
            "excretory organ spatial constraints",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="programmed_removal_threshold",
                invariant="destructive_entropy_reduction",
                biological_form="cells degrade waste when concentration exceeds threshold",
                mathematical_form="clear waste at scan interval or immediately if above max threshold",
                parameters={"scan_interval_ticks": 10, "max_waste_before_forced": 0.3, "clearance_rate": 0.01},
                stability_test="waste_cleared_before_reaching_critical_level",
            )
        ],
        digital_implementation="WasteClearanceEngine.tick() -> scan-interval + forced-clearance",
        configuration={"max_waste": 1.0, "clearance_rate": 0.01},
    )


def _temporal_coding_equivalent() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="temporal coding (spike timing as information)",
        preserved_function="encode information in precise timing of neural events",
        removed_constraints=[
            "ion channel kinetics",
            "neurotransmitter jitter",
            "propagation noise in axons",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="temporal_precision",
                invariant="nonlocal_decoherence_tolerance",
                biological_form="auditory system phase locking; hippocampal phase precession",
                mathematical_form="(ISI, phase, strength) triple as first-class signal property",
                parameters={"phase_bins": 10, "max_isi_ticks": 100},
                stability_test="temporal_code_preserves_phase_across_propagation",
            ),
            FunctionalConstraint(
                name="coincidence_detection",
                invariant="coherence_preservation",
                biological_form="neurons detect synchronous input as stronger signal",
                mathematical_form="temporal_code vectors compared for synchrony within phase window",
                parameters={"phase_window": 0.1},
            ),
        ],
        digital_implementation="SpikeEvent.temporal_code() -> [ISI, phase_norm, strength]",
        configuration={"encoding": "triple_temporal"},
    )


def _event_driven_computation_equivalent() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="event-driven computation (sparse activation)",
        preserved_function="minimize energy by activating only relevant pathways",
        removed_constraints=[
            "axonal propagation delay",
            "synaptic vesicle cycling cost",
            "metabolic overhead of maintained firing",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="sparse_activation",
                invariant="interconnection_efficiency",
                biological_form="neural circuits are silent until stimulated",
                mathematical_form="PropagationEngine emits only when SpikeEvent.strength > threshold",
                parameters={"min_activation": 0.01, "priority_cutoff": 0.0},
                stability_test="silent_circuit_consumes_no_energy",
            ),
            FunctionalConstraint(
                name="bond_gated_propagation",
                invariant="destructive_entropy_reduction",
                biological_form="synaptic strength gates signal transmission",
                mathematical_form="propagation attenuated by bond.bond_strength() and bond.molecule.amplification_factor()",
                parameters={"drop_threshold": 0.01},
            ),
        ],
        digital_implementation="PropagationEngine.emit() + propagate()",
        configuration={"mode": "event_driven_burst"},
    )


def _signal_transduction_equivalent() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="signal transduction (structure-preserving)",
        preserved_function="preserve signal structure through physical transformation to neural code",
        removed_constraints=[
            "limited frequency range of human hearing",
            "mechanical resonance constraints",
            "transducer latency",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="frequency_decomposition",
                invariant="coherence_preservation",
                biological_form="cochlea decomposes sound into frequency bands",
                mathematical_form="filter bank with logarithmic center frequency spacing",
                parameters={"filter_count": 12, "min_freq": 20.0, "max_freq": 20000.0},
                stability_test="frequency_bands_cover_expected_range",
            ),
            FunctionalConstraint(
                name="phase_preserving_encoding",
                invariant="nonlocal_decoherence_tolerance",
                biological_form="auditory nerve preserves phase structure",
                mathematical_form="phase angle extracted from analytic signal; encoded in spike phase field",
                parameters={"phase_bins": 10},
                stability_test="phase_consistency_across_transduction",
            ),
        ],
        digital_implementation="PhysioNeuralTransducer.transduce() -> filter_bank + envelope + phase",
        configuration={"signal_types": ["audio", "visual", "temperature", "pressure", "proprioceptive"]},
    )


def _memory_consolidation_equivalent() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="slow long-term memory consolidation",
        preserved_function="move stable patterns from transient to persistent storage",
        removed_constraints=[
            "protein synthesis latency (hours/days)",
            "limited molecular storage capacity",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="statistical_sampling_gate",
                invariant="destructive_entropy_reduction",
                biological_form="slow consolidation acts as a noise filter",
                mathematical_form="workspace -> persistent memory only after recurrence threshold",
                parameters={"recurrence_threshold": 3, "observation_window_ticks": 100},
                stability_test="noise_does_not_persist",
            )
        ],
        digital_implementation="GlobalWorkspace -> SemanticMemoryStore with recurrence check",
        configuration={"persistence_delay": "statistical"},
    )


def _enteroception_microbiome_equivalent() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="enteroception / gut-brain axis",
        preserved_function="modulate cognition via slow metabolite signals from a diverse population of substrate-consuming agents",
        removed_constraints=[
            "chemical diffusion through gut wall",
            "gut barrier permeability",
            "bacterial replication latency",
            "nutrient digestion time",
            "limited bacterial strain diversity",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="slow_modulatory_timescale",
                invariant="coherence_preservation",
                biological_form="gut modulation is slower than neural — prevents rapid gut-brain oscillations",
                mathematical_form="EntericSignalBus.update_interval = N ticks; metabolites averaged over window",
                parameters={"update_interval_ticks": 10},
                stability_test="no_rapid_oscillations_in_gut_feeling",
            ),
            FunctionalConstraint(
                name="population_diversity_resilience",
                invariant="destructive_entropy_reduction",
                biological_form="diverse microbiome resists perturbation; monoculture is fragile",
                mathematical_form="Shannon entropy of strain populations; floor at 0.05",
                parameters={"diversity_threshold": 0.4, "min_diversity": 0.05},
                stability_test="diversity_recovers_after_stress",
            ),
            FunctionalConstraint(
                name="substrate_dependent_growth",
                invariant="interconnection_efficiency",
                biological_form="microbiome composition responds to available nutrients",
                mathematical_form="strain.growth_rate * substrate_affinity * available_substrate",
                parameters={"max_substrate": 100.0},
                stability_test="substrate_shift_alters_metabolite_profile",
            ),
            FunctionalConstraint(
                name="bidirectional_damping",
                invariant="nonlocal_decoherence_tolerance",
                biological_form="stress suppresses microbiome; dysbiosis amplifies stress — bounded by damping",
                mathematical_form="stress_suppression_factor * stress_level * strain.stress_sensitivity",
                parameters={"stress_suppression_factor": 0.3},
                stability_test="bidirectional_feedback_does_not_diverge",
            ),
            FunctionalConstraint(
                name="gut_feeling_salience_modulation",
                invariant="generative_variability_preservation",
                biological_form="gut-derived salience biases exploration/exploitation trade-off",
                mathematical_form="gut_feeling = f(diversity, inflammation); novelty_boost modulates exploration drive",
                parameters={"gut_feeling_threshold": 0.5},
                stability_test="high_gut_feeling_reduces_exploration",
            ),
        ],
        digital_implementation="MicrobiomeModulator + EntericSignalBus -> GlobalWorkspace.broadcast('enteroception')",
        configuration={"max_strains": 10, "update_interval": 10, "metabolite_decay": 0.95},
    )


class BCELCatalog:
    """Registry of known biological-digital equivalences."""

    def __init__(self) -> None:
        self._entries: Dict[str, CyberneticEquivalent] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        for eq in (
            _dna_rna_equivalent(),
            _synapse_equivalent(),
            _identity_vector_equivalent(),
            _metabolic_cycle_equivalent(),
            _waste_clearance_equivalent(),
            _temporal_coding_equivalent(),
            _event_driven_computation_equivalent(),
            _signal_transduction_equivalent(),
            _memory_consolidation_equivalent(),
            _homeostasis_equivalent(),
            _enteroception_microbiome_equivalent(),
            _immune_response_equivalent(),
            _metabolism_equivalent(),
            _apoptosis_equivalent(),
            _refractory_period_equivalent(),
            _omni_rag_equivalent(),
            _cognitive_self_observatory_equivalent(),
        ):
            self._entries[eq.component_name] = eq

    def register(self, equivalent: CyberneticEquivalent) -> None:
        self._entries[equivalent.component_name] = equivalent

    def get(self, component_name: str) -> CyberneticEquivalent | None:
        return self._entries.get(component_name)

    def list_components(self) -> List[str]:
        return sorted(self._entries.keys())

    def evaluate_component(
        self, component: BiologicalComponent
    ) -> CyberneticEquivalent:
        """Return the catalog equivalent, or a fresh unclassified one."""
        known = self.get(component.name)
        if known is not None:
            return known
        return CyberneticEquivalent(
            component_name=component.name,
            preserved_function=component.function,
            removed_constraints=[],
            kept_constraints=[],
            digital_implementation="unknown",
        )


# --------------------------------------------------------------------------- #
# T174 — Cognitive Factors (10 equivalences, additive 2026-06-30)
# --------------------------------------------------------------------------- #
# These entries register the ten cognitive factors described in
# docs/T174_BCEL_COGNITIVE_FACTORS_SPEC.md. Each entry is *additional*;
# none of the pre-existing entries above are modified. They share the
# same CyberneticEquivalent structure: kept functional constraints map
# to one of the six informational invariants in species_orientation.yaml.


def _cognitive_factor_working_memory() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="cognitive factor: working memory",
        preserved_function="maintain multiple items active simultaneously for relational comparisons",
        removed_constraints=[
            "limited neuron firing rate in biological cortex",
            "synaptic interference from competing representations",
            "slow prefrontal bandwidth",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="wm_slot_span",
                invariant="generative_variability_preservation",
                biological_form="prefrontal cortex holds N items in active state",
                mathematical_form="bounded list of MemorySlot objects",
                parameters={"max_slots": 4, "overflow_threshold": 0.9},
                stability_test="overflow_increases_entropy",
            ),
        ],
        digital_implementation="cognition.subgrid_attention_working_memory.SubgridAttentionWorkingMemory",
        configuration={"max_slots_initial": 4},
    )


def _cognitive_factor_processing_speed() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="cognitive factor: processing speed",
        preserved_function="complete comparison/classification/inference operations within a bounded cognitive budget",
        removed_constraints=[
            "action potential propagation delay",
            "myelination quality variability",
            "neurotransmitter clearance latency",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="bounded_cost_per_tick",
                invariant="destructive_entropy_reduction",
                biological_form="metabolic budget per cognitive operation",
                mathematical_form="cognitive_cost_model with per-module cost caps",
                parameters={"cost_cap_per_tick": 0.5, "rolling_window": 200},
                stability_test="cost_rising_triggers_throttle",
            ),
        ],
        digital_implementation="metabolism.cognitive_cost_model.CognitiveCostModel",
        configuration={"rolling_window": 200},
    )


def _cognitive_factor_pattern_recognition() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="cognitive factor: pattern recognition",
        preserved_function="compress many examples into fewer, reusable schemas",
        removed_constraints=[
            "limited visual working memory in V1",
            "temporal cortex pattern-binding latency",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="abstraction_compression_ratio",
                invariant="generative_variability_preservation",
                biological_form="expert sees 3 structures / 2 anomalies / 1 hidden rule",
                mathematical_form="concept_graph abstraction ratio",
                parameters={"min_compression_ratio": 0.05},
                stability_test="low_compression_yields_more_entropy",
            ),
        ],
        digital_implementation="cognition.concept_graph + cognition.arc_primitive_discovery_engine",
        configuration={"min_compression_ratio": 0.05},
    )


def _cognitive_factor_prior_knowledge() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="cognitive factor: prior knowledge",
        preserved_function="route new inputs through an existing conceptual network",
        removed_constraints=[
            "hippocampal indexing delay",
            "slow neocortical myelination of memory traces",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="memory_link_density_floor",
                invariant="interconnection_efficiency",
                biological_form="semantic network grows denser with expertise",
                mathematical_form="edge_count / node_count^2",
                parameters={"min_density_floor": 0.0},
                stability_test="density_below_floor_stalls_abstraction",
            ),
        ],
        digital_implementation="evolutionary_memory + semantic_memory_store",
        configuration={"min_density_floor": 0.0},
    )


def _cognitive_factor_abstraction() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="cognitive factor: abstraction",
        preserved_function="climb several levels of generality without losing fidelity",
        removed_constraints=[
            "single-shot semantic encoding per neuron assembly",
            "limited range of categorical depth in IT cortex",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="abstraction_levels_active",
                invariant="generative_variability_preservation",
                biological_form="expert can move apple → fruit → organism → strategy",
                mathematical_form="HierarchicalConceptAbstractionLayer.active_levels()",
                parameters={"min_active_levels": 2},
                stability_test="levels_below_min_reduces_flexibility_score",
            ),
        ],
        digital_implementation="cognition.hierarchical_concept_abstraction_layer",
        configuration={"min_active_levels": 2},
    )


def _cognitive_factor_relational_reasoning() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="cognitive factor: relational reasoning",
        preserved_function="detect cycles, feedback, indirect causation in causal graphs",
        removed_constraints=[
            "limited short-term memory in dlPFC",
            "linear chaining bias in human reasoning",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="causal_cycle_detection",
                invariant="nonlocal_decoherence_tolerance",
                biological_form="A influences B, B influences C, C modulates A",
                mathematical_form="cycle_count() on TemporalCausalReasoningLayer",
                parameters={"min_cycles_for_relational": 1},
                stability_test="absence_of_cycles_marks_symbolic_only_reasoning",
            ),
        ],
        digital_implementation="cognition.temporal_causal_reasoning_layer",
        configuration={"min_cycles_for_relational": 1},
    )


def _cognitive_factor_metacognition() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="cognitive factor: metacognition",
        preserved_function="monitor own reasoning quality and reduce errors",
        removed_constraints=[
            "humans confabulate when introspecting",
            "cognitive reappraisal lag (seconds)",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="metacognitive_probe_rate",
                invariant="identity_preservation_through_change",
                biological_form="self-questioning: am I understanding? what is weak?",
                mathematical_form="metacognitive_probes_per_minute >= threshold",
                parameters={"min_probes_per_minute": 0.1},
                stability_test="below_threshold_doubles_error_rate_in_stress",
            ),
        ],
        digital_implementation="metacognition.metacognitive_monitor",
        configuration={"min_probes_per_minute": 0.1},
    )


def _cognitive_factor_sustained_attention() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="cognitive factor: sustained attention",
        preserved_function="suppress distractions while building a mental model",
        removed_constraints=[
            "default-mode network interruption frequency",
            "thalamic burst-mode dominance in drowsiness",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="attention_gap_budget",
                invariant="coherence_preservation",
                biological_form="thalamic tonic mode suppresses distractor inputs",
                mathematical_form="attention_gap_count <= 2 per 200 ticks",
                parameters={"gap_budget": 2},
                stability_test="gap_overshoot_degrades_coherence_phi",
            ),
        ],
        digital_implementation="regions.thalamic_relay_engine",
        configuration={"gap_budget": 2},
    )


def _cognitive_factor_motivation() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="cognitive factor: motivation",
        preserved_function="allocate cognitive resources by internal drive pressure",
        removed_constraints=[
            "hormonal diffusion latency",
            "metabolic cost of dopamine release",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="drive_pressure_cap",
                invariant="identity_preservation_through_change",
                biological_form="homeostatic drives stabilise allocation",
                mathematical_form="max(setpoint for drives) <= cap",
                parameters={"max_setpoint_cap": 0.8},
                stability_test="overshoot_pushes_exploratory_drift",
            ),
        ],
        digital_implementation="dna.genome.morphology.autonomous_drives",
        configuration={"max_setpoint_cap": 0.8},
    )


def _cognitive_factor_cognitive_flexibility() -> CyberneticEquivalent:
    return CyberneticEquivalent(
        component_name="cognitive factor: cognitive flexibility",
        preserved_function="switch perspective (math/bio/econ/philo/info) on demand",
        removed_constraints=[
            "task-set reconfiguration lag (200-500 ms)",
            "anterior cingulate switch-cost penalty",
        ],
        kept_constraints=[
            FunctionalConstraint(
                name="perspective_switch_rate",
                invariant="generative_variability_preservation",
                biological_form="set-shifting ability",
                mathematical_form="perspective_switches_per_minute >= threshold",
                parameters={"min_switches_per_minute": 0.2},
                stability_test="below_threshold_impairs_synthesis",
            ),
        ],
        digital_implementation="cognition.mmapr_council",
        configuration={"min_switches_per_minute": 0.2},
    )


def default_catalog() -> BCELCatalog:
    catalog = BCELCatalog()
    # T174 — register the ten cognitive factor entries.
    for eq in (
        _cognitive_factor_working_memory(),
        _cognitive_factor_processing_speed(),
        _cognitive_factor_pattern_recognition(),
        _cognitive_factor_prior_knowledge(),
        _cognitive_factor_abstraction(),
        _cognitive_factor_relational_reasoning(),
        _cognitive_factor_metacognition(),
        _cognitive_factor_sustained_attention(),
        _cognitive_factor_motivation(),
        _cognitive_factor_cognitive_flexibility(),
    ):
        catalog.register(eq)
    return catalog
