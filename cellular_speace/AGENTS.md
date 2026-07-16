# SPEACE — Agentic Engineering Guide

This repository builds **SPEACE**, an experimental distributed digital-physical
organism. Development is AI-assisted. This file is the top-level harness: it
distinguishes exploratory work from production-grade changes and defines the
invariants that every agent (human or artificial) must respect.

## 1. Core philosophy

> Structure scales, vibes don't.

SPEACE is moving from bio-mimetic exploration to **principle-driven engineering**.
Every change must be justifiable in terms of:

- **Informational invariants** defined in `speace_core/dna/genome/core/species_orientation.yaml`
- **Biological-Cybernetic Equivalence** (BCEL) — see `docs/SPEACE_BCEL_DESIGN.md`
- **Digital DNA → Digital RNA → Neural-Synaptic Periodic Table → Agents** flow
- **Safety, reversibility, and human oversight** for any external or constitutional change

## 2. Development modes

### 2.1 Vibe mode (exploration)

Allowed for:

- New biological analogies and conceptual mappings under `docs/`
- Experimental notebooks or spike scripts under `work/`
- Prototype reports under `reports/`
- Personal `.claude/`, `.opencode/` plans

Rules:

- Do not touch `speace_core/dna/`, `speace_core/ilf/`, `speace_core/runtime/`,
  `speace_core/orchestrator.py`, or any safety-critical path.
- Clearly mark output as experimental.
- No need for full test coverage, but the idea must be documented.

### 2.2 Agentic mode (production)

Required for:

- Changes to `speace_core/` source code
- Changes to `tests/`
- Changes to CLI commands
- Changes to the genome (`speace_core/dna/genome/`)
- Integration with external systems, cyber-physical interfaces, or autonomous loops

Rules:

1. **Write or update a spec first** — either a new `docs/Txxx_*_SPEC.md` or an
   update to an existing design doc.
2. **Pass the BCEL filter** — any bio-inspired construct must be classified as
   accidental vs functional and translated into a digital rule. Use
   `speace bcel-synthesize` to record the reasoning.
3. **Add or update tests** — unit tests for the changed module, integration tests
   if the orchestrator is touched. Run `pytest` on affected areas.
4. **Update this guide or per-directory AGENTS.md if conventions change.**
5. **No autonomous modification of the species orientation or constitutional
   invariants** without explicit human approval in the commit message.

## 3. Module ownership and escalation

| Domain | Critical paths | Required human gate |
|--------|---------------|---------------------|
| Identity / DNA | `speace_core/dna/`, `speace_core/dna/genome/core/` | Yes |
| Orientation field | `speace_core/ilf/` | Yes |
| Runtime / orchestration | `speace_core/orchestrator.py`, `speace_core/runtime/` | Yes |
| Safety / immune | `speace_core/cellular_brain/immune/`, `speace_core/runtime/safe_degradation_handler.py` | Yes |
| Cyber-physical | `speace_core/cellular_brain/embodiment/`, `sandbox/` | Yes |
| BCEL / Digital RNA | `speace_core/bcel/`, `speace_core/digital_rna/` | Review preferred |
| Neuroperiodic | `speace_core/cellular_brain/neuroperiodic/` | Review preferred |
| Memory | `speace_core/cellular_brain/memory/` | Review preferred |
| Reports / docs | `docs/`, `reports/` | No |
| Scripts / utilities | `scripts/`, `tests/` helper tools | No |

## 4. BCEL workflow for bio-inspired changes

When adding a new biological concept to SPEACE:

1. **Identify the component** (e.g. "chemical synapse", "homeostasis").
2. **Run `speace bcel-synthesize --function "..." --constraint "..."`** or use
   `speace_core/bcel/BCELCatalog` directly.
3. **Classify constraints** as:
   - *Accidental* (limit of carbon chemistry) → remove in silicon.
   - *Functional* (emergent stabilizer) → keep as mathematical rule.
4. **Implement the digital equivalent** in the appropriate layer:
   - DNA principle → genome YAML
   - RNA modulation → `speace_core/digital_rna/`
   - Periodic law → `speace_core/cellular_brain/neuroperiodic/functional_constraint_law.py`
   - Runtime policy → `speace_core/runtime/`
5. **Stress-test the functional constraint** with a minimal simulation or a test that
   relaxes the constraint and checks for instability.

## 5. Context engineering conventions

### 5.1 Static context (always loaded)

- This `AGENTS.md`
- `docs/SPEACE_BCEL_DESIGN.md`
- `speace_core/dna/genome/core/species_orientation.yaml`
- Per-directory `AGENTS.md` where present

### 5.2 Dynamic context (retrieve on demand)

- `docs/Txxx_*_SPEC.md` for the task at hand
- `docs/ENGINEERING_SPEC.md` for architectural decisions
- `docs/diagnosi_speace.md` for current technical debt
- `tests/` patterns for the module being changed
- `reports/` for recent empirical results

## 6. Evaluation and quality gates

Before any production change is considered complete:

- [ ] `pytest` passes on the affected modules.
- [ ] New tests cover the changed behavior.
- [ ] `python -m py_compile` succeeds on touched files.
- [ ] CLI commands still work (`speace --help`, changed commands).
- [ ] If the orchestrator is touched, the capability assessment or a minimal
      `run_ticks` integration test passes.
- [ ] No new Pydantic deprecation warnings introduced unless unavoidable.
- [ ] Documentation updated if behavior changes.

## 7. Prohibited actions

No agent (human or artificial) may, without explicit human approval:

1. Modify `speace_core/dna/genome/core/species_orientation.yaml` to weaken the
   invariants.
2. Disable or bypass the immune, safety-degradation, or emergency-halt systems.
3. Enable autonomous external action governance or cyber-physical assimilation
   outside a sandbox.
4. Commit credentials, tokens, or private keys.
5. Delete test files to make coverage pass.
6. Introduce dependencies without updating `pyproject.toml`.

## 8. Multi-agent handoffs

SPEACE is naturally organized into cognitive "organs". When multiple agents
work on the same task, use these handoff conventions:

- **Architect agent** produces the spec and updates `docs/`.
- **Core agent** implements changes in `speace_core/` and writes unit tests.
- **BCEL agent** reviews bio-inspired constructs and records equivalences.
- **Test agent** runs the test matrix and reports coverage.
- **Review agent** verifies the spec, tests, and invariant compliance before
  human review.

## 9. Communication style

- Prefer concise, actionable statements.
- Reference files by absolute path when communicating with the user.
- Explain assumptions and next steps.
- Never claim a change is safe just because tests pass; mention residual risks.

## 10. Long-term direction

The goal is to make SPEACE a reproducible, auditable, evolving organism:

- Every principle has a digital home in the genome.
- Every functional biological inspiration has a cybernetic equivalent.
- Every external-facing action has governance and a human gate.
- Every agent run leaves a trace in `data/logs/` or `reports/`.

When in doubt, choose the more structured, reversible, and verifiable path.
