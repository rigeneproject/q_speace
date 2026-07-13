# Q-SPEACE — Agentic Engineering Guide

Q-SPEACE is the quantum layer for the SPEACE organism. Development follows
the same two-mode discipline as `cellular_speace/AGENTS.md`.

## 1. Modes

### Vibe mode (exploration)
- New analogies / concepts under `docs/`.
- Clearly mark output as experimental.
- Do not touch safety-critical paths.

### Agentic mode (production)
Required for changes to `q_speace/` source, tests, CLI, genome.
1. Write/update a spec (`docs/Txxx_*_SPEC.md`).
2. Pass the BCEL gate: classify each bio/quantum concept as accidental
   (remove in silicon) or functional (keep as a mathematical rule). Record
   in `q_speace/bcel/catalog.py`.
3. Add/extend tests under `tests/`.
4. Run `pytest`, `ruff`, `black`, `mypy` on touched files.

## 2. Invariants (must never be weakened)
- No claim of quantum consciousness.
- Entanglement only as computational resource (no-communication theorem).
- Every feature needs tests and passes the BCEL filter.
- No real quantum backend without `QuantumGeneSet.noise_model` configured
  and an energy/Sevo gate.

## 3. Quality gates
- [ ] `pytest` passes.
- [ ] `python -m py_compile` on touched files.
- [ ] `ruff check q_speace` clean.
- [ ] New behavior covered by a test.

## 4. Prohibited
- Weakening the no-consciousness / no-communication invariants.
- Introducing dependencies without updating `pyproject.toml`.
- Deleting tests to raise coverage.
