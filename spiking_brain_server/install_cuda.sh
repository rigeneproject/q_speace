#!/usr/bin/env bash
# Install torch + vllm + fla + flash-attn for the RTX 3060 Laptop (6GB).
# Run: wsl.exe -d Ubuntu -- bash /path/to/install_cuda.sh
set -uo pipefail
REPO_ROOT="${Q_SPEACE_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
export PATH="${HOME}/.local/bin:/usr/bin:/bin"
export PIP_BREAK_SYSTEM_PACKAGES=1
export VIRTUAL_ENV="${Q_SPEACE_SPB_VENV:-${HOME}/.venvs/spikingbrain}"

# Create venv if missing.
if [[ ! -d "${VIRTUAL_ENV}" ]]; then
    echo "[install_cuda] creating venv at ${VIRTUAL_ENV}"
    mkdir -p "$(dirname "${VIRTUAL_ENV}")"
    # venv from system python; we bootstrap pip into the venv via pip from user space.
    python3 -m venv "${VIRTUAL_ENV}" 2>&1 | tail -3 || {
        # Fallback: just point VIRTUAL_ENV at a fake path; we'll use --user + --target.
        echo "[install_cuda] venv module unavailable, falling back to --user install"
        unset VIRTUAL_ENV
    }
fi

# If venv exists, activate it. Otherwise fall back to user install.
if [[ -d "${VIRTUAL_ENV}" ]]; then
    # shellcheck disable=SC1091
    source "${VIRTUAL_ENV}/bin/activate"
    PIP_FLAGS=()
    PY="$(which python3)"
    echo "[install_cuda] venv active: $(${PY} -V 2>&1)"
else
    PIP_FLAGS=(--user --break-system-packages)
    PY="python3"
    echo "[install_cuda] no venv, installing to user site"
fi

echo "[install_cuda] up: $(python3 -m pip --version 2>&1 | head -1)"

# Helper: run pip with the right flags.
pipx() {
    python3 -m pip install "${PIP_FLAGS[@]}" "$@"
}

# 1. HuggingFace CLI (re-check).
pipx --quiet "huggingface_hub[cli]>=0.24" hf_xet 2>&1 | tail -3

# 2. torch 2.7.1 + cu121.
echo "[install_cuda] torch 2.7.1 + cu121 (this is the big one: ~2GB download)"
pipx --index-url https://download.pytorch.org/whl/cu121 \
    "torch==2.7.1" "torchvision==0.22.1" "torchaudio==2.7.1" 2>&1 | tail -5

# 3. flash-attn 2.7.3 (long build, skip on failure).
echo "[install_cuda] flash-attn 2.7.3 (long build, 5-10 min)"
pipx "flash-attn==2.7.3" --no-build-isolation 2>&1 | tail -3 || \
    echo "[install_cuda] WARNING: flash-attn build failed; PyTorch SDPA fallback will be used."

# 4. triton + transformers + utils.
echo "[install_cuda] triton + transformers + utils"
pipx "triton==3.3.1" "transformers==4.55.2" "scipy" "pyyaml" "decorator" 2>&1 | tail -3

# 5. flash-linear-attention (try local copy first).
FLA_DIR="${Q_SPEACE_FLA_DIR:-${REPO_ROOT}/speace_anemos_spikingbrain/SpikingBrain-7B-main/SpikingBrain-7B-main/vllm_hymeta}"
if [[ -d "${FLA_DIR}" ]]; then
    echo "[install_cuda] installing local vllm_hymeta from ${FLA_DIR}"
    (cd "$(dirname "${FLA_DIR}")" && pipx -e . --no-build-isolation 2>&1 | tail -5) || \
        pipx -e "${FLA_DIR}" --no-build-isolation 2>&1 | tail -5
else
    echo "[install_cuda] WARNING: ${FLA_DIR} not found; using flash-linear-attention from PyPI"
    pipx "flash-linear-attention==0.1" 2>&1 | tail -3
fi

# 6. vLLM 0.10.0.
echo "[install_cuda] vllm 0.10.0 (large download, ~500 MB wheel)"
pipx "vllm==0.10.0" 2>&1 | tail -5

# 7. Sidecar deps.
echo "[install_cuda] fastapi + uvicorn + pydantic + httpx"
pipx "fastapi>=0.110" "uvicorn[standard]>=0.27" "pydantic>=2.6" "httpx>=0.27" 2>&1 | tail -3

# 8. transformers/fla patch.
PATCH="${Q_SPEACE_BITNET_PATCH:-${REPO_ROOT}/speace_anemos_spikingbrain/SpikingBrain-7B-main/SpikingBrain-7B-main/docker_build/patch_fla_bitnet.py}"
if [[ -f "${PATCH}" ]]; then
    echo "[install_cuda] applying transformers/fla patch"
    python3 "${PATCH}" 2>&1 | tail -5 || \
        echo "[install_cuda] WARNING: patch failed; manual review recommended."
fi

# 9. CUDA smoke test.
echo "[install_cuda] CUDA smoke test"
python3 - <<'PY'
import torch
assert torch.cuda.is_available(), "CUDA not available!"
name = torch.cuda.get_device_name(0)
free, total = torch.cuda.mem_get_info(0)
print(f"GPU: {name} ({free/1e6:.0f} / {total/1e6:.0f} MB free)")
x = torch.randn(1024, 1024, device="cuda")
y = x @ x.T
torch.cuda.synchronize()
print("matmul OK, mean =", float(y.mean()))
PY

echo "[install_cuda] done"
