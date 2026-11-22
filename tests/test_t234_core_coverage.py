"""Milestone 8: Core coverage hardening for quantum_state, aacm.checkpoint, and remote_mcp.server."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from q_speace.aacm.checkpoint import (
    check_compatibility,
    load_checkpoint,
    try_validate_with_jsonschema,
    write_checkpoint,
)
from q_speace.aacm.exceptions import InvariantViolation
from q_speace.quantum.quantum_state import QuantumState
from q_speace.remote_mcp.server import _reject_json_constant, bounded


def test_quantum_state_measurement_lindblad_jump_and_helpers() -> None:
    # 0. Constructor & factory validation branches + tensor_product.
    with pytest.raises(ValueError, match=">= 1"):
        QuantumState(0)
    with pytest.raises(ValueError, match="<= 16"):
        QuantumState(17)
    with pytest.raises(ValueError, match="out of range"):
        QuantumState(1, initial_state=5)
    with pytest.raises(ValueError, match="zero vector"):
        QuantumState.from_amplitudes([0.0, 0.0])
    tp = QuantumState.tensor_product(QuantumState(1, initial_state=1), QuantumState(1), seed=3)
    assert tp.num_qubits == 2 and np.isclose(abs(tp.amplitudes[2]), 1.0)

    # 1. Single-qubit measurement, measure_many, and out-of-range error.
    s = QuantumState.equal_superposition(2, seed=7)
    m0 = s.measure(0)
    assert m0.bitstring in ("0", "1")
    assert 0.0 < m0.probability <= 1.0
    many = s.measure_many([0, 1])
    assert len(many) == 2
    with pytest.raises(ValueError, match="out of range"):
        s.measure(5)

    # 2. Lindblad jump branch (high rate -> guaranteed jump) + error branches.
    sigma_minus = np.array([[0.0, 1.0], [0.0, 0.0]], dtype=np.complex128)
    excited = QuantumState.from_amplitudes([0.0, 1.0], seed=1)
    excited.apply_lindblad([(0, sigma_minus)], rates=[2.0], dt=0.5)
    # Decay |1> -> |0> via jump operator
    assert np.isclose(abs(excited.amplitudes[0]), 1.0)

    # Zero-rate jump operator is a no-op
    stay = QuantumState.from_amplitudes([0.0, 1.0], seed=2)
    stay.apply_lindblad([(0, sigma_minus)], rates=[0.0], dt=0.1)
    assert np.isclose(abs(stay.amplitudes[1]), 1.0)

    with pytest.raises(ValueError, match="out of range"):
        stay.apply_lindblad([(3, sigma_minus)], rates=[0.1], dt=0.1)
    with pytest.raises(ValueError, match="finite and >= 0"):
        stay.apply_lindblad([(0, sigma_minus)], rates=[-0.1], dt=0.1)
    with pytest.raises(ValueError, match="finite and >= 0"):
        stay.apply_lindblad([(0, sigma_minus)], rates=[0.1], dt=-0.1)

    # 3. phi_proxy (1 qubit == 0.0, Bell state > 1.0), is_entangled_with, fidelity, density, copy, repr.
    one_q = QuantumState(num_qubits=1)
    assert one_q.phi_proxy() == 0.0
    assert one_q.is_entangled_with(one_q) is False

    bell = QuantumState.from_amplitudes([1.0, 0.0, 0.0, 1.0], seed=5)
    assert bell.phi_proxy() > 1.5
    assert bell.is_entangled_with(one_q) is True

    separable = QuantumState(num_qubits=2)
    assert separable.is_entangled_with(one_q) is False

    assert np.isclose(bell.fidelity_with(bell.copy()), 1.0)
    with pytest.raises(ValueError, match="same-dimension"):
        bell.fidelity_with(one_q)

    rho = bell.to_density_matrix()
    assert rho.shape == (4, 4)
    assert np.isclose(np.real(np.trace(rho)), 1.0)
    assert "QuantumState(n=2" in repr(bell)
    assert "|00>" in repr(bell) and "|11>" in repr(bell)


def test_aacm_checkpoint_roundtrip_errors_and_jsonschema(tmp_path: Path) -> None:
    cp_path = tmp_path / "cp.json"
    payload: dict[str, Any] = {
        "schema_version": "aacm.cp.1",
        "step": 0,
        "state": {"x": 1},
    }
    write_checkpoint(cp_path, payload)
    loaded = load_checkpoint(cp_path)
    assert loaded["schema_version"] == "aacm.cp.1"

    # Non-dict JSON rejected
    bad_list = tmp_path / "list.json"
    bad_list.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        load_checkpoint(bad_list)

    # Missing / unsupported schema_version rejected
    with pytest.raises(InvariantViolation, match="missing schema_version"):
        check_compatibility({})
    with pytest.raises(InvariantViolation, match="unsupported schema_version"):
        check_compatibility({"schema_version": "aacm.cp.999"})

    # Non-JSON-serializable payload fails cleanly without leaving temp files
    with pytest.raises(TypeError):
        write_checkpoint(tmp_path / "fail.json", {"bad": object()})
    assert not list(tmp_path.glob("fail.json.*.tmp"))

    # jsonschema validation returns False on incomplete/invalid payload
    assert try_validate_with_jsonschema({"schema_version": "aacm.cp.1"}) is False


def test_remote_mcp_bounded_and_json_constant_rejection() -> None:
    # Valid small structure passes
    bounded({"a": [1, 2, 3], "b": "ok", "c": True})

    # String length limit
    with pytest.raises(ValueError, match="string_limit"):
        bounded("x" * 2049)

    # Numeric limits (including NaN / Inf)
    with pytest.raises(ValueError, match="numeric_limit"):
        bounded(1e13)
    with pytest.raises(ValueError, match="numeric_limit"):
        bounded(float("nan"))
    with pytest.raises(ValueError, match="numeric_limit"):
        bounded(float("inf"))

    # Array length limit
    with pytest.raises(ValueError, match="array_limit"):
        bounded([0] * 257)

    # Depth limit
    deep: Any = 1
    for _ in range(15):
        deep = {"k": deep}
    with pytest.raises(ValueError, match="input_structure_limit"):
        bounded(deep)

    # RFC 8259 constant rejection in json.loads
    with pytest.raises(ValueError, match="non_finite_json_constant:NaN"):
        json.loads('{"x": NaN}', parse_constant=_reject_json_constant)
    with pytest.raises(ValueError, match="non_finite_json_constant:Infinity"):
        json.loads('{"x": Infinity}', parse_constant=_reject_json_constant)
