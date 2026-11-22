# T235 — Sidecar Path Portability, Controlled-Rotation Unitarity Fix, Core Coverage & Singularity CLI

**Status:** agentic (production technical-debt remediation)  
**Date:** 2026-11-22  
**Dependencies:** `AGENTS.md`, `T230_TECHNICAL_DEBT_AND_BUGFIX_PLAN_SPEC.md`,
`T234_SINGULARITY_PHASE_TRANSITION_AND_EPIGENETIC_FRAMEWORK_SPEC.md`.  
**Non-goals:** No weakening of no-consciousness / no-communication / real-backend gates, no
physical actuation, no credentials stored on disk.

---

## 1. Remediations & Additions

1. **Critical Linear-Algebra Bugfix (`q_speace/quantum/quantum_gates.py`)**:
   - `QuantumGates._controlled_rotation()` previously omitted the diagonal element
     `mat[idx, idx] = base[t_bit, t_bit]` when `c_bit == 1`, making `CRX`, `CRY`, and `CRZ`
     non-unitary (and annihilating `|10>`/`|11>` under `CRZ`).
   - Restored exact unitarity ($U^\dagger U = I$) across all controlled rotations and added
     explicit unitarity regression tests.
2. **WSL2 / Sidecar Script Portability (`spiking_brain_server/`)**:
   - Replaced all hardcoded personal paths (`/home/roby/...`, `/mnt/c/Users/rober/...`) across
     10 helper scripts with environment variables (`Q_SPEACE_REPO_ROOT`,
     `Q_SPEACE_SPB_MODEL_PATH`, `Q_SPEACE_INSTRUCT_MODEL_PATH`, `Q_SPEACE_SPB_VENV`, `HF_HOME`)
     and portable `Path.home()` / `Path(__file__).resolve().parents[1]` defaults.
3. **CLI Integration (`q_speace/cli.py`)**:
   - Added `qspace singularity manifest [--section ...]`, `qspace singularity drills`
     (exits `3` if any drill fails or `rollback_pass_rate < 1.0`), and
     `qspace singularity assess --telemetry <path>`.
4. **Core Module Coverage Hardening (`tests/test_t235_debt_and_coverage.py`)**:
   - Added deterministic unit/mock tests for `quantum_gates.py`, `qiskit_backend.py`,
     `entanglement_registry.py`, `aacm/pr_helper.py`, `spiking_brain/client.py`, and
     `qspace singularity` CLI commands.
5. **Sanitized Live MCP Verification Evidence**:
   - Recorded `artifacts/T234_mcp_live_verification_20261122.json` capturing the live 8/8 PASS
     verification against `https://q-speace-mcp.onrender.com/mcp` (built from `main` `6ef2e9a3`),
     with zero tokens or secrets.
