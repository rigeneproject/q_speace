import json
from pathlib import Path

import pytest

from q_speace.experiments.context_decay import audit_development, sealed_inputs
from q_speace.experiments.context_decay_memory import GRID, Entry


def test_development_gate_requires_two_observable_optima() -> None:
    losses = tuple(float(i) for i in range(len(GRID)))
    a = Entry(0, 0.01, losses)
    assert not audit_development((a,))["open_evaluation"]
    assert not audit_development((a, Entry(1, 1.0, losses)))["open_evaluation"]
    result = audit_development((a, Entry(1, 1.0, losses[::-1])))
    assert result["open_evaluation"]
    assert result["global_excess_loss"] > 0


def test_archive_modified_after_freeze_refused(tmp_path: Path) -> None:
    (tmp_path / "archive.json").write_text("[]")
    (tmp_path / "freeze.json").write_text(json.dumps({"files_sha256": {"archive.json": "changed"}}))
    with pytest.raises(ValueError, match="archive.json"):
        sealed_inputs(tmp_path)
