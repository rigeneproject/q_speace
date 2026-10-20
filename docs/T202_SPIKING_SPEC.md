# T202 — Spiking Layer Spec (P1/P2/P3/P5 + SpikePlasticity)

**Status**: agentic (production)
**Scope**: pseudo-spiking integration into the quantum layer, adapted from
the BICLab/SpikingBrain-7B dynamic spike encoding (arXiv:2509.05276, TMLR 2026)
**Author**: Q-SPEACE (integration review approved)

> **Epistemic note (2026-08-12).** T202 implementa la primitiva
> `dynamic_spikes(x)` (`vth = mean(|x|)/k`) identica a
> `W8ASpike/quant_linear.py` di SpikingBrain-7B, **ma non importa il
> modello**. La regola di spike è una primitiva matematica standalone
> (numpy), non vincolata a un particolare checkpoint. Le misurazioni
> T202 (sparsity, rate, energia per spike) si applicano
> uniformemente a stub, Qwen 3B e SpB-7B.

## 1. Purpose

Incorporate, selectively, the strongest computational principles of
SpikingBrain into Q-SPEACE — *dynamic spike sparsity*, *spike encoding of
activity*, and *event-driven energy accounting* — without importing the
LLM/attention stack (GLA, MoE, vLLM, MetaX) and without weakening any
invariant. The integration is **pseudo-spiking at tensor level**, matching
both SpikingBrain's own W8ASpike choice and Q-SPEACE's numpy-only rule.

## 2. What is borrowed from SpikingBrain (and what is not)

| SpikingBrain mechanism | Adopted | How |
|---|---|---|
| `dynamic_spikes`: `vth = mean(|x|)/k`, `round(x/vth)` | yes | `q_speace/spiking/encoder.py` (numpy) |
| Sparse integer spike representation | yes | input to amplitude encoding and QCA rotations |
| Event-driven sparsity → energy | yes | `QuantumOperation.num_spikes`, `W_PER_SPIKE` |
| GLA / SWA / MoE / vLLM / VLM | no | out of scope (LLM serving layer) |
| True spiking / neuromorphic HW | no | pseudo-spiking only (per repo's own scope) |

## 3. BCEL gate (recorded in `q_speace/bcel/catalog.py`)

| Concept | Class | Digital rule |
|---|---|---|
| Spike firing (biological AP) | **accidental** | removed; only `round(x/vth)` survives |
| Spike-timing correlation / synchrony | **functional** | classical **fidelity-proxy** feeding the registry (software binding; explicitly NOT quantum state fidelity, no-communication theorem preserved) |
| Event-driven neural energy | **functional** | `E_spike = N_spike * W_PER_SPIKE` in the cost model |
| Frequency-based plasticity (STDP-like) | **functional** | EMA decay rule `exp(-λΔt)·rate`; no STDP/backprop |
| ILF-modulated spiking threshold | **functional** | `vth = mean(|x|)/(k·(1+β·coherence_phi))` |

## 4. Architecture

```
activity (numpy) ─► dynamic_spikes ─► SpikeEncodingResult
                                       ├─ spikes (int array)  ─► amplitude encoding ─► QuantumState
                                       ├─ spikes               ─► RY(π·rate)        ─► FractalQCA weights
                                       └─ num_spikes           ─► QuantumOperation(num_spikes) ─► energy + Sevo gate
spike history ─► SpikePlasticity (EMA) ─► coefficients ─► fidelity scaling (P3) / energy modulation
activity matrix ─► spike_correlation ─► entangle_by_correlation ─► EntanglementRegistry (functional layer)
spike counts ─► spike_entropy_gradient ─► CosmicVirusOptimizer (P5, closes EDD-CVT loop)
```

The quantum kernel never sees the neural model: it only receives sparse
integer representations (separation of levels).

## 5. Formulas

- Threshold: `vth = mean(|x|, axis=-1, keepdims) / k`, clamped to `[1e-5, 1e4]`;
  spikes `= round(x / vth)`. ILF modulation: `vth /= (1 + β·Φ)`.
- Sparsity: `1 − (num_nonzero / size)`. Spike count: `num_nonzero`.
- Energy (P1): `E = E_base + N_spike · W_PER_SPIKE` with
  `W_PER_SPIKE = 0.001` W (500 active spikes ≈ 1 qubit-second).
- Plasticity: `ema_i = decay·ema_i + (1−decay)·rate_i`, coefficients
  normalized to [0,1]; static rule `plasticity = exp(−λ·Δt)·rate`.
- Correlation (P3): Pearson over spike trains (rows = neurons); NaN rows →
  0. `fidelity = corr` (or `corr · mean(plasticity_a, plasticity_b)` when a
  `SpikePlasticity` is provided). Label `"spike-correlation"`; fidelity is a
  **classical proxy**, never quantum state fidelity.
- Entropy gradient (P5): `dH/ds_k = −(ln p_k + H)/Z`, `p = |s|/Z`; zero for
  uniform spike distributions (entropy maximum).

## 6. Modules

- `q_speace/spiking/encoder.py` — `dynamic_spikes`, `SpikeEncodingResult`,
  `spike_count`, `sparsity`, `spike_rate`.
- `q_speace/spiking/linear.py` — `SpikeEncodedLinear` (numpy W8ASpike-style
  pseudo-quantized linear: group-wise int8 weights + spike activations).
- `q_speace/spiking/plasticity.py` — `SpikePlasticity` (EMA coefficients).
- `q_speace/spiking/correlation.py` — `spike_correlation`,
  `entangle_by_correlation`, `spike_entropy_gradient`.
- `q_speace/spiking/bridge.py` — `SpikeQuantumBridge` (spikes → `QuantumState`
  via amplitude encoding; spikes → RY angles for QCA).
- `q_speace/metabolism/cognitive_cost_model.py` — P1 (additive, backward
  compatible: `num_spikes=0` default).

## 7. Invariants (verified)

- No quantum-consciousness claims; no communication via entanglement.
- `entangle_by_correlation` writes only to the registry (software binding);
  it never fabricates a physical entangled state.
- No new hard dependencies: all spike math is numpy. Torch/transformers/fla
  are NOT required (a torch extra is explicitly rejected for now).
- No real quantum backend involved.

## 8. Tests (`tests/test_spiking.py`)

Sparsity of `dynamic_spikes` on Gaussian input; zero-input clamp; ILF
threshold modulation; spike energy cost (dense > sparse); `SpikeEncodedLinear`
shape + quantization bound; `SpikePlasticity` EMA range; correlation matrix
(no NaN, diag 1); `entangle_by_correlation` threshold + plasticity scaling;
bridge → state normalization / power-of-2; bridge → RY angles in [0, π];
entropy gradient (≈0 uniform, >0 peaked) and a `CosmicVirusOptimizer` loop.

## 9. Quality gates

- [ ] `pytest` passes
- [ ] `python -m py_compile` on touched files
- [ ] `ruff check q_speace` clean
- [ ] `black --check` / `mypy` on touched files

## 10. Out of scope / future

- **P4 — GLA signature in RG cascade**: NOT implemented here. Only the
  coarse-grained scalars (φ, S, σ) cross level boundaries (RG/Haken slaving).
  A d×d matrix per level would be a near-full state disguised as a signature.
  Kept as experimental vibe doc `docs/T203_GLA_RG_VIBE.md`.
- Orchestrator wiring of spike energy: optional later T-ticket (the cost
  model API is ready; `QuantumOrchestrator` is untouched).
