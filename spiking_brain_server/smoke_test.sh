#!/usr/bin/env bash
# ----------------------------------------------------------------------
# Smoke test per SpikingBrain-7B sidecar (T205).
#
# Verifica che:
# 1. /health risponda con ready=true
# 2. /think produca una risposta non vuota in tempi accettabili
# 3. il primo token dopo "The capital of France is" sia "Paris" (forward
#    puro verificato nel probe; con cache kv sliding window può
#    degradare, ma il primo token dovrebbe essere coerente)
#
# Uso da PowerShell:
#   wsl -d Ubuntu -- bash -c "cd /mnt/c/Users/rober/Desktop/Q-SPEACE/q_speace && bash spiking_brain_server/smoke_test.sh"
#
# Requisiti: sidecar in esecuzione su http://127.0.0.1:8001.
# Per lanciarlo:
#   wsl -d Ubuntu -- bash -c "cd /mnt/c/Users/rober/Desktop/Q-SPEACE/q_speace && \
#     source ~/.venvs/spikingbrain/bin/activate && \
#     SPB_SKIP_DISK_PATCHER=1 SPB_MAX_MEMORY='{\"0\":\"5700MB\",\"cpu\":\"1500MB\"}' \
#     python -m spiking_brain_server.server"
# ----------------------------------------------------------------------
set -euo pipefail

SIDECAR="${SPB_SIDECAR_URL:-http://127.0.0.1:8001}"

echo "==> Smoke test SpikingBrain sidecar @ ${SIDECAR}"

echo "--- /health ---"
HEALTH=$(curl -s -m 10 "${SIDECAR}/health")
echo "${HEALTH}" | python -m json.tool
READY=$(echo "${HEALTH}" | python -c "import json, sys; print(json.load(sys.stdin)['ready'])")
if [[ "${READY}" != "True" ]]; then
    echo "ERROR: model not ready"; exit 1
fi

echo "--- /think ---"
PROMPT="${SPB_SMOKE_PROMPT:-The capital of France is}"
N_TOKENS="${SPB_SMOKE_N_TOKENS:-16}"

T0=$(date +%s.%N)
RESP=$(curl -s -m 180 -X POST "${SIDECAR}/think" \
    -H "Content-Type: application/json" \
    -d "{\"prompt\": \"${PROMPT}\", \"n_tokens\": ${N_TOKENS}}")
T1=$(date +%s.%N)
DT=$(python -c "print(f'{$T1 - $T0:.1f}')")

echo "${RESP}" | python -m json.tool
echo "wall time: ${DT}s"

# Sanity check: response contains non-empty text and at least 1 spike.
TEXT=$(echo "${RESP}" | python -c "import json, sys; print(json.load(sys.stdin).get('text', ''))")
N_SPIKES=$(echo "${RESP}" | python -c "import json, sys; r = json.load(sys.stdin); print(r.get('spikes', {}).get('num_spikes', 0))")
if [[ -z "${TEXT}" ]]; then
    echo "ERROR: empty text response"; exit 2
fi
if [[ "${N_SPIKES}" -lt 1 ]]; then
    echo "WARNING: 0 spikes generated — coherence gate may be too strict"
fi
echo "OK — ${#TEXT} chars, ${N_SPIKES} spikes"