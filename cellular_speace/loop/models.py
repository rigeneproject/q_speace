from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Finding:
    component: str
    subcomponent: str
    severity: str  # critical / error / warning / info
    category: str  # structural / functional / code-quality / security / dna / data
    title: str
    detail: str
    file_path: Optional[str] = None
    line: Optional[int] = None
    suggestion: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.datetime.now().isoformat())


@dataclass
class ComponentHealth:
    component: str
    status: str  # healthy / degraded / critical / unknown
    score: float  # 0.0 - 1.0
    findings: List[Finding] = field(default_factory=list)
    subcomponent_health: Dict[str, str] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InspectionReport:
    cycle_id: str
    timestamp: str
    duration_sec: float
    total_findings: int
    components: Dict[str, ComponentHealth]
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Diagnosis:
    root_cause: str
    affected_components: List[str]
    severity: str
    confidence: float
    evidence: List[str]
    suggested_actions: List[str]
    category: str


@dataclass
class DiagnosisReport:
    cycle_id: str
    timestamp: str
    duration_sec: float
    total_diagnoses: int
    diagnoses: List[Diagnosis]
    system_health_score: float
    priority_actions: List[str]
    trends: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationAction:
    action_type: str  # fix / refactor / proposal / config-change / ignore
    description: str
    target_file: Optional[str] = None
    target_component: Optional[str] = None
    code_before: Optional[str] = None
    code_after: Optional[str] = None
    status: str = "pending"  # pending / applied / failed / skipped
    backup_file: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.datetime.now().isoformat())


@dataclass
class OptimizationReport:
    cycle_id: str
    timestamp: str
    duration_sec: float
    total_actions: int
    applied: int
    failed: int
    skipped: int
    actions: List[OptimizationAction]
    summary: str


@dataclass
class IDOCycleResult:
    cycle_id: str
    started_at: str
    finished_at: str
    duration_sec: float
    inspection: InspectionReport
    diagnosis: DiagnosisReport
    optimization: OptimizationReport
    system_health_before: float
    system_health_after: float
    improvement: float
