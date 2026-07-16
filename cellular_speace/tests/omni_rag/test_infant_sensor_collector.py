"""Tests for the Cognitive Infant SensorBus (T173/C2)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from speace_core.omni_rag.collectors.infant_sensor_collector import (
    INFANT_SOURCES,
    InfantSensorCollector,
    InfantSensorConfig,
)


# --------------------------------------------------------------------------- #
# 1. Basic smoke — collect with default config
# --------------------------------------------------------------------------- #


def test_collector_emits_at_least_one_node_per_enabled_sensor(tmp_path):
    """Each enabled sensor emits at least one node, even when the
    underlying source is missing (graceful skip with a note)."""
    # Set up a real data/ subtree so filesystem watchers can find files.
    (tmp_path / "data" / "logs").mkdir(parents=True)
    (tmp_path / "data" / "logs" / "stub.log").write_text("x\n")
    (tmp_path / "data" / "agi_team").mkdir(parents=True)
    (tmp_path / "data" / "agi_team" / "health_alerts.jsonl").write_text("{}\n")
    (tmp_path / "data" / "omni_rag").mkdir(parents=True)
    (tmp_path / "data" / "omni_rag" / "nodes.jsonl").write_text("{}\n")

    cfg = InfantSensorConfig()  # all enabled
    collector = InfantSensorCollector(data_dir=str(tmp_path / "data"), config=cfg)
    nodes, edges = collector.collect()
    # The number of nodes is >= number of enabled sensors; sensors may
    # emit multiple nodes (e.g. fslog emits one per file).
    assert len(nodes) >= 5
    assert edges == []
    # And each enabled source is represented at least once.
    sources = {n.metadata["infant_source"] for n in nodes}
    assert {"runtime", "fslog", "gwlog", "health", "omni_delta"}.issubset(sources)


def test_collector_nodes_have_cognitive_infant_tag(tmp_path):
    cfg = InfantSensorConfig()
    collector = InfantSensorCollector(data_dir=str(tmp_path), config=cfg)
    nodes, _ = collector.collect()
    for node in nodes:
        assert "cognitive_infant" in node.tags, (
            f"node {node.id} missing 'cognitive_infant' tag"
        )
        assert "cognitive_factor:observation" in node.tags, (
            f"node {node.id} missing 'cognitive_factor:observation' tag"
        )


def test_collector_nodes_have_distinct_infant_source_tags(tmp_path):
    """All 5 sources must be present when data is available."""
    (tmp_path / "data" / "logs").mkdir(parents=True)
    (tmp_path / "data" / "logs" / "stub.log").write_text("x\n")
    (tmp_path / "data" / "agi_team").mkdir(parents=True)
    (tmp_path / "data" / "agi_team" / "health_alerts.jsonl").write_text("{}\n")
    (tmp_path / "data" / "omni_rag").mkdir(parents=True)
    (tmp_path / "data" / "omni_rag" / "nodes.jsonl").write_text("{}\n")
    cfg = InfantSensorConfig()
    collector = InfantSensorCollector(data_dir=str(tmp_path / "data"), config=cfg)
    nodes, _ = collector.collect()
    sources = set()
    for node in nodes:
        assert "infant_source" in node.metadata, (
            f"node {node.id} missing 'infant_source' metadata"
        )
        sources.add(node.metadata["infant_source"])
    # All five sources should be represented.
    assert sources == set(INFANT_SOURCES), f"missing sources: {set(INFANT_SOURCES) - sources}"


# --------------------------------------------------------------------------- #
# 2. Disable sensors
# --------------------------------------------------------------------------- #


def test_collector_with_only_filesystem_watch(tmp_path):
    cfg = InfantSensorConfig(
        enable_runtime_event_stream=False,
        enable_filesystem_watch=True,
        enable_gateway_log_stream=False,
        enable_health_alerts_watch=False,
        enable_omni_rag_index_delta=False,
    )
    collector = InfantSensorCollector(data_dir=str(tmp_path), config=cfg)
    nodes, _ = collector.collect()
    sources = {n.metadata["infant_source"] for n in nodes}
    # Only fslog should appear, *and* only if there's at least one log file.
    # The empty tmp_path has no logs, so we get no nodes.
    assert sources.issubset({"fslog"})
    assert "runtime" not in sources
    assert "gwlog" not in sources
    assert "health" not in sources
    assert "omni_delta" not in sources


def test_collector_with_all_disabled_emits_nothing(tmp_path):
    cfg = InfantSensorConfig(
        enable_runtime_event_stream=False,
        enable_filesystem_watch=False,
        enable_gateway_log_stream=False,
        enable_health_alerts_watch=False,
        enable_omni_rag_index_delta=False,
    )
    collector = InfantSensorCollector(data_dir=str(tmp_path), config=cfg)
    nodes, _ = collector.collect()
    assert nodes == []


# --------------------------------------------------------------------------- #
# 3. Real sources are read correctly
# --------------------------------------------------------------------------- #


def test_filesystem_watch_finds_real_log(tmp_path):
    logs_dir = tmp_path / "data" / "logs"
    logs_dir.mkdir(parents=True)
    log_file = logs_dir / "test.log"
    log_file.write_text("hello world\n")
    # InfantSensorCollector expects `data_dir` to be the root containing
    # logs/ — so point it at our synthetic root.
    cfg = InfantSensorConfig(
        enable_runtime_event_stream=False,
        enable_filesystem_watch=True,
        enable_gateway_log_stream=False,
        enable_health_alerts_watch=False,
        enable_omni_rag_index_delta=False,
    )
    collector = InfantSensorCollector(data_dir=str(tmp_path / "data"), config=cfg)
    nodes, _ = collector.collect()
    assert any(
        n.metadata["infant_source"] == "fslog"
        and n.metadata.get("path", "").endswith("test.log")
        for n in nodes
    ), f"expected fslog node for test.log, got {[n.metadata for n in nodes]}"


def test_health_alerts_watch_finds_real_file(tmp_path):
    alerts_path = tmp_path / "data" / "agi_team" / "health_alerts.jsonl"
    alerts_path.parent.mkdir(parents=True)
    alerts_path.write_text(
        json.dumps({"severity": "warning", "module": "test"}) + "\n"
        + json.dumps({"severity": "info", "module": "test"}) + "\n"
    )
    cfg = InfantSensorConfig(
        enable_runtime_event_stream=False,
        enable_filesystem_watch=False,
        enable_gateway_log_stream=False,
        enable_health_alerts_watch=True,
        enable_omni_rag_index_delta=False,
    )
    collector = InfantSensorCollector(data_dir=str(tmp_path / "data"), config=cfg)
    nodes, _ = collector.collect()
    health_nodes = [n for n in nodes if n.metadata["infant_source"] == "health"]
    assert health_nodes
    assert health_nodes[0].metadata["line_count"] == 2
    assert health_nodes[0].metadata["sample_last"]["severity"] == "info"


def test_omni_rag_index_delta_counts_lines(tmp_path):
    omni_dir = tmp_path / "data" / "omni_rag"
    omni_dir.mkdir(parents=True)
    (omni_dir / "nodes.jsonl").write_text("{}\n" * 7 + "{}\n")
    (omni_dir / "edges.jsonl").write_text("{}\n" * 3 + "{}\n")
    cfg = InfantSensorConfig(
        enable_runtime_event_stream=False,
        enable_filesystem_watch=False,
        enable_gateway_log_stream=False,
        enable_health_alerts_watch=False,
        enable_omni_rag_index_delta=True,
    )
    collector = InfantSensorCollector(data_dir=str(tmp_path / "data"), config=cfg)
    nodes, _ = collector.collect()
    assert len(nodes) == 1
    assert nodes[0].metadata["node_count"] == 8
    assert nodes[0].metadata["edge_count"] == 4


# --------------------------------------------------------------------------- #
# 4. Performance
# --------------------------------------------------------------------------- #


def test_collector_under_30_seconds(tmp_path):
    cfg = InfantSensorConfig()
    start = time.time()
    InfantSensorCollector(data_dir=str(tmp_path), config=cfg).collect()
    elapsed = time.time() - start
    assert elapsed < 30.0, f"collector took {elapsed:.2f}s, must be < 30s"


# --------------------------------------------------------------------------- #
# 5. Node IDs are unique within a run
# --------------------------------------------------------------------------- #


def test_node_ids_unique(tmp_path):
    cfg = InfantSensorConfig()
    collector = InfantSensorCollector(data_dir=str(tmp_path), config=cfg)
    nodes, _ = collector.collect()
    ids = [n.id for n in nodes]
    assert len(ids) == len(set(ids)), "duplicate node ids produced"


# --------------------------------------------------------------------------- #
# 6. Integration smoke with the OmniIndexer
# --------------------------------------------------------------------------- #


def test_indexer_accepts_infant_collector(tmp_path):
    """The collector must work without raising; OmniIndexer integration
    is exercised in `test_infant_pipeline.py`."""
    cfg = InfantSensorConfig()
    collector = InfantSensorCollector(data_dir=str(tmp_path), config=cfg)
    nodes, edges = collector.collect()
    assert isinstance(nodes, list)
    assert isinstance(edges, list)