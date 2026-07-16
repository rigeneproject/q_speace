"""Tests for Omni-RAG collectors."""

import tempfile
from pathlib import Path

import pytest

from speace_core.omni_rag.collectors.semantic_collector import SemanticCollector
from speace_core.omni_rag.collectors.arch_collector import ArchCollector
from speace_core.omni_rag.collectors.dna_collector import DNACollector
from speace_core.omni_rag.collectors.bcel_collector import BCELCollector


class TestSemanticCollector:
    def test_collect_finds_documents(self):
        collector = SemanticCollector(base_paths=["docs"])
        nodes = collector.collect()
        assert len(nodes) > 0
        doc_nodes = [n for n in nodes if n.node_type.value == "document"]
        assert len(doc_nodes) > 0

    def test_keyword_search(self):
        collector = SemanticCollector(base_paths=["docs"])
        collector.collect()
        results = collector.get_keyword_results("BCEL")
        assert len(results) >= 1

    def test_tokenize(self):
        collector = SemanticCollector()
        tokens = collector._tokenize("Hello World BCEL Integration")
        assert "hello" in tokens
        assert "world" in tokens
        assert "bcel" in tokens


class TestArchCollector:
    def test_collect_finds_modules(self):
        collector = ArchCollector(base_path="speace_core")
        nodes, edges = collector.collect()
        assert len(nodes) > 0
        assert len(edges) > 0
        # Should find at least one module
        modules = [n for n in nodes if n.node_type.value == "module"]
        assert len(modules) > 0

    def test_collect_finds_classes(self):
        collector = ArchCollector(base_path="speace_core/omni_rag")
        nodes, edges = collector.collect()
        classes = [n for n in nodes if n.node_type.value == "class"]
        assert len(classes) > 0

    def test_collect_finds_functions(self):
        collector = ArchCollector(base_path="speace_core/omni_rag")
        nodes, edges = collector.collect()
        functions = [n for n in nodes if n.node_type.value == "function"]
        assert len(functions) > 0


class TestDNACollector:
    def test_collect(self):
        collector = DNACollector(
            genome_dir="speace_core/dna/genome"
        )
        nodes, edges = collector.collect()
        assert len(nodes) > 0
        # Should contain principle nodes from species_orientation
        principles = [n for n in nodes if n.node_type.value == "principle"]
        assert len(principles) > 0

    def test_genome_not_found(self):
        collector = DNACollector(genome_dir="nonexistent")
        nodes, edges = collector.collect()
        assert len(nodes) == 0


class TestBCELCollector:
    def test_collect(self):
        collector = BCELCollector()
        nodes, edges = collector.collect()
        assert len(nodes) > 0
        bcel_nodes = [n for n in nodes if n.node_type.value == "bcel_mapping"]
        assert len(bcel_nodes) > 0

    def test_constraints_found(self):
        collector = BCELCollector()
        nodes, edges = collector.collect()
        constraints = [n for n in nodes if n.node_type.value == "constraint"]
        assert len(constraints) > 0
