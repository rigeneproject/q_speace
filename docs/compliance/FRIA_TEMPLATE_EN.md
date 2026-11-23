# Fundamental Rights Impact Assessment (FRIA) Template — EU AI Act Article 27

- **Template ID**: `T241-FRIA-v1`
- **Applicable Law**: Regulation (EU) 2024/1689 (EU AI Act), Article 27
- **Mandatory Ownership**: Completed and signed by the **Deployer** prior to placing or operating a `q_speace`-derived system in any regulated or High-Risk context. **This template is NOT a completed assessment.**

---

## 1. Deployment Context & System Identification

| Field | Deployer Input |
| --- | --- |
| Deployer Legal Entity & Jurisdiction | `[Fill in organization name, country, contact]` |
| System / Node Identifier (`node_id`) | `[Fill in node_id from T239/T240 pack]` |
| Attached `T240` Compliance Pack SHA-256 | `[Paste pack_sha256]` |
| External LLM / GPAI Model ID(s) Used | `[Must match approved entries in Model Governance Registry]` |
| Intended Operational Domain & Geography | `[Describe concrete process, scope, and duration]` |
| Frequency of Use & Human Decision Coupling | `[Advisory-only / human-in-the-loop / frequency]` |

## 2. Stakeholder Impact Analysis

Identify all natural persons and groups potentially affected (directly or indirectly):
- **Primary affected groups**: `[Operators, citizens, workers, customers, vulnerable groups]`
- **Categories of persons at heightened risk**: `[Minors, persons with disabilities, marginalized communities, essential-service dependents]`
- **Notification & transparency mechanism (Art. 50 / Art. 26(7))**: `[How affected persons are informed they interact with AI-assisted decisions]`

## 3. Fundamental Rights Impact Matrix (EU Charter of Fundamental Rights)

| Fundamental Right (EU Charter) | Potential Risk / Harm Scenario | Likelihood (L/M/H) | Severity (L/M/H) | Technical & Organizational Mitigation | Residual Risk |
| --- | --- | --- | --- | --- | --- |
| Human Dignity & Autonomy (Art. 1) | Over-reliance on advisory scores removing human judgment | `[ ]` | `[ ]` | `self_approval_permitted=False`; mandatory human review | `[ ]` |
| Privacy & Data Protection (Arts. 7–8, GDPR) | PII leakage in prompts, telemetry, or logs | `[ ]` | `[ ]` | `RequestRecord` SHA-256 hashing; `redact_raw_text=True`; DPIA | `[ ]` |
| Non-Discrimination & Equality (Art. 21) | Biased upstream LLM outputs or skewed calibration across subgroups | `[ ]` | `[ ]` | Held-out subgroup bias/calibration audit (`T210` extension); model governance screening | `[ ]` |
| Safety, Health & Environmental Protection (Arts. 35, 37) | Faulty cyber-physical or energy advisory causing unsafe load or resource harm | `[ ]` | `[ ]` | `mcp_actuation_permitted=False`; independent `<5ms` Layer-0 hardware interlock; `T217` review | `[ ]` |
| Right to Good Administration & Effective Remedy (Arts. 41, 47) | Unexplainable or uncontestable decisions | `[ ]` | `[ ]` | Hash-chained audit trail (`DLTSwarmLedger`, `EpigeneticAuditEntry`); human appeal channel | `[ ]` |
| Workers' Rights & Collective Consultation (Arts. 27–31) | Undisclosed workplace monitoring or automated task pacing | `[ ]` | `[ ]` | Prohibited use of emotion recognition/scoring; worker representative notice (Art. 26(7)) | `[ ]` |

## 4. Societal, Economic & Ecological Effects
- **Aggregate societal/labor impact**: `[Assess impact on workforce roles, deskilling, and accountability]`
- **Energy & environmental footprint**: `[Record measured hardware power/energy vs modeled Sevo estimates]`
- **Single-point-of-failure / vendor lock-in assessment**: `[Verify self-hosted failover capability under T238/T239]`

## 5. Human Oversight, Governance & Remediation Plan
- **Designated Human Oversight Role(s) (Art. 14)**: `[Named role, competencies, authority to halt/override]`
- **Internal Complaint & Contestability Channel**: `[Process for affected persons to request human review]`
- **Serious Incident Escalation (Art. 73)**: `[Timeline, contact for national market surveillance authority, Art. 73 record workflow]`
- **Re-assessment Trigger**: `[Material change to model, domain, risk profile, or after any serious incident]`

## 6. Formal Deployer Sign-Off (External Human Approval Required)

- **Reviewer / DPO / Legal Counsel Name & Role**: `[Name, title]`
- **Decision**: `[ ] Approved for confined pilot` / `[ ] Revisions required` / `[ ] Rejected`
- **Date & Signature**: `[YYYY-MM-DD / Signature]`
