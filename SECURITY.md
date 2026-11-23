# Security & Cyber Resilience Policy (`q_speace`, T241)

This document defines the vulnerability disclosure policy, CVE triage process, patch SLAs,
support window, and supply-chain SBOM verification controls for `q_speace` in alignment with
**EU AI Act Article 15** and the **EU Cyber Resilience Act (CRA)**.

> **Scope Note**: `q_speace` is an experimental open-source research codebase. Formal regulatory
> notifications (e.g., ENISA/CSIRT reporting under CRA) and hardware-backed signing keys (HSM)
> remain the responsibility of any legal Provider/Deployer placing a derivative system on the market.

## 1. Supported Versions & Support Window

| Branch / Release | Support Status | Security Patch Window | Notes |
| --- | --- | --- | --- |
| `main` (current) | Active research maintenance | Rolling security patches on `main` | Experimental research profile; verified by CI (`pytest`, `mypy`, `ruff`, `black`, SBOM) |
| Archived commits / forks | Unsupported | None | Operators must track `main` or maintain an independent patched fork |

## 2. Vulnerability Disclosure Policy (VDP)

- **Private Reporting**: Report suspected security vulnerabilities, authentication bypasses,
  Layer-0/MCP boundary escapes, or dependency CVEs privately to the repository maintainers via
  GitHub Security Advisories (`Security -> Advisories -> New draft security advisory`) on
  `https://github.com/rigeneproject/q_speace`.
- **Do Not Disclose Secrets**: Never include live OAuth client secrets, GitHub PATs, private keys,
  or personal data (PII) in public issues, pull requests, or chat logs.
- **Coordinated Disclosure Window**: Maintainers target a **90-day coordinated disclosure** window
  (shortened if active exploitation is observed).
- **Safe Harbor**: Good-faith security research conducted exclusively against local self-hosted
  instances (`deploy/micro-node/`) without exfiltrating data, degrading third-party services, or
  violating access controls is welcomed.

## 3. CVE Triage & Patch SLAs

| Severity (CVSS v3.1 / Impact) | Initial Acknowledgment | Target Patch / Mitigation | Examples |
| --- | --- | --- | --- |
| **Critical (9.0–10.0)** | `<= 24 hours` | `<= 48 hours` | Remote actuation bypass, OAuth signature bypass, Track A/B isolation breach |
| **High (7.0–8.9)** | `<= 48 hours` | `<= 7 days` | Session hijacking, slow-plane `consensus_quorum` leak, critical dependency CVE |
| **Medium (4.0–6.9)** | `<= 5 business days` | `<= 30 days` | DoS/rate-limit bypass, non-critical schema/audit flaw |
| **Low (0.1–3.9)** | `<= 10 business days` | Next planned release | Hardening enhancements, informational findings |

## 4. Supply-Chain Integrity & Versioned SBOM

- Every CI run (`.github/workflows/ci.yml`) generates a versioned **CycloneDX 1.5 JSON SBOM**
  (`sbom-cyclonedx.json`) with package version metadata, deterministic URN serial number, and a
  detached **SHA-256 checksum** (`sbom-cyclonedx.json.sha256`).
- CI executes dependency vulnerability scanning (`pip-audit`) and uploads the CVE report alongside
  the SBOM artifact for audit review.
- Operators deploying a production or regulated derivative must re-sign release artifacts and SBOMs
  with an organization-controlled key (e.g., Sigstore / HSM).
