import hashlib
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

import structlog

from speace_core.omni_rag.models import CognitiveNode, NodeType, RelationType, CognitiveEdge

logger = structlog.get_logger(__name__)


class SemanticCollector:
    """Indexes text content from documentation, code comments, and configuration files.

    Builds an inverted keyword index and creates DOCUMENT nodes in the graph.
    """

    def __init__(self, base_paths: Optional[List[str]] = None) -> None:
        self._base_paths = base_paths or [
            "docs",
            "reports",
            "speace_core",
        ]
        self._keyword_index: Dict[str, List[Dict]] = {}
        self._documents: Dict[str, CognitiveNode] = {}

    def collect(self) -> List[CognitiveNode]:
        """Scan configured paths and return DOCUMENT/PRINCIPLE nodes."""
        nodes: List[CognitiveNode] = []
        self._keyword_index.clear()
        self._documents.clear()

        scanned_files = 0
        for base in self._base_paths:
            base_path = Path(base)
            if not base_path.exists():
                continue
            if base_path.is_file():
                doc_nodes = self._index_file(base_path)
                nodes.extend(doc_nodes)
                scanned_files += 1
            else:
                for fpath in base_path.rglob("*"):
                    if fpath.is_file() and self._is_indexable(fpath):
                        doc_nodes = self._index_file(fpath)
                        nodes.extend(doc_nodes)
                        scanned_files += 1

        logger.info(
            "semantic_collector.complete",
            files=scanned_files,
            nodes=len(nodes),
            keywords=len(self._keyword_index),
        )
        return nodes

    def get_keyword_results(self, query: str, top_k: int = 10) -> List[Dict]:
        """Return ranked document chunks matching query keywords."""
        tokens = self._tokenize(query)
        scores: Dict[str, float] = {}

        for token in tokens:
            for entry in self._keyword_index.get(token, []):
                doc_id = entry["doc_id"]
                scores[doc_id] = scores.get(doc_id, 0.0) + entry.get("weight", 1.0)

        ranked = sorted(scores.items(), key=lambda x: -x[1])
        results = []
        for doc_id, score in ranked[:top_k]:
            doc = self._documents.get(doc_id)
            if doc:
                results.append({
                    "node": doc,
                    "score": score,
                    "doc_id": doc_id,
                })
        return results

    def get_nodes(self) -> List[CognitiveNode]:
        return list(self._documents.values())

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _is_indexable(self, path: Path) -> bool:
        ext = path.suffix.lower()
        if ext in {".pyc", ".pyo", ".egg", ".whl"}:
            return False
        if ext in {".md", ".py", ".yaml", ".yml", ".json", ".jsonl", ".txt", ".cfg", ".ini"}:
            return True
        if path.name.startswith("."):
            return False
        return ext in {".rst", ""}  # no extension might be scripts

    def _index_file(self, fpath: Path) -> List[CognitiveNode]:
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            logger.warning("semantic_collector.read_failed", path=str(fpath), error=str(exc))
            return []

        doc_id = self._doc_id(fpath)
        content_hash = hashlib.md5(text.encode()).hexdigest()[:12]

        relative_path = str(fpath).replace("\\", "/")

        if fpath.suffix in {".yaml", ".yml"}:
            node_type = NodeType.CONFIG
        elif fpath.suffix == ".md":
            node_type = NodeType.DOCUMENT
        elif fpath.suffix == ".py":
            node_type = NodeType.MODULE
        else:
            node_type = NodeType.DOCUMENT

        node = CognitiveNode(
            id=doc_id,
            node_type=node_type,
            name=fpath.name,
            description=text[:200].replace("\n", " ").strip(),
            source_path=relative_path,
            metadata={
                "path": relative_path,
                "extension": fpath.suffix,
                "size_bytes": len(text),
                "content_hash": content_hash,
            },
            tags=[node_type.value, fpath.suffix.lstrip(".")],
        )

        self._documents[doc_id] = node

        tokens = self._tokenize(text)
        token_count: Dict[str, int] = {}
        for t in tokens:
            token_count[t] = token_count.get(t, 0) + 1

        max_count = max(token_count.values()) if token_count else 1
        for token, count in token_count.items():
            weight = count / max_count
            self._keyword_index.setdefault(token, []).append({
                "doc_id": doc_id,
                "weight": weight,
            })

        return [node]

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower()
        text = re.sub(r"[^a-z0-9_]", " ", text)
        tokens = text.split()
        min_len = 3
        return [t for t in tokens if len(t) >= min_len]

    def _doc_id(self, fpath: Path) -> str:
        relative = str(fpath).replace("\\", "/")
        return f"doc:{relative}"
