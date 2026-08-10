#!/usr/bin/env bash
# ----------------------------------------------------------------------
# SpikingBrain-7B installation for WSL2 Ubuntu 24.04 + RTX 3060 Laptop 6 GB.
#
# Stack: HuggingFace transformers + bitsandbytes 4-bit (NF4).
# NO vLLM, NO vllm-hymeta, NO fla patch. The 7B model is quantised
# 4-bit on the fly and fits in ~4-4.5 GB VRAM (vs the original 14 GB
# in bf16), so everything stays resident on the RTX 3060 6 GB.
#
# Run this script from PowerShell:
#
#   $env:HF_TOKEN = "hf_xxx"
#   wsl -d Ubuntu -- bash -c "cd /mnt/c/Users/rober/Desktop/Q-SPEACE/q_speace && bash spiking_brain_server/install.sh"
#
# What it does:
#   1. Installs pip + venv into WSL2 Ubuntu 24.04
#   2. Creates venv at ~/.venvs/spikingbrain
#   3. Installs torch 2.7.1 + CUDA 12.1 wheels (compatible with the
#      CUDA 12.4 driver that WSL2 passes through from the host)
#   4. Installs flash-attn 2.7.3 (with SDPA fallback if build fails),
#      triton 3.3.1, transformers 4.55.2 (pinned per SpikingBrain README)
#   5. Installs flash-linear-attention 0.1 (kernel for the GLA custom op)
#   6. Installs bitsandbytes + accelerate (4-bit NF4 + device_map)
#   7. Installs the sidecar deps (fastapi, uvicorn, pydantic, httpx)
#   8. Downloads maujim/spikingbrain-v1-7b-base (~14 GB) via HF_TOKEN
#      into ~/models/maujim/spikingbrain-v1-7b-base
#   9. Runs a CUDA smoke test (asserts VRAM < 8 GB)
#
# After it finishes, launch the sidecar from WSL2:
#
#     source ~/.venvs/spikingbrain/bin/activate
#     cd /mnt/c/Users/rober/Desktop/Q-SPEACE/q_speace
#     python -m spiking_brain_server.server
#
# Then on Windows PowerShell:
#
#     $env:Q_SPEACE_BRAIN_ENDPOINT = "http://localhost:8001"
#     qspace brain health
#     qspace brain think "What is coherence_phi?"
# ----------------------------------------------------------------------
set -euo pipefail

VENV="${HOME}/.venvs/spikingbrain"
MODEL_REPO="maujim/spikingbrain-v1-7b-base"
MODEL_DIR="${HOME}/models/maujim/spikingbrain-v1-7b-base"

echo "==> SpikingBrain-7B installer (T205, HF + bitsandbytes 4-bit)"
echo "    target GPU : RTX 3060 Laptop 6 GB (CUDA 12.4 passthrough)"
echo "    venv       : ${VENV}"
echo "    model repo : ${MODEL_REPO}"
echo "    model path : ${MODEL_DIR}"

# 0. Sanity: HF_TOKEN must be set in the calling shell.
if [[ -z "${HF_TOKEN:-}" ]]; then
    echo "ERROR: HF_TOKEN is not set. Export it before running this script:"
    echo "       export HF_TOKEN=hf_..."
    exit 1
fi

# 1. Make sure pip itself is available in WSL2.
if ! command -v pip3 >/dev/null 2>&1 && ! python3 -m pip --version >/dev/null 2>&1; then
    echo "==> Bootstrapping pip via get-pip.py (no sudo required)"
    curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
    python3 /tmp/get-pip.py --user
fi

# 2. Python venv (re-using the system Python 3.12 from Ubuntu 24.04).
#    On Ubuntu the ``python3-venv`` apt package is needed for
#    ``ensurepip``; if it isn't installed and sudo is unavailable, we
#    create the venv with ``--without-pip`` and bootstrap pip via
#    ``get-pip.py``.
if [[ ! -d "${VENV}" ]]; then
    echo "==> Creating venv at ${VENV}"
    if python3 -m venv "${VENV}" 2>/dev/null; then
        :
    else
        echo "    venv module missing ensurepip; falling back to --without-pip + get-pip.py"
        python3 -m venv --without-pip "${VENV}"
        curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
        "${VENV}/bin/python3" /tmp/get-pip.py
    fi
fi
# shellcheck disable=SC1091
source "${VENV}/bin/activate"
python -V

pip install --upgrade pip wheel setuptools "setuptools-scm>=8"

# 3. HuggingFace hub for downloads.
pip install "huggingface_hub[cli]>=0.24"

# 4. PyTorch with CUDA 12.4 wheels (matches the WSL2 driver 552.12).
#    NOTE: torch 2.7.1 is only published on cu121/cu118; for cu124 the
#    latest is 2.6.0. ABI-compatible with the 12.4 driver.
echo "==> Installing torch 2.6.0 + cu124 (latest cu124 wheel available)"
pip install --index-url https://download.pytorch.org/whl/cu124 \
    "torch==2.6.0" "torchvision==0.21.0" "torchaudio==2.6.0"

