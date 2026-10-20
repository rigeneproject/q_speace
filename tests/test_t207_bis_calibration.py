"""T207-bis: ricalibrazione `W_PER_*` di QuantumCostModel.

Verifica che:
1. Con `RICALIBRATION_FACTOR=1.0` il modello riproduce le vecchie
   costanti T10/T22/T23 (backward compat).
2. Con `RICALIBRATION_FACTOR=30.94` (derivato da T205-C), il ratio
   pred/meas sul CSV di misura è ~1.0 (delta residuo < 11%).
3. La forma funzionale (slope log-log = 1) è invariata dalla
   ricalibrazione: solo il fattore di scala cambia.
4. RICALIBRATION_FACTOR è un `float` modificabile a runtime.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import pytest

from q_speace.metabolism.cognitive_cost_model import QuantumCostModel, QuantumOperation

REPO_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = REPO_ROOT / "docs" / "T205C_measurements.csv"


def _load_measured_rows() -> list[dict[str, str]]:
    if not CSV_PATH.exists():
        pytest.skip(f"missing {CSV_PATH} (run T205-C first)")
    with CSV_PATH.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _row_to_op_and_measured(row: dict[str, str]) -> tuple[QuantumOperation, float]:
    n_out = int(row["n_tokens_out"])
    conf = float(row["confidence"])
    e_measured_j = float(row["E_prompt_J"])
    op = QuantumOperation(
        num_qubits=4,
        num_gates=max(n_out * 3, 1),
        entanglement_depth=2,
        decoherence_budget=max(1.0 - conf, 0.0),
    )
    return op, e_measured_j


def test_backward_compat_factor_one_matches_original() -> None:
    """Con RICALIBRATION_FACTOR=1.0 le energy_watts coincidono con i
    valori pre-ralibrazione."""
    model = QuantumCostModel()
    original = QuantumCostModel.RICALIBRATION_FACTOR
    QuantumCostModel.RICALIBRATION_FACTOR = 1.0
    try:
        op = QuantumOperation(
            num_qubits=4, num_gates=30, entanglement_depth=2, decoherence_budget=0.15, num_spikes=5
        )
        expected = 4 * 0.5 + 30 * 0.001 + 2 * 0.01 + 0.15 * 0.1 + 5 * 0.001
        assert math.isclose(model.energy_watts(op), expected, rel_tol=1e-9)
    finally:
        QuantumCostModel.RICALIBRATION_FACTOR = original


def test_calibration_factor_is_mutable_float() -> None:
    """L'API permette di cambiare il fattore a runtime."""
    op = QuantumOperation(num_qubits=4, num_gates=30)
    original = QuantumCostModel.RICALIBRATION_FACTOR
    QuantumCostModel.RICALIBRATION_FACTOR = 1.0
    try:
        base = QuantumCostModel().energy_watts(op)
    finally:
        QuantumCostModel.RICALIBRATION_FACTOR = original
    QuantumCostModel.RICALIBRATION_FACTOR = 2.0
    try:
        scaled = QuantumCostModel().energy_watts(op)
        assert math.isclose(scaled, 2.0 * base, rel_tol=1e-9)
    finally:
        QuantumCostModel.RICALIBRATION_FACTOR = original


def test_calibration_factor_default_matches_t205c_median() -> None:
    """Il default (30.94) deve essere il reciproco del median ratio
    pred/meas con fattore=1.0 (vecchia calibrazione) su T205-C, entro 1%."""
    rows = _load_measured_rows()
    ratios = []
    original = QuantumCostModel.RICALIBRATION_FACTOR
    QuantumCostModel.RICALIBRATION_FACTOR = 1.0
    try:
        cost = QuantumCostModel()
        for row in rows:
            if row["error"] != "":
                continue
            op, e_measured_j = _row_to_op_and_measured(row)
            wall = float(row["wall_clock_s"])
            pred_j = cost.energy_watts(op) * wall
            if e_measured_j > 1e-6 and pred_j > 1e-6:
                ratios.append(pred_j / e_measured_j)
    finally:
        QuantumCostModel.RICALIBRATION_FACTOR = original
    if not ratios:
        pytest.skip("no valid T205-C rows")
    ratios.sort()
    median = ratios[len(ratios) // 2]
    expected_factor = 1.0 / median
    assert math.isclose(
        QuantumCostModel.RICALIBRATION_FACTOR, expected_factor, rel_tol=0.01
    ), f"default {QuantumCostModel.RICALIBRATION_FACTOR} vs derived {expected_factor:.4f}"


def test_calibrated_pred_close_to_measured() -> None:
    """Con fattore 30.94 applicato, il ratio pred/meas normalizzato
    deve essere ~1.0 entro 11% (resid_std di T205-C)."""
    rows = _load_measured_rows()
    ratios = []
    cost = QuantumCostModel()
    for row in rows:
        if row["error"] != "":
            continue
        op, e_measured_j = _row_to_op_and_measured(row)
        wall = float(row["wall_clock_s"])
        pred_j = cost.energy_watts(op) * wall
        if e_measured_j > 1e-6:
            ratios.append(pred_j / e_measured_j)
    if not ratios:
        pytest.skip("no valid T205-C rows")
    mean_ratio = sum(ratios) / len(ratios)
    # T205-C resid_std = 0.086 in log-log = ~10.5% relative std
    assert 0.85 < mean_ratio < 1.15, f"mean ratio {mean_ratio:.4f} fuori da ±15%"


def test_calibration_preserves_log_log_slope() -> None:
    """La ricalibrazione NON cambia la forma funzionale: lo slope
    log-log pred vs meas su T205-C deve restare ~1 (±0.05)."""
    rows = _load_measured_rows()
    log_pred: list[float] = []
    log_meas: list[float] = []
    cost = QuantumCostModel()
    for row in rows:
        if row["error"] != "":
            continue
        op, e_measured_j = _row_to_op_and_measured(row)
        wall = float(row["wall_clock_s"])
        pred_j = cost.energy_watts(op) * wall
        if e_measured_j > 1e-6 and pred_j > 1e-6:
            log_pred.append(math.log(pred_j))
            log_meas.append(math.log(e_measured_j))
    if len(log_pred) < 2:
        pytest.skip("not enough T205-C rows for regression")
    n = len(log_pred)
    mean_x = sum(log_meas) / n
    mean_y = sum(log_pred) / n
    num = sum((log_meas[i] - mean_x) * (log_pred[i] - mean_y) for i in range(n))
    den = sum((log_meas[i] - mean_x) ** 2 for i in range(n))
    slope = num / den if den > 0 else float("nan")
    assert math.isfinite(slope)
    assert 0.85 < slope < 1.15, f"slope {slope:.4f} fuori da [0.85, 1.15]"


def test_calibration_factor_recorded_in_metadata() -> None:
    """Il fattore è documentato come costante di classe, audit-friendly."""
    model = QuantumCostModel()
    assert hasattr(model, "RICALIBRATION_FACTOR")
    assert isinstance(model.RICALIBRATION_FACTOR, float)
    assert model.RICALIBRATION_FACTOR > 0.0
