"""Stratified failure taxonomy, GC MemoryLeakAuditor & DifferentialErrorRatchet (T249-06).

Synthesized via BCEL from:
- ``cellular_speace_gpt`` (``arc_agi_report_analyzer.py``): regime-stratified
  separation of gate/candidate starvation vs confident errors vs near-misses.
- ``cellular_speace_opus`` (``memory_leak_auditor.py``): deterministic ``gc``
  object-count growth detector & unbounded history container check.
- ``cellular_speace_big`` (``auto_improve_daemon.py``): persisted set-difference
  error ratchet ``|E_t \\ E_base| == 0`` with zero source-tree mutation.
"""

from __future__ import annotations

import gc
import json
import math
from collections import Counter, deque
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .contracts import TraceRecord


@dataclass(frozen=True)
class RegimeFailureSummary:
    """Counts per failure taxonomy category inside one input regime."""

    regime: str
    total: int
    correct_answered: int
    gate_starvation: int
    confident_error: int
    near_miss_partial: int
    execution_failed: int


@dataclass(frozen=True)
class StratifiedDiagnosticReport:
    """Complete stratified failure report across regimes (T249-06)."""

    total_cases: int
    regimes: dict[str, RegimeFailureSummary]
    recommendations: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "total_cases": self.total_cases,
            "regimes": {
                k: {
                    "regime": v.regime,
                    "total": v.total,
                    "correct_answered": v.correct_answered,
                    "gate_starvation": v.gate_starvation,
                    "confident_error": v.confident_error,
                    "near_miss_partial": v.near_miss_partial,
                    "execution_failed": v.execution_failed,
                }
                for k, v in self.regimes.items()
            },
            "recommendations": list(self.recommendations),
        }


class StratifiedFailureAnalyzer:
    """Partitions vertical-slice traces by regime and failure mode (T249-06)."""

    def __init__(
        self,
        *,
        high_energy_j: float = 40.0,
        long_tokens_in: int = 64,
        confident_error_threshold: float = 0.70,
    ) -> None:
        if not math.isfinite(high_energy_j) or high_energy_j < 0.0:
            raise ValueError("high_energy_j must be finite and >= 0")
        if long_tokens_in < 1:
            raise ValueError("long_tokens_in must be >= 1")
        if not math.isfinite(confident_error_threshold) or not (
            0.0 <= confident_error_threshold <= 1.0
        ):
            raise ValueError("confident_error_threshold must be finite and in [0, 1]")
        self.high_energy_j = float(high_energy_j)
        self.long_tokens_in = long_tokens_in
        self.confident_error_threshold = float(confident_error_threshold)

    def _classify_regime(self, trace: TraceRecord) -> str:
        pred_e = trace.decision.predicted_energy_j or 0.0
        tok_in = trace.outcome.tokens_in or 0
        if pred_e >= self.high_energy_j or tok_in >= self.long_tokens_in:
            return "high_demand"
        return "compact"

    def analyze(
        self,
        traces: Sequence[TraceRecord],
        labels: Mapping[str, bool],
    ) -> StratifiedDiagnosticReport:
        """Analyze ``traces`` against ground-truth correctness/answerability ``labels``."""
        buckets: dict[str, dict[str, int]] = {}
        for tr in traces:
            regime = self._classify_regime(tr)
            b = buckets.setdefault(
                regime,
                {
                    "total": 0,
                    "correct_answered": 0,
                    "gate_starvation": 0,
                    "confident_error": 0,
                    "near_miss_partial": 0,
                    "execution_failed": 0,
                },
            )
            b["total"] += 1
            is_correct = bool(labels.get(tr.case_id, labels.get(tr.request.request_id, False)))
            status = tr.outcome.status
            conf = tr.decision.confidence if tr.decision.confidence is not None else 0.0

            if status == "failed":
                b["execution_failed"] += 1
            elif status in ("refused", "fallback"):
                if is_correct:
                    b["gate_starvation"] += 1
                else:
                    b["correct_answered"] += 1
            elif is_correct:
                b["correct_answered"] += 1
            elif conf >= self.confident_error_threshold:
                b["confident_error"] += 1
            else:
                b["near_miss_partial"] += 1

        summaries = {
            reg: RegimeFailureSummary(
                regime=reg,
                total=vals["total"],
                correct_answered=vals["correct_answered"],
                gate_starvation=vals["gate_starvation"],
                confident_error=vals["confident_error"],
                near_miss_partial=vals["near_miss_partial"],
                execution_failed=vals["execution_failed"],
            )
            for reg, vals in sorted(buckets.items())
        }

        recs: list[str] = []
        total_starved = sum(s.gate_starvation for s in summaries.values())
        total_conf_err = sum(s.confident_error for s in summaries.values())
        if total_starved > 0:
            recs.append(
                "Gate starvation detected on valid cases: review max_energy_j or min_confidence thresholds."
            )
        if total_conf_err > 0:
            recs.append(
                "Overconfident errors detected: recalibrate confidence threshold or attach TruthEngine."
            )
        if not recs:
            recs.append("No gate starvation or overconfident error clusters detected.")

        return StratifiedDiagnosticReport(
            total_cases=len(traces),
            regimes=summaries,
            recommendations=tuple(recs),
        )


