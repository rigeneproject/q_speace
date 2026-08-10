#!/usr/bin/env bash
set -euo pipefail
cd /mnt/c/Users/rober/Desktop/Q-SPEACE/q_speace
source ~/.venvs/spikingbrain/bin/activate
exec python spiking_brain_server/_t205_measure.py "$@"