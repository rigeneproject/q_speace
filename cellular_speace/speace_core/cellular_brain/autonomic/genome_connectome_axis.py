"""GenomeConnectomeAxis — Coordinatore unificato Genoma–Connettoma.

Asse verticale che sincronizza tre stati:
  Genotipo  →  CognitiveGenome
  Epigenotipo → EpigeneticTagsManager / AdaptiveExpressionEngine
  Connettoma  → RegionConnectome + TopologyHistory

Chiude il ciclo a cinque stadi:
  Genotipo ↔ Epigenotipo ↔ Connettoma ↔ Attivita Cognitiva ↔ Esperienza
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from speace_core.cellular_brain.cells.cellular_epigenetic_adapter import (
    CellularEpigeneticAdapter,
    CellularEpigeneticResult,
    NodeTopologyData,
)
from speace_core.cellular_brain.regions.region_connectome import RegionConnectome
from speace_core.cellular_brain.regions.region_registry import RegionRegistry
from speace_core.dna.cognitive_genome import CognitiveGenome
from speace_core.dna.models import ConnectomeGeneSet
from speace_core.organism_observer.topology_history import TopologyHistory

logger = logging.getLogger("speace.genome_connectome_axis")


@dataclass
class AdaptiveCognitiveState:
    """Vista unificata dello stato corrente dell'asse Genoma-Connettoma."""
    genotype_signature: str = ""
    epigenetic_modifier: float = 1.0
    connectome_density: float = 0.0
    modularity: float = 0.0
    global_efficiency: float = 0.0
    small_world_sigma: float = 0.0
    active_plasticity: float = 0.0
    adaptation_score: float = 0.0
    tick: int = 0


