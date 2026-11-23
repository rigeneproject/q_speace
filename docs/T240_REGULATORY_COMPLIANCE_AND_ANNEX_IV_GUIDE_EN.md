# Q-SPEACE Regulatory Compliance Readiness & Technical Documentation Guide (T240)

- **Document ID**: `T240`
- **Version**: `1.0`
- **Date**: `2026-11-23`
- **Status**: Agentic Technical Specification & Compliance Readiness Guide (Experimental Research / Open-Source Software)
- **Applicable Frameworks**: EU AI Act (Regulation (EU) 2024/1689), NIST AI Risk Management Framework (AI RMF 1.0), ISO/IEC 42001:2023 (AIMS), EU Cyber Resilience Act (CRA), GDPR (Regulation (EU) 2016/679)
- **Parent Specifications**: `AGENTS.md`, `T208`, `T217`, `T218`, `T220`, `T221`, `T225`, `T234`, `T236`, `T237`, `T238`, `T239`

> **Legal Boundary Notice**: This document provides a technical engineering assessment and machine-verifiable compliance artifacts produced by `q_speace`. It is **not** formal legal advice, an EU Declaration of Conformity, a CE marking, or an ISO certification. Under Regulation (EU) 2024/1689 and `T217`, legal compliance and operational promotion in regulated or high-risk domains remain the responsibility of an identified legal Provider/Deployer and independent conformity assessment bodies.

---

## 1. Executive Summary & Scope Classification

### 1.1 Is `q_speace` in conflict with international AI regulations?
**No.** `q_speace` does not implement any prohibited AI practice under **EU AI Act Article 5** (no subliminal manipulation, no social scoring, no real-time remote biometric identification, no workplace/educational emotion recognition, and no biometric scraping).

In its current release profile, `q_speace` is an **open-source scientific research and advisory governance library** with bounded numerical primitives, simulated digital twins, and an authenticated advisory Model Context Protocol (MCP) service. As such:
- **Research & Open-Source Scope (EU AI Act Art. 2(6), 2(8), 2(12))**: When used strictly for pre-commercial scientific R&D or distributed under an open-source license without being placed on the market as a High-Risk AI system or as a safety component of a regulated physical product, `q_speace` falls within the EU AI Act R&D and open-source exemptions.
- **High-Risk Transition Trigger (EU AI Act Art. 6, Annex I, Annex III)**: If a third-party integrator connects `q_speace` to **critical infrastructure** (e.g., live electrical microgrids, transport, water, healthcare) or **physical cyber-physical / IoNT actuators** as a safety component, the open-source exemption no longer applies (Art. 2(12)). Full High-Risk obligations (Articles 8–15, Annex IV, Quality Management System Art. 17, Conformity Assessment Arts. 43–49, and CE marking) are triggered and **must** be completed by the legal Provider/Deployer before operational deployment.

### 1.2 Architectural Alignment by Design
`q_speace` embeds regulatory-grade engineering invariants directly into code and automated CI verification:
- **Non-Actuating Boundary (`mcp_actuation_permitted = False`)**: Remote MCP tools (12 HTTP advisory tools) perform bounded numerical evaluation only; they cannot actuate hardware, mutate accounting balances (`dat_mint`/`dat_spend` excluded from HTTP), or promote operational changes.
- **No Self-Approval (`self_approval_permitted = False`, `I3`/`C3`)**: Neither an agent, nor an epigenetic regulator, nor a compliance bundle can approve its own deployment or modification.
- **Independent Deterministic Layer-0 Safety (`T236`–`T238`)**: Simulated physical bounds, thermal caps, and hardware emergency stop (`< 5 ms` physical SLA) execute strictly outside LLM, DLT, and MCP loops.
- **Slow-Plane DLT Governance Isolation**: `consensus_quorum` is structurally restricted to `host_scope="slow_plane_dlt_governance_only"` and rejected fail-closed (`EpigeneticFaultError`) if injected into any motor-control payload.
- **Strict Track Separation (`T221`)**: Static AST verification enforces zero imports from Track B (`q_speace.seed`, `q_speace.singularity`) inside Track A (`q_speace.ptaa`).

---

## 2. Regulatory Terminology Translation (BCEL Discipline)

Research literature in `q_speace` uses cybernetic and biological analogies. To prevent regulatory misclassification during legal or technical audits, every concept passes through the **Biological-to-Computational Equivalence Law (BCEL)** filter (`q_speace/bcel/catalog.py`):

