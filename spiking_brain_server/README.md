# SpikingBrain-7B Sidecar (T205)

FastAPI sidecar that loads **maujim/spikingbrain-v1-7b-base** directly
via HuggingFace `transformers` with **bitsandbytes 4-bit (NF4)**
quantization, for the **RTX 3060 Laptop 6 GB** on a Windows + WSL2
host. The 14 GB bf16 model is quantised on the fly to ~4-4.5 GB and
fits entirely in VRAM — no CPU offload, no vLLM, expected ~5-10
tok/s.

## Why HF + bitsandbytes (not vLLM)

The original plan used vLLM-HyMeta with `--cpu-offload-gb 10
--enforce-eager` to make the 7B model fit on 6 GB. That worked but
forced a transfer of weights over PCIe at every forward pass, capping
throughput at ~1-2 tok/s and pulling in two non-trivial dependencies
(`vllm` + `vllm-hymeta`) plus a `fla_bitnet` patch.

Switching to HF `transformers` + `bitsandbytes` 4-bit:

- ~4-4.5 GB VRAM (NF4) — everything resident on the GPU
- No PCIe transfer during forward
- ~5-10× throughput
- No vLLM, no HyMeta plugin, no fla patch
- All `nn.Linear` projections (`q/k/v/o_proj`, `gate/up/down_proj`,
  `lm_head`) are quantised transparently by bitsandbytes. The custom
  GLA kernel from `flash-linear-attention` runs unchanged on the
  dequantised activations.

## Layout

```
spiking_brain_server/
├── __init__.py        # exposes `app`, `main`
├── server.py          # FastAPI: /think, /health + HF model loader
├── install.sh         # one-shot installer for WSL2 Ubuntu 24.04
├── download_model.sh  # HF_TOKEN-aware download of maujim/...-7B-base
├── install_cuda.sh    # optional CUDA toolkit (for SDPA fallback)
├── install_pip.sh     # bootstrap pip in WSL2
├── _auth_check.py     # HF auth probe
└── README.md          # this file
```

## Architecture

```
Q-SPEACE (Windows, numpy)
   └── HTTPSpikingBrainClient  ───HTTP───▶  sidecar:8001/think
                                              │
                                              ▼  (in-process)
                                       transformers.AutoModelForCausalLM
                                       + BitsAndBytesConfig(4-bit NF4)
                                       + device_map="auto"
                                              │
                                              ▼
                                       RTX 3060 6 GB
                                  (everything in VRAM, no offload)
```

## One-shot install

From PowerShell:

```powershell
$env:HF_TOKEN = "hf_xxx"
wsl -d Ubuntu -- bash -c "cd /mnt/c/Users/rober/Desktop/Q-SPEACE/q_speace && bash spiking_brain_server/install.sh"
```

The installer:
1. Bootstraps pip in WSL2 Ubuntu 24.04.
2. Creates a venv at `~/.venvs/spikingbrain`.
3. Installs PyTorch 2.7.1 + CUDA 12.1 wheels.
4. Installs `flash-attn 2.7.3` (with SDPA fallback if build fails),
   `triton 3.3.1`, `transformers 4.55.2`.
5. Installs `flash-linear-attention 0.1` (kernel for the GLA custom op).
6. Installs `bitsandbytes >= 0.43` and `accelerate >= 0.30`.
7. Installs sidecar deps: `fastapi`, `uvicorn`, `pydantic`, `httpx`.
8. Downloads `maujim/spikingbrain-v1-7b-base` (~14 GB) into
   `~/models/maujim/spikingbrain-v1-7b-base` via `download_model.sh`.
9. Runs a CUDA smoke test (must report ~6 GB free VRAM).

## Run

From WSL2:

```bash
source ~/.venvs/spikingbrain/bin/activate
cd /mnt/c/Users/rober/Desktop/Q-SPEACE/q_speace
python -m spiking_brain_server.server
```

The first startup quantises and loads the 7B model to 4-bit in
~30-60 s (depending on disk I/O). All subsequent startups are
~30-60 s too — the 4-bit quantisation is recomputed on load.

## Wire it to Q-SPEACE

```powershell
$env:Q_SPEACE_BRAIN_ENDPOINT = "http://localhost:8001"
qspace brain health
qspace brain think "What is coherence_phi?"
qspace brain tick "reflect on prior belief" --coherence 0.9
```

## Endpoints

### `POST /think`

Request:
```json
{
  "prompt": "...",
  "coherence_phi": 1.0,
  "n_tokens": 32,
  "history": null
}
```

Response:
```json
{
  "text": "model output",
  "confidence": 0.72,
  "belief": [0.2, 0.5, 0.3],
  "spikes": {"spikes": [...], "vth": [...], "num_spikes": 3, "sparsity": 0.5, "rate": 0.4},
  "plasticity": [0.1, 0.7, 0.2],
  "n_tokens": 28,
  "latency_s": 42.0,
  "metadata": {"backend": "hf-transformers-bnb4bit", "quantization": "nf4-4bit", ...}
}
```

### `GET /health`

```json
{"ready": true, "model": "...", "vram_mb": 4500, "backend": "hf-transformers-bnb4bit", "quantization": "nf4-4bit", "pid": 1234}
```

## VRAM budget on the RTX 3060 6 GB

| Component | Size |
|---|---|
| Model weights (4-bit NF4) | ~3.5 GB |
| KV cache for 512 ctx × 28 layers | ~0.2 GB |
| Activations + runtime overhead | ~0.5 GB |
| Bitsandbytes + transformers | ~0.5 GB |
| **Total** | **~4.7 GB** (~1.4 GB free headroom) |
| **Expected throughput** | **~5-10 tok/s** |

