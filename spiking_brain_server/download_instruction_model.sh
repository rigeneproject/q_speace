#!/usr/bin/env bash
set -euo pipefail
MODEL_ID="${Q_SPEACE_INSTRUCT_MODEL:-Qwen/Qwen2.5-3B-Instruct}"
MODEL_DIR="${Q_SPEACE_INSTRUCT_MODEL_PATH:-$HOME/models/qwen2.5-3b-instruct}"
source "$HOME/.venvs/spikingbrain/bin/activate"
python - <<PY
from huggingface_hub import snapshot_download
snapshot_download(repo_id="${MODEL_ID}", local_dir="${MODEL_DIR}")
PY
echo "Downloaded ${MODEL_ID} to ${MODEL_DIR}"