@dataclass(frozen=True)
class LeakAuditReport:
    """Result of one GC object-growth & history-container boundedness audit."""

    passed: bool
    suspected_type_growth: dict[str, float]
    unbounded_containers: tuple[str, ...]


class MemoryLeakAuditor:
    """Deterministic GC object-count growth & bounded-history auditor (T249-06)."""

    def __init__(
        self,
        *,
        max_growth_ratio: float = 0.20,
        min_baseline_count: int = 100,
    ) -> None:
        if not math.isfinite(max_growth_ratio) or max_growth_ratio <= 0.0:
            raise ValueError("max_growth_ratio must be finite and > 0")
        if min_baseline_count < 1:
            raise ValueError("min_baseline_count must be >= 1")
        self.max_growth_ratio = float(max_growth_ratio)
        self.min_baseline_count = min_baseline_count
        self._baseline: Counter[str] | None = None

    @staticmethod
    def _count_gc_types() -> Counter[str]:
        gc.collect()
        counts: Counter[str] = Counter()
        for obj in gc.get_objects():
            counts[type(obj).__qualname__] += 1
        return counts

    def capture_baseline(self) -> Counter[str]:
        self._baseline = self._count_gc_types()
        return Counter(self._baseline)

    def audit(
        self,
        inspected_objects: Mapping[str, object] | None = None,
        *,
        history_attrs: Sequence[str] = ("_history", "_spike_history"),
    ) -> LeakAuditReport:
        if self._baseline is None:
            self.capture_baseline()
        assert self._baseline is not None

        current = self._count_gc_types()
        suspected: dict[str, float] = {}
        for type_name, base_n in self._baseline.items():
            if base_n < self.min_baseline_count:
                continue
            cur_n = current.get(type_name, 0)
            growth = (cur_n - base_n) / base_n
            if growth > self.max_growth_ratio:
                suspected[type_name] = round(float(growth), 4)

        unbounded: list[str] = []
        if inspected_objects is not None:
            for obj_name, obj in inspected_objects.items():
                for attr in history_attrs:
                    if not hasattr(obj, attr):
                        continue
                    val = getattr(obj, attr)
                    if isinstance(val, list) or (isinstance(val, deque) and val.maxlen is None):
                        unbounded.append(f"{obj_name}.{attr}")

        passed = len(unbounded) == 0
        return LeakAuditReport(
            passed=passed,
            suspected_type_growth=suspected,
            unbounded_containers=tuple(sorted(unbounded)),
        )


@dataclass(frozen=True)
class RatchetVerdict:
    """Set-differential static/test regression verdict against a persisted baseline."""

    passed: bool
    new_errors: tuple[str, ...]
    fixed_errors: tuple[str, ...]
    remaining_count: int


class DifferentialErrorRatchet:
    """Monotonic set-difference error ratchet ``|E_t \\ E_base| == 0`` (T249-06)."""

    def __init__(self, baseline_path: Path) -> None:
        self.baseline_path = baseline_path

    def save_baseline(self, errors: Iterable[str]) -> list[str]:
        canonical = sorted({e.strip() for e in errors if e.strip()})
        self.baseline_path.parent.mkdir(parents=True, exist_ok=True)
        self.baseline_path.write_text(
            json.dumps({"baseline_errors": canonical}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return canonical

    def load_baseline(self) -> set[str]:
        if not self.baseline_path.exists():
            return set()
        raw = json.loads(self.baseline_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or not isinstance(raw.get("baseline_errors"), list):
            raise ValueError("invalid baseline JSON format")
        return {str(x) for x in raw["baseline_errors"]}

    def check(self, current_errors: Iterable[str]) -> RatchetVerdict:
        base = self.load_baseline()
        cur = {e.strip() for e in current_errors if e.strip()}
        new_err = tuple(sorted(cur - base))
        fixed_err = tuple(sorted(base - cur))
        return RatchetVerdict(
            passed=len(new_err) == 0,
            new_errors=new_err,
            fixed_errors=fixed_err,
            remaining_count=len(cur),
        )
