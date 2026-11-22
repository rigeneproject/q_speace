"""T208 Group B / T231 reference vertical-slice contracts, policies, and evaluator."""

from __future__ import annotations

from .contracts import (
    DecisionRecord,
    ExperimentManifest,
    OutcomeRecord,
    OutcomeStatus,
    RequestRecord,
    TraceRecord,
    read_manifest,
    read_traces_jsonl,
    sha256_text,
    write_manifest,
    write_traces_jsonl,
)
from .dataset import BenchmarkCase, BenchmarkDataset, default_fixture_dataset
from .evaluator import (
    CalibrationMetrics,
    PolicyEvaluation,
    compare_policies,
    compute_calibration,
    evaluate_traces,
    paired_bootstrap_ci,
)
from .policies import (
    VALID_POLICY_KINDS,
    FallbackMode,
    PolicyConfig,
    PolicyKind,
    default_policy,
    evaluate_policy,
)
from .runner import VerticalSliceRunner

__all__ = [
    "BenchmarkCase",
    "BenchmarkDataset",
    "CalibrationMetrics",
    "DecisionRecord",
    "ExperimentManifest",
    "FallbackMode",
    "OutcomeRecord",
    "OutcomeStatus",
    "PolicyConfig",
    "PolicyEvaluation",
    "PolicyKind",
    "RequestRecord",
    "TraceRecord",
    "VALID_POLICY_KINDS",
    "VerticalSliceRunner",
    "compare_policies",
    "compute_calibration",
    "default_fixture_dataset",
    "default_policy",
    "evaluate_policy",
    "evaluate_traces",
    "paired_bootstrap_ci",
    "read_manifest",
    "read_traces_jsonl",
    "sha256_text",
    "write_manifest",
    "write_traces_jsonl",
]
