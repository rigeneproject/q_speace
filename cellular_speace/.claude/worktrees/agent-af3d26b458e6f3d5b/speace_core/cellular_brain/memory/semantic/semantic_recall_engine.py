import math
from typing import List, Optional

from speace_core.cellular_brain.memory.semantic.cell_assembly import (
    AssemblyActivationTrace,
    CellAssembly,
    SemanticRecallResult,
)
from speace_core.cellular_brain.memory.semantic.semantic_memory_store import (
    SemanticMemoryStore,
)
from speace_core.orchestrator import CellularBrainOrchestrator


class SemanticRecallEngine:
    """Recall and reactivation engine for semantic cell assemblies."""

    def __init__(
        self,
        store: SemanticMemoryStore,
        similarity_threshold: float = 0.70,
        max_reactivation_energy: float = 0.30,
    ):
        self.store = store
        self.similarity_threshold = similarity_threshold
        self.max_reactivation_energy = max_reactivation_energy

    # ------------------------------------------------------------------ #
    # Similarity
    # ------------------------------------------------------------------ #

    @staticmethod
    def compute_similarity(a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 0.0
        # Pad shorter vector
        length = max(len(a), len(b))
        av = a + [0.0] * (length - len(a))
        bv = b + [0.0] * (length - len(b))
        dot = sum(x * y for x, y in zip(av, bv))
        norm_a = math.sqrt(sum(x * x for x in av)) or 1.0
        norm_b = math.sqrt(sum(x * x for x in bv)) or 1.0
        return max(0.0, min(1.0, dot / (norm_a * norm_b)))

    # ------------------------------------------------------------------ #
    # Recall
    # ------------------------------------------------------------------ #

    def recall(self, query_signature: List[float]) -> SemanticRecallResult:
        best: Optional[CellAssembly] = None
        best_score = 0.0
        matched_ids: List[str] = []

        for assembly in self.store.list_active():
            score = self.compute_similarity(query_signature, assembly.activation_signature)
            if score >= self.similarity_threshold:
                matched_ids.append(assembly.assembly_id)
                if score > best_score:
                    best_score = score
                    best = assembly

        if best is None:
            return SemanticRecallResult(
                query_signature=query_signature,
                recall_success=False,
            )

        return SemanticRecallResult(
            query_signature=query_signature,
            matched_assemblies=matched_ids,
            best_match_id=best.assembly_id,
            similarity_score=best_score,
            recalled_activation_pattern=list(best.activation_signature),
            recall_confidence=best_score * best.stability,
            recall_success=True,
        )

    def recall_from_current_activation(
        self, orchestrator: CellularBrainOrchestrator
    ) -> SemanticRecallResult:
        trace = self._extract_trace_from_orchestrator(orchestrator)
        return self.recall(trace.activation_vector)

    # ------------------------------------------------------------------ #
    # Reactivation
    # ------------------------------------------------------------------ #

    def reactivate_assembly(
        self, assembly_id: str, orchestrator: CellularBrainOrchestrator
    ) -> bool:
        assembly = self.store.get_by_id(assembly_id)
        if assembly is None or not assembly.active:
            return False

        all_neurons = {
            n.cell_id: n
            for n in orchestrator.circuit.input_neurons
            + orchestrator.circuit.hidden_neurons
            + orchestrator.circuit.output_neurons
        }

        for nid in assembly.neuron_ids:
            neuron = all_neurons.get(nid)
            if neuron is None:
                continue
            # Bounded weak activation injection
            bump = min(
                self.max_reactivation_energy,
                max(0.0, 0.5 - getattr(neuron, "energy", 0.5)),
            )
            if bump > 0:
                neuron.activation = min(
                    2.0, getattr(neuron, "activation", 0.0) + bump
                )

        return True

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _extract_trace_from_orchestrator(
        orchestrator: CellularBrainOrchestrator,
    ) -> AssemblyActivationTrace:
        neurons = (
            orchestrator.circuit.input_neurons
            + orchestrator.circuit.hidden_neurons
            + orchestrator.circuit.output_neurons
        )
        active_ids = [n.cell_id for n in neurons if getattr(n, "activation", 0.0) > 0.1]
        activations = [getattr(n, "activation", 0.0) for n in neurons]
        mean_activation = sum(activations) / max(1, len(activations))
        mean_energy = sum(getattr(n, "energy", 0.0) for n in neurons) / max(1, len(neurons))

        region_ids: List[str] = []
        if orchestrator.region_registry:
            for region in orchestrator.region_registry.regions.values():
                if getattr(region, "last_activation_proxy", 0.0) > 0.1:
                    region_ids.append(getattr(region, "region_id", ""))

        phi = getattr(orchestrator, "last_phi", 0.0)
        confidence = 0.0
        if hasattr(orchestrator, "last_confidence_state") and orchestrator.last_confidence_state:
            confidence = getattr(orchestrator.last_confidence_state, "confidence_score", 0.0)

        return AssemblyActivationTrace(
            tick_id=getattr(orchestrator, "current_tick", 0),
            active_neuron_ids=active_ids,
            active_region_ids=region_ids,
            activation_vector=activations,
            mean_activation=mean_activation,
            coherence_phi=phi,
            mean_energy=mean_energy,
            confidence_score=confidence,
        )
