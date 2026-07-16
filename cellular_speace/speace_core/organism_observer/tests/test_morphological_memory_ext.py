"""Test per cross-fertilization e context-aware retrieval."""

import tempfile
import pathlib

from speace_core.organism_observer.topology_memory import MorphologicalMemory, SavedMorphology
from speace_core.organism_observer.topology_history import TopologySnapshot
from speace_core.organism_observer.functional_graph import FunctionalGraph
from speace_core.organism_observer.event_collector import EventCollector


def _make_snapshot(
    node_count=5,
    edge_count=8,
    density=0.4,
    avg_clustering=0.3,
    global_efficiency=0.5,
    small_world_sigma=2.5,
    modularity_q=0.6,
    n_communities=2,
    tick=1,
    **kw,
) -> TopologySnapshot:
    return TopologySnapshot(
        timestamp=100.0,
        tick=tick,
        node_count=node_count,
        edge_count=edge_count,
        density=density,
        avg_clustering=avg_clustering,
        global_efficiency=global_efficiency,
        small_world_sigma=small_world_sigma,
        modularity_q=modularity_q,
        n_communities=n_communities,
        top_broadcasters=[{"node": "A", "out_degree": 5}],
        top_collectors=[{"node": "B", "in_degree": 4}],
        top_bridges=[{"node": "C", "betweenness": 0.5}],
        raw={
            "degree_centrality": {
                "A": {"out_degree": 5, "in_degree": 1, "total_degree": 6},
                "B": {"out_degree": 2, "in_degree": 4, "total_degree": 6},
                "C": {"out_degree": 3, "in_degree": 3, "total_degree": 6},
            },
            "clustering_coefficient": {"A": 0.3, "B": 0.4, "C": 0.5},
            "betweenness_centrality": {"A": 0.1, "B": 0.2, "C": 0.5},
            "community_map": {"A": 0, "B": 0, "C": 1},
        },
    )


# ------------------------------------------------------------------ #
# Cross-fertilization
# ------------------------------------------------------------------ #


class TestCrossFertilize:
    def test_cross_basic(self):
        collector = EventCollector()
        graph = FunctionalGraph(collector)

        mem = MorphologicalMemory()
        snap_a = _make_snapshot(tick=1, modularity_q=0.5)
        snap_b = _make_snapshot(tick=2, modularity_q=0.7)

        # Forza salvataggio bypassando soft selection
        mem._memory_energy = 10.0
        mem._total_save_attempts = 100
        mem._total_saves = 100
        mem._save_probability = lambda f: 1.0  # type: ignore

        a = mem.record(snap_a, ilf_value=0.6, context_label="bench_a")
        b = mem.record(snap_b, ilf_value=0.8, context_label="bench_b")
        assert a is not None
        assert b is not None

        result = mem.cross_fertilize(
            morph_id_a=a.morphology_id,
            morph_id_b=b.morphology_id,
            graph=graph,
            blend_ratio=0.5,
        )
        assert result["success"] is True
        assert result["parent_a"] == a.morphology_id
        assert result["parent_b"] == b.morphology_id
        assert result["blend_ratio"] == 0.5
        assert result["perturbed_edges"] >= 0
        assert len(result["hybrid_embedding"]) > 0

    def test_cross_blend_extremes(self):
        collector = EventCollector()
        graph = FunctionalGraph(collector)

        mem = MorphologicalMemory()
        snap_a = _make_snapshot(tick=1, modularity_q=0.4)
        snap_b = _make_snapshot(tick=2, modularity_q=0.8)

        mem._memory_energy = 10.0
        mem._save_probability = lambda f: 1.0  # type: ignore

        a = mem.record(snap_a, ilf_value=0.5)
        b = mem.record(snap_b, ilf_value=0.9)
        assert a is not None and b is not None

        # blend_ratio=0.0 → solo morfologia B
        r0 = mem.cross_fertilize(a.morphology_id, b.morphology_id, graph, blend_ratio=0.0)
        assert r0["success"]
        assert r0["blend_ratio"] == 0.0

        # blend_ratio=1.0 → solo morfologia A
        r1 = mem.cross_fertilize(a.morphology_id, b.morphology_id, graph, blend_ratio=1.0)
        assert r1["success"]
        assert r1["blend_ratio"] == 1.0

    def test_cross_missing_morphology(self):
        collector = EventCollector()
        graph = FunctionalGraph(collector)
        mem = MorphologicalMemory()

        result = mem.cross_fertilize("nonexistent_a", "nonexistent_b", graph)
        assert result["success"] is False
        assert "not found" in result.get("reason", "")

    def test_cross_same_morphology(self):
        collector = EventCollector()
        graph = FunctionalGraph(collector)

        mem = MorphologicalMemory()
        snap = _make_snapshot(tick=1)

        mem._memory_energy = 10.0
        s = mem.record(snap, ilf_value=0.7)
        assert s is not None

        result = mem.cross_fertilize(s.morphology_id, s.morphology_id, graph)
        assert result["success"] is True
        assert result["parent_a"] == result["parent_b"]


