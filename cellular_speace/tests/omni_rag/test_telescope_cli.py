"""Tests for the Omni-RAG telescope CLI wiring (T172/B3).

These tests assert that `speace omni telescope` is reachable from the
registered Typer app, and that it returns the 10 cognitive factors
defined in `scripts/print_cognitive_telescope.py` (single source of
truth — `tests/cognitive_factors/test_telescope_units.py` already
covers the script's contents directly).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from speace_core.cli import app
from speace_core.omni_rag.cli_commands import omni_app

FACTOR_KEYS = {
    "wm",
    "speed",
    "pattern",
    "knowledge",
    "abstraction",
    "relational",
    "metacognition",
    "attention",
    "motivation",
    "flexibility",
}


# --------------------------------------------------------------------------- #
# Typer-level: command is registered on omni_app
# --------------------------------------------------------------------------- #


def test_omni_app_has_telescope_command():
    """The Typer app must expose a `telescope` command (T172/B3 wiring)."""
    runner = CliRunner()
    result = runner.invoke(omni_app, ["--help"])
    assert result.exit_code == 0, result.stdout
    assert "telescope" in result.stdout, (
        "telescope command must be visible in `omni --help`; "
        f"got: {result.stdout!r}"
    )


def test_omni_telescope_help_describes_purpose():
    runner = CliRunner()
    result = runner.invoke(omni_app, ["telescope", "--help"])
    assert result.exit_code == 0, result.stdout
    # The help text must mention the 10 cognitive factors.
    assert "Cognitive Factors Telescope" in result.stdout
    assert "10" in result.stdout


# --------------------------------------------------------------------------- #
# Subprocess smoke: real CLI produces real JSON
# --------------------------------------------------------------------------- #


REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "speace_core.cli", "omni", "telescope", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )


def test_subprocess_omni_telescope_text_mode():
    """End-to-end: the top-level CLI app must run `omni telescope`."""
    proc = _run_cli("--format", "text")
    assert proc.returncode == 0, f"stderr={proc.stderr}\nstdout={proc.stdout}"
    # Text mode prints the header and a line per factor.
    assert "Cognitive Factors Telescope" in proc.stdout
    assert "Timestamp" in proc.stdout


def test_subprocess_omni_telescope_json_mode_has_ten_factors():
    proc = _run_cli("--format", "json")
    assert proc.returncode == 0, f"stderr={proc.stderr}\nstdout={proc.stdout}"
    payload = json.loads(proc.stdout)
    assert "factors" in payload
    assert set(payload["factors"].keys()) == FACTOR_KEYS, (
        f"expected 10 factors, got {sorted(payload['factors'].keys())}"
    )


def test_subprocess_omni_telescope_json_writes_output_file(tmp_path):
    out = tmp_path / "snapshot.json"
    proc = _run_cli("--format", "json", "--output", str(out))
    assert proc.returncode == 0, f"stderr={proc.stderr}\nstdout={proc.stdout}"
    assert out.exists(), f"expected snapshot file at {out}"
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert set(payload["factors"].keys()) == FACTOR_KEYS