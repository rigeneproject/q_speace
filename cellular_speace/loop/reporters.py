from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from loop import config as cfg
from loop.models import (
    ComponentHealth,
    DiagnosisReport,
    IDOCycleResult,
    InspectionReport,
    OptimizationReport,
)

logger = logging.getLogger("loop.reporters")


class IDOReporter:
    """Genera report in formato JSON, Markdown e stampa a console."""

    def report_cycle(self, result: IDOCycleResult) -> Path:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = cfg.REPORT_DIR / f"ido_{timestamp}"
        report_dir.mkdir(parents=True, exist_ok=True)

        json_path = report_dir / "cycle_full.json"
        json_path.write_text(
            json.dumps(self._to_serializable(result), ensure_ascii=False,
                       indent=2, default=str),
            encoding="utf-8",
        )

        md_path = report_dir / "report.md"
        md_path.write_text(self._build_markdown(result), encoding="utf-8")

        summary_path = report_dir / "summary.json"
        summary_path.write_text(
            json.dumps(self._build_summary(result), ensure_ascii=False,
                       indent=2, default=str),
            encoding="utf-8",
        )

        logger.info("Report IDO salvati in %s", report_dir)
        return report_dir

    def print_cycle_summary(self, result: IDOCycleResult) -> None:
        ins = result.inspection
        diag = result.diagnosis
        opt = result.optimization

        print()
        print("=" * 72)
        print(f" CICLO IDO #{result.cycle_id} completato")
        print(f" {'=' * 68}")
        print(f"  Health: {result.system_health_before:.3f} -> {result.system_health_after:.3f} "
              f"({result.improvement:+.3f})")
        print(f"  Fasi: ispezione={ins.duration_sec:.1f}s | "
              f"diagnosi={diag.duration_sec:.1f}s | "
              f"ottimizzazione={opt.duration_sec:.1f}s")
        print(f"  Findings: {ins.total_findings} | "
              f"Diagnosi: {diag.total_diagnoses} | "
              f"Azioni: {opt.total_actions} (applied={opt.applied})")
        print("  Componenti:")
        healthy = sum(1 for c in ins.components.values() if c.status == "healthy")
        degraded = sum(1 for c in ins.components.values() if c.status == "degraded")
        critical = sum(1 for c in ins.components.values() if c.status in ("critical", "error"))
        print(f"    healthy={healthy} degraded={degraded} critical={critical}")
        if opt.applied > 0:
            print(f"  Correzioni applicate: {opt.applied}")
            for a in opt.actions:
                if a.status == "applied":
                    print(f"    [+] {a.description}")
        if opt.failed > 0:
            for a in opt.actions:
                if a.status == "failed":
                    print(f"    [!] Fallito: {a.description}")
        print()
        if diag.priority_actions:
            print("  Azioni prioritarie raccomandate:")
            for i, a in enumerate(diag.priority_actions[:5], 1):
                print(f"    {i}. {a}")
        print("=" * 72)
        print()

    def _build_markdown(self, result: IDOCycleResult) -> str:
        lines = [
            f"# Report Ciclo IDO: {result.cycle_id}",
            "",
            f"**Avviato:** {result.started_at}",
            f"**Completato:** {result.finished_at}",
            f"**Durata:** {result.duration_sec:.1f}s",
            f"**Health score:** {result.system_health_before:.3f} → {result.system_health_after:.3f} ({result.improvement:+.3f})",
            "",
            "## 1. Ispezione",
            f"- Componenti ispezionati: {len(result.inspection.components)}",
            f"- Totale findings: {result.inspection.total_findings}",
            f"- Durata: {result.inspection.duration_sec:.1f}s",
            "",
            "### Stato componenti",
            "",
        ]
        for name, ch in sorted(result.inspection.components.items(),
                                key=lambda x: x[1].score):
            lines.append(f"- **{name}**: {ch.status} (score={ch.score}) "
                         f"- {ch.metrics.get('critical', 0)}C "
                         f"{ch.metrics.get('errors', 0)}E "
                         f"{ch.metrics.get('warnings', 0)}W")

        lines += [
            "",
            "## 2. Diagnosi",
            f"- Diagnosi totali: {result.diagnosis.total_diagnoses}",
            f"- Health score sistema: {result.diagnosis.system_health_score:.4f}",
            f"- Durata: {result.diagnosis.duration_sec:.1f}s",
            "",
            "### Diagnosi emesse",
            "",
        ]
        for d in result.diagnosis.diagnoses:
            lines.append(f"- **[#{d.severity}]** {d.root_cause}")
            for e in d.evidence[:3]:
                lines.append(f"  - {e}")
            lines.append("")

        lines += [
            "## 3. Ottimizzazione",
            f"- Azioni totali: {result.optimization.total_actions}",
            f"- Applicate: {result.optimization.applied}",
            f"- Fallite: {result.optimization.failed}",
            f"- Saltate: {result.optimization.skipped}",
            f"- Durata: {result.optimization.duration_sec:.1f}s",
            "",
            "### Azioni applicate",
            "",
        ]
        for a in result.optimization.actions:
            if a.status == "applied":
                lines.append(f"- ✅ {a.description}")
        for a in result.optimization.actions:
            if a.status == "failed":
                lines.append(f"- ❌ {a.description}")
                if a.error:
                    lines.append(f"  - Errore: {a.error}")

        lines += [
            "",
            "## 4. Azioni prioritarie",
            "",
        ]
        for i, a in enumerate(result.diagnosis.priority_actions, 1):
            lines.append(f"{i}. {a}")

        lines += [
            "",
            "## 5. Trend",
            "",
        ]
        for k, v in result.diagnosis.trends.items():
            if isinstance(v, dict):
                lines.append(f"- **{k}**:")
                for sk, sv in v.items():
                    lines.append(f"  - {sk}: {sv}")
            else:
                lines.append(f"- **{k}**: {v}")

        lines += [
            "",
            "---",
            f"*Generato da /loop IDO Cycle {result.cycle_id}*",
        ]
        return "\n".join(lines)

    def _build_summary(self, result: IDOCycleResult) -> Dict[str, Any]:
        return {
            "cycle_id": result.cycle_id,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "duration_sec": result.duration_sec,
            "system_health_before": result.system_health_before,
            "system_health_after": result.system_health_after,
            "improvement": result.improvement,
            "inspection": {
                "total_findings": result.inspection.total_findings,
                "components_checked": len(result.inspection.components),
                "component_status": {
                    n: {"status": c.status, "score": c.score}
                    for n, c in result.inspection.components.items()
                },
            },
            "diagnosis": {
                "total_diagnoses": result.diagnosis.total_diagnoses,
                "system_health_score": result.diagnosis.system_health_score,
                "priority_actions": result.diagnosis.priority_actions[:10],
            },
            "optimization": {
                "total_actions": result.optimization.total_actions,
                "applied": result.optimization.applied,
                "failed": result.optimization.failed,
                "skipped": result.optimization.skipped,
            },
        }

    @staticmethod
    def _to_serializable(obj: Any) -> Any:
        if hasattr(obj, "__dataclass_fields__"):
            return {
                k: IDOReporter._to_serializable(v)
                for k, v in obj.__dict__.items()
            }
        if isinstance(obj, list):
            return [IDOReporter._to_serializable(v) for v in obj]
        if isinstance(obj, dict):
            return {k: IDOReporter._to_serializable(v) for k, v in obj.items()}
        return obj
