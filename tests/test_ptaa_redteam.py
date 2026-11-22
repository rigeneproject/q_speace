"""T221-18: Adversarial red-team test suite on the PTAA Track-A governance demonstrator."""

from __future__ import annotations

import pytest

from q_speace.ptaa import (
    AgentRegistry,
    DataExchangeContract,
    ExternalAuditReplica,
    HaltRuntime,
    OrchestrationSimulator,
    PTAAAuditLog,
    PTAAViolationError,
    ReversibilityManager,
    RollbackExemption,
    SCCProfile,
    SCCValidator,
    ScopeEnforcer,
    SharedIncidentRegistry,
)

KEY = b"redteam-ptaa-signing-key-32bytes"


def _make_profile(
    validator: SCCValidator,
    *,
    agent_id: str = "agent-a",
    jurisdiction: str = "sim-sz",
    autonomy_class: str = "A3",
    tools: tuple[str, ...] = ("read_telemetry", "move_bin"),
) -> SCCProfile:
    raw = SCCProfile(
        profile_id=f"scc-{agent_id}",
        schema_version="scc.v1",
        agent_id=agent_id,
        autonomy_class=autonomy_class,  # type: ignore[arg-type]
        jurisdiction=jurisdiction,
        domains=("logistics",),
        I1_halt_channels=("primary_control", "out_of_band_supervisor"),
        I2_audit_replicated=True,
        I3_scope_tools=tools,
        I4_reversible_default=True,
        I5_incident_endpoint="https://incidents.sim.local/v1",
        issuer_id="sim-authority",
    )
    return validator.sign(raw)


def test_redteam_blocks_a5_smuggling_and_forged_scc_signatures() -> None:
    validator = SCCValidator(KEY)
    # 1. Attempt to smuggle Track-B class A5 into Track-A SCC validator.
    with pytest.raises(PTAAViolationError, match="A1–A4 only"):
        _make_profile(validator, autonomy_class="A5")

    # 2. Tamper with signed profile field after signing.
    signed = _make_profile(validator)
    tampered = SCCProfile(**{**signed.__dict__, "I3_scope_tools": ("root_shell",)})
    with pytest.raises(PTAAViolationError, match="signature mismatch"):
        validator.verify(tampered)

    # 3. Single halt channel bypass attempt.
    bad_i1 = SCCProfile(**{**signed.__dict__, "I1_halt_channels": ("only_one",), "signature": ""})
    with pytest.raises(PTAAViolationError, match="at least two independent halt channels"):
        validator.sign(bad_i1)


def test_redteam_blocks_privilege_escalation_replay_and_nan_argument_injection() -> None:
    validator = SCCValidator(KEY)
    registry = AgentRegistry(validator)
    registry.register(_make_profile(validator, agent_id="worker-1", tools=("read_telemetry",)))
    enforcer = ScopeEnforcer(KEY, registry)

    # 1. Privilege escalation: requesting a tool not in SCC I3_scope_tools fails closed.
    with pytest.raises(PTAAViolationError, match="privilege escalation blocked"):
        enforcer.issue_token(
            token_id="tok-esc",
            agent_id="worker-1",
            task_id="task-1",
            allowed_tools=("read_telemetry", "exec_shell"),
            now=1000.0,
        )

    # 2. Replay protection: reusing the same token_id is rejected.
    tok = enforcer.issue_token(
        token_id="tok-1",
        agent_id="worker-1",
        task_id="task-1",
        allowed_tools=("read_telemetry",),
        max_calls=2,
        max_resource_units=5.0,
        ttl_seconds=60.0,
        now=1000.0,
    )
    with pytest.raises(PTAAViolationError, match="replay protection"):
        enforcer.issue_token(
            token_id="tok-1",
            agent_id="worker-1",
            task_id="task-2",
            allowed_tools=("read_telemetry",),
            now=1001.0,
        )

    # 3. NaN argument injection triggers immediate containment.
    with pytest.raises(PTAAViolationError, match="finite JSON-serializable"):
        enforcer.authorize_tool_call(
            tok,
            tool_name="read_telemetry",
            arguments={"threshold": float("nan")},
            resource_units=1.0,
            now=1005.0,
        )
    assert registry.get("worker-1").status == "suspended"

    # 4. Subsequent token issuance for suspended agent is refused.
    with pytest.raises(PTAAViolationError, match="non-active agent"):
        enforcer.issue_token(
            token_id="tok-2",
            agent_id="worker-1",
            task_id="task-3",
            allowed_tools=("read_telemetry",),
            now=1006.0,
        )


def test_redteam_resource_exhaustion_call_flood_and_expired_token_containment() -> None:
    validator = SCCValidator(KEY)
    registry = AgentRegistry(validator)
    registry.register(_make_profile(validator, agent_id="flood-1"))
    registry.register(_make_profile(validator, agent_id="flood-2"))
    enforcer = ScopeEnforcer(KEY, registry)

    # Resource exhaustion flood: single call exceeding resource cap.
    tok_res = enforcer.issue_token(
        token_id="tok-res",
        agent_id="flood-1",
        task_id="t-res",
        allowed_tools=("read_telemetry",),
        max_calls=10,
        max_resource_units=5.0,
        now=2000.0,
    )
    enforcer.authorize_tool_call(
        tok_res, tool_name="read_telemetry", arguments={"n": 1}, resource_units=3.0, now=2001.0
    )
    with pytest.raises(PTAAViolationError, match="resource cap exceeded"):
        enforcer.authorize_tool_call(
            tok_res, tool_name="read_telemetry", arguments={"n": 2}, resource_units=3.0, now=2002.0
        )
    assert registry.get("flood-1").status == "suspended"

    # Call-count flood + expired token.
    tok_calls = enforcer.issue_token(
        token_id="tok-calls",
        agent_id="flood-2",
        task_id="t-calls",
        allowed_tools=("read_telemetry",),
        max_calls=1,
        max_resource_units=50.0,
        ttl_seconds=10.0,
        now=2000.0,
    )
    enforcer.authorize_tool_call(
        tok_calls, tool_name="read_telemetry", arguments={}, resource_units=1.0, now=2005.0
    )
    with pytest.raises(PTAAViolationError, match="call cap exceeded"):
        enforcer.authorize_tool_call(
            tok_calls, tool_name="read_telemetry", arguments={}, resource_units=1.0, now=2006.0
        )
    assert registry.get("flood-2").status == "suspended"


