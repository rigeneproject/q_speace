import uuid
from typing import TYPE_CHECKING, List, Optional

from speace_core.cellular_brain.memory.morphological_memory import MorphologicalMemory
from speace_core.cellular_brain.memory.morphology_events import MorphologyEvent, MorphologyEventType
from speace_core.cellular_brain.memory.semantic.cell_assembly import (
    AssemblyActivationTrace,
    CellAssembly,
    SemanticMemoryMetrics,
)
from speace_core.cellular_brain.memory.semantic.semantic_memory_store import (
    SemanticMemoryStore,
)

if TYPE_CHECKING:
    from speace_core.orchestrator import CellularBrainOrchestrator


class CellAssemblyEngine:
    """T43 — Detect, consolidate, and manage cell assemblies from recurrent
    co-activation patterns."""

    def __init__(
        self,
        store: SemanticMemoryStore,
        min_neurons: int = 3,
        min_regions: int = 0,
        min_mean_activation: float = 0.15,
        min_confidence: float = 0.0,
        min_phi: float = 0.0,
        similarity_threshold: float = 0.70,
        consolidation_recurrence: int = 3,
        consolidation_stability: float = 0.30,
        decay_rate: float = 0.02,
        decay_threshold: float = 0.05,
        soft_activation_threshold: float = 0.05,
    ):
        self.store = store
        self.min_neurons = min_neurons
        self.min_regions = min_regions
        self.min_mean_activation = min_mean_activation
        self.min_confidence = min_confidence
        self.min_phi = min_phi
        self.similarity_threshold = similarity_threshold
        self.consolidation_recurrence = consolidation_recurrence
        self.consolidation_stability = consolidation_stability
        self.decay_rate = decay_rate
        self.decay_threshold = decay_threshold
        self.soft_activation_threshold = soft_activation_threshold

    # ------------------------------------------------------------------ #
    # Observation
    # ------------------------------------------------------------------ #

    def observe_activation(
        self, orchestrator: "CellularBrainOrchestrator"
    ) -> AssemblyActivationTrace:
        neurons = (
            orchestrator.circuit.input_neurons
            + orchestrator.circuit.hidden_neurons
            + orchestrator.circuit.output_neurons
        )
        active_neuron_ids = [
            n.cell_id
            for n in neurons
            if getattr(n, "activation", 0.0) >= self.soft_activation_threshold
        ]
        activation_vector = [getattr(n, "activation", 0.0) for n in neurons]
        mean_activation = sum(activation_vector) / max(1, len(activation_vector))
        mean_energy = sum(getattr(n, "energy", 0.0) for n in neurons) / max(1, len(neurons))

        region_ids: List[str] = []
        if orchestrator.region_registry:
            for region in orchestrator.region_registry.regions.values():
                if getattr(region, "last_activation_proxy", 0.0) >= self.soft_activation_threshold:
                    region_ids.append(getattr(region, "region_id", ""))

        phi = getattr(orchestrator, "last_phi", 0.0)
        confidence = 0.0
        if hasattr(orchestrator, "last_confidence_state") and orchestrator.last_confidence_state:
            confidence = getattr(orchestrator.last_confidence_state, "confidence_score", 0.0)

        return AssemblyActivationTrace(
            tick_id=getattr(orchestrator, "current_tick", 0),
            active_neuron_ids=active_neuron_ids,
            active_region_ids=region_ids,
            activation_vector=activation_vector,
            mean_activation=mean_activation,
            coherence_phi=phi,
            mean_energy=mean_energy,
            confidence_score=confidence,
        )

    # ------------------------------------------------------------------ #
    # Detection
    # ------------------------------------------------------------------ #

    def detect_candidate_assembly(
        self, trace: AssemblyActivationTrace
    ) -> Optional[CellAssembly]:
        if len(trace.active_neuron_ids) < self.min_neurons:
            return None
        if len(trace.active_region_ids) < self.min_regions:
            return None
        if trace.mean_activation < self.min_mean_activation:
            return None
        if trace.confidence_score < self.min_confidence:
            return None
        if trace.coherence_phi < self.min_phi:
            return None

        assembly = CellAssembly(
            assembly_id=f"asm-{uuid.uuid4().hex[:8]}",
            created_tick=trace.tick_id,
            last_activated_tick=trace.tick_id,
            neuron_ids=list(trace.active_neuron_ids),
            region_ids=list(trace.active_region_ids),
            activation_signature=list(trace.activation_vector),
            strength=0.20,
            stability=0.10,
            coherence_phi_at_creation=trace.coherence_phi,
            mean_energy_at_creation=trace.mean_energy,
        )
        return assembly

    def match_existing_assembly(
        self, trace: AssemblyActivationTrace
    ) -> Optional[CellAssembly]:
        from speace_core.cellular_brain.memory.semantic.semantic_recall_engine import (
            SemanticRecallEngine,
        )

        best: Optional[CellAssembly] = None
        best_score = 0.0
        for assembly in self.store.list_active():
            score = SemanticRecallEngine.compute_similarity(
                trace.activation_vector, assembly.activation_signature
            )
            if score > best_score:
                best_score = score
                best = assembly

        if best is not None and best_score >= self.similarity_threshold:
            return best
        return None

    # ------------------------------------------------------------------ #
    # Reinforcement / decay / consolidation
    # ------------------------------------------------------------------ #

    def reinforce_assembly(
        self, assembly: CellAssembly, trace: AssemblyActivationTrace
    ) -> None:
        assembly.strength = min(1.0, assembly.strength + 0.05)
        assembly.recurrence_count += 1
        assembly.last_activated_tick = trace.tick_id
        # Stability grows with recurrence, phi, energy, utility
        energy_factor = max(0.0, min(1.0, trace.mean_energy))
        phi_factor = max(0.0, min(1.0, trace.coherence_phi))
        stability_boost = (
            0.4 * (assembly.recurrence_count / max(1, self.consolidation_recurrence * 2))
            + 0.3 * phi_factor
            + 0.3 * energy_factor
        )
        assembly.stability = min(1.0, assembly.stability + stability_boost * 0.05)

    def decay_assemblies(self) -> None:
        for assembly in self.store.list_active():
            if not assembly.consolidated:
                assembly.strength = max(0.0, assembly.strength - self.decay_rate)
            else:
                # Consolidated assemblies decay more slowly
                assembly.strength = max(0.0, assembly.strength - self.decay_rate * 0.3)
            if assembly.strength < self.decay_threshold:
                assembly.active = False

    def consolidate_assemblies(self) -> None:
        for assembly in self.store.list_active():
            if (
                not assembly.consolidated
                and assembly.recurrence_count >= self.consolidation_recurrence
                and assembly.stability >= self.consolidation_stability
            ):
                assembly.consolidated = True
                assembly.stability = min(1.0, assembly.stability + 0.10)

    # ------------------------------------------------------------------ #
    # Main cycle
    # ------------------------------------------------------------------ #

    def run_semantic_memory_cycle(
        self, orchestrator: "CellularBrainOrchestrator"
    ) -> SemanticMemoryMetrics:
        trace = self.observe_activation(orchestrator)

        matched = self.match_existing_assembly(trace)
        if matched is not None:
            self.reinforce_assembly(matched, trace)
            self._log_event(
                orchestrator,
                MorphologyEventType.CELL_ASSEMBLY_REINFORCED,
                matched.assembly_id,
            )
        else:
            candidate = self.detect_candidate_assembly(trace)
            if candidate is not None:
                self.store.save(candidate)
                self._log_event(
                    orchestrator,
                    MorphologyEventType.CELL_ASSEMBLY_CREATED,
                    candidate.assembly_id,
                )

        self.decay_assemblies()
        self.consolidate_assemblies()

        metrics = self._compute_metrics()
        self.store.persist_metrics(metrics)
        return metrics

    # ------------------------------------------------------------------ #
    # Metrics
    # ------------------------------------------------------------------ #

    def _compute_metrics(self) -> SemanticMemoryMetrics:
        assemblies = list(self.store._assemblies.values())
        if not assemblies:
            return SemanticMemoryMetrics()

        active = [a for a in assemblies if a.active]
        consolidated = [a for a in assemblies if a.consolidated]
        n = len(assemblies)

        mean_strength = sum(a.strength for a in assemblies) / n
        mean_stability = sum(a.stability for a in assemblies) / n
        density = min(1.0, n / max(1, len(active) * 2))
        utility = sum(a.utility_score for a in assemblies) / n
        consolidation_rate = len(consolidated) / max(1, n)
        # Simple decay rate = fraction of assemblies that became inactive recently
        decay_rate = len([a for a in assemblies if not a.active]) / max(1, n)

        return SemanticMemoryMetrics(
            assembly_count=n,
            active_assembly_count=len(active),
            mean_assembly_strength=mean_strength,
            mean_assembly_stability=mean_stability,
            semantic_recall_success_rate=0.0,  # populated by recall engine
            semantic_memory_density=density,
            semantic_memory_utility=utility,
            semantic_consolidation_rate=consolidation_rate,
            semantic_decay_rate=decay_rate,
        )

    # ------------------------------------------------------------------ #
    # Logging
    # ------------------------------------------------------------------ #

    @staticmethod
    def _log_event(
        orchestrator: "CellularBrainOrchestrator",
        event_type: MorphologyEventType,
        assembly_id: str,
    ) -> None:
        mem = getattr(orchestrator, "memory", None)
        if mem is not None and hasattr(mem, "create_event"):
            mem.create_event(
                event_type=event_type,
                source_id="cell_assembly_engine",
                target_id=assembly_id,
            )
