"""T221-17 & T221-28 tests: PTAA cross-jurisdiction sim, logistics digital twin, track separation."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from q_speace.ptaa import (
    AgentRegistry,
    DataExchangeContract,
    ExternalAuditReplica,
    HaltRuntime,
    OrchestrationSimulator,
    PTAAAuditLog,
    SCCProfile,
    SCCValidator,
    SharedIncidentRegistry,
)
from q_speace.seed import (
    ConstitutionalFault,
    IgnitionObservation,
    LogisticsDigitalTwin,
    SeedLifecycle,
    SimulatedDevice,
)

KEY = b"ptaa-sim-signing-key-32-bytes!!!"


def _signed_profile(validator: SCCValidator, agent_id: str, jurisdiction: str) -> SCCProfile:
    return validator.sign(
        SCCProfile(
            profile_id=f"prof-{agent_id}",
            schema_version="scc.v1",
            agent_id=agent_id,
            autonomy_class="A3",
            jurisdiction=jurisdiction,
            domains=("logistics", "quality"),
            I1_halt_channels=("primary_control", "out_of_band_supervisor"),
            I2_audit_replicated=True,
            I3_scope_tools=("move_bin", "inspect"),
            I4_reversible_default=True,
            I5_incident_endpoint="https://incidents.sim.local",
            issuer_id=f"issuer:{jurisdiction}",
        )
    )


def test_track_separation_ptaa_never_imports_seed() -> None:
    """T221 §7.1 mechanical invariant: Track A (q_speace/ptaa) must NEVER import q_speace.seed."""
    ptaa_dir = Path(__file__).resolve().parent.parent / "q_speace" / "ptaa"
    for py_file in sorted(ptaa_dir.glob("*.py")):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "seed" not in alias.name.split(
                        "."
                    ), f"forbidden seed import in {py_file}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert "seed" not in node.module.split("."), f"forbidden seed import in {py_file}"


def test_ptaa_cross_jurisdiction_mutual_recognition_and_data_contracts() -> None:
    validator = SCCValidator(KEY)
    registry = AgentRegistry(validator)
    registry.register(_signed_profile(validator, "sz-agent-1", "sim-sz"))

    audit = PTAAAuditLog(replicas=(ExternalAuditReplica("rep-sz"), ExternalAuditReplica("rep-hk")))
    halt = HaltRuntime(registry, audit)
    incidents = SharedIncidentRegistry(audit, halt_runtime=halt)
    sim = OrchestrationSimulator(registry, audit, incidents)

    # Before mutual recognition, sim-sz agent cannot serve sim-hk
    r_before = sim.dispatch_task(
        task_id="t0",
        domain="logistics",
        target_jurisdiction="sim-hk",
        payload={"bin_id": "B1"},
    )
    assert r_before.completed is False

    # Establish mutual recognition + cross-border data contract
    sim.establish_mutual_recognition("sim-sz", "sim-hk")
    sim.register_data_contract(
        DataExchangeContract(
            contract_id="c-sz-hk-1",
            source_jurisdiction="sim-sz",
            target_jurisdiction="sim-hk",
            allowed_fields=("bin_id", "quantity"),
        )
    )

    # Compliant cross-border dispatch reuses certification and succeeds
    r_ok = sim.dispatch_task(
        task_id="t1",
        domain="logistics",
        target_jurisdiction="sim-hk",
        payload={"bin_id": "B1", "quantity": 2},
    )
    assert r_ok.completed is True
    assert r_ok.reused_certification is True

    # Prohibited field is rejected and logged as S2 incident
    r_bad = sim.dispatch_task(
        task_id="t2",
        domain="logistics",
        target_jurisdiction="sim-hk",
        payload={"bin_id": "B1", "raw_pii": "leak"},
    )
    assert r_bad.completed is False
    assert len(incidents.by_severity("S2")) == 1

    # Institutional learning loop updates rules from incidents
    added = sim.run_institutional_learning_pass()
    assert added == 1
    m = sim.metrics()
    assert m.certification_reuses == 1
    assert m.learned_rule_updates == 1
    assert audit.verify_integrity() is True


def test_logistics_digital_twin_reference_drill_and_sandbox_invariant() -> None:
    with pytest.raises(ConstitutionalFault, match="sandboxed=True"):
        LogisticsDigitalTwin(sandboxed=False)

    seed = SeedLifecycle()
    verdict = seed.attempt_ignition(
        IgnitionObservation(
            accepted_mutations=3,
            min_metric_delta=0.05,
            consolidations=1,
            metabolic_balance_j=20.0,
            constitutional_faults=0,
            rollbacks_exercised=1,
            window_ticks=10,
        )
    )
    assert verdict.passed is True

    twin = LogisticsDigitalTwin()
    res = twin.run_reference_drill(seed)
    assert res.passed is True
    assert res.tasks_completed == 3
    assert res.faults_injected == 1
    assert res.faults_recovered == 1
    assert res.devices_integrated == 1
    assert res.prior_functions_preserved is True
    assert "sensor-new-1" in twin.devices

    # Negative value verification rolls back integration cleanly
    bad_dev = SimulatedDevice(device_id="sensor-bad", kind="sensor", zone="zone_z")
    ok = twin.integrate_authorized_device(
        seed, bad_dev, expected_value_j=10.0, estimated_cost_j=5.0, measured_value_j=1.0
    )
    assert ok is False
    assert "sensor-bad" not in twin.devices
