#!/usr/bin/env bash
# Minimal: just install huggingface_hub into WSL2 user space.
# Run: wsl -d Ubuntu -- bash /mnt/c/Users/rober/Desktop/Q-SPEACE/q_speace/spiking_brain_server/install_pip.sh
set -euo pipefail
# Use the user-local pip we already installed via get-pip.py.
export PATH="$HOME/.local/bin:$PATH"

echo "[install_pip] pip: $(python3 -m pip --version)"
echo "[install_pip] installing huggingface_hub + hf_xet (user space)"
python3 -m pip install --user --break-system-packages "huggingface_hub[cli]>=0.24" hf_xet 2>&1 | tail -5
echo "[install_pip] done"
echo "[install_pip] hf version: $($HOME/.local/bin/hf --version 2>&1 | head -2)"