# 5. Flash-attn (must be built against the same torch). 2.7.x is for
#    torch 2.7; for torch 2.6 use 2.6.3. SDPA is a fine fallback for
#    the GLA / SWA ops if the build fails.
echo "==> Installing flash-attn 2.6.3 (this can take a few minutes)"
pip install "flash-attn==2.6.3" --no-build-isolation || {
    echo "WARNING: flash-attn build failed; the model will still load with"
    echo "         a slower PyTorch SDPA fallback. Continuing."
}

# 6. triton + transformers (pinned per SpikingBrain-7B README).
#    transformers 4.54.x is the latest version that combines:
#      - compatibility with fla 0.1 and the SWA/varlen ops in
#        modeling_gla_swa.py
#      - lower latency than 4.55.x on RTX 3060 (2-8x faster on greedy)
#    4.55.x works but kv-cache sliding window has a known fla
#    compatibility issue (pérdida/adultes degeneration). See
#    docs/T205_status.md for benchmark numbers.
pip install "triton==3.2.0" "transformers==4.54.1" "scipy" "pyyaml" "decorator"

# 7. flash-linear-attention (fla) — required by the GatedLinearAttention
#    custom op in modeling_gla_swa.py. Fallback to the local copy in
#    the SpikingBrain-7B repo if PyPI is unavailable for that version.
echo "==> Installing flash-linear-attention 0.1"
FLA_DIR="$(dirname "$(readlink -f "$0")")/../speace_anemos_spikingbrain/SpikingBrain-7B-main/SpikingBrain-7B-main/vllm_hymeta"
if [[ -d "${FLA_DIR}" ]]; then
    pip install -e "${FLA_DIR}" --no-build-isolation || \
        pip install "flash-linear-attention==0.1"
else
    pip install "flash-linear-attention==0.1"
fi

# 8. bitsandbytes + accelerate (the 4-bit NF4 quantization pair).
echo "==> Installing bitsandbytes + accelerate"
pip install "bitsandbytes>=0.43"
pip install "accelerate>=0.30"

# 9. Sidecar deps.
pip install "fastapi>=0.110" "uvicorn[standard]>=0.27" "pydantic>=2.6" "httpx>=0.27"

# 10. Download the model.
echo "==> Downloading ${MODEL_REPO} (~14 GB)"
mkdir -p "$(dirname "${MODEL_DIR}")"
python - <<PY
import os
from huggingface_hub import snapshot_download
path = snapshot_download(
    repo_id=os.environ.get("SPB_REPO_ID", "${MODEL_REPO}"),
    local_dir=os.path.expanduser("${MODEL_DIR}"),
    token=os.environ["HF_TOKEN"],
    allow_patterns=[
        "*.json", "*.txt", "*.md", "*.py",
        "*.safetensors", "*.bin",
        "tokenizer*", "special_tokens*", "vocab*", "merges*",
    ],
)
print("downloaded to", path)
PY

# 11. Smoke test.
echo "==> CUDA smoke test"
python - <<'PY'
import torch
assert torch.cuda.is_available(), "CUDA not available!"
name = torch.cuda.get_device_name(0)
free, total = torch.cuda.mem_get_info(0)
free_mb = free / (1024 * 1024)
total_mb = total / (1024 * 1024)
print(f"GPU: {name} ({free_mb:.0f} / {total_mb:.0f} MB free)")
assert total_mb < 8000, f"expected ~6 GB VRAM, got {total_mb:.0f} MB"
x = torch.randn(1024, 1024, device="cuda")
y = x @ x.T
torch.cuda.synchronize()
print("matmul OK, mean =", float(y.mean()))

# bitsandbytes + accelerate import check.
import bitsandbytes  # noqa: F401
import accelerate  # noqa: F401
print("bitsandbytes", bitsandbytes.__version__, "+ accelerate", accelerate.__version__, "OK")
PY

cat <<'EOF'

==> Installation complete.

Stack:
  - torch 2.6.0 + CUDA 12.4 (cu124 wheel, latest available)
  - transformers 4.55.2
  - triton 3.2.0
  - flash-linear-attention 0.1
  - bitsandbytes >= 0.43
  - accelerate >= 0.30

Model:
  - 7B bf16 on disk (~14 GB), quantised 4-bit NF4 in VRAM (~4-4.5 GB)
  - Expected inference: ~5-10 tok/s on RTX 3060 Laptop 6 GB

Next steps:
  1. Launch the sidecar from this WSL2 shell:
       source ~/.venvs/spikingbrain/bin/activate
       cd /mnt/c/Users/rober/Desktop/Q-SPEACE/q_speace
       python -m spiking_brain_server.server

  2. From Windows PowerShell, point Q-SPEACE at the sidecar:
       $env:Q_SPEACE_BRAIN_ENDPOINT = "http://localhost:8001"
       qspace brain health
       qspace brain think "What is coherence_phi?"
EOF
