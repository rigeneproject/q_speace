"""Test end-to-end del pipeline OFG: Collector → Graph → Metrics → History → Diff → Events."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from speace_core.organism_observer.event_collector import EventCollector
from speace_core.organism_observer.functional_graph import FunctionalGraph
from speace_core.organism_observer.topology_metrics import TopologyMetrics
from speace_core.organism_observer.topology_history import TopologyHistory
from speace_core.organism_observer.topology_diff import TopologyDiff
from speace_core.organism_observer.topology_events import TopologyEvents


def test_full_pipeline():
    with tempfile.TemporaryDirectory() as tmp:
        collector = EventCollector(persist_path=os.path.join(tmp, "events.jsonl"))

        # Popola con eventi simulati
        for src, tgt, cnt in [("A", "B", 5), ("B", "C", 3), ("A", "C", 2), ("C", "A", 1), ("B", "A", 4)]:
            for _ in range(cnt):
                collector.record(source=src, target=tgt, latency_ms=1.0, message_type="test", success=True)

        # FunctionalGraph
        g = FunctionalGraph(collector)
        g.build()

        # TopologyMetrics
        tm = TopologyMetrics(g)
        report = tm.compute_all()
        assert report["node_count"] == 3, f"Expected 3 nodes, got {report['node_count']}"
        assert report["edge_count"] > 0, "Expected > 0 edges"
        print(f"Nodi: {report['node_count']}, Archi: {report['edge_count']}")
        print(f"Q: {report['modularity']['Q']:.4f}, sigma: {report['small_world']['sigma']:.4f}")

        # TopologyHistory
        hist = TopologyHistory(g, persist_path=os.path.join(tmp, "history.jsonl"))
        s1 = hist.sample(tick=100)
        assert s1.node_count == 3, "Snapshot 1: expected 3 nodes"
        print(f"Snapshot 1: nodes={s1.node_count}, edges={s1.edge_count}")

        # Aggiungi nodo D
        collector.record(source="D", target="A", latency_ms=2.0, message_type="test", success=True)
        collector.record(source="D", target="B", latency_ms=2.0, message_type="test", success=True)
        collector.record(source="D", target="C", latency_ms=2.0, message_type="test", success=True)
        s2 = hist.sample(tick=200)
        assert s2.node_count == 4, "Snapshot 2: expected 4 nodes"
        print(f"Snapshot 2: nodes={s2.node_count}, edges={s2.edge_count}")

        # TopologyDiff
        delta = TopologyDiff.compute(s1, s2, prev_raw=s1.raw, cur_raw=s2.raw)
        assert delta.d_node_count > 0, "Expected nodes to increase"
        print(f"Delta nodes: {delta.d_node_count}, edges: {delta.d_edge_count}")
        print(f"Change velocity: {delta.change_velocity:.4f}")
        print(f"Entropy change: {delta.entropy_change:.4f}")
        print(f"Nodes appeared: {delta.nodes_appeared}")

        # TopologyEvents
        events = TopologyEvents(hist)
        n = events.record_series(ilf_history=[0.50, 0.55])
        assert n == 1, f"Expected 1 event, got {n}"
        print(f"Recorded events: {n}")

        report = events.report()
        assert report.n_events == 1, "Expected 1 event in report"
        print(f"Event report: n={report.n_events}, mean_d_ilf={report.mean_d_ilf:.4f}")
        print(f"  Positive correlations: {report.n_positive_correlation}")
        print(f"  Negative correlations: {report.n_negative_correlation}")

        # Salva e ricarica
        saved = hist.save()
        assert saved > 0, "Expected snapshots saved"
        print(f"Saved snapshots: {saved}")

        hist2 = TopologyHistory(g, persist_path=os.path.join(tmp, "history.jsonl"))
        loaded = hist2.load()
        assert loaded > 0, "Expected snapshots loaded"
        print(f"Loaded snapshots: {loaded}")

        summary = hist2.summary()
        assert summary["total_snapshots"] > 0, "Expected positive total"
        print(f"Summary: {summary['total_snapshots']} total snapshots")

        print()
        print("=== Pipeline OFG completa: OK ===")


if __name__ == "__main__":
    test_full_pipeline()
