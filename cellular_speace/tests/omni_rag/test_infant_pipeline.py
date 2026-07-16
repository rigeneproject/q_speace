"""Integration test for Infant SensorBus → Omni-RAG pipeline.

This test wires the InfantSensorCollector output directly into the
CognitiveGraph to ensure the end-to-end flow (collect → node → graph)
is functional.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from speace_core.omni_rag.collectors.infant_sensor_collector import (
    InfantSensorCollector,
    InfantSensorConfig,
)
from speace_core.omni_rag.graph import CognitiveGraph
from speace_core.omni_rag.models import CognitiveNode, NodeType
from speace_core.omni_rag.persistence.graph_store import GraphStore


def _setup_data_root(root: Path) -> None:
    """Create 5 stub source files to simulate a real SPEACE install."""
    # 1. data/logs/foo.log
    logs_dir = root / "data" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "foo.log").write_text("test line\n")
    (logs_dir / "gateway_20260630.log").write_text("gateway test\n")
    # 2. data/agi_team/health_alerts.jsonl
    agi_dir = root / "data" / "agi_team"
    agi_dir.mkdir(parents=True, exist_ok=True)
    (agi_dir / "health_alerts.jsonl").write_text(
        json.dumps({"severity": "info", "module": "test"}) + "\n"
    )
    # 3. data/omni_rag/nodes.jsonl + edges.jsonl
    omni_dir = root / "data" / "omni_rag"
    omni_dir.mkdir(parents=True, exist_ok=True)
    (omni_dir / "nodes.jsonl").write_text("{}\n" * 5)
    (omni_dir / "edges.jsonl").write_text("{}\n" * 3)


def test_end_to_end_infant_to_graph(tmp_path):
    _setup_data_root(tmp_path)

    cfg = InfantSensorConfig()
    collector = InfantSensorCollector(data_dir=str(tmp_path / "data"), config=cfg)
    nodes, _ = collector.collect()
    assert len(nodes) >= 5, f"expected >= 5 infant nodes, got {len(nodes)}"

    # Add them to a CognitiveGraph. Use a clean per-test store so the
    # assertion is exact (the default store would include any pre-existing
    # project-wide nodes).
    graph = CognitiveGraph(GraphStore(data_dir=str(tmp_path / "data" / "omni_rag")))
    for n in nodes:
        graph.add_node(n)

    # Verify by-tag retrieval.
    infant_nodes = graph.get_nodes_by_tag("cognitive_infant")
    assert len(infant_nodes) == len(nodes)

    # Verify by source-tag retrieval.
    for source in ("runtime", "fslog", "gwlog", "health", "omni_delta"):
        tagged = graph.get_nodes_by_tag(f"infant_source:{source}")
        # All sensors should have at least one node (graceful skip emits too).
        assert len(tagged) >= 1, f"missing {source} sensor nodes"


def test_infant_performance_under_30_seconds(tmp_path):
    _setup_data_root(tmp_path)
    cfg = InfantSensorConfig()
    start = time.time()
    InfantSensorCollector(data_dir=str(tmp_path / "data"), config=cfg).collect()
    elapsed = time.time() - start
    assert elapsed < 30.0, f"pipeline took {elapsed:.2f}s, must be < 30s"


def test_infant_nodes_have_correct_node_type(tmp_path):
    _setup_data_root(tmp_path)
    cfg = InfantSensorConfig()
    nodes, _ = InfantSensorCollector(
        data_dir=str(tmp_path / "data"), config=cfg
    ).collect()
    for node in nodes:
        assert node.node_type == NodeType.RUNTIME_EVENT, (
            f"node {node.id} has wrong node_type: {node.node_type}"
        )


def test_infant_sources_are_distinct(tmp_path):
    _setup_data_root(tmp_path)
    cfg = InfantSensorConfig()
    nodes, _ = InfantSensorCollector(
        data_dir=str(tmp_path / "data"), config=cfg
    ).collect()
    sources = sorted({n.metadata["infant_source"] for n in nodes})
    assert sources == sorted(
        ["runtime", "fslog", "gwlog", "health", "omni_delta"]
    ), f"sources: {sources}"