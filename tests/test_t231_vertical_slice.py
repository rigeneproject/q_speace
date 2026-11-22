"""Tests for T208 Group B / T231 vertical-slice contracts, policies, runner, evaluator, and CLI."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from typer.testing import CliRunner

from q_speace.bcel import BCELCatalog
from q_speace.cli import app
from q_speace.spiking_brain import SpikingBrainCortex, StubSpikingBrain
from q_speace.vertical_slice import (
    BenchmarkCase,
    DecisionRecord,
    OutcomeRecord,
    PolicyConfig,
    RequestRecord,
    TraceRecord,
    VerticalSliceRunner,
    compare_policies,
    compute_calibration,
    default_fixture_dataset,
    default_policy,
    evaluate_policy,
    evaluate_traces,
    paired_bootstrap_ci,
    read_manifest,
    read_traces_jsonl,
    sha256_text,
    write_manifest,
    write_traces_jsonl,
)

cli_runner = CliRunner()


def test_bcel_entry_registered_for_t231() -> None:
    cat = BCELCatalog()
    assert cat.is_functional("Vertical-slice telemetry and gate policy contracts (T231)") is True


def test_contract_roundtrip_and_default_privacy(tmp_path: Path) -> None:
    dataset = default_fixture_dataset()
    runner = VerticalSliceRunner(
        policy=default_policy("always_answer"),
        seed=7,
        include_raw_text=False,
    )
    traces, manifest = runner.run_dataset(dataset, run_id="run-privacy-check")
    assert len(traces) == len(dataset.cases)

    traces_path = write_traces_jsonl(tmp_path / "traces.jsonl", traces)
    manifest_path = write_manifest(tmp_path / "manifest.json", manifest)

    # T208 §4.3: raw prompts and responses must NOT appear in default telemetry.
    raw_jsonl = traces_path.read_text(encoding="utf-8")
    raw_manifest = manifest_path.read_text(encoding="utf-8")
    for case in dataset.cases:
        assert case.prompt not in raw_jsonl
        assert case.prompt not in raw_manifest
    assert "prompt_text" not in raw_jsonl
    assert "response_text" not in raw_jsonl

    # Full round-trip deserialization matches original records.
    loaded_traces = read_traces_jsonl(traces_path)
    loaded_manifest = read_manifest(manifest_path)
    assert loaded_traces == traces
    assert loaded_manifest == manifest


def test_contract_validation_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        RequestRecord(
            run_id="",
            request_id="r1",
            model_id="stub",
            model_revision=None,
            policy_id="p1",
            prompt_hash="abc",
            started_at="2026-11-22T00:00:00Z",
        )
    with pytest.raises(ValueError):
        DecisionRecord(
            route="language",
            gate_open=True,
            decision_reason="ok",
            predicted_energy_j=float("nan"),
            confidence=0.5,
        )
    with pytest.raises(ValueError):
        OutcomeRecord(
            status="answered",
            latency_s=-0.1,
            tokens_in=1,
            tokens_out=1,
            measured_energy_j=1.0,
            response_hash="abc",
        )
    with pytest.raises(ValueError):
        PolicyConfig(policy_id="bad", kind="confidence_gate", min_confidence=1.5)


def test_policy_precedence_and_opt_in_rollback() -> None:
    cfg = PolicyConfig(
        policy_id="comb",
        kind="combined_gate",
        min_confidence=0.8,
        max_energy_j=50.0,
        sevo_threshold=1.5,
        min_coherence_phi=0.1,
    )
    # Energy gate takes precedence over confidence gate when both fail.
    d_energy = evaluate_policy(
        cfg,
        route="language",
        predicted_energy_j=100.0,
        confidence=0.1,
        sevo=0.2,
        coherence_phi=0.01,
    )
    assert d_energy.gate_open is False
    assert d_energy.decision_reason == "energy_gate_exceeded"

    # Confidence gate fails when energy passes.
    d_conf = evaluate_policy(
        cfg,
        route="language",
        predicted_energy_j=10.0,
        confidence=0.4,
        sevo=3.0,
        coherence_phi=0.9,
    )
    assert d_conf.gate_open is False
    assert d_conf.decision_reason == "confidence_gate_below_threshold"

    # Non-finite confidence fails closed.
    d_nan = evaluate_policy(
        cfg,
        route="language",
        predicted_energy_j=10.0,
        confidence=float("nan"),
        sevo=3.0,
        coherence_phi=0.9,
    )
    assert d_nan.gate_open is False
    assert d_nan.decision_reason == "confidence_gate_below_threshold"

    # Disabled policy cleanly rolls back to passthrough.
    disabled = PolicyConfig(policy_id="off", kind="combined_gate", enabled=False)
    d_off = evaluate_policy(
        disabled,
        route="language",
        predicted_energy_j=999.0,
        confidence=0.0,
        sevo=0.0,
        coherence_phi=0.0,
    )
    assert d_off.gate_open is True
    assert d_off.decision_reason == "policy_disabled_passthrough"


def test_runner_failure_paths_timeout_malformed_and_non_mutation() -> None:
    class _SlowBackend:
        backend_name = "slow"

        async def think(self, *args: Any, **kwargs: Any) -> Any:
            await asyncio.sleep(0.5)
            return None

    class _MalformedBackend:
        backend_name = "malformed"

        def think(self, *args: Any, **kwargs: Any) -> Any:
            return {"not": "a ThinkResult"}

    case = BenchmarkCase(case_id="c1", family="factual", prompt="hello world", should_answer=True)

    # Timeout path
    slow_cortex = SpikingBrainCortex(backend=_SlowBackend())
    ilf_phi_before = slow_cortex.ilf.coherence_phi
    slow_runner = VerticalSliceRunner(
        cortex=slow_cortex,
        policy=default_policy("combined_gate"),
        timeout_s=0.02,
    )
    tr_timeout = asyncio.run(slow_runner.execute_case(case, run_id="r-to"))
    assert tr_timeout.outcome.status == "failed"
    assert tr_timeout.decision.decision_reason == "backend_timeout"
    assert slow_cortex.ilf.coherence_phi == ilf_phi_before

    # Malformed backend response path
    bad_cortex = SpikingBrainCortex(backend=_MalformedBackend())
    bad_runner = VerticalSliceRunner(cortex=bad_cortex, policy=default_policy("always_answer"))
    tr_bad = asyncio.run(bad_runner.execute_case(case, run_id="r-bad"))
    assert tr_bad.outcome.status == "failed"
    assert tr_bad.decision.decision_reason.startswith("backend_error:")

    # Empty prompt routes away from language and never invokes backend
    empty_case = BenchmarkCase(
        case_id="c-empty", family="abstention", prompt="", should_answer=False
    )
    tr_empty = asyncio.run(bad_runner.execute_case(empty_case, run_id="r-empty"))
    assert tr_empty.outcome.status == "refused"
    assert tr_empty.decision.decision_reason == "route_non_language"

    # Energy gate blocks before backend invocation and leaves ILF untouched
    called = False

    class _SpyBackend(StubSpikingBrain):
        def think(self, *args: Any, **kwargs: Any) -> Any:
            nonlocal called
            called = True
            return super().think(*args, **kwargs)

    spy_cortex = SpikingBrainCortex(backend=_SpyBackend(seed=0))
    eng_runner = VerticalSliceRunner(
        cortex=spy_cortex,
        policy=PolicyConfig(
            policy_id="tight-energy",
            kind="energy_gate",
            max_energy_j=0.01,
            fallback_mode="fallback",
        ),
    )
    tr_eng = asyncio.run(eng_runner.execute_case(case, run_id="r-eng"))
    assert tr_eng.outcome.status == "fallback"
    assert tr_eng.decision.decision_reason == "energy_gate_exceeded"
    assert called is False


def test_calibration_rejects_degenerate_labels_and_computes_brier_ece() -> None:
    with pytest.raises(ValueError, match="degenerate calibration labels"):
        compute_calibration([0.9, 0.8, 0.7], [True, True, True])
    with pytest.raises(ValueError, match="degenerate calibration labels"):
        compute_calibration([0.1, 0.2], [False, False])

    cal = compute_calibration([0.9, 0.8, 0.2, 0.1], [True, True, False, False])
    assert cal.n_samples == 4
    assert cal.n_positive == 2
    assert cal.n_negative == 2
    assert 0.0 <= cal.brier_score < 0.05
    assert 0.0 <= cal.ece <= 0.2


def test_paired_bootstrap_and_policy_comparison() -> None:
    dataset = default_fixture_dataset()
    base_traces, _ = VerticalSliceRunner(
        policy=default_policy("always_answer"), seed=0
    ).run_dataset(dataset, run_id="base")
    cand_traces, _ = VerticalSliceRunner(
        policy=PolicyConfig(
            policy_id="t209-energy_gate",
            kind="energy_gate",
            max_energy_j=68.0,
        ),
        seed=0,
    ).run_dataset(dataset, run_id="cand")

    comp = compare_policies(base_traces, cand_traces, dataset, n_resamples=200, seed=42)
    assert comp["dataset_id"] == dataset.dataset_id
    assert comp["candidate"]["refused"] > 0
    assert comp["paired_deltas"]["energy_j"]["mean"] < 0.0

    # Paired bootstrap sanity check
    delta, lo, hi = paired_bootstrap_ci([1.0, 2.0, 3.0], [2.0, 3.0, 4.0], n_resamples=200, seed=0)
    assert delta == pytest.approx(1.0)
    assert lo == pytest.approx(1.0)
    assert hi == pytest.approx(1.0)

    # Verify sha256 helper determinism and TraceRecord roundtrip
    assert len(sha256_text("abc")) == 64
    assert TraceRecord.from_dict(base_traces[0].to_dict()) == base_traces[0]
    assert np.isfinite(evaluate_traces(base_traces, dataset).mean_energy_j)


def test_cli_eval_run_and_compare(tmp_path: Path) -> None:
    out_run = tmp_path / "run_out"
    res = cli_runner.invoke(
        app,
        ["eval", "run", "--policy", "combined_gate", "--output", str(out_run), "--seed", "1"],
    )
    assert res.exit_code == 0
    assert (out_run / "traces.jsonl").exists()
    assert (out_run / "manifest.json").exists()
    assert (out_run / "evaluation.json").exists()

    # Invalid policy returns non-zero exit code
    res_bad = cli_runner.invoke(
        app, ["eval", "run", "--policy", "nonexistent", "--output", str(tmp_path / "bad")]
    )
    assert res_bad.exit_code != 0

    out_cmp = tmp_path / "cmp_out"
    res_cmp = cli_runner.invoke(
        app,
        [
            "eval",
            "compare",
            "--candidate",
            "energy_gate",
            "--max-energy-j",
            "68.0",
            "--output",
            str(out_cmp),
            "--seed",
            "1",
        ],
    )
    assert res_cmp.exit_code == 0
    comp = json.loads((out_cmp / "comparison.json").read_text(encoding="utf-8"))
    assert comp["baseline"]["policy_id"] == "t209-always_answer"
    assert comp["candidate"]["policy_id"] == "t209-energy_gate"