class GenomeConnectomeAxis:
    """Coordinatore dell'asse Genoma–Connettoma.

    Responsabilita':
    1. Applicare i geni del connettoma (ConnectomeGeneSet) alla struttura
    2. Fornire metriche topologiche all'espressione genica cellulare
    3. Salvare/ripristinare morphologial genomes basati su fitness
    4. Fornire una vista unificata (AdaptiveCognitiveState) agli AGI agents

    Usage:
        axis = GenomeConnectomeAxis(genome, registry)
        axis.sync(tick=current_tick)
        state = axis.get_state()
    """

    def __init__(
        self,
        genome: CognitiveGenome,
        registry: RegionRegistry,
        topology_history: Optional[TopologyHistory] = None,
        epigenetic_adapter: Optional[CellularEpigeneticAdapter] = None,
    ):
        self.genome = genome
        self.registry = registry
        self.topology_history = topology_history
        self.epigenetic_adapter = epigenetic_adapter

        self._last_state: AdaptiveCognitiveState = AdaptiveCognitiveState()
        self._sync_count: int = 0

    # ------------------------------------------------------------------ #
    # Sincronizzazione principale
    # ------------------------------------------------------------------ #

    def sync(self, tick: int = 0) -> AdaptiveCognitiveState:
        """Esegue una sincronizzazione completa dell'asse.

        1. Legge i geni del connettoma dal genoma (modulati da epigenetica)
        2. Applica i geni alla struttura del connettoma
        3. Calcola le metriche topologiche correnti
        4. Se disponibile, invia i dati topologici all'adattatore epigenetico
        5. Restituisce una vista unificata dello stato
        """
        self._sync_count += 1

        # 1. Leggi i geni del connettoma modulati da epigenetica
        effective_genes = self._get_effective_connectome_genes()

        # 2. Applica i geni al connettoma
        added = 0
        if self.registry and self.registry.connectome:
            added = self.registry.connectome.apply_genome_genes(effective_genes)

        # 3. Calcola metriche topologiche
        topo_metrics = self._compute_topology_metrics()

        # 4. Prepara i dati topologici per cella (se adattatore disponibile)
        topology_per_cell = self._build_topology_per_cell(topo_metrics)

        # 5. Costruisci stato unificato
        state = AdaptiveCognitiveState(
            genotype_signature=f"gen_{self.genome.generation}",
            epigenetic_modifier=self._compute_global_epigenetic_modifier(),
            connectome_density=topo_metrics.get("density", 0.0),
            modularity=topo_metrics.get("modularity_q", 0.0),
            global_efficiency=topo_metrics.get("global_efficiency", 0.0),
            small_world_sigma=topo_metrics.get("small_world_sigma", 0.0),
            active_plasticity=effective_genes.plasticity,
            adaptation_score=self._compute_adaptation_score(topo_metrics),
            tick=tick,
        )

        self._last_state = state
        return state

    # ------------------------------------------------------------------ #
    # Topology data for cellular epigenetic adapter
    # ------------------------------------------------------------------ #

    def build_topology_per_cell(
        self, circuit
    ) -> Dict[str, NodeTopologyData]:
        """Costruisce dati topologici per ogni cella basati sul connettoma.

        Chiamato dall'esterno per passare i topology_per_cell
        a CellularEpigeneticAdapter.adapt().
        """
        topo_metrics = self._compute_topology_metrics()
        return self._build_topology_per_cell(topo_metrics)

    def _build_topology_per_cell(
        self, topo_metrics: Dict[str, Any]
    ) -> Dict[str, NodeTopologyData]:
        """Costruisce mappa cell_id → NodeTopologyData dalle metriche globali."""
        degree_c = topo_metrics.get("degree_centrality", {})
        clustering_c = topo_metrics.get("clustering_coefficient", {})
        betweenness = topo_metrics.get("betweenness_centrality", {})

        topology_per_cell: Dict[str, NodeTopologyData] = {}

        # Identifica hub e bridge
        hubs_data = topo_metrics.get("hubs", {})
        broadcasters = {h["node"] for h in hubs_data.get("broadcasters", [])}
        collectors = {h["node"] for h in hubs_data.get("collectors", [])}
        bridges = {h["node"] for h in hubs_data.get("bridges", [])}

        for node_id in degree_c:
            deg_info = degree_c.get(node_id, {})
            total_deg = deg_info.get("total_degree", 0.0)
            clust = clustering_c.get(node_id, 0.0)
            btwn = betweenness.get(node_id, 0.0)

            topology_per_cell[node_id] = NodeTopologyData(
                centrality=total_deg,
                clustering=clust,
                efficiency=1.0 / max(1.0, btwn + 0.1),
                degree=int(total_deg * 100),
                community_size=topo_metrics.get("n_communities", 1),
                is_hub=node_id in broadcasters or node_id in collectors,
                is_bridge=node_id in bridges,
                overload=total_deg * 0.5 + btwn * 0.5,
            )

        return topology_per_cell

    # ------------------------------------------------------------------ #
    # Supporto MorphologicalGenome
    # ------------------------------------------------------------------ #

    def save_morphological_genome(
        self, tick: int, fitness: float
    ) -> bool:
        """Salva la topologia corrente come MorphologicalGenome se fitness sufficiente."""
        if not self.topology_history or not self.registry:
            return False

        snapshot = self.topology_history.last()
        if snapshot is None:
            return False

        record = self.topology_history.save_morphological_genome(snapshot, fitness)
        return record is not None

    def find_matching_morphological_genome(
        self, min_similarity: float = 0.8
    ) -> Optional[Dict[str, Any]]:
        """Cerca un MorphologicalGenome che corrisponda alla topologia corrente."""
        if not self.topology_history:
            return None

        snapshot = self.topology_history.last()
        if snapshot is None:
            return None

        match = self.topology_history.recall_morphological_genome(
            snapshot, min_similarity=min_similarity
        )
        if match is None:
            return None

        return {
            "matched_record": match,
            "similarity": match.similarity_to(
                type(match)(
                    timestamp=snapshot.timestamp,
                    tick=snapshot.tick,
                    fitness=0.0,
                    modularity=snapshot.modularity_q,
                    global_efficiency=snapshot.global_efficiency,
                    small_world_sigma=snapshot.small_world_sigma,
                    density=snapshot.density,
                    avg_clustering=snapshot.avg_clustering,
                    n_communities=snapshot.n_communities,
                )
            ),
        }

    # ------------------------------------------------------------------ #
    # Metodi interni
    # ------------------------------------------------------------------ #

    def _get_effective_connectome_genes(self) -> ConnectomeGeneSet:
        """Legge i geni del connettoma modulati dall'epigenetica."""
        modifier = self._compute_global_epigenetic_modifier()
        return self.genome.shared.get_effective_connectome_genes(modifier)

    def _compute_global_epigenetic_modifier(self) -> float:
        """Calcola un modificatore epigenetico globale."""
        modifier = 1.0
        for gene in ["connectivity_density", "hub_formation", "modularity", "plasticity",
                      "long_range_connections", "memory_consolidation", "small_world_bias",
                      "redundancy", "exploration"]:
            mod = self.genome.epigenome.get_expression_modifier(gene)
            modifier = min(modifier, mod)
        return modifier

    def _compute_topology_metrics(self) -> Dict[str, Any]:
        """Recupera le metriche topologiche correnti."""
        if self.topology_history:
            snapshot = self.topology_history.last()
            if snapshot:
                return {
                    "density": snapshot.density,
                    "modularity_q": snapshot.modularity_q,
                    "global_efficiency": snapshot.global_efficiency,
                    "small_world_sigma": snapshot.small_world_sigma,
                    "n_communities": snapshot.n_communities,
                    "avg_clustering": snapshot.avg_clustering,
                    "degree_centrality": snapshot.raw.get("degree_centrality", {}),
                    "clustering_coefficient": snapshot.raw.get("clustering_coefficient", {}),
                    "betweenness_centrality": snapshot.raw.get("betweenness_centrality", {}),
                    "hubs": {
                        "broadcasters": snapshot.top_broadcasters,
                        "collectors": snapshot.top_collectors,
                        "bridges": snapshot.top_bridges,
                    },
                }
        return {}

    def _compute_adaptation_score(self, metrics: Dict[str, Any]) -> float:
        """Calcola un punteggio di adattamento basato sulle metriche globali."""
        score = 0.0
        score += metrics.get("global_efficiency", 0.0) * 0.3
        score += min(1.0, metrics.get("modularity_q", 0.0) * 0.3)
        sw = metrics.get("small_world_sigma", 1.0)
        score += min(1.0, sw / 3.0) * 0.2
        score += metrics.get("density", 0.0) * 0.2
        return min(1.0, score)

    # ------------------------------------------------------------------ #
    # Query
    # ------------------------------------------------------------------ #

    def get_state(self) -> AdaptiveCognitiveState:
        return self._last_state

    def summary(self) -> Dict[str, Any]:
        state = self._last_state
        return {
            "sync_count": self._sync_count,
            "genotype_generation": self.genome.generation,
            "state": {
                "genotype_signature": state.genotype_signature,
                "epigenetic_modifier": round(state.epigenetic_modifier, 4),
                "connectome_density": round(state.connectome_density, 4),
                "modularity": round(state.modularity, 4),
                "global_efficiency": round(state.global_efficiency, 4),
                "small_world_sigma": round(state.small_world_sigma, 4),
                "active_plasticity": round(state.active_plasticity, 4),
                "adaptation_score": round(state.adaptation_score, 4),
            },
            "morphological_genomes": (
                self.topology_history.get_morphological_genome_count()
                if self.topology_history else 0
            ),
        }