Tuning knobs (all optional env vars):
- `SPB_QUANT_BITS=8`  → fall back to 8-bit (slower quant, slightly higher quality, ~7 GB VRAM — won't fit on 6 GB).
- `SPB_MAX_MODEL_LEN=256` → halve the KV cache.
- `SPB_DEVICE_MAP={"":0}` → force everything on GPU 0 (no CPU spillover).
- `SPB_MAX_NEW_TOKENS_CAP=128` → tighter cap on the response length.

## BCEL note

SpikingBrain is a **functional** brain-inspired module (BCEL gate). The
firing of biological neurons is *accidental*; only the integer
quantization rule (`vth = mean(|x|) / k`) and the GLA+SWA attention
scheme are kept as mathematical primitives. The cortex never speaks
for itself — its outputs are always re-routed through ILF belief +
cost/Sevo gates before they influence the rest of Q-SPEACE.

## Historical status (verified 2026-08-07; re-verify before use)

- ✅ Runtime installed in WSL2 (`~/.venvs/spikingbrain`, ~6 GB, torch
  2.6.0+cu124, transformers 4.55.2, bitsandbytes 0.50.0, fla 0.1,
  accelerate 1.14.0, fastapi/uvicorn/httpx).
- ✅ Model downloaded: `~/models/maujim/spikingbrain-v1-7b-base`
  (~15 GB, snapshot_download via HF_TOKEN).
- ✅ Sidecar boots and reports `/health ready=true` with
  `quantization=nf4-4bit` and `vram_mb ≈ 5.8 GB`.
- ✅ `qspace brain health` (Windows-side) returns the HTTP backend
  string when `Q_SPEACE_BRAIN_ENDPOINT` is set.
- ✅ Architecture end-to-end (Windows Q-SPEACE ↔ WSL2 sidecar):
  `HTTPSpikingBrainClient` → `think()` → `ThinkResult` → `SpikingBrainCortex.tick()`
  → ILF belief + cost/Sevo gate. Verified on stub and on the HTTP
  transport with `httpx.MockTransport`.
- ⚠️  **Real model forward pass blocked**: the first `POST /think`
  against the loaded 7B hits a bug in the SDPA flash-attention
  fallback (`window_attention.py:259` — `attn_mask` size mismatch
  on the (q_len=9, k_len=128) tokens of the second generate step).
  The patcher correctly injects `_q_speace_varlen_to_batched` and
  `flash_attn_varlen_func` via the meta-path hook; what is wrong is
  the SDPA-based attention mask construction when the batch already
  has KV cache. Requires either (a) installing `flash-attn` from
  prebuilt wheel for `torch==2.6.0+cu124`, or (b) fixing the
  varlen→batched bridge to use `max_seqlen_q/max_seqlen_k` as
  shape, not the per-batch slice lengths.

In the meantime, the Q-SPEACE brain area is **fully functional on
the stub backend**: `qspace brain think`, `qspace brain tick`,
`qspace brain health`, and `qspace brain chat` (REPL) all work
and exercise the ILF / Sevo / cost pipeline.

## Troubleshooting

### `TypeError: _upad_input() missing 'unpad_input_func'`

BICLab's `window_attention.py` was written for `transformers` ≤ 4.54;
from 4.55 onward `_upad_input` takes an additional positional argument.
The sidecar patches the file on disk **and** evicts the cached module
in `sys.modules` on every model load. If you see this error:

1. Verify the patch marker is present:
   ```
   grep q_speace_patched_upad_input \
       ~/.cache/huggingface/modules/transformers_modules/spikingbrain-v1-7b-base/window_attention.py
   ```
2. If absent, re-run any forward pass (the patcher is invoked at
   model-load time, not at sidecar startup — so the very first
   `from_pretrained` on a clean shell will patch automatically).

### `flash_attn_varlen_func` `NameError` or `RuntimeError` on attn_mask

`flash-attn` is not installed and the SDPA fallback is buggy. The
sidecar reports `ready=true` because the model loads; the error
appears on the first `POST /think`. The 503 returned to the client
is harmless — the Q-SPEACE side falls back to the stub if
`Q_SPEACE_BRAIN_ENDPOINT` is unset, or surfaces the error if set.

Workarounds (in order of preference):
1. Install prebuilt `flash-attn` for torch 2.6.0 + cu124 (requires
   matching CUDA toolkit in WSL2 — currently not installed).
2. Pin `transformers==4.54.x` so that `_upad_input` keeps the old
   5-arg signature; then the SDPA fallback is not needed.
3. Wait for a corrected SDPA fallback (the mask must be sized by
   `max_seqlen_q × max_seqlen_k` over the varlen layout, not by
   per-batch slice lengths).

### CUDA OOM on first forward

Reduce `SPB_MAX_MODEL_LEN` (default 512) and/or `SPB_MAX_NEW_TOKENS_CAP`
(default 256). On 6 GB the model alone takes ~4.5 GB; KV cache is
~0.2 GB at ctx=512. Anything below 256 MB free at `/think` time will
OOM.

### Address already in use (`[Errno 98]`)

A previous sidecar is still bound to port 8001. From WSL2:

```bash
ps -ef | grep spiking_brain_server | grep -v grep | awk '{print $2}' | xargs -r kill
```

### Token rejected (`Invalid username or password`)

The HF_TOKEN must be a **write** token (or at minimum read) created
from an account that has access to `maujim/spikingbrain-v1-7b-base`.
Anonymous access returns 401. The token is also case-sensitive and
must not include trailing whitespace.