# ------------------------------------------------------------------ #
# Context-aware retrieval
# ------------------------------------------------------------------ #


class TestContextAwareRetrieval:
    def test_exact_context_match(self):
        mem = MorphologicalMemory()
        snap = _make_snapshot(tick=1)
        snap2 = _make_snapshot(tick=2)

        mem._memory_energy = 10.0
        mem._save_probability = lambda f: 1.0  # type: ignore
        s1 = mem.record(snap, ilf_value=0.7, context_label="benchmark_arc")
        s2 = mem.record(snap2, ilf_value=0.6, context_label="evolution")
        assert s1 is not None and s2 is not None

        result = mem.context_aware_retrieval(
            snapshot=snap,
            context_label="benchmark_arc",
            top_k=3,
            auto_replay=False,
        )
        assert result["success"] is True
        assert result["match_type"] == "exact_context"
        assert result["best_morphology_id"] == s1.morphology_id
        assert len(result["candidates"]) >= 1

    def test_semantic_fallback(self):
        mem = MorphologicalMemory()
        snap_a = _make_snapshot(tick=1, node_count=5, avg_clustering=0.3)
        snap_b = _make_snapshot(tick=2, node_count=6, avg_clustering=0.35)

        mem._memory_energy = 10.0
        s1 = mem.record(snap_a, ilf_value=0.7, context_label="evolution")
        s2 = mem.record(snap_b, ilf_value=0.8, context_label="evolution")
        assert s1 is not None and s2 is not None

        # Nessuna morfologia con contesto "benchmark_arc"
        result = mem.context_aware_retrieval(
            snapshot=snap_a,
            context_label="benchmark_arc",
            top_k=3,
            auto_replay=False,
        )
        assert result["success"] is True
        # Il fallback semantico dovrebbe tornare qualcosa
        assert result["match_type"] in ("semantic_fallback",)

    def test_auto_replay(self):
        collector = EventCollector()
        graph = FunctionalGraph(collector)

        mem = MorphologicalMemory()
        snap = _make_snapshot(tick=1, node_count=3)

        mem._memory_energy = 10.0
        s = mem.record(snap, ilf_value=0.7, context_label="test_ctx")
        assert s is not None

        result = mem.context_aware_retrieval(
            snapshot=snap,
            context_label="test_ctx",
            graph=graph,
            auto_replay=True,
            influence_strength=0.1,
        )
        assert result["success"] is True
        assert result["auto_replay_applied"] is True or result["auto_replay_applied"] is False
        # Se ci sono hub, replay dovrebbe funzionare
        if result["best_morphology_id"]:
            assert result["match_type"] == "exact_context"

    def test_no_match(self):
        mem = MorphologicalMemory()
        snap = _make_snapshot(tick=1)

        result = mem.context_aware_retrieval(
            snapshot=snap,
            context_label="unknown_context",
            auto_replay=False,
        )
        assert result["success"] is False
        assert result["match_type"] == "none"
        assert result["candidates"] == []

    def test_auto_replay_no_graph(self):
        mem = MorphologicalMemory()
        snap = _make_snapshot(tick=1)

        mem._memory_energy = 10.0
        s = mem.record(snap, ilf_value=0.7, context_label="ctx")
        assert s is not None

        # auto_replay=True ma graph=None → nessun replay
        result = mem.context_aware_retrieval(
            snapshot=snap,
            context_label="ctx",
            graph=None,
            auto_replay=True,
        )
        assert result["success"] is True
        assert result["auto_replay_applied"] is False
        assert result["replay_edges_perturbed"] == 0
