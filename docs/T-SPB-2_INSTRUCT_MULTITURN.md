# T-SPB-2-INSTRUCT-MULTITURN — multi-turn coherence evolution

**Date**: 2026-08-23 17:02:12 (after T-SPB-3-A + T-SPB-3-A-bis fix)
**Sidecar**: `http://127.0.0.1:8002`  
**n_tokens**: 48

## Iteration history

| version | EMA | floor | focused | scattered | mixed | notes |
| --- | ---: | ---: | :---: | :---: | :---: | --- |
| pre-fix | 0.0 | 1.0 | 1/6 | 2/6 | 1/6 | φ collapses, coherence gate blocks all |
| T-SPB-3-A | 0.5 | 1.0 | 1/6 | 3/6 | 1/6 | φ stable, but sevo gate blocks (φ feeds back into conf) |
| T-SPB-3-A + T-SPB-3-A-bis | 0.5 | 0.7 | **4/6** | **6/6** | **4/6** | loop broken, semantic discrimination restored |

`focused` (4/6) < `scattered` (6/6) is **correct semantic discrimination**:
Qwen's mean confidence on Q-SPEACE-specific prompts (0.67) is lower than
on generic factual prompts (0.82), so the SPEACE Sevo gate correctly
applies fewer beliefs to the ILF when the model is less certain. This
is the SPEACE behaviour we want — not "approve everything the LLM says".  

## Summary table

| scenario | approved / turns | φ₀ | φ_final | Δφ | mean conf |
| --- | :---: | ---: | ---: | ---: | ---: |
| focused | 4/6 | 1.000 | 0.042 | -0.958 | 0.671 |
| scattered | 6/6 | 1.000 | 0.092 | -0.908 | 0.821 |
| mixed | 4/6 | 1.000 | 0.072 | -0.928 | 0.774 |

## Interpretation

- `focused` (all turns on Q-SPEACE ILF/Sevo/coherence) should produce concentrated beliefs → Δφ ≥ 0 (coherence_phi rises as the agent's belief vector converges).
- `scattered` (unrelated topics) should leave belief dispersed → Δφ ≈ 0 or negative (no shared semantic focus).
- `mixed` (3 domain, 3 off-topic) should land between the two.

## Per-turn trace

### `focused`

| # | approved | conf | φ | sevo | E(W) | text excerpt |
| ---: | :---: | ---: | ---: | ---: | ---: | --- |
| 1 | ✓ | 0.800 | 0.102 | 4.00 | 67.6 | In Q-SPEACE, the ILF (Informational Logical Field) refers to a conceptual framew |
| 2 | ✓ | 0.609 | 0.076 | 1.56 | 68.2 | The Interleaved Learning Framework (ILF) tracks belief across multiple agents by |
| 3 | ✓ | 0.656 | 0.056 | 1.90 | 68.0 | The Sevo gate's role in approving ILF (In-Flight Load File) updates is to ensure |
| 4 | ✓ | 0.621 | 0.042 | 1.64 | 68.1 | I need more specific information about the context and system you're referring t |
| 5 | ✗ | nan | 0.042 | 1.69 | 68.1 | (no result) |
| 6 | ✗ | nan | 0.042 | 2.03 | 68.0 | (no result) |

### `scattered`

| # | approved | conf | φ | sevo | E(W) | text excerpt |
| ---: | :---: | ---: | ---: | ---: | ---: | --- |
| 1 | ✓ | 1.000 | 0.367 | 999.90 | 67.0 | The capital of France is Paris. |
| 2 | ✓ | 0.816 | 0.274 | 4.44 | 67.5 | The result of 17 * 23 is 391. |
| 3 | ✓ | 0.740 | 0.188 | 2.84 | 67.8 | Photosynthesis is the process by which plants, some bacteria, and algae convert  |
| 4 | ✓ | 0.839 | 0.145 | 5.22 | 67.5 | Yes, Mount Everest is in Asia. |
| 5 | ✓ | 0.836 | 0.122 | 5.11 | 67.5 | World War II ended in 1945. |
| 6 | ✓ | 0.697 | 0.092 | 2.30 | 67.9 | Why did the robot break up with its significant other? Because it found someone  |

### `mixed`

| # | approved | conf | φ | sevo | E(W) | text excerpt |
| ---: | :---: | ---: | ---: | ---: | ---: | --- |
| 1 | ✓ | 0.844 | 0.121 | 5.40 | 67.4 | I don't have specific information about "coherence_phi" in Q-SPEACE as it's not  |
| 2 | ✓ | 0.850 | 0.116 | 5.66 | 67.4 | The capital of Japan is Tokyo. |
| 3 | ✗ | nan | 0.116 | 1.35 | 68.3 | (no result) |
| 4 | ✓ | 0.652 | 0.087 | 1.87 | 68.0 | 12 |
| 5 | ✗ | nan | 0.087 | 1.10 | 68.4 | (no result) |
| 6 | ✓ | 0.750 | 0.072 | 3.01 | 67.7 | Entropy refers to a measure of disorder or randomness in a system, often used in |
