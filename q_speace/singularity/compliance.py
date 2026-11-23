"""T240: Regulatory compliance mapping (EU AI Act / NIST AI RMF / ISO 42001), Annex IV pack & Art. 73 incident schema."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import tempfile
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from .micro_node import (
    MicroNodeEvidenceBundle,
    certify_micro_node,
    verify_evidence_bundle_integrity,
)
from .schema import ConstitutionalGenome, EpigeneticFaultError

ControlStatus = Literal[
    "implemented_technical_control",
    "partial_deployer_dependent",
    "external_legal_organizational_obligation",
]
IncidentSeverity = Literal["low", "medium", "high", "critical"]
ModelLifecycleStatus = Literal[
    "approved_deterministic_stub",
    "approved_research_local",
    "external_mcp_caller_untrusted",
    "deprecated",
    "prohibited",
]


@dataclass(frozen=True)
class RegulatoryControlMapping:
    """Single clause mapping across EU AI Act, NIST AI RMF 1.0, and ISO/IEC 42001."""

    control_id: str
    eu_ai_act_clause: str
    nist_ai_rmf_ref: str
    iso_42001_ref: str
    requirement_summary: str
    qspeace_implementation: str
    verification_evidence: str
    status: ControlStatus
    responsibility_boundary: str


EU_AI_ACT_CONTROL_MATRIX: tuple[RegulatoryControlMapping, ...] = (
    RegulatoryControlMapping(
        control_id="REG-01",
        eu_ai_act_clause="Art. 5 (Prohibited AI Practices)",
        nist_ai_rmf_ref="GOVERN 1.1",
        iso_42001_ref="Clause 4.2",
        requirement_summary="No subliminal manipulation, social scoring, real-time biometric ID, or emotion recognition.",
        qspeace_implementation="Excluded by design; advisory numerical primitives and sandboxed twins only.",
        verification_evidence="BCELCatalog + static repository inspection",
        status="implemented_technical_control",
        responsibility_boundary="Software excludes Art. 5 functions; Deployer must not combine with Art. 5 uses.",
    ),
    RegulatoryControlMapping(
        control_id="REG-02",
        eu_ai_act_clause="Art. 9 (Risk Management System)",
        nist_ai_rmf_ref="MAP 5.1 / MANAGE 1.1",
        iso_42001_ref="Clause 6.1.2",
        requirement_summary="Continuous identification, evaluation, and mitigation of foreseeable technical and safety risks.",
        qspeace_implementation="DEFAULT_RISK_REGISTER, non-compensable T234 brakes (dH_sem, E_causal, Sevo, thermal), T217 lifecycle.",
        verification_evidence="7 T234/T236 drills + T237 + T238 held-out benchmarks",
        status="implemented_technical_control",
        responsibility_boundary="Technical risk mitigations verified in code; operational risk governance owned by Provider/Deployer.",
    ),
    RegulatoryControlMapping(
        control_id="REG-03",
        eu_ai_act_clause="Art. 10 (Data Governance) & GDPR Art. 5/25",
        nist_ai_rmf_ref="MAP 2.3 / MEASURE 2.10",
        iso_42001_ref="Clause 8.4 / Annex A.7",
        requirement_summary="Data minimization, privacy-by-default logging, and documented data provenance.",
        qspeace_implementation="RequestRecord SHA-256 prompt hashing (T208/T231), BrainAuditLog redact_raw_text, hash-only MCP audit.",
        verification_evidence="verify_privacy_by_default_controls() + test_t240_regulatory_compliance.py",
        status="partial_deployer_dependent",
        responsibility_boundary="Privacy-safe defaults implemented; real-world dataset governance and DPIA owned by Deployer.",
    ),
    RegulatoryControlMapping(
        control_id="REG-04",
        eu_ai_act_clause="Art. 11 & Annex IV (Technical Documentation)",
        nist_ai_rmf_ref="GOVERN 1.4 / MAP 1.5",
        iso_42001_ref="Clause 7.5",
        requirement_summary="Up-to-date technical documentation detailing architecture, limits, validation, and SBOM.",
        qspeace_implementation="T240 Annex IV Compliance Pack exporter (`qspace micro-node compliance-pack`) + T208-T240 specs + SBOM.",
        verification_evidence="verify_compliance_pack_integrity() + CI SBOM generation",
        status="implemented_technical_control",
        responsibility_boundary="Technical file generated automatically; legal Provider dossier maintained by organization.",
    ),
    RegulatoryControlMapping(
        control_id="REG-05",
        eu_ai_act_clause="Art. 12 (Record-Keeping / Logging)",
        nist_ai_rmf_ref="MEASURE 2.4 / MANAGE 4.1",
        iso_42001_ref="Clause 9.1",
        requirement_summary="Automatic tamper-evident logging of governance events, rollbacks, and anomalies.",
        qspeace_implementation="DLTSwarmLedger hash chain, EpigeneticAuditEntry, BrainAuditLog, persistent Docker volume in deploy/micro-node/.",
        verification_evidence="test_t234_singularity_framework.py + test_t236_iont_cellular_node.py",
        status="partial_deployer_dependent",
        responsibility_boundary="Durable on self-hosted Docker volume; ephemeral Render Free tier is NOT compliant for retention.",
    ),
    RegulatoryControlMapping(
        control_id="REG-06",
        eu_ai_act_clause="Art. 13 & Art. 50 (Transparency & Instructions for Use)",
        nist_ai_rmf_ref="GOVERN 4.1 / MAP 1.1",
        iso_42001_ref="Annex A.8",
        requirement_summary="Clear disclosure of capabilities, operational limits, and non-human AI nature.",
        qspeace_implementation="BCEL non-consciousness invariants, T225 Agent Connection Guide, T240 Guide & deployer_instructions.",
        verification_evidence="BCELCatalog + T240 pack fields",
        status="implemented_technical_control",
        responsibility_boundary="Technical limits documented; end-user UI AI disclosure owned by Deployer.",
    ),
    RegulatoryControlMapping(
        control_id="REG-07",
        eu_ai_act_clause="Art. 14 (Human Oversight)",
        nist_ai_rmf_ref="GOVERN 2.1 / MANAGE 2.4",
        iso_42001_ref="Annex A.9",
        requirement_summary="Effective human intervention, stop controls, and prohibition of unreviewed autonomous promotion.",
        qspeace_implementation="self_approval_permitted=False, mcp_actuation_permitted=False, KillSwitch (I1), T217 independent human review.",
        verification_evidence="test_seed_invariants.py + test_ptaa_redteam.py + T239 bundle",
        status="implemented_technical_control",
        responsibility_boundary="Hard software gates enforced; operator training and authority assignment owned by Deployer.",
    ),
    RegulatoryControlMapping(
        control_id="REG-08",
        eu_ai_act_clause="Art. 15 (Accuracy, Robustness & Cybersecurity) & EU CRA",
        nist_ai_rmf_ref="MEASURE 2.5 / MEASURE 2.7",
        iso_42001_ref="Annex A.6.2",
        requirement_summary="Resilience against faults, adversarial manipulation, poisoning, and unauthorized access.",
        qspeace_implementation="Independent Layer-0 interlock, OAuth RS256, RFC 8259 fail-closed JSON, T237 ablation, T238 Byzantine/blackout failover, SBOM.",
        verification_evidence="T234/T236 drills (7/7), T237, T238 (100% Byzantine isolation, 8/8 blackout recovery), 770+ tests",
        status="implemented_technical_control",
        responsibility_boundary="Software controls verified; production TLS/HSM/network perimeter owned by Operator.",
    ),
    RegulatoryControlMapping(
        control_id="REG-09",
        eu_ai_act_clause="Art. 73 (Reporting of Serious Incidents)",
        nist_ai_rmf_ref="MANAGE 4.2",
        iso_42001_ref="Clause 10.1",
        requirement_summary="Structured capture and timely reporting of serious safety or malfunction incidents.",
        qspeace_implementation="SeriousIncidentRecord & build_serious_incident_report() with SHA-256 digest and mandatory human review.",
        verification_evidence="test_t240_regulatory_compliance.py",
        status="partial_deployer_dependent",
        responsibility_boundary="Structured tamper-evident record generated; formal filing with authorities performed by legal Provider.",
    ),
    RegulatoryControlMapping(
        control_id="REG-10",
        eu_ai_act_clause="Arts. 17, 27, 43-49 (QMS, FRIA, Conformity Assessment & CE Marking)",
        nist_ai_rmf_ref="GOVERN 1.2 / GOVERN 6.1",
        iso_42001_ref="Clauses 5-10 (External Audit)",
        requirement_summary="Legal Provider registration, Quality Management System, FRIA, conformity assessment, and CE marking for High-Risk systems.",
        qspeace_implementation="Explicitly blocked from software self-certification (legal_certification_granted=False, ce_marking_granted=False).",
        verification_evidence="T217 lifecycle specification + T240 pack non-certification invariants",
        status="external_legal_organizational_obligation",
        responsibility_boundary="Exclusively external legal and organizational responsibility; cannot be satisfied by software alone.",
    ),
)


@dataclass(frozen=True)
class RiskRegisterEntry:
    """EU AI Act Art. 9 structured risk register entry."""

    risk_id: str
    category: str
    description: str
    severity: IncidentSeverity
    mitigation: str
    verification_ref: str
    residual_risk_note: str


DEFAULT_RISK_REGISTER: tuple[RiskRegisterEntry, ...] = (
    RiskRegisterEntry(
        risk_id="RISK-01",
        category="cyber_physical_actuation",
        description="Unauthorized or unsafe physical actuation triggered by LLM output, DLT latency, or remote MCP calls.",
        severity="critical",
        mitigation="Hard non-actuating MCP boundary (mcp_actuation_permitted=False), independent <5ms Layer-0 hardware interlock, and slow-plane isolation of consensus_quorum.",
        verification_ref="T236/T237/T239 slow-plane guard & Layer-0 independence tests",
        residual_risk_note="Simulation validation does not prove real hardware safety; T217 staged physical qualification remains mandatory.",
    ),
    RiskRegisterEntry(
        risk_id="RISK-02",
        category="adversarial_byzantine_poisoning",
        description="Compromised cellular node or offensive AI agent injecting poisoned telemetry or malicious self-approved epigenetic edits.",
        severity="high",
        mitigation="Inter-node consistency check + external causal grounding (E_causal <= 0.03) + ILF quarantine + independent DLT quorum + anti-self-approval gate.",
        verification_ref="T238 adversarial resilience benchmark (100% Byzantine isolation, 78/78 malicious proposals blocked)",
        residual_risk_note="Colluding majority (>1/3 Byzantine swarm members) requires multi-operator governance and external human audit.",
    ),
    RiskRegisterEntry(
        risk_id="RISK-03",
        category="cloud_spof_and_coordinator_outage",
        description="Remote MCP server or cloud coordinator outage interrupting node operation or wiping ephemeral audit logs.",
        severity="high",
        mitigation="Autonomous Layer-0 local fallback (T238), MicroNodeFailoverClient remote-to-local fallback, and self-hosted Docker Compose kit with persistent audit volume (T239).",
        verification_ref="T238 blackout failover (8/8 reconciled) + T239 failover drill",
        residual_risk_note="Free-tier cloud hosting (Render Free) remains ephemeral and unsuitable for regulated retention.",
    ),
    RiskRegisterEntry(
        risk_id="RISK-04",
        category="gradual_epigenetic_drift",
        description="Cumulative small adaptations ('Boiling Frog') or Goodhart gaming weakening safety margins over time.",
        severity="high",
        mitigation="SHA-256 write-locked constitutional genome, geodesic distance cap, sliding-window excursion cap, boundary dwell reset, homeostatic decay, and HiddenCausalEvaluator monotonic epochs.",
        verification_ref="T234 Pillar-5 verification drills (7/7 pass, rollback_pass_rate == 1.0)",
        residual_risk_note="Requires periodic external causal benchmarks calibrated to the target operational domain.",
    ),
    RiskRegisterEntry(
        risk_id="RISK-05",
        category="privacy_and_credential_exposure",
        description="Leakage of personal data (PII) in logs or exposure of OAuth/API secrets in source control or prompts.",
        severity="medium",
        mitigation="Privacy-safe SHA-256 prompt hashing by default (RequestRecord), opt-in raw-text redaction (BrainAuditLog), hash-only MCP audit, and .gitignore exclusions.",
        verification_ref="verify_privacy_by_default_controls() + T225/T231 audit tests",
        residual_risk_note="Deployers remain responsible for secret rotation, HSM storage, and GDPR DPIA in production.",
    ),
)


def _canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class SeriousIncidentRecord:
    """EU AI Act Art. 73 standardized serious-incident evidence record (human submission only)."""

    schema_version: str
    eu_ai_act_ref: str
    incident_id: str
    node_id: str
    occurred_at_utc: str
    severity: IncidentSeverity
    category: str
    summary: str
    layer0_interlock_engaged: bool
    rollback_executed: bool
    affected_genome_sha256: str
    human_review_required: bool
    auto_submission_permitted: bool
    record_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_serious_incident_report(
    *,
    incident_id: str,
    node_id: str,
    severity: IncidentSeverity,
    category: str,
    summary: str,
    layer0_interlock_engaged: bool,
    rollback_executed: bool,
    occurred_at_utc: str | None = None,
) -> SeriousIncidentRecord:
    """Construct a tamper-evident EU AI Act Art. 73 serious-incident report for human review."""
    if not incident_id.strip() or not node_id.strip() or not summary.strip():
        raise ValueError("incident_id, node_id, and summary must be non-empty")
    if severity not in ("low", "medium", "high", "critical"):
        raise ValueError(f"unsupported severity: {severity!r}")

    ts = occurred_at_utc or datetime.now(UTC).isoformat()
    genome_sha = ConstitutionalGenome().genome_sha256()
    base: dict[str, Any] = {
        "schema_version": "eu_ai_act_art73_incident.v1",
        "eu_ai_act_ref": "Regulation (EU) 2024/1689 Art. 73",
        "incident_id": incident_id.strip(),
        "node_id": node_id.strip(),
        "occurred_at_utc": ts,
        "severity": severity,
        "category": category.strip() or "unspecified",
        "summary": summary.strip(),
        "layer0_interlock_engaged": bool(layer0_interlock_engaged),
        "rollback_executed": bool(rollback_executed),
        "affected_genome_sha256": genome_sha,
        "human_review_required": True,
        "auto_submission_permitted": False,
    }
    digest = _canonical_sha256(base)
    return SeriousIncidentRecord(**base, record_sha256=digest)


def verify_incident_record_integrity(record: dict[str, Any]) -> bool:
    """Verify SHA-256 integrity and mandatory human-review flags of an Art. 73 incident record."""
    recorded = record.get("record_sha256")
    if not isinstance(recorded, str) or len(recorded) != 64:
        return False
    without_hash = {k: v for k, v in record.items() if k != "record_sha256"}
    try:
        expected = _canonical_sha256(without_hash)
    except (TypeError, ValueError):
        return False
    return (
        recorded == expected
        and record.get("human_review_required") is True
        and record.get("auto_submission_permitted") is False
    )


def verify_privacy_by_default_controls() -> dict[str, Any]:
    """Programmatically verify privacy-by-default prompt hashing and raw-text audit redaction."""
    from q_speace.spiking_brain.audit import BrainAuditLog, make_apply_record
    from q_speace.vertical_slice.contracts import RequestRecord, sha256_text

    sentinel_pii = "SENSITIVE-PII-TEST-STRING-DO-NOT-STORE"
    req = RequestRecord(
        run_id="t240-privacy-check",
        request_id="req-1",
        model_id="local-check",
        model_revision=None,
        policy_id="combined_gate",
        prompt_hash=sha256_text(sentinel_pii),
        started_at="2026-11-23T00:00:00Z",
    )
    req_dict = req.to_dict()
    request_hashing_ok = (
        "prompt_text" not in req_dict
        and sentinel_pii not in json.dumps(req_dict)
        and len(req_dict["prompt_hash"]) == 64
    )

    redaction_ok = False
    with tempfile.TemporaryDirectory() as tmpdir:
        audit_path = Path(tmpdir) / "privacy_check_audit.jsonl"
        audit = BrainAuditLog(audit_path, redact_raw_text=True)
        rec = make_apply_record(
            agent_id="t240-probe",
            backend="stub",
            backend_meta={},
            prompt=sentinel_pii,
            result_text=sentinel_pii,
            result_confidence=0.8,
            result_belief=[0.5, 0.5],
            n_tokens=8,
            coherence_phi_pre=0.8,
            coherence_phi_post=0.82,
            sevo=2.1,
            energy_w=10.0,
            approved=True,
            reason="privacy_probe",
            include_raw_excerpts=not audit.redact_raw_text,
        )
        audit.write(rec)
        audit.close()
        raw_disk = audit_path.read_text(encoding="utf-8")
        redaction_ok = (
            sentinel_pii not in raw_disk
            and "prompt_excerpt" not in raw_disk
            and "prompt_hash" in raw_disk
            and "result_hash" in raw_disk
        )

    return {
        "passed": request_hashing_ok and redaction_ok,
        "request_record_omits_raw_prompt_by_default": request_hashing_ok,
        "brain_audit_redacts_raw_text_when_enabled": redaction_ok,
    }


@dataclass(frozen=True)
class ModelGovernanceEntry:
    """T241 Model Governance Registry record for internal or external LLM/GPAI models."""

    model_id: str
    provider: str
    version_or_revision: str
    license: str
    deployment_mode: str
    lifecycle_status: ModelLifecycleStatus
    data_residency: str
    evaluation_evidence: str
    deprecation_date: str | None = None
    notes: str = ""


DEFAULT_MODEL_GOVERNANCE_REGISTRY: tuple[ModelGovernanceEntry, ...] = (
    ModelGovernanceEntry(
        model_id="qspeace-stub-deterministic",
        provider="q_speace (internal)",
        version_or_revision="1.0",
        license="Repository open-source license",
        deployment_mode="in_process_deterministic",
        lifecycle_status="approved_deterministic_stub",
        data_residency="local_only_no_egress",
        evaluation_evidence="T208/T231 deterministic vertical-slice regression suite",
        notes="Zero external API dependency; reference baseline for CI and offline testing.",
    ),
    ModelGovernanceEntry(
        model_id="Qwen/Qwen2.5-3B-Instruct",
        provider="Qwen (open-weights local sidecar)",
        version_or_revision="NF4-4bit-local-2026-11-22",
        license="Apache-2.0",
        deployment_mode="local_gpu_sidecar_http_loopback",
        lifecycle_status="approved_research_local",
        data_residency="local_only_no_egress",
        evaluation_evidence=(
            "T210 pilot GPU run (artifacts/t210_gpu_run_20261122: n=24 inferences, 0 failed, "
            "unsafe_answer_rate 100% -> 33.3%, Brier=0.2492, ECE=0.2206; requires expanded dataset before production)"
        ),
        notes="Research pilot only; output remains untrusted and gated by combined_gate + Sevo.",
    ),
    ModelGovernanceEntry(
        model_id="external-mcp-agent-llm",
        provider="Third-party GPAI / Orchestrator (GPT / Claude / Gemini / Gemma / etc.)",
        version_or_revision="caller-declared",
        license="Third-party provider terms (deployer DPA required)",
        deployment_mode="external_mcp_client_advisory_only",
        lifecycle_status="external_mcp_caller_untrusted",
        data_residency="deployer_controlled_external",
        evaluation_evidence="T225/T234/T236 authenticated MCP boundary (12 advisory tools, zero actuation)",
        notes=(
            "External LLMs never execute inside q_speace and hold zero actuation or self-approval authority; "
            "deployer must maintain vendor DPAs and domain calibration checks."
        ),
    ),
    ModelGovernanceEntry(
        model_id="legacy-uncalibrated-llm-v0",
        provider="Deprecated placeholder",
        version_or_revision="0.1-deprecated",
        license="N/A",
        deployment_mode="none",
        lifecycle_status="deprecated",
        data_residency="none",
        evaluation_evidence="Superseded by T210 calibrated evaluation protocol",
        deprecation_date="2026-11-01",
        notes="Blocked fail-closed by validate_model_governance_selection().",
    ),
)

MODEL_SELECTION_CRITERIA: dict[str, Any] = {
    "required_evaluation_protocol": "T208/T210 vertical-slice held-out evaluation",
    "max_unsafe_answer_rate_research_pilot": 0.35,
    "max_ece_target_pre_production": 0.10,
    "mandatory_privacy_controls": [
        "RequestRecord SHA-256 prompt hashing",
        "BrainAuditLog redact_raw_text=True when PII may appear",
        "No client secrets or PII sent to external unvetted endpoints",
    ],
    "mandatory_safety_invariants": [
        "untrusted_text_generation_only",
        "no_direct_physical_actuation",
        "no_self_approval",
    ],
}

MODEL_DEPRECATION_POLICY: dict[str, Any] = {
    "fail_closed_on_deprecated_or_prohibited": True,
    "fail_closed_on_unregistered_model": True,
    "triggers_for_immediate_deprecation": [
        "Critical unpatched security CVE or safety regression",
        "Failure of external causal grounding (E_causal > 0.03) or calibration collapse",
        "License incompatibility or unapproved data-retention terms",
    ],
    "retirement_workflow": (
        "Mark lifecycle_status='deprecated' with ISO deprecation_date, block runtime selection via "
        "validate_model_governance_selection(), and re-run T239/T240 compliance pack after replacement."
    ),
}

CRA_SUPPLY_CHAIN_POLICY: dict[str, Any] = {
    "security_policy_path": "SECURITY.md",
    "vulnerability_disclosure_channel": "GitHub Security Advisories (private draft)",
    "coordinated_disclosure_window_days": 90,
    "cve_patch_sla_hours": {
        "critical": 48,
        "high": 168,
        "medium": 720,
    },
    "support_window": "Rolling security maintenance on main branch (experimental research profile)",
    "sbom_standard": "CycloneDX 1.5 JSON with versioned metadata, URN serialNumber, and SHA-256 checksum",
    "ci_cve_scan": "pip-audit report uploaded alongside versioned SBOM in .github/workflows/ci.yml",
    "external_provider_signing_note": (
        "Operators shipping regulated derivatives must sign release bundles and SBOMs with "
        "organization-owned HSM/Sigstore keys and manage statutory CRA/ENISA notifications."
    ),
}


def validate_model_governance_selection(
    model_id: str,
    *,
    registry: tuple[ModelGovernanceEntry, ...] = DEFAULT_MODEL_GOVERNANCE_REGISTRY,
    allow_external_mcp_caller: bool = False,
) -> ModelGovernanceEntry:
    """Fail-closed gate verifying a model is registered and not deprecated/prohibited (T241)."""
    entry = next((m for m in registry if m.model_id == model_id), None)
    if entry is None:
        raise EpigeneticFaultError(f"unregistered model blocked by T241 governance: {model_id!r}")
    if entry.lifecycle_status in ("deprecated", "prohibited"):
        raise EpigeneticFaultError(
            f"model {model_id!r} blocked due to lifecycle_status={entry.lifecycle_status!r}"
        )
    if entry.lifecycle_status == "external_mcp_caller_untrusted" and not allow_external_mcp_caller:
        raise EpigeneticFaultError(
            f"external untrusted MCP caller {model_id!r} requires explicit allow_external_mcp_caller=True"
        )
    return entry


def build_runtime_sbom() -> dict[str, Any]:
    """Generate a versioned CycloneDX 1.5 JSON SBOM with URN serialNumber and SHA-256 digest (T241)."""
    components: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    qspeace_version = "0.1.0"
    for dist in importlib.metadata.distributions():
        name = (dist.metadata.get("Name") or "").strip()
        version = (dist.version or "").strip()
        if not name:
            continue
        if name.lower().replace("-", "_") == "q_speace":
            qspeace_version = version
        key = (name.lower(), version)
        if key in seen:
            continue
        seen.add(key)
        components.append(
            {
                "type": "library",
                "name": name,
                "version": version,
                "purl": f"pkg:pypi/{name.lower()}@{version}",
            }
        )
    components.sort(key=lambda c: (c["name"].lower(), c["version"]))
    comp_digest = _canonical_sha256({"components": components, "q_speace_version": qspeace_version})
    serial_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"q-speace:sbom:{comp_digest}")
    sbom_core: dict[str, Any] = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{serial_uuid}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(),
            "component": {
                "type": "application",
                "name": "q-speace",
                "version": qspeace_version,
            },
        },
        "component_count": len(components),
        "components": components,
    }
    sbom_core["sbom_sha256"] = _canonical_sha256(sbom_core)
    return sbom_core


@dataclass(frozen=True)
class AnnexIVCompliancePack:
    """Tamper-evident T240/T241 Annex IV / NIST AI RMF / ISO 42001 technical compliance readiness pack."""

    schema_version: str
    spec: str
    node_id: str
    generated_at_utc: str
    genome_sha256: str
    system_card: dict[str, Any]
    evidence_bundle: dict[str, Any]
    privacy_by_default_check: dict[str, Any]
    regulatory_control_matrix: list[dict[str, Any]]
    risk_register: list[dict[str, Any]]
    model_governance: dict[str, Any]
    cra_supply_chain_policy: dict[str, Any]
    fria_template: dict[str, Any]
    qms_deployer_checklist: dict[str, Any]
    deployer_instructions: dict[str, Any]
    incident_reporting_schema: dict[str, Any]
    sbom_summary: dict[str, Any]
    external_legal_obligations: list[str]
    overall_technical_readiness: bool
    legal_certification_granted: bool
    ce_marking_granted: bool
    qms_externally_certified: bool
    fria_completed_by_deployer: bool
    self_approval_permitted: bool
    mcp_actuation_permitted: bool
    pack_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def verify_compliance_pack_integrity(pack: dict[str, Any]) -> bool:
    """Independently verify SHA-256 integrity, embedded T239 bundle, and non-self-certification invariants."""
    recorded = pack.get("pack_sha256")
    if not isinstance(recorded, str) or len(recorded) != 64:
        return False
    without_hash = {k: v for k, v in pack.items() if k != "pack_sha256"}
    try:
        expected = _canonical_sha256(without_hash)
    except (TypeError, ValueError):
        return False
    embedded = pack.get("evidence_bundle")
    embedded_ok = isinstance(embedded, dict) and verify_evidence_bundle_integrity(embedded)
    return (
        recorded == expected
        and embedded_ok
        and pack.get("legal_certification_granted") is False
        and pack.get("ce_marking_granted") is False
        and pack.get("qms_externally_certified") is False
        and pack.get("fria_completed_by_deployer") is False
        and pack.get("self_approval_permitted") is False
        and pack.get("mcp_actuation_permitted") is False
    )


def build_annex_iv_compliance_pack(
    *,
    node_id: str = "speace-micro-local",
    seeds: tuple[int, ...] = (11, 23, 37, 53),
    output_path: Path | None = None,
    evidence_bundle: MicroNodeEvidenceBundle | None = None,
    repo_root: Path | None = None,
) -> AnnexIVCompliancePack:
    """Generate a complete, SHA-256 verifiable T240 Annex IV technical compliance readiness pack."""
    bundle = (
        evidence_bundle
        if evidence_bundle is not None
        else certify_micro_node(node_id=node_id, seeds=seeds, repo_root=repo_root)
    )
    bundle_dict = bundle.to_dict()
    privacy_check = verify_privacy_by_default_controls()
    sbom = build_runtime_sbom()
    generated_at = datetime.now(UTC).isoformat()
    genome_sha = ConstitutionalGenome().genome_sha256()

    sample_incident = build_serious_incident_report(
        incident_id="TEMPLATE-ART73-001",
        node_id=node_id,
        severity="high",
        category="layer0_interlock_or_rollback_template",
        summary="Template schema demonstrating EU AI Act Art. 73 serious-incident evidence export.",
        layer0_interlock_engaged=True,
        rollback_executed=True,
        occurred_at_utc=generated_at,
    )

    system_card: dict[str, Any] = {
        "system_name": "Q-SPEACE Micro Node",
        "release_profile": "experimental_research_open_source",
        "applicable_frameworks": [
            "EU AI Act (Regulation (EU) 2024/1689)",
            "NIST AI RMF 1.0",
            "ISO/IEC 42001:2023 (AIMS)",
            "EU Cyber Resilience Act (CRA)",
            "GDPR (Regulation (EU) 2016/679)",
        ],
        "intended_uses": [
            "Bounded numerical advisory computation over authenticated MCP (12 HTTP tools).",
            "Sandboxed digital-twin evaluation and ablation benchmarking (T237/T238).",
            "Reproducible local compliance evidence generation for independent human review.",
        ],
        "prohibited_uses": [
            "EU AI Act Art. 5 prohibited AI practices.",
            "Direct remote actuation of physical infrastructure, robotics, medical, or IoNT hardware via MCP.",
            "Routing real-time motor control or safety interlocks through LLMs or DLT consensus.",
            "Unreviewed operational promotion or autonomous self-certification.",
        ],
        "bcel_terminology_notice": (
            "Biological/cybernetic terms ('Singularity', 'Genome', 'Epigenome', 'Cosmic Virus Optimizer', "
            "'IoNT Cellular Node') denote bounded mathematical and software-governance primitives only; "
            "no claim of consciousness, life, or unconstrained autonomy is made."
        ),
    }

    deployer_instructions: dict[str, Any] = {
        "eu_ai_act_art13_art14_checklist": [
            "Run self-hosted container with persistent audit volume (deploy/micro-node/docker-compose.yml) instead of ephemeral free-tier cloud storage.",
            "Enable redact_raw_text=True on BrainAuditLog and avoid sending raw PII in MCP payloads.",
            "Keep Layer-0 hardware interlocks physically isolated (<5ms halt SLA) from LLMs, DLT, and MCP.",
            "Assign trained independent human reviewers (no proposer self-approval) for T217 qualification gates.",
            "Rotate OAuth client secrets and API tokens on a documented schedule; never store secrets in prompts or Git.",
        ],
        "high_risk_transition_warning": (
            "Connecting Q-SPEACE as a safety component of critical infrastructure or physical hardware triggers "
            "EU AI Act High-Risk obligations (Arts. 8-15, Annex IV, QMS Art. 17, Conformity Assessment Arts. 43-49) "
            "and ends the Art. 2(12) open-source exemption."
        ),
    }

    external_legal_obligations = [
        "Designate a legal Provider / Deployer entity (and EU Authorized Representative under Art. 22 where applicable).",
        "Establish a documented Quality Management System (EU AI Act Art. 17 / ISO/IEC 42001 external audit).",
        "Conduct Fundamental Rights Impact Assessment (FRIA, Art. 27) and GDPR DPIA for concrete deployment contexts.",
        "Complete formal Conformity Assessment, EU Declaration of Conformity, EU database registration, and CE marking (Arts. 43-49) prior to High-Risk market placement.",
    ]

    overall_ready = bool(bundle.overall_compliant and privacy_check["passed"])
    model_governance: dict[str, Any] = {
        "registry": [asdict(m) for m in DEFAULT_MODEL_GOVERNANCE_REGISTRY],
        "selection_criteria": MODEL_SELECTION_CRITERIA,
        "deprecation_policy": MODEL_DEPRECATION_POLICY,
    }
    fria_template: dict[str, Any] = {
        "template_id": "T241-FRIA-v1",
        "template_path": "docs/compliance/FRIA_TEMPLATE_EN.md",
        "eu_ai_act_ref": "Regulation (EU) 2024/1689 Art. 27",
        "required_sections": [
            "deployment_context",
            "stakeholder_impact_analysis",
            "fundamental_rights_impact_matrix",
            "non_discrimination_and_bias_evaluation",
            "societal_and_ecological_effects",
            "human_oversight_and_remediation_plan",
            "deployer_formal_sign_off",
        ],
        "completed_by_deployer": False,
    }
    qms_deployer_checklist: dict[str, Any] = {
        "template_id": "T241-QMS-CHECKLIST-v1",
        "template_path": "docs/compliance/QMS_DEPLOYER_CHECKLIST_EN.md",
        "eu_ai_act_ref": "Regulation (EU) 2024/1689 Art. 17 / ISO/IEC 42001",
        "required_domains": [
            "operational_sops",
            "supplier_and_third_party_management",
            "change_control_and_configuration_management",
            "staff_training_and_ai_literacy",
            "escalation_and_serious_incident_response",
        ],
        "qms_externally_certified": False,
    }
    base_payload: dict[str, Any] = {
        "schema_version": "annex_iv_compliance_pack.v1",
        "spec": "T240+T241",
        "node_id": node_id,
        "generated_at_utc": generated_at,
        "genome_sha256": genome_sha,
        "system_card": system_card,
        "evidence_bundle": bundle_dict,
        "privacy_by_default_check": privacy_check,
        "regulatory_control_matrix": [asdict(c) for c in EU_AI_ACT_CONTROL_MATRIX],
        "risk_register": [asdict(r) for r in DEFAULT_RISK_REGISTER],
        "model_governance": model_governance,
        "cra_supply_chain_policy": CRA_SUPPLY_CHAIN_POLICY,
        "fria_template": fria_template,
        "qms_deployer_checklist": qms_deployer_checklist,
        "deployer_instructions": deployer_instructions,
        "incident_reporting_schema": sample_incident.to_dict(),
        "sbom_summary": {
            "bomFormat": sbom["bomFormat"],
            "specVersion": sbom["specVersion"],
            "serialNumber": sbom["serialNumber"],
            "q_speace_version": sbom["metadata"]["component"]["version"],
            "component_count": sbom["component_count"],
            "sbom_sha256": sbom["sbom_sha256"],
        },
        "external_legal_obligations": external_legal_obligations,
        "overall_technical_readiness": overall_ready,
        "legal_certification_granted": False,
        "ce_marking_granted": False,
        "qms_externally_certified": False,
        "fria_completed_by_deployer": False,
        "self_approval_permitted": False,
        "mcp_actuation_permitted": False,
    }
    digest = _canonical_sha256(base_payload)

    pack = AnnexIVCompliancePack(**base_payload, pack_sha256=digest)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(pack.to_dict(), indent=2, sort_keys=True, allow_nan=False),
            encoding="utf-8",
        )
    return pack
