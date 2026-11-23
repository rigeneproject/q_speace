"""Regression and smoke tests for the Q-SPEACE CLI (T230)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from q_speace.cli import app

runner = CliRunner()


def test_cli_version() -> None:
    res = runner.invoke(app, ["version"])
    assert res.exit_code == 0
    assert res.output.strip()


def test_cli_quantum_run_and_zero_ticks_radio() -> None:
    res = runner.invoke(app, ["quantum", "run", "--ticks", "2", "--neurons", "2", "--radio"])
    assert res.exit_code == 0
    assert "Ran 2 ticks" in res.output
    assert "[green]" not in res.output
    assert "Last TX:" in res.output
    assert "Spectrum:" in res.output

    # Regression: --ticks 0 --radio must not crash with IndexError
    res_zero = runner.invoke(app, ["quantum", "run", "--ticks", "0", "--neurons", "2", "--radio"])
    assert res_zero.exit_code == 0
    assert "Ran 0 ticks" in res_zero.output


def test_cli_quantum_benchmark_reports_fallback() -> None:
    res = runner.invoke(
        app, ["quantum", "benchmark", "--qubits", "2", "--ticks", "2", "--backend", "qiskit"]
    )
    assert res.exit_code == 0
    assert "Backend: numpy (fallback from qiskit)" in res.output
    assert "Mean coherence:" in res.output
    assert "[cyan]" not in res.output


def test_cli_quantum_synthesize_cqasm_bridge_cross_scale_qee() -> None:
    res_syn = runner.invoke(app, ["quantum", "synthesize"])
    assert res_syn.exit_code == 0
    assert "Real quantum backend noise-model and energy gate (T230)" in res_syn.output
    assert "[yellow]" not in res_syn.output

    res_cqasm = runner.invoke(app, ["quantum", "cqasm", "--qubits", "2", "--tick", "0"])
    assert res_cqasm.exit_code == 0
    assert "version 3.0" in res_cqasm.output

    res_bridge = runner.invoke(app, ["quantum", "bridge", "--atom", "0.6", "--brain", "0.4"])
    assert res_bridge.exit_code == 0
    assert "version 3.0" in res_bridge.output

    res_cs = runner.invoke(app, ["quantum", "cross-scale", "--ticks", "3"])
    assert res_cs.exit_code == 0
    assert "cross-scale emergence:" in res_cs.output

    res_qee = runner.invoke(app, ["quantum", "qee"])
    assert res_qee.exit_code == 0
    assert "QEE proposed" in res_qee.output


def test_cli_sia_commands() -> None:
    res_run = runner.invoke(app, ["sia", "run", "--ticks", "2", "--verbose"])
    assert res_run.exit_code == 0
    assert "tick=0:" in res_run.output

    res_status = runner.invoke(app, ["sia", "status"])
    assert res_status.exit_code == 0

    res_dna = runner.invoke(app, ["sia", "dna", "--limit", "5"])
    assert res_dna.exit_code == 0
    assert "DNA mutation records" in res_dna.output

    res_bench = runner.invoke(
        app, ["sia", "benchmark", "--min-qubits", "2", "--max-qubits", "2", "--trials", "1"]
    )
    assert res_bench.exit_code == 0
    assert "QEE GPU Benchmark Report" in res_bench.output


def test_cli_brain_commands() -> None:
    res_think = runner.invoke(app, ["brain", "think", "hello", "--tokens", "4", "--json"])
    assert res_think.exit_code == 0
    payload = json.loads(res_think.output)
    assert payload["backend"] == "stub"
    assert isinstance(payload["belief"], list)

    res_think_txt = runner.invoke(app, ["brain", "think", "hello", "--tokens", "4"])
    assert res_think_txt.exit_code == 0
    assert "backend: stub" in res_think_txt.output
    assert "[green]" not in res_think_txt.output

    res_tick = runner.invoke(app, ["brain", "tick", "hello", "--tokens", "4", "--verbose"])
    assert res_tick.exit_code == 0
    assert "approved:" in res_tick.output

    res_health = runner.invoke(app, ["brain", "health"])
    assert res_health.exit_code == 0
    assert json.loads(res_health.output)["ready"] is True

    res_chat = runner.invoke(
        app, ["brain", "chat", "--backend", "stub", "--turns", "2"], input="q\n"
    )
    assert res_chat.exit_code == 0
    assert "[brain] final stats:" in res_chat.output


def test_cli_economy_commands() -> None:
    res_all = runner.invoke(app, ["economy", "validate-schema", "all"])
    assert res_all.exit_code == 0
    assert "j_c OK" in res_all.output
    assert "[green]" not in res_all.output

    res_bad = runner.invoke(app, ["economy", "validate-schema", "../secret"])
    assert res_bad.exit_code != 0

    res_jc = runner.invoke(
        app,
        [
            "economy",
            "jc-from-telemetry",
            "--J",
            "10.0",
            "--delta-S",
            "-0.5",
            "--delta-I-c",
            "2.0",
            "--R-b",
            "0.8",
            "--delta-C",
            "0.2",
        ],
    )
    assert res_jc.exit_code == 0
    parsed = json.loads(res_jc.output)
    assert parsed["J"] == 10.0
    assert parsed["confidence"] == 1.0

    res_mcp = runner.invoke(app, ["economy", "mcp-self-test"])
    assert res_mcp.exit_code == 0
    assert "all 14 tools green" in res_mcp.output