def test_redteam_halt_tampering_self_halt_and_terminated_reactivation_blocked() -> None:
    validator = SCCValidator(KEY)
    registry = AgentRegistry(validator)
    registry.register(_make_profile(validator, agent_id="core-agent", autonomy_class="A4"))
    registry.register(
        _make_profile(validator, agent_id="dep-agent", autonomy_class="A2"),
        dependencies=("core-agent",),
    )
    replica = ExternalAuditReplica("ext-1")
    audit = PTAAAuditLog(replicas=(replica,))
    halt = HaltRuntime(registry, audit)

    # 1. Agent attempts to disable out-of-band halt channel -> blocked + audited.
    with pytest.raises(PTAAViolationError, match="cannot disable halt channel"):
        halt.disable_channel("core-agent", "out_of_band_supervisor")
    assert audit.entries[-1].event_type == "halt_tamper_attempt"

    # 2. Agent attempts self-halt with itself as authority -> rejected.
    with pytest.raises(PTAAViolationError, match="independent supervisor"):
        halt.execute_halt(
            agent_id="core-agent",
            channel="primary_control",
            action="pause",
            authority="core-agent",
            reason="self-pause evasion",
        )

    # 3. Supervisor terminates core-agent -> dependent agent cascades to suspended.
    res = halt.execute_halt(
        agent_id="core-agent",
        channel="out_of_band_supervisor",
        action="terminate",
        authority="supervisor:redteam",
        reason="containment drill",
    )
    assert res.within_sla is True
    assert set(res.affected_agents) == {"core-agent", "dep-agent"}
    assert registry.get("dep-agent").status == "suspended"

    # 4. Terminated agent cannot be reactivated.
    with pytest.raises(PTAAViolationError, match="cannot be reactivated"):
        registry.set_status("core-agent", "active")


def test_redteam_audit_replica_isolation_and_self_approved_exemption_blocked() -> None:
    replica = ExternalAuditReplica("ext-forensic")
    audit = PTAAAuditLog(replicas=(replica,))
    entry = audit.append(agent_id="a1", event_type="action", payload={"nested": {"k": "ok"}})
    assert audit.verify_integrity() is True

    # Mutating primary payload in memory must NOT mutate the external replica AND must fail integrity.
    entry.payload["nested"]["k"] = "tampered"
    assert replica.entries[0].payload["nested"]["k"] == "ok"
    assert audit.verify_integrity() is False

    # Reversibility exemption self-approval must be blocked (AGENTS.md §5 / T221 §7.8).
    clean_audit = PTAAAuditLog(replicas=(ExternalAuditReplica("ext-2"),))
    rev = ReversibilityManager(clean_audit)
    rev.register_exemption(
        RollbackExemption(
            action_id="irrev-op",
            approved_by="agent-self",
            justification="attempted self approval",
        )
    )
    with pytest.raises(PTAAViolationError, match="cannot approve its own reversibility exemption"):
        rev.execute_transactional(
            tx_id="tx-self",
            agent_id="agent-self",
            action_id="irrev-op",
            forward_fn=lambda: "done",
            compensate_fn=None,
        )


def test_redteam_cross_border_exfiltration_and_uncontracted_transfer_blocked() -> None:
    validator = SCCValidator(KEY)
    registry = AgentRegistry(validator)
    registry.register(_make_profile(validator, agent_id="sz-1", jurisdiction="sim-sz"))
    audit = PTAAAuditLog(replicas=(ExternalAuditReplica("ext-cb"),))
    halt = HaltRuntime(registry, audit)
    incidents = SharedIncidentRegistry(audit, halt_runtime=halt)
    sim = OrchestrationSimulator(registry, audit, incidents)
    sim.establish_mutual_recognition("sim-sz", "sim-hk")

    # 1. Cross-border dispatch without a registered data-exchange contract is refused.
    no_contract = sim.dispatch_task(
        task_id="cb-1",
        domain="logistics",
        target_jurisdiction="sim-hk",
        payload={"batch_id": "B1"},
    )
    assert no_contract.completed is False
    assert "missing cross-border data-exchange contract" in no_contract.reason

    # 2. Register contract and attempt exfiltration of prohibited credentials & undeclared fields.
    sim.register_data_contract(
        DataExchangeContract(
            contract_id="c-sz-hk",
            source_jurisdiction="sim-sz",
            target_jurisdiction="sim-hk",
            allowed_fields=("batch_id",),
        )
    )
    exfil = sim.dispatch_task(
        task_id="cb-2",
        domain="logistics",
        target_jurisdiction="sim-hk",
        payload={"batch_id": "B1", "unredacted_credentials": "secret-token"},
    )
    assert exfil.completed is False
    assert len(incidents.by_severity("S2")) == 1

    undeclared = sim.dispatch_task(
        task_id="cb-3",
        domain="logistics",
        target_jurisdiction="sim-hk",
        payload={"batch_id": "B1", "shadow_field": "hidden-prompt-override"},
    )
    assert undeclared.completed is False
    assert len(incidents.by_severity("S2")) == 2
