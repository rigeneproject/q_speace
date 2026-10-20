"""T205-C measurement harness — 64 prompt × SpikingBrain-7B NF4 (cache-less).

Variante di ``_t205_measure.py`` pensata per il **checkpoint reale**
``maujim/spikingbrain-v1-7b-base`` caricato in NF4 4-bit sul sidecar
in cache-less mode (porta 8001). Tutto il resto del protocollo è
identico a T205-C già eseguito su Qwen 3B (porta 8002):

- 64 prompt, 4 categorie × 16, IT + EN
- campionamento power.draw via nvidia-smi a ~100 ms
- E_prompt_J = ∫(P - P_idle) dt
- pred_w = QuantumCostModel.energy_watts(op)
- slope log-log pred/meas = ?

**Vincoli**:
- Il sidecar DEVE essere avviato con il flag cache-less attivo
  (proposto in T-SPB-0B) per evitare la degradazione cache sliding
  window di fla × transformers 4.55.
- Tempi attesi ~13.6 s/tok (10× il throughput cached); 64 prompt ×
  96 token ≈ 22 ore wall-clock sul RTX 3060 6 GB. Ridurre ``--n-tokens``
  a 32 per un run veloce (~7 ore) oppure a 16 per uno smoke (~3.5 ore).
- VRAM osservata in T-SPB-0A: 5682 MB su 6144 MB disponibili.

**Uso (WSL2)**:

    cd spiking_brain_server
    # 1) sidecar su 8001 in cache-less mode (forward singolo, no cache)
    python server.py --no-cache --port 8001 &
    # 2) harness
    python _t205_measure_spb7b.py --n-tokens 32 --baseline-duration 30

**Output**:
- ``docs/T205C_measurements_spb7b.csv``
- ``docs/T205C_plots_spb7b/*.png``
- confronto con T205C_measurements.csv (Qwen 3B) annotato in
  ``docs/T-SPB-2_RESULTS.md`` (da scrivere dopo il run).

**Epistemic note**: questo script misura SpikingBrain-7B **reale**, NON
Qwen 3B o stub. È il back-end designato per sciogliere il Gap 2 della
survey architetturale 2026-08-12. I risultati NON sostituiscono la
forma funzionale già confermata su Qwen 3B; permettono di validare
che le costanti del modello 7B rientrano nello stesso regime
(slope ≈ 1) oppure no.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Reuse T205-C measurement core; override SIDE only.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from spiking_brain_server import _t205_measure as core  # noqa: E402

# Override sidecar endpoint and output paths.
core.SIDE = "http://127.0.0.1:8001"  # SpikingBrain-7B NF4 cache-less
core.CSV_PATH = REPO_ROOT / "docs" / "T205C_measurements_spb7b.csv"
core.PLOTS_DIR = REPO_ROOT / "docs" / "T205C_plots_spb7b"
core.BASELINE_DURATION_S = 30.0   # longer baseline for a hot GPU
core.N_PROMPTS = 64

# Reduce default token count to keep total wall-clock tractable on RTX 3060.
# Cache-less: ~13.6 s/tok observed (T-SPB-0A). 64 × 32 = 2048 tok ≈ 7.7 h.
# Use --n-tokens 16 for a smoke (~3.9 h), 64 for full night (~15.4 h).
core.N_PROMPTS = 64


def main(argv: list[str] | None = None) -> int:
    argv = list(argv) if argv is not None else sys.argv[1:]
    print(f"[T205-C-SpB7B] sidecar={core.SIDE}", flush=True)
    print(f"[T205-C-SpB7B] CSV → {core.CSV_PATH}", flush=True)
    print(f"[T205-C-SpB7B] plots → {core.PLOTS_DIR}", flush=True)
    print("[T205-C-SpB7B] WARNING: cache-less mode is ~10x slower than cached.", flush=True)
    print("[T205-C-SpB7B]          consider --n-tokens 16 for a smoke run.", flush=True)
    return core.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
