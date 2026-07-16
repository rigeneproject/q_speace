"""MorphologicalMemory — memoria delle morfologie funzionali vincenti.

Conserva gli snapshot topologici associati a stati ad alta prestazione
(ILF elevato, performance positive). Permette di:

  - Registrare una morfologia con selezione probabilistica (soft selection)
  - Recuperare le top N morfologie per fitness composita
  - Retrieval per similarita' strutturale (firma spettrale 28 float)
  - Replay: perturbare il grafo corrente verso una morfologia passata
  - Dimenticare morfologie degeneranti
  - Persistere su JSONL per analisi successive

Obiettivo: trasformare l'evoluzione da
    prova → errore → dimentica
a
    prova → misura → salva morfologia vincente → ricombina → riutilizza
"""

from __future__ import annotations

import json
import math
import pathlib
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple

from speace_core.organism_observer.topology_history import TopologySnapshot
from speace_core.organism_observer.functional_graph import FunctionalGraph


# ------------------------------------------------------------------ #
# Constants
# ------------------------------------------------------------------ #

_EMBEDDING_DIM = 28
"""Firma spettrale leggera: 8 momenti grado out + 8 momento grado in
+ 4 clustering + 4 betweenness + 4 comunita'."""


@dataclass
class SavedMorphology:
    """Una morfologia funzionale salvata perche' associata a uno stato vincente."""

    morphology_id: str = ""
    saved_at: float = 0.0
    tick: int = 0
    fitness_score: float = 0.0
    save_probability: float = 0.0
    ilf_value: float = 0.0
    ari_score: float = 0.0

    # Topology snapshot fields
    node_count: int = 0
    edge_count: int = 0
    density: float = 0.0
    avg_clustering: float = 0.0
    global_efficiency: float = 0.0
    small_world_sigma: float = 0.0
    modularity_q: float = 0.0
    n_communities: int = 0

    # Hub structure snapshot
    top_broadcasters: List[Dict[str, Any]] = field(default_factory=list)
    top_collectors: List[Dict[str, Any]] = field(default_factory=list)
    top_bridges: List[Dict[str, Any]] = field(default_factory=list)

    # Context
    context_label: str = ""

    # Embedding strutturale per retrieval per similarita'
    embedding: List[float] = field(default_factory=list)

    # Raw degree/betweenness per reconstruction
    raw: Dict[str, Any] = field(default_factory=dict)

    # Etichette per ritrovamento
    tags: List[str] = field(default_factory=list)


