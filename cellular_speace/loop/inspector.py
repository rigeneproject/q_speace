from __future__ import annotations

import ast
import datetime
import json
import logging
import re
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loop import config as cfg
from loop.models import ComponentHealth, Finding, InspectionReport
from loop.utils import (
    compute_health_score,
    find_dangerous_patterns,
    find_todos,
    get_file_patterns,
    get_python_files,
    read_file_safe,
    short_id,
)

logger = logging.getLogger("loop.inspector")


class BrainInspector:
    """Ispettore sistemico di tutti i componenti del cervello e organismo SPEACE."""

    def __init__(self):
        self.project_root = cfg.PROJECT_ROOT
        self.max_chars = cfg.MAX_FILE_SIZE_CHARS
        self.max_files = cfg.MAX_FILES_PER_COMPONENT

    def inspect_all(self) -> InspectionReport:
        cycle_id = f"insp-{short_id()}"
        started = time.time()
        logger.info("===== FASE 1: ISPEZIONE SISTEMICA =====")

        components: Dict[str, ComponentHealth] = {}
        all_findings: List[Finding] = []

        inspection_tasks = [
            ("cells", self._inspect_cells),
            ("regulation", self._inspect_regulation),
            ("regions", self._inspect_regions),
            ("memory", self._inspect_memory),
            ("cognition", self._inspect_cognition),
            ("dynamics", self._inspect_dynamics),
            ("autonomic", self._inspect_autonomic),
            ("self_improvement", self._inspect_self_improvement),
            ("immune", self._inspect_immune),
            ("metabolism", self._inspect_metabolism),
            ("sleep", self._inspect_sleep),
            ("organism", self._inspect_organism),
            ("runtime", self._inspect_runtime),
            ("monitoring", self._inspect_monitoring),
            ("organism_observer", self._inspect_organism_observer),
            ("evolution", self._inspect_evolution),
            ("ilf", self._inspect_ilf),
            ("evolution_daemon", self._inspect_evolution_daemon),
            ("speace_core_root", self._inspect_core_root),
            ("scripts", self._inspect_scripts),
            ("tests", self._inspect_tests),
            ("docs", self._inspect_docs),
            ("dna", self._inspect_dna_genome),
            ("istruttore", self._inspect_existing_inspector),
        ]

        with ThreadPoolExecutor(max_workers=cfg.MAX_WORKERS) as ex:
            futures = {ex.submit(fn): name for name, fn in inspection_tasks}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    ch, findings = future.result()
                    components[name] = ch
                    all_findings.extend(findings)
                except Exception as e:
                    logger.error("Ispettore %s fallito: %s", name, e)
                    components[name] = ComponentHealth(
                        component=name, status="error", score=0.0,
                        findings=[Finding(
                            component=name, subcomponent="inspection",
                            severity="critical", category="structural",
                            title=f"Inspection crashed: {e}",
                            detail=traceback.format_exc(),
                        )]
                    )

        duration = round(time.time() - started, 3)
        logger.info("Ispezione completata: %d componenti, %d findings in %.1fs",
                     len(components), len(all_findings), duration)

        return InspectionReport(
            cycle_id=cycle_id,
            timestamp=datetime.datetime.now().isoformat(),
            duration_sec=duration,
            total_findings=len(all_findings),
            components=components,
        )

    def _check_python_module(self, path: Path, component: str, sub: str) -> Tuple[List[Finding], int]:
        findings = []
        checks = 0
        for f in get_python_files(path, self.max_files):
            checks += 1
            truncated = f.stat().st_size > self.max_chars
            content = read_file_safe(f, self.max_chars)

            if not truncated:
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    findings.append(Finding(
                        component=component, subcomponent=sub,
                        severity="error", category="structural",
                        title="Errore di sintassi Python",
                        detail=str(e),
                        file_path=str(f),
                    ))
                    continue

            for todo in find_todos(content):
                findings.append(Finding(
                    component=component, subcomponent=sub,
                    severity="info", category="code-quality",
                    title=f"Marker: {todo['type']}",
                    detail=todo["context"][:120],
                    file_path=str(f),
                    line=todo["line"],
                ))

            for danger in find_dangerous_patterns(content):
                findings.append(Finding(
                    component=component, subcomponent=sub,
                    severity="warning", category="security",
                    title=danger["description"],
                    detail=f"Trovato {danger['description']}",
                    file_path=str(f),
                    line=danger["line"],
                ))

            if checks >= self.max_files:
                break

        return findings, checks

    def _check_file_integrity(self, root: Path, component: str, sub: str,
                              patterns: List[str] = None) -> List[Finding]:
        findings = []
        if patterns is None:
            patterns = ["*.py", "*.json", "*.yaml", "*.yml", "*.md"]
        files = get_file_patterns(root, patterns, self.max_files)
        for f in files:
            if f.suffix in (".json", ".yaml", ".yml"):
                content = read_file_safe(f, min(self.max_chars, 20000))
                if f.suffix == ".json":
                    try:
                        json.loads(content)
                    except json.JSONDecodeError as e:
                        findings.append(Finding(
                            component=component, subcomponent=sub,
                            severity="error", category="data",
                            title="JSON non valido",
                            detail=str(e),
                            file_path=str(f),
                        ))
        return findings

    def _build_health(self, component: str, findings: List[Finding],
                      sub_health: Dict[str, str] = None, checks: int = 0) -> ComponentHealth:
        critical = [f for f in findings if f.severity == "critical"]
        errors = [f for f in findings if f.severity == "error"]
        warnings = [f for f in findings if f.severity == "warning"]
        info = [f for f in findings if f.severity == "info"]
        score = compute_health_score(len(findings), len(critical), len(errors), max(checks, 1))
        if critical:
            status = "critical"
        elif errors:
            status = "degraded"
        elif len(warnings) > 20 and score < 0.5:
            status = "degraded"
        else:
            status = "healthy"
        capped = (critical + errors + warnings + info)[:200]
        return ComponentHealth(
            component=component, status=status, score=score,
            findings=capped, subcomponent_health=sub_health or {},
            metrics={"critical": len(critical), "errors": len(errors),
                     "warnings": len(warnings), "info": len(info), "capped": len(capped)},
        )

    def _inspect_cells(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "speace_core" / "cellular_brain" / "cells"
        findings = []
        sub_health = {}
        if path.exists():
            findings, checks = self._check_python_module(path, "cells", "neurons")
            sub_health["neurons"] = "ok"
            for f in path.iterdir():
                if f.is_file() and f.suffix == ".py" and f.stem != "__init__":
                    inner_findings, _ = self._check_python_module(path, "cells", f.stem)
                    findings.extend(inner_findings)
        return self._build_health("cells", findings, sub_health), findings

    def _inspect_regulation(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "speace_core" / "cellular_brain" / "regulation"
        findings = []
        sub_health = {}
        if path.exists():
            for f in path.iterdir():
                if f.is_file() and f.suffix == ".py" and f.stem != "__init__":
                    inner, _ = self._check_python_module(path, "regulation", f.stem)
                    findings.extend(inner)
        return self._build_health("regulation", findings, sub_health), findings

    def _inspect_regions(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "speace_core" / "cellular_brain" / "regions"
        findings = []
        sub_health = {}
        if path.exists():
            findings, checks = self._check_python_module(path, "regions", "region_network")
            sub_health["region_network"] = "ok"
        return self._build_health("regions", findings, sub_health), findings

    def _inspect_memory(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "speace_core" / "cellular_brain" / "memory"
        findings = []
        sub_health = {}
        if path.exists():
            for d in path.iterdir():
                if d.is_dir() and not d.name.startswith("__"):
                    inner, _ = self._check_python_module(d, "memory", d.name)
                    findings.extend(inner)
                    sub_health[d.name] = "ok"
            findings_file, _ = self._check_python_module(path, "memory", "memory_core")
            findings.extend(findings_file)
        return self._build_health("memory", findings, sub_health), findings

    def _inspect_cognition(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "speace_core" / "cellular_brain" / "cognition"
        findings = []
        sub_health = {}
        if path.exists():
            for f in path.iterdir():
                if f.is_file() and f.suffix == ".py" and f.stem != "__init__":
                    inner, _ = self._check_python_module(path, "cognition", f.stem)
                    findings.extend(inner)
        return self._build_health("cognition", findings, sub_health), findings

    def _inspect_dynamics(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "speace_core" / "cellular_brain" / "dynamics"
        findings = []
        sub_health = {}
        if path.exists():
            for f in path.iterdir():
                if f.is_file() and f.suffix == ".py" and f.stem != "__init__":
                    inner, _ = self._check_python_module(path, "dynamics", f.stem)
                    findings.extend(inner)
        return self._build_health("dynamics", findings, sub_health), findings

    def _inspect_autonomic(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "speace_core" / "cellular_brain" / "autonomic"
        findings = []
        sub_health = {}
        if path.exists():
            findings, checks = self._check_python_module(path, "autonomic", "ans")
        return self._build_health("autonomic", findings, sub_health), findings

    def _inspect_self_improvement(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "speace_core" / "cellular_brain" / "self_improvement"
        findings = []
        sub_health = {}
        if path.exists():
            for f in path.iterdir():
                if f.is_file() and f.suffix == ".py" and f.stem != "__init__":
                    inner, _ = self._check_python_module(path, "self_improvement", f.stem)
                    findings.extend(inner)
        return self._build_health("self_improvement", findings, sub_health), findings

    def _inspect_immune(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "speace_core" / "cellular_brain" / "immune"
        findings = []
        sub_health = {}
        if path.exists():
            findings, checks = self._check_python_module(path, "immune", "immune_system")
        return self._build_health("immune", findings, sub_health), findings

    def _inspect_metabolism(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "speace_core" / "cellular_brain" / "metabolism"
        findings = []
        sub_health = {}
        if path.exists():
            findings, checks = self._check_python_module(path, "metabolism", "metabolic_system")
        return self._build_health("metabolism", findings, sub_health), findings

    def _inspect_sleep(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "speace_core" / "cellular_brain" / "sleep"
        findings = []
        sub_health = {}
        if path.exists():
            findings, checks = self._check_python_module(path, "sleep", "sleep_cycle")
        return self._build_health("sleep", findings, sub_health), findings

    def _inspect_organism(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "speace_core" / "organism"
        findings = []
        sub_health = {}
        if path.exists():
            findings, checks = self._check_python_module(path, "organism", "organism_layer")
        path2 = cfg.PROJECT_ROOT / "speace_core" / "cellular_brain" / "organism"
        if path2.exists():
            inner, _ = self._check_python_module(path2, "organism", "organism_in_brain")
            findings.extend(inner)
        return self._build_health("organism", findings, sub_health), findings

    def _inspect_runtime(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "speace_core" / "runtime"
        findings = []
        sub_health = {}
        if path.exists():
            for f in path.iterdir():
                if f.is_file() and f.suffix == ".py" and f.stem != "__init__":
                    inner, _ = self._check_python_module(path, "runtime", f.stem)
                    findings.extend(inner)
        return self._build_health("runtime", findings, sub_health), findings

    def _inspect_monitoring(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "speace_core" / "monitoring"
        findings = []
        sub_health = {}
        if path.exists():
            for f in path.iterdir():
                if f.is_file() and f.suffix == ".py" and f.stem != "__init__":
                    inner, _ = self._check_python_module(path, "monitoring", f.stem)
                    findings.extend(inner)
        return self._build_health("monitoring", findings, sub_health), findings

    def _inspect_organism_observer(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "speace_core" / "organism_observer"
        findings = []
        sub_health = {}
        if path.exists():
            findings, checks = self._check_python_module(path, "organism_observer", "ofg")
        return self._build_health("organism_observer", findings, sub_health), findings

    def _inspect_evolution(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "speace_core" / "evolution"
        findings = []
        sub_health = {}
        if path.exists():
            for f in path.iterdir():
                if f.is_file() and f.suffix == ".py" and f.stem != "__init__":
                    inner, _ = self._check_python_module(path, "evolution", f.stem)
                    findings.extend(inner)
        return self._build_health("evolution", findings, sub_health), findings

    def _inspect_ilf(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "speace_core" / "ilf"
        findings = []
        sub_health = {}
        if path.exists():
            findings, checks = self._check_python_module(path, "ilf", "field")
        return self._build_health("ilf", findings, sub_health), findings

    def _inspect_evolution_daemon(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "evolution_daemon"
        findings = []
        sub_health = {}
        if path.exists():
            for f in path.iterdir():
                if f.is_file() and f.suffix == ".py" and f.stem != "__init__":
                    inner, _ = self._check_python_module(path, "evolution_daemon", f.stem)
                    findings.extend(inner)
        return self._build_health("evolution_daemon", findings, sub_health), findings

    def _inspect_core_root(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "speace_core"
        findings = []
        sub_health = {}
        key_files = ["__init__.py", "cli.py", "orchestrator.py", "event_bus.py"]
        for kf in key_files:
            kp = path / kf
            if kp.exists():
                inner, _ = self._check_python_module(path, "speace_core", Path(kf).stem)
                findings.extend(inner)
        return self._build_health("speace_core_root", findings, sub_health), findings

    def _inspect_scripts(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "scripts"
        findings = []
        sub_health = {}
        if path.exists():
            findings, checks = self._check_python_module(path, "scripts", "automation")
        return self._build_health("scripts", findings, sub_health), findings

    def _inspect_tests(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "tests"
        findings = []
        sub_health = {}
        if path.exists():
            findings, checks = self._check_python_module(path, "tests", "test_suite")
        return self._build_health("tests", findings, sub_health), findings

    def _inspect_docs(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "docs"
        findings = []
        sub_health = {}
        if path.exists():
            files = get_file_patterns(path, ["*.md", "*.txt", "*.pdf"], self.max_files)
            for f in files:
                content = read_file_safe(f, min(self.max_chars, 10000))
                for todo in find_todos(content):
                    findings.append(Finding(
                        component="docs", subcomponent="documentation",
                        severity="info", category="code-quality",
                        title=f"Marker doc: {todo['type']}",
                        detail=todo["context"],
                        file_path=str(f), line=todo["line"],
                    ))
        return self._build_health("docs", findings, sub_health), findings

    def _inspect_dna_genome(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "speace_core" / "dna"
        findings = []
        sub_health = {}
        if path.exists():
            findings_py, checks = self._check_python_module(path, "dna", "dna_core")
            findings.extend(findings_py)
            genome_dir = path / "genome"
            if genome_dir.exists():
                for f in genome_dir.rglob("*.yaml"):
                    content = read_file_safe(f, self.max_chars)
                    findings.append(Finding(
                        component="dna", subcomponent="genome_yaml",
                        severity="info", category="data",
                        title=f"Genoma: {f.name} ({len(content)} bytes)",
                        detail=f"Presente in {f.relative_to(self.project_root)}",
                        file_path=str(f),
                    ))
                for f in genome_dir.rglob("*.json"):
                    content = read_file_safe(f, min(self.max_chars, 20000))
                    try:
                        json.loads(content)
                    except json.JSONDecodeError as e:
                        findings.append(Finding(
                            component="dna", subcomponent="genome_json",
                            severity="error", category="data",
                            title="Genoma JSON non valido",
                            detail=str(e), file_path=str(f),
                        ))
        return self._build_health("dna", findings, sub_health), findings

    def _inspect_existing_inspector(self) -> Tuple[ComponentHealth, List[Finding]]:
        path = cfg.PROJECT_ROOT / "ispettore_manutentore_neurologico_organismico_di_speace"
        findings = []
        sub_health = {}
        if path.exists():
            findings, checks = self._check_python_module(path, "ispettore", "ispettore_core")
        return self._build_health("ispettore", findings, sub_health), findings
