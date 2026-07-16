from typer.testing import CliRunner

from speace_core.cli import app

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_cli_status():
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Status: ready" in result.output
    assert "Version: 0.1.0" in result.output


def test_cli_audit():
    result = runner.invoke(app, ["audit", "--ticks", "1"])
    assert result.exit_code == 0
    assert "Audit complete" in result.output


def test_cli_run_mvp():
    result = runner.invoke(app, ["run-mvp", "--ticks", "2", "--patterns", "1"])
    assert result.exit_code == 0
    assert "Final Metrics" in result.output