class MorphologicalMemory:
    """Conserva e recupera morfologie funzionali vincenti.

    Usage::

        memory = MorphologicalMemory(
            persist_path="data/organism_observer/morphologies.jsonl"
        )

        # Dopo un sample della topology history
        saved = memory.record(
            snapshot=history.last(),
            ilf_value=0.82,
            ari_score=0.65,
            context_label="benchmark_arc",
        )
        if saved:
            print(f"Salvata morfologia {saved.morphology_id} "
                  f"(fitness={saved.fitness_score:.4f}, P={saved.save_probability:.3f})")

        # Retrieval per similarita' strutturale
        sim = memory.retrieve(snapshot=current, top_k=3)
        for morph, score in sim:
            print(f"  {morph.morphology_id}: cosine={score:.4f}")

        # Replay: inclina il grafo corrente verso una morfologia vincente
        memory.replay(morphology_id=best.morphology_id, graph=current_graph)
    """

    def __init__(
        self,
        persist_path: str = "data/organism_observer/morphologies.jsonl",
        max_morphologies: int = 1000,
        fitness_weights: Optional[Dict[str, float]] = None,
        soft_selection_exponent: float = 4.0,
        memory_energy_max: float = 10.0,
        memory_energy_decay_per_call: float = 0.03,
    ) -> None:
        self.persist_path = pathlib.Path(persist_path)
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_morphologies = max_morphologies
        self._morphologies: Dict[str, SavedMorphology] = {}

        # Pesi per il fitness composito (default: ILF-centrico)
        self.fitness_weights = fitness_weights or {
            "ilf": 0.40,
            "modularity": 0.20,
            "global_efficiency": 0.15,
            "clustering": 0.10,
            "small_world": 0.10,
            "ari": 0.05,
        }

        # Soft selection
        self.soft_selection_exponent = soft_selection_exponent

        # Memory energy budget — vincolo fisico simulato
        self.memory_energy_max = memory_energy_max
        self.memory_energy_decay_per_call = memory_energy_decay_per_call
        self._memory_energy: float = memory_energy_max
        self._total_save_attempts: int = 0
        self._total_saves: int = 0

        self._id_counter: int = 0

    # ------------------------------------------------------------------ #
    # Soft selection & energy
    # ------------------------------------------------------------------ #

    @property
    def memory_energy(self) -> float:
        return self._memory_energy

    @property
    def save_acceptance_rate(self) -> float:
        if self._total_save_attempts == 0:
            return 0.0
        return self._total_saves / self._total_save_attempts

    def _save_probability(self, fitness: float) -> float:
        """Probabilita' di salvataggio basata su soft selection.

        P = f^n / (f^n + (1-f)^n + epsilon)

        Con n=4: f=0.3 → P≈0.01, f=0.5 → P=0.5, f=0.8 → P=0.94
        """
        n = self.soft_selection_exponent
        if fitness <= 0.0:
            return 0.0
        if fitness >= 1.0:
            return 1.0
        f_n = fitness ** n
        one_minus_f_n = (1.0 - fitness) ** n
        return f_n / (f_n + one_minus_f_n + 1e-12)

    def _decay_energy(self) -> None:
        """Decadimento energetico a ogni tentativo di salvataggio."""
        self._memory_energy = max(
            0.0,
            self._memory_energy - self.memory_energy_decay_per_call,
        )

    def _recharge_energy(self, amount: Optional[float] = None) -> None:
        """Ricarica energia dopo un salvataggio riuscito."""
        self._memory_energy = min(
            self.memory_energy_max,
            self._memory_energy + (amount or self.memory_energy_max * 0.2),
        )

    # ------------------------------------------------------------------ #
    # Embedding
    # ------------------------------------------------------------------ #

    @staticmethod
    def _compute_embedding(snapshot: TopologySnapshot) -> List[float]:
        """Firma spettrale leggera (28 float) per retrieval strutturale.

        Composizione:
          - 8  momenti distribuzione out-degree  (mean, var, skew, kurt, min, max, Q1, Q3)
          - 8  momenti distribuzione in-degree   (idem)
          - 4  statistiche clustering coefficient
          - 4  statistiche betweenness centrality
          - 4  statistiche dimensione comunita'
        """
        emb: List[float] = []

        deg_out = [
            v.get("out_degree", 0)
            for v in snapshot.raw.get("degree_centrality", {}).values()
        ]
        deg_in = [
            v.get("in_degree", 0)
            for v in snapshot.raw.get("degree_centrality", {}).values()
        ]
        clust_vals = list(
            snapshot.raw.get("clustering_coefficient", {}).values()
        )
        between_vals = list(
            snapshot.raw.get("betweenness_centrality", {}).values()
        )
        comm_map = snapshot.raw.get("community_map", {})
        comm_sizes: List[int] = []
        if comm_map:
            from collections import Counter
            comm_sizes = list(Counter(comm_map.values()).values())

        # Momenti per una lista
        def _moments(vals: List[float], n: int) -> List[float]:
            if not vals:
                return [0.0] * n
            m = sum(vals) / len(vals)
            variance = sum((x - m) ** 2 for x in vals) / len(vals)
            std = math.sqrt(variance) if variance > 0 else 0.0
            skew = (
                sum((x - m) ** 3 for x in vals) / (len(vals) * (std ** 3))
                if std > 0 else 0.0
            )
            kurt = (
                sum((x - m) ** 4 for x in vals) / (len(vals) * (std ** 4)) - 3.0
                if std > 0 else 0.0
            )
            mn = min(vals)
            mx = max(vals)
            sorted_v = sorted(vals)
            q1 = sorted_v[len(sorted_v) // 4]
            q3 = sorted_v[3 * len(sorted_v) // 4]
            return [m, variance, skew, kurt, mn, mx, float(q1), float(q3)]

        emb.extend(_moments(deg_out, 8))
        emb.extend(_moments(deg_in, 8))
        emb.extend(_moments(clust_vals, 4)[:4])
        emb.extend(_moments(between_vals, 4)[:4])
        emb.extend(_moments(
            [float(c) for c in comm_sizes], 4
        )[:4])

        # Padding/truncation to _EMBEDDING_DIM
        if len(emb) < _EMBEDDING_DIM:
            emb.extend([0.0] * (_EMBEDDING_DIM - len(emb)))
        return emb[:_EMBEDDING_DIM]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        denom = max(na * nb, 1e-12)
        return max(-1.0, min(1.0, dot / denom))

    # ------------------------------------------------------------------ #
    # Recording
    # ------------------------------------------------------------------ #

    def record(
        self,
        snapshot: TopologySnapshot,
        ilf_value: float = 0.5,
        ari_score: float = 0.0,
        context_label: str = "",
        tags: Optional[List[str]] = None,
    ) -> Optional[SavedMorphology]:
        """Registra una morfologia con selezione probabilistica.

        La probabilita' di salvataggio e' proporzionale alla fitness
        (soft selection) e limitata dal memory energy budget.
        """
        self._total_save_attempts += 1
        self._decay_energy()

        fitness = self._compute_fitness(
            ilf=ilf_value,
            modularity_q=snapshot.modularity_q,
            global_efficiency=snapshot.global_efficiency,
            avg_clustering=snapshot.avg_clustering,
            small_world_sigma=snapshot.small_world_sigma,
            ari=ari_score,
        )

        # Soft selection
        p_save = self._save_probability(fitness)

        # Decisione: energia sufficiente e sorte favorevole
        if self._memory_energy <= 0.0:
            return None

        if p_save < 1.0:
            # Deterministic roll against probability
            roll = (hash(f"{time.time()}_{self._id_counter}") & 0xFFFF) / 65536.0
            roll = abs(roll)
            if roll > p_save:
                return None

        # Salvataggio
        self._id_counter += 1
        morphology_id = f"morph_{self._id_counter:06d}_{int(time.time())}"
        self._recharge_energy()
        self._total_saves += 1

        embedding = self._compute_embedding(snapshot)

        saved = SavedMorphology(
            morphology_id=morphology_id,
            saved_at=snapshot.timestamp,
            tick=snapshot.tick,
            fitness_score=round(fitness, 6),
            save_probability=round(p_save, 6),
            ilf_value=ilf_value,
            ari_score=ari_score,
            node_count=snapshot.node_count,
            edge_count=snapshot.edge_count,
            density=snapshot.density,
            avg_clustering=snapshot.avg_clustering,
            global_efficiency=snapshot.global_efficiency,
            small_world_sigma=snapshot.small_world_sigma,
            modularity_q=snapshot.modularity_q,
            n_communities=snapshot.n_communities,
            top_broadcasters=snapshot.top_broadcasters,
            top_collectors=snapshot.top_collectors,
            top_bridges=snapshot.top_bridges,
            context_label=context_label,
            embedding=embedding,
            raw={
                "degree_centrality": snapshot.raw.get("degree_centrality", {}),
                "betweenness_centrality": snapshot.raw.get("betweenness_centrality", {}),
                "clustering_coefficient": snapshot.raw.get("clustering_coefficient", {}),
                "community_map": snapshot.raw.get("community_map", {}),
            },
            tags=tags or [],
        )

        self._morphologies[morphology_id] = saved
        self._trim()
        return saved

    # ------------------------------------------------------------------ #
    # Retrieval per similarita' strutturale
    # ------------------------------------------------------------------ #

    def retrieve(
        self,
        snapshot: TopologySnapshot,
        top_k: int = 5,
        min_fitness: float = 0.0,
        context_filter: Optional[str] = None,
    ) -> List[Tuple[SavedMorphology, float]]:
        """Recupera morfologie simili per embedding strutturale.

        Args:
            snapshot: Snapshot corrente da confrontare.
            top_k: Numero massimo di risultati.
            min_fitness: Fitness minima per filtrare.
            context_filter: Filtra per contesto (es. "benchmark_arc").

        Returns:
            Lista di (morfologia, cosine_similarity) ordinate per similarita'.
        """
        query_emb = self._compute_embedding(snapshot)

        candidates: List[Tuple[SavedMorphology, float]] = []
        for morph in self._morphologies.values():
            if morph.fitness_score < min_fitness:
                continue
            if context_filter and morph.context_label != context_filter:
                continue
            if not morph.embedding:
                continue
            sim = self._cosine_similarity(query_emb, morph.embedding)
            candidates.append((morph, sim))

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_k]

    # ------------------------------------------------------------------ #
    # Replay — perturbazione del grafo verso morfologia passata
    # ------------------------------------------------------------------ #

    def replay(
        self,
        morphology_id: str,
        graph: FunctionalGraph,
        influence_strength: float = 0.15,
        min_edge_weight: float = 1.0,
    ) -> int:
        """Perturba il grafo corrente inclinandolo verso una morfologia salvata.

        Per ogni arco che esisteva nella morfologia passata ma e' debole
        o assente nel grafo corrente, ne aumenta il peso simulando eventi.

        Questo e' l'embrione del 'condiziona → rigenera':
        la memoria non accumola, ma inclina la probabilita' delle
        connessioni future.

        Args:
            morphology_id: ID della morfologia da riattivare.
            graph: FunctionalGraph corrente da perturbare.
            influence_strength: Frazione di eventi simulati da iniettare.
            min_edge_weight: Peso minimo per considerare un arco presente.

        Returns:
            Numero di archi perturbati.
        """
        morph = self._morphologies.get(morphology_id)
        if morph is None:
            return 0

        # Ricostruisce l'insieme di archi della morfologia salvata
        # dal raw degree centrality (abbiamo source→target mapping)
        saved_edges: Set[Tuple[str, str]] = set()
        dc = morph.raw.get("degree_centrality", {})
        # degree_centrality contiene out_neighbors per ogni nodo?
        # No, contiene solo out_degree/in_degree come scalari.
        # Dobbiamo ricostruire gli archi dai top broadcasters/collectors
        # oppure dal community_map se etichettato per coppia.

        # Strategia: usa top broadcasters/collectors/bridges come proxy
        # degli hub, e perturba solo archi che coinvolgono questi hub.
        hub_nodes: Set[str] = set()
        for hub_list in [morph.top_broadcasters, morph.top_collectors, morph.top_bridges]:
            for h in hub_list:
                node = h.get("node", "")
                if node:
                    hub_nodes.add(node)

        # Se non abbiamo abbastanza hub, usa tutti i nodi noti
        if len(hub_nodes) < 2:
            hub_nodes = set(dc.keys())

        # Per ogni coppia di hub, se il grafo corrente non ha l'arco
        # (o ha peso < min_edge_weight), simula un evento per inclinare
        graph.build()
        current_edges = {(s, t) for (s, t) in graph._edges.keys()}

        perturbed = 0
        for src in hub_nodes:
            for tgt in hub_nodes:
                if src == tgt:
                    continue
                key = (src, tgt)
                current_weight = 0.0
                if key in graph._edges:
                    current_weight = graph._edges[key].weight

                if current_weight < min_edge_weight:
                    # Simula influence_strength × avg_frequency eventi
                    fake_count = max(1, int(influence_strength * 10))
                    for _ in range(fake_count):
                        graph.collector.record(
                            source=src,
                            target=tgt,
                            latency_ms=1.0,
                            message_type="morphology_replay",
                            success=True,
                        )
                    perturbed += 1

        return perturbed

    # ------------------------------------------------------------------ #
    # Cross-fertilization — ricombinazione di morfologie
    # ------------------------------------------------------------------ #

    def cross_fertilize(
        self,
        morph_id_a: str,
        morph_id_b: str,
        graph: FunctionalGraph,
        blend_ratio: float = 0.5,
        influence_strength: float = 0.15,
        min_edge_weight: float = 1.0,
    ) -> Dict[str, Any]:
        """Combina due morfologie per generare una topologia ibrida.

        Per ogni morfologia, calcola gli hub unici e applica replay
        con intensita' scalata da blend_ratio. Il grafo risultante
        sara' inclinato verso entrambe le morfologie ancestrali.

        Args:
            morph_id_a: Prima morfologia parentale.
            morph_id_b: Seconda morfologia parentale.
            graph: FunctionalGraph corrente da perturbare.
            blend_ratio: Peso della prima morfologia (0.0 = solo B, 1.0 = solo A).
            influence_strength: Intensita' base del replay.
            min_edge_weight: Peso minimo arco per considerarlo presente.

        Returns:
            Dict con risultati dell'incrocio.
        """
        morph_a = self._morphologies.get(morph_id_a)
        morph_b = self._morphologies.get(morph_id_b)
        if morph_a is None or morph_b is None:
            return {"success": False, "reason": "Morphology not found"}

        blend_ratio = max(0.0, min(1.0, blend_ratio))

        # Embedding ibrido (media pesata)
        if morph_a.embedding and morph_b.embedding:
            hybrid_emb = [
                blend_ratio * a + (1.0 - blend_ratio) * b
                for a, b in zip(morph_a.embedding, morph_b.embedding)
            ]
        else:
            hybrid_emb = morph_a.embedding or morph_b.embedding or []

        # Estrai hub unici per morfologia
        def _hub_set(morph: SavedMorphology) -> Set[str]:
            hubs: Set[str] = set()
            for hub_list in [morph.top_broadcasters, morph.top_collectors, morph.top_bridges]:
                for h in hub_list:
                    node = h.get("node", "")
                    if node:
                        hubs.add(node)
            if len(hubs) < 2:
                hubs = set(morph.raw.get("degree_centrality", {}).keys())
            return hubs

        hubs_a = _hub_set(morph_a)
        hubs_b = _hub_set(morph_b)

        # Hub specifici di ogni parente (non condivisi)
        only_a = hubs_a - hubs_b
        only_b = hubs_b - hubs_a

        # Replay pesato — archi unici di A con intensita' blend_ratio
        # archi unici di B con intensita' (1 - blend_ratio)
        graph.build()
        total_perturbed = 0

        for src in hubs_a:
            for tgt in hubs_a:
                if src == tgt:
                    continue
                key = (src, tgt)
                if key in graph._edges and graph._edges[key].weight >= min_edge_weight:
                    continue
                weight = blend_ratio if src in only_a or tgt in only_a else 1.0
                fake_count = max(1, int(influence_strength * weight * 10))
                for _ in range(fake_count):
                    graph.collector.record(
                        source=src,
                        target=tgt,
                        latency_ms=1.0,
                        message_type="morphology_cross",
                        success=True,
                    )
                total_perturbed += 1

        for src in hubs_b:
            for tgt in hubs_b:
                if src == tgt:
                    continue
                key = (src, tgt)
                if key in graph._edges and graph._edges[key].weight >= min_edge_weight:
                    continue
                weight = (1.0 - blend_ratio) if src in only_b or tgt in only_b else 1.0
                fake_count = max(1, int(influence_strength * weight * 10))
                for _ in range(fake_count):
                    graph.collector.record(
                        source=src,
                        target=tgt,
                        latency_ms=1.0,
                        message_type="morphology_cross",
                        success=True,
                    )
                total_perturbed += 1

        return {
            "success": True,
            "parent_a": morph_id_a,
            "parent_b": morph_id_b,
            "blend_ratio": blend_ratio,
            "hubs_a": len(hubs_a),
            "hubs_b": len(hubs_b),
            "hubs_only_a": len(only_a),
            "hubs_only_b": len(only_b),
            "perturbed_edges": total_perturbed,
            "hybrid_embedding": hybrid_emb,
        }

    # ------------------------------------------------------------------ #
    # Context-aware retrieval — recupero condizionato dal contesto
    # ------------------------------------------------------------------ #

    def context_aware_retrieval(
        self,
        snapshot: TopologySnapshot,
        context_label: str,
        graph: Optional[FunctionalGraph] = None,
        auto_replay: bool = True,
        influence_strength: float = 0.15,
        top_k: int = 3,
    ) -> Dict[str, Any]:
        """Recupera morfologie rilevanti per un dato contesto.

        Cerca prima per corrispondenza esatta di contesto (label),
        poi per similarita' strutturale (embedding) come fallback.
        Opzionalmente applica replay automatico della morfologia migliore.

        Args:
            snapshot: Snapshot topologico corrente.
            context_label: Contesto attuale (es. "benchmark_arc").
            graph: FunctionalGraph corrente (necessario per auto_replay).
            auto_replay: Se True, applica replay della morfologia migliore.
            influence_strength: Intensita' del replay.
            top_k: Numero di risultati da restituire.

        Returns:
            Dict con risultati del retrieval.
        """
        # 1. Cerca per contesto esatto
        exact_matches = self.find_by_context(context_label)
        exact_matches.sort(key=lambda m: m.fitness_score, reverse=True)

        # 2. Fallback per similarita' strutturale
        semantic_matches: List[Tuple[SavedMorphology, float]] = []
        if not exact_matches:
            semantic_matches = self.retrieve(
                snapshot=snapshot,
                top_k=top_k,
                min_fitness=0.0,
            )

        # 3. Seleziona la migliore
        best: Optional[SavedMorphology] = None
        match_type = ""
        if exact_matches:
            best = exact_matches[0]
            match_type = "exact_context"
            candidates = exact_matches[:top_k]
        elif semantic_matches:
            best = semantic_matches[0][0]
            match_type = "semantic_fallback"
            candidates = [m for m, _ in semantic_matches[:top_k]]
        else:
            return {
                "success": False,
                "reason": "No matching morphologies found",
                "context_label": context_label,
                "match_type": "none",
                "candidates": [],
                "auto_replay_applied": False,
            }

        # 4. Auto-replay
        replay_applied = False
        replay_count = 0
        if auto_replay and graph is not None and best is not None:
            replay_count = self.replay(
                morphology_id=best.morphology_id,
                graph=graph,
                influence_strength=influence_strength,
            )
            replay_applied = replay_count > 0

        return {
            "success": True,
            "context_label": context_label,
            "match_type": match_type,
            "best_morphology_id": best.morphology_id,
            "best_fitness": best.fitness_score,
            "best_ilf": best.ilf_value,
            "candidates": [
                {
                    "morphology_id": m.morphology_id,
                    "fitness_score": m.fitness_score,
                    "context_label": m.context_label,
                }
                for m in candidates
            ],
            "auto_replay_applied": replay_applied,
            "replay_edges_perturbed": replay_count,
        }

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #

    @property
    def count(self) -> int:
        return len(self._morphologies)

    def top(self, n: int = 10) -> List[SavedMorphology]:
        """Restituisce le N morfologie con fitness piu' alta."""
        sorted_items = sorted(
            self._morphologies.values(),
            key=lambda m: m.fitness_score,
            reverse=True,
        )
        return sorted_items[:n]

    def get(self, morphology_id: str) -> Optional[SavedMorphology]:
        return self._morphologies.get(morphology_id)

    def find_by_context(self, context_label: str) -> List[SavedMorphology]:
        return [
            m for m in self._morphologies.values()
            if m.context_label == context_label
        ]

    def find_by_tag(self, tag: str) -> List[SavedMorphology]:
        return [
            m for m in self._morphologies.values()
            if tag in m.tags
        ]

    def find_by_fitness_range(
        self, min_fitness: float = 0.0, max_fitness: float = 1.0
    ) -> List[SavedMorphology]:
        return [
            m for m in self._morphologies.values()
            if min_fitness <= m.fitness_score <= max_fitness
        ]

    def forget(self, morphology_id: str) -> bool:
        """Rimuove una morfologia dalla memoria."""
        if morphology_id in self._morphologies:
            del self._morphologies[morphology_id]
            return True
        return False

    def forget_below(self, threshold: float = 0.3) -> int:
        """Dimentica tutte le morfologie con fitness sotto soglia."""
        to_forget = [
            mid for mid, m in self._morphologies.items()
            if m.fitness_score < threshold
        ]
        for mid in to_forget:
            del self._morphologies[mid]
        return len(to_forget)

    def best(self) -> Optional[SavedMorphology]:
        """Restituisce la morfologia con fitness massima."""
        if not self._morphologies:
            return None
        return max(self._morphologies.values(), key=lambda m: m.fitness_score)

    def summary(self) -> Dict[str, Any]:
        best_m = self.best()
        return {
            "total_morphologies": len(self._morphologies),
            "best_fitness": best_m.fitness_score if best_m else None,
            "best_ilf": best_m.ilf_value if best_m else None,
            "best_modularity": best_m.modularity_q if best_m else None,
            "contexts": list({
                m.context_label for m in self._morphologies.values()
            }),
            "memory_energy": round(self._memory_energy, 4),
            "memory_energy_max": self.memory_energy_max,
            "save_acceptance_rate": round(self.save_acceptance_rate, 4),
            "total_save_attempts": self._total_save_attempts,
            "total_saves": self._total_saves,
            "persist_path": str(self.persist_path),
        }

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #

    def save(self, path: Optional[str] = None) -> int:
        """Salva tutte le morfologie su JSONL."""
        dst = pathlib.Path(path) if path else self.persist_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not self._morphologies:
            return 0
        count = 0
        try:
            with dst.open("w", encoding="utf-8") as f:
                for morph in self._morphologies.values():
                    line = {
                        "morphology_id": morph.morphology_id,
                        "saved_at": morph.saved_at,
                        "tick": morph.tick,
                        "fitness_score": morph.fitness_score,
                        "save_probability": morph.save_probability,
                        "ilf_value": morph.ilf_value,
                        "ari_score": morph.ari_score,
                        "node_count": morph.node_count,
                        "edge_count": morph.edge_count,
                        "density": morph.density,
                        "avg_clustering": morph.avg_clustering,
                        "global_efficiency": morph.global_efficiency,
                        "small_world_sigma": morph.small_world_sigma,
                        "modularity_q": morph.modularity_q,
                        "n_communities": morph.n_communities,
                        "top_broadcasters": morph.top_broadcasters,
                        "top_collectors": morph.top_collectors,
                        "top_bridges": morph.top_bridges,
                        "context_label": morph.context_label,
                        "embedding": morph.embedding,
                        "tags": morph.tags,
                    }
                    f.write(json.dumps(line) + "\n")
                    count += 1
            return count
        except OSError:
            return 0

    def load(self, path: Optional[str] = None) -> int:
        """Carica morfologie da JSONL."""
        src = pathlib.Path(path) if path else self.persist_path
        if not src.exists():
            return 0
        count = 0
        try:
            with src.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    mid = data.get("morphology_id", f"loaded_{count}")
                    if mid in self._morphologies:
                        continue
                    self._morphologies[mid] = SavedMorphology(
                        morphology_id=mid,
                        saved_at=data.get("saved_at", 0.0),
                        tick=data.get("tick", 0),
                        fitness_score=data.get("fitness_score", 0.0),
                        save_probability=data.get("save_probability", 0.0),
                        ilf_value=data.get("ilf_value", 0.0),
                        ari_score=data.get("ari_score", 0.0),
                        node_count=data.get("node_count", 0),
                        edge_count=data.get("edge_count", 0),
                        density=data.get("density", 0.0),
                        avg_clustering=data.get("avg_clustering", 0.0),
                        global_efficiency=data.get("global_efficiency", 0.0),
                        small_world_sigma=data.get("small_world_sigma", 0.0),
                        modularity_q=data.get("modularity_q", 0.0),
                        n_communities=data.get("n_communities", 0),
                        top_broadcasters=data.get("top_broadcasters", []),
                        top_collectors=data.get("top_collectors", []),
                        top_bridges=data.get("top_bridges", []),
                        context_label=data.get("context_label", ""),
                        embedding=data.get("embedding", []),
                        tags=data.get("tags", []),
                    )
                    self._id_counter = max(self._id_counter, count + 1)
                    count += 1
            return count
        except OSError:
            return 0

    # ------------------------------------------------------------------ #
    # Private
    # ------------------------------------------------------------------ #

    def _compute_fitness(
        self,
        ilf: float,
        modularity_q: float,
        global_efficiency: float,
        avg_clustering: float,
        small_world_sigma: float,
        ari: float = 0.0,
    ) -> float:
        """Calcola fitness composita pesata.

        Valori attesi normalizzati [0, 1] per ogni metrica.
        """
        w = self.fitness_weights

        # Modularity: Q > 0.5 e' buono, > 0.7 e' forte
        # Normalizza con sigmoid
        q_norm = 1.0 / (1.0 + math.exp(-10.0 * (modularity_q - 0.4)))

        # Global efficiency: gia' in [0, 1]
        eff_norm = max(0.0, min(1.0, global_efficiency))

        # Clustering: valori tipici 0.2-0.8, normalizza
        clust_norm = max(0.0, min(1.0, avg_clustering))

        # Small-world sigma: 2-8 e' goldilocks zone
        if small_world_sigma >= 2.0 and small_world_sigma <= 8.0:
            sw_norm = 1.0 - abs(small_world_sigma - 4.0) / 4.0
        elif small_world_sigma < 2.0:
            sw_norm = small_world_sigma / 2.0
        else:
            sw_norm = max(0.0, 1.0 - (small_world_sigma - 8.0) / 12.0)

        fitness = (
            w.get("ilf", 0.40) * max(0.0, min(1.0, ilf))
            + w.get("modularity", 0.20) * q_norm
            + w.get("global_efficiency", 0.15) * eff_norm
            + w.get("clustering", 0.10) * clust_norm
            + w.get("small_world", 0.10) * sw_norm
            + w.get("ari", 0.05) * max(0.0, min(1.0, ari))
        )

        return max(0.0, min(1.0, fitness))

    def _trim(self) -> None:
        """Rimuove le morfologie peggiori se si supera max_morphologies."""
        if len(self._morphologies) <= self.max_morphologies:
            return
        sorted_m = sorted(
            self._morphologies.values(),
            key=lambda m: m.fitness_score,
        )
        excess = len(sorted_m) - self.max_morphologies
        for m in sorted_m[:excess]:
            del self._morphologies[m.morphology_id]
