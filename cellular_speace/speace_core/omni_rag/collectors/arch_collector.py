import ast
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import structlog

from speace_core.omni_rag.models import (
    CognitiveNode,
    CognitiveEdge,
    NodeType,
    RelationType,
)

logger = structlog.get_logger(__name__)


class ArchCollector:
    """Parses Python source code to extract structural architecture.

    Produces nodes for modules, classes, functions and edges for
    IMPORTS, EXTENDS, CONTAINS, BELONGS_TO, REFERENCES relationships.
    """

    def __init__(self, base_path: str = "speace_core") -> None:
        self._base_path = Path(base_path)

    def collect(self) -> Tuple[List[CognitiveNode], List[CognitiveEdge]]:
        """Walk all Python files and extract architecture."""
        nodes: Dict[str, CognitiveNode] = {}
        edges: List[CognitiveEdge] = []

        py_files = list(self._base_path.rglob("*.py"))
        for fpath in py_files:
            if self._is_excluded(fpath):
                continue
            file_nodes, file_edges = self._parse_file(fpath)
            for n in file_nodes:
                nodes[n.id] = n
            edges.extend(file_edges)

        # Resolve IMPORTS edges between module nodes
        module_edges = self._resolve_imports(nodes)
        edges.extend(module_edges)

        logger.info(
            "arch_collector.complete",
            files=len(py_files),
            nodes=len(nodes),
            edges=len(edges),
        )
        return list(nodes.values()), edges

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _is_excluded(self, path: Path) -> bool:
        excluded_dirs = {"__pycache__", ".venv", "venv", "env", ".git", "node_modules"}
        for part in path.parts:
            if part in excluded_dirs:
                return True
        return False

    def _module_id(self, fpath: Path) -> str:
        relative = str(fpath.relative_to(self._base_path.parent)).replace("\\", "/")
        relative = relative.replace(".py", "").replace("/", ".")
        relative = re.sub(r"\.__init__$", "", relative)
        return f"module:{relative}"

    def _class_id(self, class_name: str, module_id: str) -> str:
        return f"class:{module_id}.{class_name}"

    def _function_id(self, func_name: str, parent_id: str) -> str:
        return f"func:{parent_id}.{func_name}"

    def _parse_file(self, fpath: Path) -> Tuple[List[CognitiveNode], List[CognitiveEdge]]:
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text, filename=str(fpath))
        except SyntaxError as exc:
            logger.warning("arch_collector.syntax_error", path=str(fpath), error=str(exc))
            return [], []

        nodes: List[CognitiveNode] = []
        edges: List[CognitiveEdge] = []

        mod_id = self._module_id(fpath)
        relative_path = str(fpath.resolve())

        # Module node
        docstring = ast.get_docstring(tree) or ""
        mod_node = CognitiveNode(
            id=mod_id,
            node_type=NodeType.MODULE,
            name=fpath.stem,
            description=docstring[:200].replace("\n", " ").strip(),
            source_path=relative_path,
            metadata={"package": ".".join(mod_id.split(".")[1:-1])},
            tags=["python_module"],
        )
        nodes.append(mod_node)

        imports: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    full = f"{module}.{alias.name}" if module else alias.name
                    imports.append(full)

            elif isinstance(node, ast.ClassDef):
                class_id = self._class_id(node.name, mod_id)
                class_doc = ast.get_docstring(node) or ""
                class_node = CognitiveNode(
                    id=class_id,
                    node_type=NodeType.CLASS,
                    name=node.name,
                    description=class_doc[:200].replace("\n", " ").strip(),
                    source_path=relative_path,
                    source_line=node.lineno,
                    tags=["python_class"],
                )
                nodes.append(class_node)

                # CONTAINS edge
                edges.append(CognitiveEdge(
                    source_id=mod_id,
                    target_id=class_id,
                    relation=RelationType.CONTAINS,
                    weight=1.0,
                ))

                # EXTENDS edges
                for base in node.bases:
                    base_name = self._extract_name(base)
                    if base_name and base_name not in {"object", "BaseModel", "ABC"}:
                        base_id = self._class_id(base_name, mod_id)
                        edges.append(CognitiveEdge(
                            source_id=class_id,
                            target_id=base_id,
                            relation=RelationType.EXTENDS,
                            weight=1.0,
                        ))

                # Methods
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        func_id = self._function_id(item.name, class_id)
                        func_doc = ast.get_docstring(item) or ""
                        func_node = CognitiveNode(
                            id=func_id,
                            node_type=NodeType.FUNCTION,
                            name=item.name,
                            description=func_doc[:200].replace("\n", " ").strip(),
                            source_path=relative_path,
                            source_line=item.lineno,
                            tags=["python_method"],
                        )
                        nodes.append(func_node)
                        edges.append(CognitiveEdge(
                            source_id=class_id,
                            target_id=func_id,
                            relation=RelationType.CONTAINS,
                            weight=1.0,
                        ))

            elif isinstance(node, ast.FunctionDef):
                func_id = self._function_id(node.name, mod_id)
                func_doc = ast.get_docstring(node) or ""
                func_node = CognitiveNode(
                    id=func_id,
                    node_type=NodeType.FUNCTION,
                    name=node.name,
                    description=func_doc[:200].replace("\n", " ").strip(),
                    source_path=relative_path,
                    source_line=node.lineno,
                    tags=["python_function"],
                )
                nodes.append(func_node)
                edges.append(CognitiveEdge(
                    source_id=mod_id,
                    target_id=func_id,
                    relation=RelationType.CONTAINS,
                    weight=1.0,
                ))

        # Import edges
        for imp in imports:
            imp_mod_id = f"module:{imp}"
            if imp_mod_id != mod_id:
                edges.append(CognitiveEdge(
                    source_id=mod_id,
                    target_id=imp_mod_id,
                    relation=RelationType.IMPORTS,
                    weight=1.0,
                    metadata={"import_name": imp},
                ))

        return nodes, edges

    def _extract_name(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._extract_name(node.value)
        return None

    def _resolve_imports(self, nodes: Dict[str, CognitiveNode]) -> List[CognitiveEdge]:
        """Resolve IMPORTS edges to actual module IDs by finding the closest match."""
        existing_ids = set(nodes.keys())
        resolved: List[CognitiveEdge] = []
        for node in nodes.values():
            for edge in self._find_import_edges(node):
                resolved.append(edge)
        return resolved

    def _find_import_edges(self, node: CognitiveNode) -> List[CognitiveEdge]:
        # This is handled during parse; we store imports as edges directly.
        return []