| Research / Internal Term | Formal Engineering & Regulatory Meaning | Explicitly Excluded Interpretation |
|---|---|---|
| `Singularity` (`T234`) | Bounded multi-stage readiness evaluator with non-compensable entropy, causal, energy, and thermal brakes | Unbounded autonomous superintelligence or self-awakening AI |
| `Constitutional Genome` / `Epigenome` | SHA-256 write-locked safety configuration (`I1`–`I5`, `C1`–`C5`) paired with bounded, rate-limited, reversible runtime tuning parameters | Biological DNA or unrestrained self-modifying code |
| `Cosmic Virus Optimizer` | Deterministic bounded single-locus perturbation generator with explicit step clamping | Computer malware, self-propagating software, or cyber-offensive tooling |
| `IoNT Cellular Node` / `SPEACE Macro Mini` (`T236`–`T238`) | Multi-node cyber-physical digital twin architecture separated into 4 layers (hardware interlock, sensor telemetry, permissioned audit ledger, advisory MCP) | Living biological organism or autonomous physical swarm |
| `Organismic Gain` ($G_{\mathrm{org}}$, `T237`) | Paired comparative performance metric with 95% bootstrap CI and controlled ablation against isolated/static/non-Singularity baselines | Emergent consciousness or uncontrolled collective agency |
| `Micro-Node Certify` (`T239`) | Reproducible SHA-256 technical evidence bundle (`micro_node_evidence.v1`) for external reviewers | Legal certification, regulatory approval, or CE marking |

---

## 3. International Regulatory Control Matrix

Each control below is encoded in machine-readable form in `q_speace/singularity/compliance.py` (`EU_AI_ACT_CONTROL_MATRIX`).

| Framework & Clause | Requirement Summary | `q_speace` Technical Implementation | Automated Evidence | Status & Responsibility Boundary |
|---|---|---|---|---|
| **EU AI Act Art. 5** | Prohibited AI practices | None implemented; no biometric, emotional, subliminal, or social-scoring capabilities | Static codebase + BCEL catalog | **Compliant (Design)** |
| **EU AI Act Art. 9** / **NIST MAP & MANAGE** / **ISO 42001 §6.1** | Continuous Risk Management System | `DEFAULT_RISK_REGISTER`, non-compensable brakes ($\Delta H_{\mathrm{sem}} \le 0.05$, $E_{\mathrm{causal}} \le 0.03$, `Sevo`, thermal caps), `T217` lifecycle | `qspace micro-node compliance-pack`, 7 drills (`T234`/`T236`), `T237`, `T238` | **Technical Controls Implemented**; lifecycle governance owned by Provider/Deployer |
| **EU AI Act Art. 10** / **GDPR Art. 5, 25** | Data Governance & Privacy-by-Design | Privacy-safe SHA-256 request hashing (`vertical_slice/contracts.py`), opt-in raw-text redaction (`spiking_brain/audit.py`), hash-only MCP audit (`remote_mcp/audit.py`) | `verify_privacy_by_default_controls()`, `test_t231_vertical_slice.py`, `test_t240_regulatory_compliance.py` | **Technical Controls Implemented**; domain datasets & DPIA owned by Deployer |
| **EU AI Act Art. 11 & Annex IV** | Technical Documentation | `T240` Annex IV Compliance Pack (`annex_iv_compliance_pack.v1`, `pack_sha256`), `T208`–`T240` specs, CI SBOM generation | `qspace micro-node compliance-pack --output ...`, `verify_compliance_pack_integrity()` | **Technical File Export Implemented**; legal Provider identity & market filing external |
| **EU AI Act Art. 12** / **ISO 42001 §9.1** | Record-Keeping & Traceability | Hash-chained `DLTSwarmLedger`, `EpigeneticAuditEntry`, `BrainAuditLog`, persistent Docker volume (`deploy/micro-node/docker-compose.yml`) | `test_t234_singularity_framework.py`, `test_t236_iont_cellular_node.py` | **Implemented for Self-Hosted**; Render Free ephemeral storage is **not** durable compliance logging |
| **EU AI Act Art. 13 & Art. 50** / **NIST GOVERN** | Transparency & Instructions for Use | `T225_AGENT_CONNECTION_GUIDE_EN.md`, BCEL catalog, `deployer_instructions` inside `T240` pack, explicit non-consciousness/non-actuation notices | `test_t240_regulatory_compliance.py`, `bcel_lookup` | **Implemented**; end-user UI disclosure owned by Deployer |
| **EU AI Act Art. 14** / **NIST GOVERN** | Human Oversight & Intervention | `self_approval_permitted=False`, `mcp_actuation_permitted=False`, `KillSwitch` (`I1`), `requires_independent_human_review_for_t217=True` | `test_seed_invariants.py`, `test_ptaa_redteam.py`, `test_t239_micro_node_certification.py` | **Technical Controls Implemented**; trained human operators owned by Deployer |
| **EU AI Act Art. 15** / **NIST MEASURE** / **EU CRA** | Accuracy, Robustness & Cybersecurity | Layer-0 interlock, 7 adversarial drills (`rollback_pass_rate=1.0`), `T237` held-out ablation, `T238` Byzantine (100% isolation) & blackout failover (8/8), RFC 8259 fail-closed JSON, OAuth RS256, CI SBOM | `pytest` (770+ tests, >90% cov), `mypy`, `ruff`, `black`, CI SBOM artifact | **Technical Controls Implemented**; production network/HSM hardening owned by Operator |
| **EU AI Act Art. 73** | Reporting of Serious Incidents | Standardized `SeriousIncidentRecord` (`build_serious_incident_report`) with `record_sha256`, `human_review_required=True`, `auto_submission_permitted=False` | `test_t240_regulatory_compliance.py` | **Schema & Evidence Export Implemented**; regulatory notification submitted by legal Provider |
| **EU AI Act Arts. 17, 27, 43–49** | QMS, FRIA, Conformity Assessment & CE Marking | Documented as blocking prerequisites in `T217` and `external_legal_obligations` of `T240` pack | Explicit non-certification flags (`legal_certification_granted=False`, `ce_marking_granted=False`) | **External Legal / Organizational Obligation** (cannot be automated in software) |

