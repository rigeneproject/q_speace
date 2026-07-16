from typing import TYPE_CHECKING, Any, Dict, List, Optional

from speace_core.cellular_brain.memory.morphological_memory import MorphologicalMemory
from speace_core.cellular_brain.memory.morphology_events import MorphologyEventType
from speace_core.cellular_brain.regions.region_registry import RegionRegistry

if TYPE_CHECKING:
    from speace_core.dna.models import ConnectomeGeneSet


class DeepRegionSpecialization:
    """Extends the 4-region pipeline into an 8-region deep architecture.

    T31 adds limbic, cerebellar, default_mode, and brainstem_homeostatic regions
    with specialized inter-region pathways and metrics.
    """

    # Deep region roles for validation
    DEEP_REGION_ROLES: Dict[str, str] = {
        "sensory": "input_processing",
        "limbic": "salience_valence_regulation",
        "hippocampus": "memory_binding",
        "default_mode": "internal_simulation_consolidation",
        "prefrontal": "planning_control",
        "cerebellar": "error_correction_prediction",
        "motor": "output_execution",
        "brainstem_homeostatic": "metabolic_arousal_survival_control",
    }

    # Extended pathway topology beyond the feedforward pipeline
    DEEP_PATHWAYS: List[tuple[str, str, str]] = [
        ("sensory", "limbic", "salience"),
        ("limbic", "prefrontal", "valence"),
        ("hippocampus", "default_mode", "consolidation"),
        ("default_mode", "prefrontal", "reflection"),
        ("prefrontal", "cerebellar", "prediction"),
        ("cerebellar", "motor", "correction"),
        ("brainstem_homeostatic", "sensory", "arousal"),
        ("brainstem_homeostatic", "limbic", "arousal"),
        ("brainstem_homeostatic", "hippocampus", "arousal"),
        ("brainstem_homeostatic", "default_mode", "arousal"),
        ("brainstem_homeostatic", "prefrontal", "arousal"),
        ("brainstem_homeostatic", "cerebellar", "arousal"),
        ("brainstem_homeostatic", "motor", "arousal"),
    ]

    @classmethod
    def extend_region_connectome(
        cls,
        registry: RegionRegistry,
        connectome_genes: Optional["ConnectomeGeneSet"] = None,
    ) -> int:
        """Add deep-region pathways to an existing connectome.

        If connectome_genes are provided, they modulate connection parameters:
        - connectivity_density → piu'/meno connessioni aggiunte
        - hub_formation → forza delle connessioni hub
        - plasticity → abilita/disabilita plasticita'
        - long_range_connections → favorisce path-away non standard

        Returns the number of new connections added.
        """
        if registry is None or registry.connectome is None:
            return 0

        added = 0
        existing_pairs = {
            (c.source_region_id, c.target_region_id)
            for c in registry.connectome.connections
        }

        # Applica geni connettoma alla forza e plasticita' delle pathway standard
        strength_mod = 1.0
        plasticity = True
        if connectome_genes:
            strength_mod = 0.5 + connectome_genes.connectivity_density * 0.5
            plasticity = connectome_genes.plasticity > 0.3

        for src, tgt, conn_type in cls.DEEP_PATHWAYS:
            if (src, tgt) in existing_pairs:
                continue
            if src not in registry.regions or tgt not in registry.regions:
                continue
            base_strength = 0.5

            # Hub formation boost: se il gene e' alto, rinforza connessioni verso regioni hub
            if connectome_genes and connectome_genes.hub_formation > 0.6:
                if tgt in ("prefrontal", "limbic", "hippocampus"):
                    base_strength += 0.15

            # Long-range boost: favorisce pathway non-lineari
            if connectome_genes and connectome_genes.long_range_connections > 0.5:
                if conn_type in ("consolidation", "reflection", "prediction"):
                    base_strength += 0.1

            registry.connectome.add_connection(
                source_region_id=src,
                target_region_id=tgt,
                connection_type=conn_type,
                strength=min(1.0, base_strength * strength_mod),
                plasticity_enabled=plasticity,
                inhibitory=False,
            )
            added += 1

        # Se exploration e' alto, aggiungi pathway non-standard (oltre DEEP_PATHWAYS)
        if connectome_genes and connectome_genes.exploration > 0.6 and len(registry.regions) >= 4:
            import random

            region_ids = list(registry.regions.keys())
            extra_paths = int(connectome_genes.exploration * 3)
            for _ in range(extra_paths):
                src = random.choice(region_ids)
                tgt = random.choice(region_ids)
                if src == tgt:
                    continue
                if (src, tgt) in existing_pairs:
                    continue
                registry.connectome.add_connection(
                    source_region_id=src,
                    target_region_id=tgt,
                    connection_type="exploratory",
                    strength=0.3,
                    plasticity_enabled=True,
                    inhibitory=False,
                )
                added += 1

        return added

    @classmethod
    def apply_deep_region_specialization(
        cls,
        registry: RegionRegistry,
        memory: Optional[MorphologicalMemory] = None,
        connectome_genes: Optional["ConnectomeGeneSet"] = None,
    ) -> Dict[str, Any]:
        """Apply full deep-region specialization to a registry.

        Extends connectome and records events. Returns summary dict.
        """
        added = cls.extend_region_connectome(registry, connectome_genes=connectome_genes)

        # Backward connections from all regions to brainstem
        brainstem = "brainstem_homeostatic"
        if brainstem in registry.regions:
            for rid in registry.regions:
                if rid != brainstem:
                    registry.connectome.add_connection(
                        source_region_id=rid,
                        target_region_id=brainstem,
                        connection_type="feedback",
                        strength=0.3,
                        plasticity_enabled=True,
                        inhibitory=False,
                    )

        if memory is not None:
            memory.create_event(
                event_type=MorphologyEventType.DEEP_REGION_SPECIALIZATION_APPLIED,
                source_id="deep_region_specialization",
                metadata={
                    "added_pathways": added,
                    "region_count": len(registry.regions),
                    "connection_count": len(registry.connectome.connections),
                },
            )

        return {
            "added_pathways": added,
            "region_count": len(registry.regions),
            "connection_count": len(registry.connectome.connections),
        }

    @classmethod
    def validate_deep_region_architecture(cls, registry: RegionRegistry) -> tuple[bool, List[str]]:
        """Validate that all expected deep regions and pathways are present.

        Returns (is_valid, missing_items).
        """
        missing: List[str] = []

        for rid in cls.DEEP_REGION_ROLES:
            if rid not in registry.regions:
                missing.append(f"missing_region:{rid}")

        existing_pairs = {
            (c.source_region_id, c.target_region_id)
            for c in registry.connectome.connections
        }
        for src, tgt, _ in cls.DEEP_PATHWAYS:
            if (src, tgt) not in existing_pairs:
                missing.append(f"missing_pathway:{src}->{tgt}")

        return len(missing) == 0, missing

    @classmethod
    def compute_region_role_alignment(cls, registry: RegionRegistry) -> float:
        """Score how well regions match their intended roles.

        Returns 0.0–1.0 based on presence of role_description and neuron count.
        """
        if not registry.regions:
            return 0.0

        scores = []
        for rid, expected_role in cls.DEEP_REGION_ROLES.items():
            region = registry.regions.get(rid)
            if region is None:
                scores.append(0.0)
                continue
            has_description = bool(region.role_description)
            has_neurons = len(region.neuron_ids) > 0
            scores.append(1.0 if has_description and has_neurons else 0.5)

        return sum(scores) / len(scores) if scores else 0.0

    @classmethod
    def compute_region_specialization_diversity(cls, registry: RegionRegistry) -> float:
        """Compute how diverse the region specializations are.

        Returns 0.0–1.0 based on unique dominant cell types across regions.
        """
        if not registry.regions:
            return 0.0

        all_types = set()
        for region in registry.regions.values():
            all_types.update(region.dominant_cell_types)

        max_possible = len(cls.DEEP_REGION_ROLES)
        return min(1.0, len(all_types) / max_possible) if max_possible > 0 else 0.0

    @classmethod
    def compute_deep_region_signal_flow(cls, registry: RegionRegistry) -> float:
        """Compute aggregate signal flow across deep region pathways.

        Returns mean strength * active_fraction * density.
        """
        if registry is None or registry.connectome is None:
            return 0.0

        conns = registry.connectome.connections
        if not conns:
            return 0.0

        deep_conns = [
            c for c in conns
            if c.source_region_id in cls.DEEP_REGION_ROLES
            and c.target_region_id in cls.DEEP_REGION_ROLES
        ]
        if not deep_conns:
            return 0.0

        mean_strength = sum(c.strength for c in deep_conns) / len(deep_conns)
        active_fraction = sum(1 for c in deep_conns if c.plasticity_enabled) / len(deep_conns)
        density = registry.connectome.compute_connectome_density()

        return mean_strength * active_fraction * density

    @classmethod
    def compute_deep_region_metrics(cls, registry: RegionRegistry) -> Dict[str, float]:
        """Compute all T31 deep-region metrics.

        Returns dict with:
        - deep_region_count
        - limbic_salience_score
        - cerebellar_error_correction_score
        - default_mode_consolidation_score
        - brainstem_homeostatic_stability_score
        - deep_region_signal_flow
        - region_specialization_diversity
        - region_role_alignment_score
        """
        if not registry or not registry.regions:
            return {
                "deep_region_count": 0,
                "limbic_salience_score": 0.0,
                "cerebellar_error_correction_score": 0.0,
                "default_mode_consolidation_score": 0.0,
                "brainstem_homeostatic_stability_score": 0.0,
                "deep_region_signal_flow": 0.0,
                "region_specialization_diversity": 0.0,
                "region_role_alignment_score": 0.0,
            }

        # Individual region scores based on neuron count and local connectivity
        def _region_score(rid: str) -> float:
            region = registry.regions.get(rid)
            if region is None:
                return 0.0
            n_neurons = len(region.neuron_ids)
            n_outgoing = len(registry.connectome.get_connections_from(rid))
            n_incoming = len(registry.connectome.get_connections_to(rid))
            connectivity = min(1.0, (n_outgoing + n_incoming) / 4.0)
            return min(1.0, n_neurons / 10.0) * connectivity

        return {
            "deep_region_count": sum(1 for r in registry.regions if r in cls.DEEP_REGION_ROLES),
            "limbic_salience_score": _region_score("limbic"),
            "cerebellar_error_correction_score": _region_score("cerebellar"),
            "default_mode_consolidation_score": _region_score("default_mode"),
            "brainstem_homeostatic_stability_score": _region_score("brainstem_homeostatic"),
            "deep_region_signal_flow": cls.compute_deep_region_signal_flow(registry),
            "region_specialization_diversity": cls.compute_region_specialization_diversity(registry),
            "region_role_alignment_score": cls.compute_region_role_alignment(registry),
        }
