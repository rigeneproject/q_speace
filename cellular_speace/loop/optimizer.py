from __future__ import annotations

import datetime
import logging
import re
import shutil
import time
from pathlib import Path
from typing import List, Optional

from loop import config as cfg
from loop.models import (
    ComponentHealth,
    Diagnosis,
    DiagnosisReport,
    Finding,
    InspectionReport,
    OptimizationAction,
    OptimizationReport,
)
from loop.utils import short_id

logger = logging.getLogger("loop.optimizer")


class SystemOptimizer:
    """Applica correzioni automatiche e propone ottimizzazioni strutturali."""

    def __init__(self):
        self.project_root = cfg.PROJECT_ROOT
        self.auto_fix = cfg.AUTO_FIX_ENABLED
        self.backup_enabled = cfg.BACKUP_ENABLED
        self.dry_run = cfg.DRY_RUN

    def optimize(self, inspection: InspectionReport,
                 diagnosis: DiagnosisReport) -> OptimizationReport:
        cycle_id = f"opt-{short_id()}"
        started = time.time()
        logger.info("===== FASE 3: OTTIMIZZAZIONE =====")

        actions: List[OptimizationAction] = []

        # 1. Correzioni rapide da findings ispezione
        for name, ch in inspection.components.items():
            for finding in ch.findings:
                if finding.severity in ("critical", "error"):
                    fix = self._try_quick_fix(finding, name)
                    if fix:
                        actions.append(fix)

        # 2. Correzioni da diagnosi prioritarie
        for diag in diagnosis.diagnoses:
            if diag.severity in ("critical", "error"):
                fix = self._try_diagnosis_fix(diag, inspection)
                if fix:
                    actions.append(fix)

        # 3. Ottimizzazioni preventive
        for name, ch in inspection.components.items():
            opt_actions = self._suggest_optimizations(name, ch)
            actions.extend(opt_actions)

        # 4. Pulizia import/logging (refactoring automatico)
        for name, ch in inspection.components.items():
            for finding in ch.findings:
                if "print()" in finding.title or "logging" in finding.detail.lower():
                    fix = self._fix_print_to_logging(finding)
                    if fix:
                        actions.append(fix)

        applied = sum(1 for a in actions if a.status == "applied")
        failed = sum(1 for a in actions if a.status == "failed")
        skipped = sum(1 for a in actions if a.status == "skipped")

        summary_parts = []
        if applied:
            summary_parts.append(f"{applied} correzioni applicate")
        if failed:
            summary_parts.append(f"{failed} fallite")
        if skipped:
            summary_parts.append(f"{skipped} saltate")
        summary = ", ".join(summary_parts) if summary_parts else "Nessuna azione eseguita"

        duration = round(time.time() - started, 3)
        logger.info("Ottimizzazione completata: %s in %.1fs", summary, duration)

        return OptimizationReport(
            cycle_id=cycle_id,
            timestamp=datetime.datetime.now().isoformat(),
            duration_sec=duration,
            total_actions=len(actions),
            applied=applied,
            failed=failed,
            skipped=skipped,
            actions=actions,
            summary=summary,
        )

    def _try_quick_fix(self, finding: Finding, component: str) -> Optional[OptimizationAction]:
        if not finding.file_path or not self.auto_fix:
            return None
        path = Path(finding.file_path)
        if not path.exists():
            return None

        # Fix per file vuoti o non leggibili
        if "FILE_VUOTO" in finding.title.upper() or "FILE TROPPO GRANDE" in finding.title.upper():
            return OptimizationAction(
                action_type="ignore",
                target_file=str(path),
                target_component=component,
                description=f"Segnalazione: {finding.title}",
                status="skipped",
            )

        # Fix per JSON non validi
        if "JSON non valido" in finding.title:
            return self._fix_json(path, finding, component)

        return None

    def _fix_json(self, path: Path, finding: Finding, component: str) -> OptimizationAction:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            if content.startswith("\ufeff"):
                content = content[1:]
            content_clean = content.strip()
            if not content_clean:
                return OptimizationAction(
                    action_type="fix", target_file=str(path),
                    target_component=component,
                    description="File JSON vuoto - nessuna correzione possibile",
                    status="skipped",
                )
            return OptimizationAction(
                action_type="ignore",
                target_file=str(path),
                target_component=component,
                description=f"JSON malformato: {finding.detail}",
                status="skipped",
            )
        except Exception as e:
            return OptimizationAction(
                action_type="fix", target_file=str(path),
                target_component=component,
                description=f"Tentativo di fix JSON fallito: {e}",
                status="failed",
                error=str(e),
            )

    def _fix_print_to_logging(self, finding: Finding) -> Optional[OptimizationAction]:
        if not finding.file_path or not self.auto_fix:
            return None
        path = Path(finding.file_path)
        if not path.exists() or path.suffix != ".py":
            return None
        if self.dry_run:
            return OptimizationAction(
                action_type="fix", target_file=str(path),
                description="[DRY RUN] print() -> logging.info()",
                status="skipped",
            )
        try:
            content = path.read_text(encoding="utf-8")
            new_content = content
            has_logging = "import logging" in content or "from logging" in content
            pattern = re.compile(r"^(\s*)print\s*\((.*?)\)\s*$", re.MULTILINE)
            replacements = []
            for m in pattern.finditer(content):
                indent = m.group(1)
                args = m.group(2).strip()
                if not args:
                    args = '""'
                replacements.append((m.start(), m.end(), f'{indent}logging.info({args})'))

            if replacements:
                new_content = list(content)
                for start, end, replacement in reversed(replacements):
                    new_content = list(content)
                    new_content = content[:start] + replacement + content[end:]
                    content = new_content

                if not has_logging:
                    new_content = "import logging\n" + new_content

                if self.backup_enabled:
                    backup = cfg.BACKUP_DIR / f"{path.name}.{short_id()}.bak"
                    shutil.copy2(str(path), str(backup))

                path.write_text(new_content, encoding="utf-8")
                return OptimizationAction(
                    action_type="fix", target_file=str(path),
                    description=f"Sostituiti {len(replacements)} print() con logging.info()",
                    status="applied",
                    code_before=f"print() x{len(replacements)}",
                    code_after="logging.info()",
                    backup_file=str(backup) if self.backup_enabled else None,
                )
        except Exception as e:
            return OptimizationAction(
                action_type="fix", target_file=str(path),
                description=f"Fix print->logging fallito: {e}",
                status="failed", error=str(e),
            )
        return None

    def _try_diagnosis_fix(self, diag: Diagnosis,
                           inspection: InspectionReport) -> Optional[OptimizationAction]:
        component = diag.affected_components[0] if diag.affected_components else "unknown"
        ch = inspection.components.get(component)
        if not ch:
            return None
        return OptimizationAction(
            action_type="proposal",
            target_component=component,
            description=f"Diagnosi: {diag.root_cause}",
            status="skipped" if self.dry_run else "pending",
        )

    def _suggest_optimizations(self, name: str,
                               ch: ComponentHealth) -> List[OptimizationAction]:
        actions = []
        if ch.score < 0.5:
            actions.append(OptimizationAction(
                action_type="proposal",
                target_component=name,
                description=f"Health score critico ({ch.score}): necessario intervento su {name}",
                status="pending",
            ))
        return actions
