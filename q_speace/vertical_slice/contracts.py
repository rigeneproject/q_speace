"""Typed, privacy-safe telemetry contracts for the T208/T231 vertical slice."""

from __future__ import annotations

import hashlib
import json
import math
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

OutcomeStatus = Literal["answered", "refused", "fallback", "failed"]


def sha256_text(text: str) -> str:
    """Return the full lowercase SHA-256 hex digest of UTF-8 text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _check_optional_finite(name: str, value: float | None) -> None:
    if value is not None and not math.isfinite(value):
        raise ValueError(f"{name} must be finite (got {value!r})")


@dataclass(frozen=True)
class RequestRecord:
    """Privacy-safe request metadata (T208 §4.3)."""

    run_id: str
    request_id: str
    model_id: str
    model_revision: str | None
    policy_id: str
    prompt_hash: str
    started_at: str
    prompt_text: str | None = None

    def __post_init__(self) -> None:
        if not self.run_id or not self.request_id or not self.policy_id:
            raise ValueError("run_id, request_id, and policy_id must be non-empty")
        if not self.prompt_hash:
            raise ValueError("prompt_hash must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if data["prompt_text"] is None:
            del data["prompt_text"]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RequestRecord:
        return cls(
            run_id=str(data["run_id"]),
            request_id=str(data["request_id"]),
            model_id=str(data["model_id"]),
            model_revision=data.get("model_revision"),
            policy_id=str(data["policy_id"]),
            prompt_hash=str(data["prompt_hash"]),
            started_at=str(data["started_at"]),
            prompt_text=data.get("prompt_text"),
        )


@dataclass(frozen=True)
class DecisionRecord:
    """Deterministic routing and gate decision trace (T208 §4.3)."""

    route: str
    gate_open: bool
    decision_reason: str
    predicted_energy_j: float | None
    confidence: float | None
    thresholds: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.route or not self.decision_reason:
            raise ValueError("route and decision_reason must be non-empty")
        _check_optional_finite("predicted_energy_j", self.predicted_energy_j)
        _check_optional_finite("confidence", self.confidence)
        for k, v in self.thresholds.items():
            if not math.isfinite(v):
                raise ValueError(f"threshold {k!r} must be finite (got {v!r})")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DecisionRecord:
        return cls(
            route=str(data["route"]),
            gate_open=bool(data["gate_open"]),
            decision_reason=str(data["decision_reason"]),
            predicted_energy_j=(
                float(data["predicted_energy_j"])
                if data.get("predicted_energy_j") is not None
                else None
            ),
            confidence=float(data["confidence"]) if data.get("confidence") is not None else None,
            thresholds={str(k): float(v) for k, v in dict(data.get("thresholds", {})).items()},
        )


@dataclass(frozen=True)
class OutcomeRecord:
    """Measured or simulated request outcome (T208 §4.3)."""

    status: OutcomeStatus
    latency_s: float
    tokens_in: int | None
    tokens_out: int | None
    measured_energy_j: float | None
    response_hash: str | None
    response_text: str | None = None

    def __post_init__(self) -> None:
        if self.status not in ("answered", "refused", "fallback", "failed"):
            raise ValueError(f"invalid status: {self.status!r}")
        if not math.isfinite(self.latency_s) or self.latency_s < 0.0:
            raise ValueError(f"latency_s must be finite and >= 0 (got {self.latency_s!r})")
        _check_optional_finite("measured_energy_j", self.measured_energy_j)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if data["response_text"] is None:
            del data["response_text"]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OutcomeRecord:
        status_raw = str(data["status"])
        if status_raw not in ("answered", "refused", "fallback", "failed"):
            raise ValueError(f"invalid status: {status_raw!r}")
        status: OutcomeStatus = status_raw  # type: ignore[assignment]
        return cls(
            status=status,
            latency_s=float(data["latency_s"]),
            tokens_in=int(data["tokens_in"]) if data.get("tokens_in") is not None else None,
            tokens_out=int(data["tokens_out"]) if data.get("tokens_out") is not None else None,
            measured_energy_j=(
                float(data["measured_energy_j"])
                if data.get("measured_energy_j") is not None
                else None
            ),
            response_hash=data.get("response_hash"),
            response_text=data.get("response_text"),
        )


@dataclass(frozen=True)
class TraceRecord:
    """Complete request + decision + outcome record for one benchmark case."""

    case_id: str
    request: RequestRecord
    decision: DecisionRecord
    outcome: OutcomeRecord

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "request": self.request.to_dict(),
            "decision": self.decision.to_dict(),
            "outcome": self.outcome.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TraceRecord:
        return cls(
            case_id=str(data["case_id"]),
            request=RequestRecord.from_dict(data["request"]),
            decision=DecisionRecord.from_dict(data["decision"]),
            outcome=OutcomeRecord.from_dict(data["outcome"]),
        )


@dataclass(frozen=True)
class ExperimentManifest:
    """Reproducible experiment manifest (T208 §5.2)."""

    manifest_version: str
    run_id: str
    created_at: str
    git_commit: str | None
    git_dirty: bool | None
    python_version: str
    platform: str
    model_id: str
    model_revision: str | None
    dataset_id: str
    dataset_sha256: str
    dataset_size: int
    policy_id: str
    policy_config: dict[str, Any]
    seed: int
    include_raw_text: bool
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExperimentManifest:
        return cls(
            manifest_version=str(data["manifest_version"]),
            run_id=str(data["run_id"]),
            created_at=str(data["created_at"]),
            git_commit=data.get("git_commit"),
            git_dirty=data.get("git_dirty"),
            python_version=str(data["python_version"]),
            platform=str(data["platform"]),
            model_id=str(data["model_id"]),
            model_revision=data.get("model_revision"),
            dataset_id=str(data["dataset_id"]),
            dataset_sha256=str(data["dataset_sha256"]),
            dataset_size=int(data["dataset_size"]),
            policy_id=str(data["policy_id"]),
            policy_config=dict(data.get("policy_config", {})),
            seed=int(data["seed"]),
            include_raw_text=bool(data["include_raw_text"]),
            summary=dict(data.get("summary", {})),
        )


def capture_git_state(cwd: Path | None = None) -> tuple[str | None, bool | None]:
    """Best-effort git commit and dirty-tree capture for manifests."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if commit.returncode != 0:
            return None, None
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        dirty = bool(status.stdout.strip()) if status.returncode == 0 else None
        return commit.stdout.strip() or None, dirty
    except OSError:
        return None, None


def runtime_environment() -> tuple[str, str]:
    return sys.version.split()[0], platform.platform()


def write_traces_jsonl(path: Path, traces: list[TraceRecord]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(t.to_dict(), sort_keys=True, ensure_ascii=False, allow_nan=False) for t in traces
    ]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return path


def read_traces_jsonl(path: Path) -> list[TraceRecord]:
    out: list[TraceRecord] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            out.append(TraceRecord.from_dict(json.loads(raw)))
    return out


def write_manifest(path: Path, manifest: ExperimentManifest) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return path


def read_manifest(path: Path) -> ExperimentManifest:
    return ExperimentManifest.from_dict(json.loads(path.read_text(encoding="utf-8")))
