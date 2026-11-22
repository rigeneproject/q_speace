#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="${Q_SPEACE_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
VENV_DIR="${Q_SPEACE_SPB_VENV:-${HOME}/.venvs/spikingbrain}"
cd "${REPO_ROOT}"
source "${VENV_DIR}/bin/activate"
exec python spiking_brain_server/_t205_measure.py "$@"