---

## 4. Intended Uses, Prohibited Uses & Residual Risks

### 4.1 Intended Uses
- Bounded numerical advisory computation over authenticated MCP (`bcel_lookup`, `adaptive_clock_rate`, `metabolism_cost_eval`, `compute_jc`, `cme_evaluate`, `elasticity_test`, `kl_barycentre_aggregate`, `vtec_allocate`, `singularity_framework_manifest`, `phase_transition_assess`, `epigenetic_step_evaluate`, `iont_node_assess`).
- Sandboxed digital-twin evaluation, controlled ablation benchmarking (`T237`/`T238`), and reproducible local compliance evidence generation (`T239`/`T240`).
- Human-reviewed decision support where an external authorized orchestrator enforces budgets, permissions, and stop rules.

### 4.2 Explicitly Prohibited Uses
- Direct remote actuation of physical infrastructure, robotics, medical devices, or IoNT hardware via MCP.
- Routing real-time motor control or hardware safety interlocks through LLM inference, remote HTTP calls, or DLT consensus (`consensus_quorum`).
- Autonomous self-approval of constitutional changes, operational promotion, or legal compliance claims.
- Any prohibited practice enumerated in EU AI Act Article 5.

### 4.3 Summary of Residual Risks (EU AI Act Art. 9)
1. **Ephemeral cloud logging (Render Free)**: Free-tier instances wipe local SQLite audit logs on sleep/restart. *Mitigation*: Deploy self-hosted (`deploy/micro-node/docker-compose.yml`) with persistent append-only volume for any sustained evaluation.
2. **External LLM hallucination or prompt injection**: Upstream generative models remain untrusted text generators. *Mitigation*: Strict schema validation, RFC 8259 finite-JSON parsing, `E_causal <= 0.03` external grounding, and zero direct execution authority.
3. **Simulation-to-reality gap**: Passing `T237`/`T238` in sandboxed simulation does not prove physical safety in real hardware. *Mitigation*: Mandatory `T217` staged qualification (simulation → isolated replica → confined prototype → independent review) before any physical contact.
4. **External credential exposure**: Operator OAuth client secrets or GitHub tokens must never be embedded in prompts, browsers, or source control; rotate credentials immediately if exposed.

---

## 5. Reproducible Verification & Export Workflow

Any independent auditor or operator can reproduce the full technical evidence and Annex IV readiness pack locally with zero cloud or vendor lock-in:

```bash
# 1. Run all 7 adversarial drills (requires rollback_pass_rate == 1.0)
qspace singularity drills

# 2. Run T237 4-configuration federation & Singularity ablation benchmark
qspace singularity federation-benchmark --seeds 11,23,37,53

# 3. Run T238 adversarial Byzantine & coordinator-blackout resilience benchmark
qspace singularity resilience-benchmark --seeds 11,23,37,53

# 4. Generate SHA-256 verifiable Micro-Node Evidence Bundle (T239)
qspace micro-node certify --node-id org-micro-01 --output evidence_bundle.json
qspace micro-node verify-bundle --bundle evidence_bundle.json

# 5. Export full Annex IV / NIST / ISO 42001 Compliance Readiness Pack (T240)
qspace micro-node compliance-pack --node-id org-micro-01 --output annex_iv_pack.json
```

