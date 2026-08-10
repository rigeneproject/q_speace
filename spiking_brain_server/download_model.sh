#!/usr/bin/env bash
# Download maujim/spikingbrain-v1-7b-base (~14 GB) into ~/models/.
#
# Usage:
#   wsl.exe -d Ubuntu -- bash /path/to/download_model.sh <HF_TOKEN>
#
# The token is taken as the first argument to bypass WSL2's lack of env
# var propagation from Windows PowerShell/Git Bash. NEVER put a real
# token in a committed file — pass it on the command line.
set -uo pipefail
export PATH="$HOME/.local/bin:/usr/bin:/bin"

if [[ $# -lt 1 || -z "$1" ]]; then
    echo "Usage: $0 <HF_TOKEN>" >&2
    echo "  wsl.exe -d Ubuntu -- bash $0 hf_xxxxxxxxxxxxxxxxxxxx" >&2
    exit 1
fi
export HF_TOKEN="$1"

MODEL_REPO="maujim/spikingbrain-v1-7b-base"
MODEL_DIR="$HOME/models/maujim/spikingbrain-v1-7b-base"

echo "[download] target: $MODEL_REPO"
echo "[download] dest:   $MODEL_DIR"
echo "[download] HF_TOKEN length: ${#HF_TOKEN}"

# Auth check first (fast fail if token is wrong).
if ! python3 -c "from huggingface_hub import HfApi; import os; api=HfApi(token=os.environ['HF_TOKEN']); print('whoami:', api.whoami().get('name'))" 2>&1; then
    echo "[download] ERROR: HF_TOKEN rejected by HuggingFace" >&2
    exit 1
fi

mkdir -p "$HOME/models/maujim"
echo "[download] starting snapshot_download (this can take 5-20 minutes)"

python3 - <<PY
import os
from huggingface_hub import snapshot_download
try:
    p = snapshot_download(
        repo_id="$MODEL_REPO",
        local_dir="$MODEL_DIR",
        token=os.environ["HF_TOKEN"],
        allow_patterns=[
            "*.json", "*.txt", "*.md", "*.py",
            "*.safetensors", "*.bin",
            "tokenizer*", "special_tokens*", "vocab*", "merges*",
        ],
        max_workers=4,
    )
    print("downloaded to:", p)
except Exception as e:
    print("DOWNLOAD FAILED:", type(e).__name__, str(e)[:300])
    raise
PY

echo "[download] done."
du -sh "$MODEL_DIR" 2>/dev/null
ls -la "$MODEL_DIR" | head -20
