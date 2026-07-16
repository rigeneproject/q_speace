from __future__ import annotations

import datetime
import logging
import time
from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple

from loop import config as cfg
from loop.models import (
    ComponentHealth,
    Diagnosis,
    DiagnosisReport,
    Finding,
    InspectionReport,
)
from loop.utils import short_id

logger = logging.getLogger("loop.diagnostician")


class SystemDiagnostician:
    """Analizza i risultati dell'ispezione e produce diagnosi delle cause radice."""

    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self.history_max = 50

    def diagnose(self, inspection: InspectionReport) -> DiagnosisReport:
        cycle_id = f"diag-{short_id()}"
        started = time.time()
        logger.info("===== FASE 2: DIAGNOSI SISTEMICA =====")

        diagnoses: List[Diagnosis] = []
        all_findings_by_component = {
            name: ch.findings for name, ch in inspection.components.items()
        }

        # 1. Analisi per ogni componente
        for comp_name, ch in inspection.components.items():
            comp_diags = self._diagnose_component(comp_name, ch, inspection)
            diagnoses.extend(comp_diags)

        # 2. Diagnosi cross-componente (pattern sistemici)
        cross_diags = self._diagnose_cross_component(inspection)
        diagnoses.extend(cross_diags)

        # 3. Diagnosi strutturali e architetturali
        arch_diags = self._diagnose_architecture(inspection)
        diagnoses.extend(arch_diags)

        # 4. Calcola health score complessivo
        system_health = self._compute_system_health(inspection.components)

        # 5. Priorità azioni
        priority_actions = self._extract_priority_actions(diagnoses)

        # 6. Trend analysis
        trends = self._analyze_trends(inspection)

        duration = round(time.time() - started, 3)
        logger.info("Diagnosi completata: %d diagnosi, health=%.3f in %.1fs",
                     len(diagnoses), system_health, duration)

        return DiagnosisReport(
            cycle_id=cycle_id,
            timestamp=datetime.datetime.now().isoformat(),
            duration_sec=duration,
            total_diagnoses=len(diagnoses),
            diagnoses=diagnoses,
            system_health_score=system_health,
            priority_actions=priority_actions,
            trends=trends,
        )

    def _diagnose_component(self, name: str, ch: ComponentHealth,
                            inspection: InspectionReport) -> List[Diagnosis]:
        diags = []
        if not ch.findings:
            return diags

        critical = [f for f in ch.findings if f.severity == "critical"]
        errors = [f for f in ch.findings if f.severity == "error"]
        warnings = [f for f in ch.findings if f.severity == "warning"]

        if critical:
            diags.append(Diagnosis(
                root_cause=f"{name}: problemi critici rilevati",
                affected_components=[name],
                severity="critical",
                confidence=0.95,
                evidence=[f.title for f in critical[:5]],
                suggested_actions=[
                    f"Correggere immediatamente: {f.title}" for f in critical[:3]
                ],
                category="structural",
            ))

        if errors and len(errors) >= 3:
            error_types = Counter(f.category for f in errors)
            dominant = error_types.most_common(1)[0][0]
            diags.append(Diagnosis(
                root_cause=f"{name}: errori ricorrenti di categoria {dominant}",
                affected_components=[name],
                severity="error",
                confidence=0.85,
                evidence=[f"{f.title} ({f.file_path})" for f in errors[:5]],
                suggested_actions=[
                    f"Revisionare {dominant} in {name}",
                    "Eseguire test mirati sui moduli interessati",
                ],
                category=dominant,
            ))

        if warnings and len(warnings) >= 5:
            diags.append(Diagnosis(
                root_cause=f"{name}: elevato numero di warning ({len(warnings)})",
                affected_components=[name],
                severity="warning",
                confidence=0.7,
                evidence=[f.title for f in warnings[:5]],
                suggested_actions=[
                    "Pianificare pulizia tecnica (tech debt)",
                    f"Prioritizzare warning in {name}",
                ],
                category="code-quality",
            ))

        return diags

    def _diagnose_cross_component(self, inspection: InspectionReport) -> List[Diagnosis]:
        diags = []
        all_findings = []
        comp_map = {}
        for name, ch in inspection.components.items():
            for f in ch.findings:
                all_findings.append(f)
                comp_map[id(f)] = name

        todo_findings = [f for f in all_findings if f.category == "code-quality" and "MARKER" in f.title.upper()]
        if len(todo_findings) >= 5:
            comps = set(comp_map.get(id(f), "?") for f in todo_findings)
            diags.append(Diagnosis(
                root_cause=f"Marker TODO/FIXME/HACK diffusi in {len(comps)} componenti",
                affected_components=list(comps),
                severity="warning",
                confidence=0.8,
                evidence=[f"{f.title}: {f.detail[:80]}" for f in todo_findings[:5]],
                suggested_actions=[
                    "Pianificare sprint di completamento feature sospese",
                    "Risolvere marker FIXME e HACK prioritari",
                ],
                category="code-quality",
            ))

        security = [f for f in all_findings if f.category == "security"]
        if security:
            comps = set(comp_map.get(id(f), "?") for f in security)
            diags.append(Diagnosis(
                root_cause=f"Pattern di sicurezza rischiosi in {len(comps)} componenti",
                affected_components=list(comps),
                severity="error",
                confidence=0.9,
                evidence=[f.title for f in security[:5]],
                suggested_actions=[
                    "Revisionare eval/exec/subprocess per sicurezza",
                    "Valutare se i pattern sono necessari o sostituibili",
                ],
                category="security",
            ))

        import_errors = [f for f in all_findings if "non importabile" in f.title.lower()]
        if import_errors:
            diags.append(Diagnosis(
                root_cause=f"Moduli non importabili: {len(import_errors)} file",
                affected_components=list(set(
                    comp_map.get(id(f), "?") for f in import_errors
                )),
                severity="error",
                confidence=0.85,
                evidence=[f"{f.title}: {f.file_path}" for f in import_errors[:5]],
                suggested_actions=[
                    "Correggere dipendenze circolari e import mancanti",
                    "Verificare assenza di errori di sintassi",
                ],
                category="structural",
            ))

        return diags

    def _diagnose_architecture(self, inspection: InspectionReport) -> List[Diagnosis]:
        diags = []
        degraded = [n for n, c in inspection.components.items() if c.status == "degraded"]
        critical = [n for n, c in inspection.components.items() if c.status == "critical"]

        if critical:
            diags.append(Diagnosis(
                root_cause=f"Componenti in stato critico: {', '.join(critical)}",
                affected_components=critical,
                severity="critical",
                confidence=0.95,
                evidence=[f"{c}: score={inspection.components[c].score}" for c in critical],
                suggested_actions=[
                    f"Diagnosticare e correggere {c} con priorita massima" for c in critical
                ],
                category="structural",
            ))

        if len(degraded) >= 3:
            diags.append(Diagnosis(
                root_cause=f"Multipla degradazione: {len(degraded)} componenti degradati",
                affected_components=degraded,
                severity="warning",
                confidence=0.7,
                evidence=[f"{c}: score={inspection.components[c].score}" for c in degraded[:5]],
                suggested_actions=[
                    "Analizzare causa comune della degradazione multipla",
                    "Eseguire audit architetturale approfondito",
                ],
                category="structural",
            ))

        return diags

    def _compute_system_health(self, components: Dict[str, ComponentHealth]) -> float:
        if not components:
            return 0.0
        scores = [c.score for c in components.values()]
        return round(sum(scores) / len(scores), 4)

    def _extract_priority_actions(self, diagnoses: List[Diagnosis]) -> List[str]:
        actions = []
        seen = set()
        for d in sorted(diagnoses, key=lambda d: (
            {"critical": 0, "error": 1, "warning": 2, "info": 3}.get(d.severity, 4)
        )):
            for a in d.suggested_actions:
                if a not in seen:
                    actions.append(a)
                    seen.add(a)
            if len(actions) >= 10:
                break
        return actions

    def _analyze_trends(self, inspection: InspectionReport) -> Dict[str, Any]:
        now = datetime.datetime.now()
        return {
            "timestamp": now.isoformat(),
            "total_components": len(inspection.components),
            "healthy": sum(1 for c in inspection.components.values() if c.status == "healthy"),
            "degraded": sum(1 for c in inspection.components.values() if c.status == "degraded"),
            "critical": sum(1 for c in inspection.components.values() if c.status == "critical"),
            "error": sum(1 for c in inspection.components.values() if c.status == "error"),
            "total_findings": inspection.total_findings,
            "severity_breakdown": dict(Counter(
                f.severity for c in inspection.components.values() for f in c.findings
            )),
            "category_breakdown": dict(Counter(
                f.category for c in inspection.components.values() for f in c.findings
            )),
        }
