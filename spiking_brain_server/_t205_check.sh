#!/usr/bin/env bash
set -euo pipefail

OUT=/tmp/power_idle.csv
: > $OUT

# driver v550 dropped -lms; emulate 100ms sampling via short bash loop
echo "=== sampling power for 10s at ~100ms ==="
for i in $(seq 1 100); do
    nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits >> $OUT 2>/dev/null || true
    sleep 0.1
done

echo "captured $(wc -l < $OUT) samples"
head -3 $OUT
echo "---"
awk 'NF { s += $1; n++ } END { if (n) printf "P_idle mean = %.2f W (n=%d)\n", s/n, n; else print "no parseable rows" }' $OUT
