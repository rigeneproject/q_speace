"""CLI tests for the TFTpsp commands."""

import pytest
from typer.testing import CliRunner

from speace_core.cli import app


runner = CliRunner()


# ---------------------------------------------------------------------------
# tftpsp-list
# ---------------------------------------------------------------------------


def test_tftpsp_list_default_lists_33_genes():
    result = runner.invoke(app, ["tftpsp-list"])
    assert result.exit_code == 0
    assert "33 / 33" in result.output
    assert "TFT-01" in result.output
    assert "TFT-23" in result.output
    assert "EPSHCPE-TFT" in result.output


def test_tftpsp_list_filter_by_domain_crisis():
    result = runner.invoke(app, ["tftpsp-list", "--domain", "crisis"])
    assert result.exit_code == 0
    # Must include at least TFT-18 and TFT-23
    assert "TFT-18" in result.output
    assert "TFT-23" in result.output


def test_tftpsp_list_with_bcel_only():
    result = runner.invoke(app, ["tftpsp-list", "--with-bcel"])
    assert result.exit_code == 0
    # Five genes have BCEL mappings
    assert "5 /" in result.output
    # Each listed gene has a "_equivalent" suffix on its BCEL mapping.
    assert "_equivalent" in result.output
    # The 5 BCEL genes (TFT-17, 23, 28, 29, 33) must be the only entries.
    for tft in ("TFT-17", "TFT-23", "TFT-28", "TFT-29", "TFT-33"):
        assert tft in result.output


# ---------------------------------------------------------------------------
# tftpsp-show
# ---------------------------------------------------------------------------


def test_tftpsp_show_emergency_gene():
    result = runner.invoke(app, ["tftpsp-show", "tftpsp_023_epshcpe"])
    assert result.exit_code == 0
    assert "EPSHCPE-TFT" in result.output
    assert "lock_open" in result.output
    assert "mutation_policy.allowed: False" in result.output


def test_tftpsp_show_descriptive_gene():
    result = runner.invoke(app, ["tftpsp-show", "tftpsp_001_tft"])
    assert result.exit_code == 0
    assert "Technological Fields Theory" in result.output
    # No BCEL mapping
    assert "bcel:        none" in result.output


def test_tftpsp_show_unknown_gene_exits_1():
    result = runner.invoke(app, ["tftpsp-show", "tftpsp_999_unknown"])
    assert result.exit_code == 1
    assert "not found" in result.output


# ---------------------------------------------------------------------------
# tftpsp-express
# ---------------------------------------------------------------------------


def test_tftpsp_express_default_state():
    result = runner.invoke(app, ["tftpsp-express", "--top", "5"])
    assert result.exit_code == 0
    assert "TFTpsp Expression" in result.output
    # 33 profiles reported in metadata
    assert "33 total" in result.output


def test_tftpsp_express_crisis_state_elevates_emergency_gene():
    result = runner.invoke(
        app,
        ["tftpsp-express", "--state", "crisis=1.0", "--top", "33"],
    )
    assert result.exit_code == 0
    # EPSHCPE should be visibly elevated above its 0.1 base priority
    # (lock_open rule fires when crisis is explicit -> 0.1 * 2.0 = 0.2)
    assert "tftpsp_023_epshcpe" in result.output
    assert "0.200" in result.output or "0.20" in result.output


def test_tftpsp_express_invalid_state_pair_exits_1():
    result = runner.invoke(app, ["tftpsp-express", "--state", "badpair"])
    assert result.exit_code == 1
    assert "Invalid" in result.output


def test_tftpsp_express_invalid_numeric_value_exits_1():
    result = runner.invoke(app, ["tftpsp-express", "--state", "crisis=NaN"])
    assert result.exit_code == 1
    assert "Invalid numeric value" in result.output


# ---------------------------------------------------------------------------
# tftpsp-audit
# ---------------------------------------------------------------------------


def test_tftpsp_audit_summary():
    result = runner.invoke(app, ["tftpsp-audit"])
    assert result.exit_code == 0
    assert "TFTpsp Audit" in result.output
    assert "gene_count:        33" in result.output
    assert "with_bcel:         5" in result.output
    assert "tftpsp_023_epshcpe" in result.output  # emergency gene
    assert "locked_mutations:" in result.output
