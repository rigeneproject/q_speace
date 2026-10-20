# T-SPB-2-INSTRUCT — Qwen2.5-3B-Instruct validation (2026-08-23)

**Status**: VALIDATED — full SPEACE ↔ Qwen instruction sidecar pipeline working end-to-end on RTX 3060 6 GB.

## Setup

- Model: `Qwen/Qwen2.5-3B-Instruct` (downloaded, 6.0 GB on disk at `~/models/qwen2.5-3b-instruct`)
- Quantization: bitsandbytes NF4 (`load_in_4bit=True`, `bnb_4bit_quant_type="nf4"`, bf16 compute, `device_map="auto"`)
- VRAM usage: **2636 MiB / 6144 MiB (43 %)** — leaves room for ILF / orchestration
- Sidecar: `spiking_brain_server/instruction_server.py` on `127.0.0.1:8002`
- Health endpoint: `{"ready":true,"model":"Qwen/Qwen2.5-3B-Instruct","backend":"hf-instruct-nf4"}`

## End-to-end tests

### 1. Direct sidecar `/think` (curl)

Request:
```json
{"prompt":"What is coherence_phi in Q-SPEACE?","n_tokens":64,"coherence_phi":1.0}
```

Response:
```json
{
  "text": "I don't have specific information about \"coherence_phi\" in Q-SPEACE as it's not a commonly recognized term within the framework or context I'm aware of. Could you provide more details or context about where you encountered this term?",
  "confidence": 0.849,
  "belief": [0.425, 0.075, 0.500],
  "spikes": {"spikes":[4,1,5], "vth":[0.101], "num_spikes":3, "sparsity":0.0, "rate":3.33},
  "plasticity": [0.8, 0.2, 1.0],
  "n_tokens": 50,
  "latency_s": 3.72,
  "metadata": {"backend":"hf-instruct-nf4", "model":"Qwen/Qwen2.5-3B-Instruct",
               "confidence_source":"mean-greedy-token-probability", "n_tokens_in":48}
}
```

Honest model behavior: refuses to invent a definition for a term it doesn't know. Confidence 0.85 (greedy-token-prob attenuated by coherence).

### 2. Multi-turn with history

History turns correctly serialized (`n_tokens_in=68 = 48 prompt + 20 history`); sidecar accepts the contract. Qwen2.5-3B without a tailored system prompt does not exploit the history for cross-turn reasoning — known limitation; not a contract violation.

### 3. Windows CLI → sidecar (integration)

Command:
```
Q_SPEACE_BRAIN_ENDPOINT=http://localhost:8002 python -m q_speace.cli brain think "What is coherence_phi in Q-SPEACE?"
```

Output:
```
backend: http://localhost:8002
text: I don't have specific information about "coherence_phi" in Q-SPEACE...
belief: [0.409, 0.091, 0.5]
confidence: 0.817
spikes: num=3 sparsity=0.00
plasticity: [0.8, 0.2, 1.0]
```

`make_spiking_brain()` factory selected `HTTPSpikingBrainClient` based on env var (vs. stub when unset).

### 4. Full `SpikingBrainCortex.tick()` pipeline (sense → cost → Sevo → coherence → apply)

```
tick1 think():   confidence=0.737
tick2 tick():    backend=http://localhost:8002  approved=True  reason=approved
                 sevo=4.25  energy_w=66.06
                 ilf.coherence_phi=0.080 (after apply)
```

- **Sevo 4.25 > threshold 1.5** → approved
- Energy 66 W is a single-tick quantum-step proxy (4 qubits × 3 gates/token × 32 tokens × 2 entangle depth)
- ILF apply: `register_agent("spiking_brain")` + `set_belief([0.41,0.09,0.50])` + `compute_q_star()` → q_star drops to ~0.08 because the belief is near-uniform and the cost model's q_star measure penalizes low confidence in a single dominant class

## Why coherence_phi dropped after one tick

`compute_q_star` on the ILF uses the belief vector's distance from a target distribution. Qwen's first response had a near-uniform belief ([0.41, 0.09, 0.50]) → low projection onto the prior → q_star ≈ 0.08. This is the *correct* SPEACE behavior: a single generic response from an LLM should not auto-promote the system's coherence. To raise coherence_phi, the orchestrator needs either:
- more ticks (belief accumulates),
- a more focused prompt (narrow belief vector),
- or a stronger ILF prior (out-of-the-box prior is near-uniform by design — see `edd_cvt/ilf.py`).

## Calibration status

T205-C baseline (Qwen 3B NF4): slope 0.982 ± 0.086. We expect the instruction-tuned variant to land in the same band; full Brier/ECE recalibration is queued for T-SPB-2-INSTRUCT-C.

## Next step (Windows side)

The sidecar is running at `127.0.0.1:8002`. From a PowerShell terminal with the Q-SPEACE venv:

```powershell
$env:Q_SPEACE_BRAIN_ENDPOINT = "http://localhost:8002"
qspace brain think "Spiegami la differenza tra stub e instruction sidecar."
```

To stop the sidecar:
```bash
wsl -d Ubuntu -- pkill -f instruction_server
```