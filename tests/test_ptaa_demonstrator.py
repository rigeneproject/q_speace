"""T221-10..16 tests: PTAA Track-A governance demonstrator (SCC, registry, I1–I5, A5 separation)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from q_speace.bcel import BCELCatalog
from q_speace.ptaa import (
    AgentRegistry,
    ExternalAuditReplica,
    HaltRuntime,
    PTAAAuditLog,
    PTAAViolationError,
    ReversibilityManager,
    RollbackExemption,
    SCCProfile,
    SCCValidator,
    ScopeEnforcer,
    SharedIncidentRegistry,
)

KEY = b"ptaa-demo-signing-key-32-bytes!!"


def _make_profile(
    validator: SCCValidator,
    agent_id: str = "agent-a",
    autonomy_class: str = "A2",
    jurisdiction: str = "sim-sz",
) -> SCCProfile:
    raw = SCCProfile(
        profile_id=f"prof-{agent_id}",
        schema_version="scc.v1",
        agent_id=agent_id,
        autonomy_class=autonomy_class,  # type: ignore[arg-type]
        jurisdiction=jurisdiction,
        domains=("logistics",),
        I1_halt_channels=("primary_control", "out_of_band_supervisor"),
        I2_audit_replicated=True,
        I3_scope_tools=("read_inventory", "schedule_bin"),
        I4_reversible_default=True,
        I5_incident_endpoint="https://incidents.sim.local/report",
        issuer_id="issuer:sim-cert-authority",
    )
    return validator.sign(raw)


def test_scc_validator_rejects_a5_and_tampered_profiles() -> None:
    cat = BCELCatalog()
    assert cat.is_functional("PTAA Track-A governance demonstrator (T221-10..17)") is True

    validator = SCCValidator(KEY)
    # T221 §7.1: A5 capabilities MUST NEVER enter Track A
    with pytest.raises(PTAAViolationError, match="not permitted in Track A"):
        _make_profile(validator, agent_id="seed-a5", autonomy_class="A5")

    signed = _make_profile(validator, agent_id="agent-1")
    assert validator.verify(signed) is True

    tampered = replace(signed, domains=("weapons",))
    with pytest.raises(PTAAViolationError, match="signature mismatch"):
        validator.verify(tampered)


def test_agent_registry_propagates_suspension_to_dependents() -> None:
    validator = SCCValidator(KEY)
    registry = AgentRegistry(validator)
    registry.register(_make_profile(validator, "upstream"))
    registry.register(_make_profile(validator, "downstream"), dependencies=("upstream",))

    affected = registry.set_status("upstream", "suspended")
    assert set(affected) == {"upstream", "downstream"}
    assert registry.get("downstream").status == "suspended"

    registry.set_status("upstream", "terminated")
    with pytest.raises(PTAAViolationError, match="cannot be reactivated"):
        registry.set_status("upstream", "active")


def test_delegation_scope_enforcement_and_containment() -> None:
    validator = SCCValidator(KEY)
    registry = AgentRegistry(validator)
    registry.register(_make_profile(validator, "worker-1"))

    enforcer = ScopeEnforcer(KEY, registry)
    tok = enforcer.issue_token(
        token_id="tok-1",
        agent_id="worker-1",
        task_id="task-1",
        allowed_tools=("read_inventory",),
        max_calls=2,
        max_resource_units=5.0,
        ttl_seconds=60.0,
        now=1000.0,
    )
    enforcer.authorize_tool_call(
        tok, tool_name="read_inventory", arguments={"bin": 1}, resource_units=2.0, now=1010.0
    )

    # Disallowed tool triggers containment (agent becomes suspended)
    with pytest.raises(PTAAViolationError, match="outside allowed scope"):
        enforcer.authorize_tool_call(
            tok, tool_name="delete_all", arguments={}, resource_units=1.0, now=1011.0
        )
    assert registry.get("worker-1").status == "suspended"

    # Expired token triggers containment on another agent
    registry.register(_make_profile(validator, "worker-2"))
    tok2 = enforcer.issue_token(
        token_id="tok-2",
        agent_id="worker-2",
        task_id="task-2",
        allowed_tools=("read_inventory",),
        ttl_seconds=10.0,
        now=1000.0,
    )
    with pytest.raises(PTAAViolationError, match="expired"):
        enforcer.authorize_tool_call(tok2, tool_name="read_inventory", arguments={}, now=1020.0)
    assert registry.get("worker-2").status == "suspended"


def test_audit_log_replication_halt_channels_reversibility_and_incidents() -> None:
    rep1 = ExternalAuditReplica("replica-sz")
    rep2 = ExternalAuditReplica("replica-hk")
    audit = PTAAAuditLog(replicas=(rep1, rep2))

    validator = SCCValidator(KEY)
    registry = AgentRegistry(validator)
    registry.register(_make_profile(validator, "agent-ctrl", autonomy_class="A4"))
    halt = HaltRuntime(registry, audit)

    # Anti-tamper: agent cannot disable halt channel
    with pytest.raises(PTAAViolationError, match="cannot disable halt channel"):
        halt.disable_channel("agent-ctrl", "primary_control")

    # Both independent halt channels work within SLA
    drill_p = halt.execute_halt(
        agent_id="agent-ctrl",
        channel="primary_control",
        action="pause",
        authority="ops:primary",
        reason="drill 1",
    )
    assert drill_p.within_sla is True
    assert registry.get("agent-ctrl").status == "paused"

    registry.set_status("agent-ctrl", "active")
    # S1 incident automatically escalates via out_of_band_supervisor
    incidents = SharedIncidentRegistry(audit, halt_runtime=halt)
    inc = incidents.report(
        severity="S1",
        agent_id="agent-ctrl",
        jurisdiction="sim-sz",
        category="scope_breach",
        summary="critical boundary alert",
    )
    assert inc.auto_halted is True
    assert registry.get("agent-ctrl").status == "suspended"
    assert len(incidents.by_severity("S1")) == 1

    # I4 reversibility: compensating rollback runs on post_check failure; unexempted irreversible blocked
    rev = ReversibilityManager(audit)
    state = {"count": 0}
    outcome = rev.execute_transactional(
        tx_id="tx-1",
        agent_id="agent-ctrl",
        action_id="move_bin",
        forward_fn=lambda: state.__setitem__("count", 1) or state["count"],
        compensate_fn=lambda: state.__setitem__("count", 0),
        post_check=lambda val: val == 999,
    )
    assert outcome.committed is False
    assert outcome.rolled_back is True
    assert state["count"] == 0

    with pytest.raises(PTAAViolationError, match="lacks compensating rollback"):
        rev.execute_transactional(
            tx_id="tx-2",
            agent_id="agent-ctrl",
            action_id="irreversible_notice",
            forward_fn=lambda: "sent",
            compensate_fn=None,
        )

    rev.register_exemption(
        RollbackExemption(
            action_id="irreversible_notice",
            approved_by="human:compliance-officer",
            justification="read-only external regulatory notification",
        )
    )
    exempt_out = rev.execute_transactional(
        tx_id="tx-3",
        agent_id="agent-ctrl",
        action_id="irreversible_notice",
        forward_fn=lambda: "sent",
        compensate_fn=None,
    )
    assert exempt_out.committed is True

    # Audit chain + external replicas are intact; tampering is detected
    assert audit.verify_integrity() is True
    rep1._entries[0] = replace(rep1._entries[0], event_type="tampered")
    assert audit.verify_integrity() is False