CI (`.github/workflows/ci.yml`) additionally executes `ruff`, `black --check`, `mypy`, `compileall`, `pytest`, exports a versioned CycloneDX 1.5 JSON **Software Bill of Materials (SBOM)** with a detached SHA-256 checksum, and runs `pip-audit` CVE scanning to support EU AI Act Article 15 and EU Cyber Resilience Act supply-chain traceability.

---

## 6. Auditor Gap Closure: CRA Security Policy, Model Governance, FRIA & QMS Templates (T241)

To address the four operational and governance areas typically scrutinized during formal AI compliance audits—while preserving the strict separation between software-verifiable controls and external legal obligations—`q_speace` includes the following T241 extensions embedded directly in the `T240` compliance pack (`annex_iv_compliance_pack.v1`):

### 6.1 Supply-Chain Security & EU Cyber Resilience Act (CRA) Controls
- **Security & Vulnerability Disclosure Policy (`SECURITY.md`)**: Defines the private disclosure channel (GitHub Security Advisories), safe-harbor scope, **90-day coordinated disclosure** window, and rolling research support window on `main`.
- **CVE Triage & Patch SLAs**: Targets `<= 48 h` for Critical (`CVSS 9.0–10.0`), `<= 7 days` for High (`7.0–8.9`), and `<= 30 days` for Medium (`4.0–6.9`) vulnerabilities.
- **Versioned & Hashed CycloneDX 1.5 SBOM**: `build_runtime_sbom()` emits a deterministic `urn:uuid` `serialNumber`, `metadata.timestamp`, `q-speace` application version, full package list, and `sbom_sha256` checksum. CI archives `sbom-cyclonedx.json`, `sbom-cyclonedx.json.sha256`, and a `pip-audit` CVE report on every build. *(External obligation: legal Providers shipping regulated products must additionally sign release artifacts with organization-owned HSM/Sigstore keys and manage statutory ENISA/CSIRT notifications.)*

### 6.2 Model Governance Registry (Internal & External LLM/GPAI Controls)
- **Authorized Model Registry (`DEFAULT_MODEL_GOVERNANCE_REGISTRY` in `q_speace/singularity/compliance.py`)**: Tracks `model_id`, provider, pinned version/revision, license, deployment mode, data residency, evaluation evidence (`T208`/`T210`), and lifecycle status (`approved_deterministic_stub`, `approved_research_local`, `external_mcp_caller_untrusted`, `deprecated`, `prohibited`).
- **Selection Criteria (`MODEL_SELECTION_CRITERIA`)**: Mandates `T208`/`T210` held-out calibration evaluation (`Brier`, `ECE`, `unsafe_answer_rate`), privacy-by-default hashing/redaction, and non-actuating untrusted-text framing.
- **Fail-Closed Deprecation Policy (`validate_model_governance_selection()`)**: Deterministically blocks unregistered, `deprecated`, or `prohibited` models (`EpigeneticFaultError`), and requires explicit opt-in acknowledgment (`allow_external_mcp_caller=True`) for third-party external LLM callers (GPT, Claude, Gemini, Gemma, etc.), whose vendor DPAs and SLAs remain the Deployer's contractual responsibility.

### 6.3 Fundamental Rights Impact Assessment (FRIA — EU AI Act Art. 27)
- **Structured Deployer Template (`docs/compliance/FRIA_TEMPLATE_EN.md`)**: Covers deployment context, stakeholder impact analysis (including vulnerable groups), EU Charter Fundamental Rights Impact Matrix (human dignity, privacy/GDPR, non-discrimination/bias, health/safety/environment, effective remedy, workers' rights), societal/ecological impact, and formal human sign-off.
- **Non-Self-Completion Guard**: The `T240+T241` compliance pack references the template and enforces `fria_completed_by_deployer = False` until a legal Deployer completes and signs the contextual assessment externally.

### 6.4 Quality Management System (QMS — EU AI Act Art. 17 / ISO 42001)
- **Deployer Readiness Checklist (`docs/compliance/QMS_DEPLOYER_CHECKLIST_EN.md`)**: Maps operational SOPs, supplier/vendor management, peer-reviewed change control, staff AI literacy & oversight training (Art. 4 & Art. 14), and L1→L3→Authority escalation workflows.
- **Non-Self-Certification Guard**: A software repository cannot certify an organizational QMS; the pack enforces `qms_externally_certified = False` alongside `legal_certification_granted = False` and `ce_marking_granted = False`.

---

## 7. BCEL Classification

Recorded in `q_speace/bcel/catalog.py`:
- **Functional**: `Regulatory compliance mapping, Annex IV technical pack, and incident reporting schema (T240)` and `Model governance registry, CRA security policy, and FRIA/QMS deployer templates (T241)`.
- **Accidental**: `Automated self-certification or legal CE-marking by software (T240)` and `Repository-certified organizational QMS or automated FRIA sign-off (T241)`.
