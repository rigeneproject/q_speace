# Quality Management System (QMS) Deployer Readiness Checklist — EU AI Act Article 17 / ISO 42001

- **Template ID**: `T241-QMS-CHECKLIST-v1`
- **Applicable Standards**: Regulation (EU) 2024/1689 Art. 17, ISO/IEC 42001:2023 (AIMS)
- **Boundary Notice**: **A software repository cannot certify an organization's QMS.** This checklist maps organizational procedures that a legal Provider/Deployer must establish and audit externally before regulated operation (`qms_externally_certified = False` in code).

---

## 1. Operational Procedures (SOPs)
- [ ] Written Standard Operating Procedures (SOPs) cover installation (`deploy/micro-node/`), backup/retention of persistent SQLite audit logs (`>= 6 months` for High-Risk Art. 12/26), key rotation, and emergency stop (`KillSwitch` / Layer-0).
- [ ] Documented runbook defines remote-to-local failover (`MicroNodeFailoverClient`) and post-blackout `DLTSwarmLedger` reconciliation verification.

## 2. Supplier & Third-Party Vendor Management
- [ ] Inventory of all third-party providers (cloud hosts, OAuth issuers, external LLM/GPAI APIs, hardware vendors) with signed Data Processing Agreements (DPAs) and SLAs.
- [ ] Model selection adheres strictly to the **Model Governance Registry (`T241`)** — unapproved, deprecated, or uncalibrated models are blocked.
- [ ] Supply-chain SBOM (`sbom-cyclonedx.json`) and CVE scan artifacts reviewed before every release promotion (`SECURITY.md`).

## 3. Change Control & Configuration Management
- [ ] Every modification to configuration, models, or code passes version-controlled peer review (proposer != reviewer, zero self-approval), automated CI gates (`pytest`, `mypy`, `ruff`, `black`), and `qspace micro-node compliance-pack`.
- [ ] Material changes trigger re-execution of `T234`/`T236` drills, `T237`/`T238` benchmarks, and FRIA/DPIA review (`T217`).

## 4. Staff Training & Competency (Art. 4 AI Literacy & Art. 14 Oversight)
- [ ] Human operators and reviewers are trained on automation bias, advisory-only boundaries, Layer-0 independence, and BCEL terminology limits (no consciousness/autonomy claims).
- [ ] Oversight personnel hold documented organizational authority to pause, roll back, or decommission a node without retaliation.

## 5. Escalation, Post-Market Monitoring & Incident Response (Arts. 72–73)
- [ ] Defined escalation tiers (L1 Operator -> L2 Security/Safety Lead -> L3 Legal/DPO -> National Supervisory Authority).
- [ ] Serious incidents are captured via `build_serious_incident_report()` (`eu_ai_act_art73_incident.v1`), verified with `verify_incident_record_integrity()`, and formally submitted by authorized human personnel within statutory deadlines.
- [ ] Independent third-party audit (ISO/IEC 42001 / Notified Body where required under Arts. 43–49) scheduled prior to any High-Risk market placement.
