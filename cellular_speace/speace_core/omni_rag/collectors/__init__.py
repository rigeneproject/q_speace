"""T172 — Omni-RAG collectors (one module per cognitive plane).

Registers ``InformationValueCollector`` so the indexer can pick it up.
"""

from speace_core.omni_rag.collectors.information_value_collector import (
    InformationValueCollector,
    motivation_audit,
)

__all__ = ["InformationValueCollector", "motivation_audit"]
