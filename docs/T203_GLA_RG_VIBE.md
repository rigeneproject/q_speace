# T203 — GLA signature in the RG cascade (VIBE / experimental — no code)

**Status**: experimental concept note (vibe mode). Do NOT implement.

## 1. Idea

SpikingBrain's Gated Linear Attention keeps a recurrent state of size
`head_dim × head_dim` per head — an O(1)-per-step memory summary of a
sequence. Q-SPEACE's `FractalQCACascade` couples scales by exchanging only
coarse-grained signatures `(coherence_phi, entropy S, sigma)` per level
(RG / Haken slaving principle). Proposal under discussion: enrich
`LevelSignature` with a GLA-style `d × d` summary matrix.

## 2. Why it is risky (why it stays vibe)

- The nested-cascade architecture exists because of *information
  compression* between levels: a full state of a 2^64 planet level is
  infeasible, so only order parameters cross boundaries.
- A `d × d` matrix per level is not a coarse-grained order parameter — it is
  a near-full state disguised as a signature. It would (a) raise memory and
  coupling complexity, (b) reduce interpretability, (c) silently replace the
  very mechanism that makes the cascade stable.
- No measurement exists yet of "how coarse" the matrix is relative to the
  full state.

## 3. If ever explored (intermediate phase only)

`LevelSignature` → 3 scalars **plus** a small fixed set of GLA-style
statistics (e.g. 8 aggregates: mean/var of the diagonal, off-diagonal mass,
spectral radius, ...) — never the full matrix — and only after defining an
information-compression metric comparing the summary to the full state.

## 4. Relation to T202

T202 deliberately does not include P4. The pseudo-spiking layer keeps the
cascade coupling surface exactly as it is: scalars only.
