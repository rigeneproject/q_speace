"""Pytest configuration: register custom markers used by the suite.

Markers are registered here (not in pyproject.toml) to keep AGENTS.md
invariant "no pyproject.toml changes without explicit review".
"""

from __future__ import annotations


def pytest_configure(config: object) -> None:
    """Register custom markers known to the test suite."""
    config.addinivalue_line(  # type: ignore[attr-defined]
        "markers",
        "gpu: tests that require a GPU + a downloaded model "
        "(skipped by default; opt-in with `-m gpu`).",
    )
