from __future__ import annotations

import ast
import datetime
import json
import logging
import re
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("loop.utils")


def setup_logging(level: str = "INFO", log_file: Optional[Path] = None) -> None:
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s | %(message)s",
        handlers=handlers,
    )


def read_file_safe(path: Path, max_chars: int = 80000) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        if len(content) > max_chars:
            content = content[:max_chars] + "\n\n[...TRUNCATED...]"
        return content
    except Exception as e:
        return f"[ERROR READING {path}: {e}]"


def get_python_files(root: Path, max_files: int = 200) -> List[Path]:
    if not root.exists():
        return []
    files = []
    for f in root.rglob("*.py"):
        if f.is_file() and not any(p.startswith(".") or p == "__pycache__" for p in f.parts):
            files.append(f)
            if len(files) >= max_files:
                break
    return sorted(files)


def get_file_patterns(root: Path, patterns: List[str], max_files: int = 200) -> List[Path]:
    if not root.exists():
        return []
    files = []
    for pattern in patterns:
        for f in root.rglob(pattern):
            if f.is_file() and not any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                files.append(f)
                if len(files) >= max_files:
                    break
        if len(files) >= max_files:
            break
    return sorted(set(files))


def safe_import_check(module_path: Path, project_root: Path) -> Dict[str, Any]:
    result = {"path": str(module_path), "importable": False, "syntax_ok": False, "errors": []}
    try:
        source = module_path.read_text(encoding="utf-8", errors="replace")
        try:
            ast.parse(source)
            result["syntax_ok"] = True
        except SyntaxError as e:
            result["errors"].append(f"SyntaxError: {e}")
            return result
        old_path = sys.path.copy()
        sys.path.insert(0, str(project_root))
        try:
            rel = module_path.relative_to(project_root)
            mod_name = str(rel.with_suffix("")).replace("\\", ".").replace("/", ".")
            __import__(mod_name)
            result["importable"] = True
        except Exception as e:
            result["errors"].append(f"ImportError: {e}")
        finally:
            sys.path = old_path
        for mod_name in list(sys.modules.keys()):
            if "speace" in mod_name or "loop" in mod_name:
                if mod_name not in ("speace_core", "loop", "evolution_daemon"):
                    try:
                        del sys.modules[mod_name]
                    except KeyError:
                        pass
    except Exception as e:
        result["errors"].append(f"ReadError: {e}")
    return result


def find_todos(content: str) -> List[Dict[str, Any]]:
    findings = []
    for m in re.finditer(r"(?i)(TODO|FIXME|HACK|XXX|BUG|WORKAROUND|HARDCODED)\b", content):
        line_num = content[:m.start()].count("\n") + 1
        findings.append({
            "type": m.group(1).upper(),
            "line": line_num,
            "context": content[max(0, m.start() - 40):m.end() + 60].strip(),
        })
    return findings


def find_dangerous_patterns(content: str) -> List[Dict[str, Any]]:
    findings = []
    patterns = [
        (r"\beval\s*\(", "eval() - code injection risk"),
        (r"\bexec\s*\(", "exec() - code injection risk"),
        (r"\b__import__\s*\(", "__import__() - dynamic import"),
        (r"\bcompile\s*\(", "compile() - dynamic compilation"),
        (r"(?i)(password|secret|api_key|token)\s*=\s*['\"][^'\"]+['\"]", "Hardcoded credential"),
        (r"subprocess\.(call|Popen|run)\s*\(", "subprocess execution"),
        (r"os\.system\s*\(", "os.system() execution"),
        (r"\bpickle\.loads?\s*\(", "pickle deserialization"),
        (r"\byaml\.load\s*\(", "unsafe yaml.load()"),
    ]
    for pattern, desc in patterns:
        for m in re.finditer(pattern, content):
            line_num = content[:m.start()].count("\n") + 1
            findings.append({"type": "DANGEROUS", "description": desc, "line": line_num})
    return findings


def find_missing_imports(source: str) -> List[str]:
    issues = []
    try:
        tree = ast.parse(source)
        imported_names: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_names.add(node.module.split(".")[0])
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                name = node.id
                if name[0].isupper() and name not in imported_names and name not in dir(__builtins__):
                    issues.append(f"Potenziale nome non importato: {name} (linea {node.lineno})")
    except SyntaxError:
        pass
    return issues


def compute_health_score(findings_count: int, critical_count: int, error_count: int, total_checks: int) -> float:
    if total_checks == 0:
        return 1.0
    sig_findings = max(0, findings_count - total_checks)
    deductions = (critical_count * 0.3) + (error_count * 0.1) + (min(sig_findings, total_checks) * 0.01)
    score = max(0.0, 1.0 - deductions)
    return round(score, 4)


def timestamp() -> str:
    return datetime.datetime.now().isoformat()


def short_id() -> str:
    import uuid
    return uuid.uuid4().hex[:8]


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def load_json(path: Path) -> Optional[Any]:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None
