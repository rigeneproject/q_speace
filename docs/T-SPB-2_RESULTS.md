# T-SPB-2 — T205-C characterization on real SpikingBrain-7B (NF4, cache-less)

**Status**: harness ready, run pending (operator action)
**Data creazione**: 2026-08-12
**Predecessore**: T-SPB-0A (forward confermato), T-SPB-0B (cache-less fix proposto)
**Successore previsto**: T-SPB-3 (instrumentation), T-SPB-5 (binding come brain area)

> **Epistemic note (2026-08-12)**. Questo ticket misura
> **`maujim/spikingbrain-v1-7b-base` reale** caricato in NF4 4-bit
> sul sidecar `spiking_brain_server/server.py` in cache-less mode
> (forward singolo, no cache sliding window). NON sostituisce le
> misurazioni T205-C su Qwen 3B: serve a verificare se la forma
> funzionale `QuantumCostModel` (slope log-log ≈ 1, confermato su
> Qwen) regge anche sul 7B nativo oppure se le costanti cambiano.

## 1. Cosa è pronto

- **Harness**: `spiking_brain_server/_t205_measure_spb7b.py`
  riusa il core di `_t205_measure.py` (64 prompt, campionamento
  power.draw 100 ms, pred/meas ratio, log-log regression).
  Override di `SIDE` → 8001 e output path dedicati.
- **CSV destinazione**: `docs/T205C_measurements_spb7b.csv`
- **Plot destinazione**: `docs/T205C_plots_spb7b/*.png`

## 2. Cosa serve per partire (azione operatore)

```bash
# In WSL2 (RTX 3060 6 GB visibile):
cd /mnt/c/Users/rober/Desktop/Q-SPEACE/q_speace/spiking_brain_server

# 1) Avviare il sidecar SpB-7B in cache-less mode (T-SPB-0B fix).
python server.py --no-cache --port 8001 &
#    attesa: ~30-60 s per load + warm-up

# 2) Verificare readiness
curl http://localhost:8001/health

# 3) Lanciare harness. Smoke consigliato: --n-tokens 16 (≈ 3.9 h).
#    Produzione: --n-tokens 32 (≈ 7.7 h) oppure --n-tokens 64 (≈ 15.4 h).
python _t205_measure_spb7b.py --n-tokens 32 --baseline-duration 30
```

## 3. Risultati attesi (predizioni operative)

Se il 7B si comporta come Qwen 3B sul contratto `/think`:

| Metrica | Atteso (ordine di grandezza) |
|---|---|
| `P_idle` | 8–12 W (modello caricato, no generation) |
| `E_per_token` (J) | 1–5 J/tok (10× Qwen 3B, atteso) |
| `slope log-log pred/meas` | 0.95–1.05 (forma funzionale confermata) |
| `max_memory_allocated_MB` | 5500–6000 MB (su 6144 MB totali) |
| `wall_s_mean` (32 tok) | 400–450 s (≈ 13 s/tok × 32) |

Se `slope` esce da [0.9, 1.1] o `E_per_token` cambia di > 2× rispetto
a Qwen 3B, aggiornare `RICALIBRATION_FACTOR` nel
`QuantumCostModel` e annotare la modifica in T205_status.md.

## 4. Cosa NON è ancora pronto

- **Flag `--no-cache` in `server.py`**: proposto in `T-SPB-0B_DIAGNOSIS.md`
  come fix post-diagnosi ma **non implementato**. Senza questo flag il
  forward produce testo degradato (perdita/adulti/Publié) e le
  misurazioni di confidenza sono rumorose. L'implementazione richiede
  una singola modifica: nel loop di generazione sostituire
  `model.generate(...)` con un loop `for _ in range(n): out = model(...)`
  che passa sempre l'intera history (no cache).
- **Hook `n_tokens_in` lato server**: lo script si aspetta che
  `metadata.n_tokens_in` sia valorizzato dal sidecar. Verificare che
  `server.py` lo scriva; in caso negativo aggiungere
  `len(tokenizer.encode(prompt))` al dizionario `metadata` di ritorno.

## 5. Confronto con T205-C Qwen 3B

Una volta ottenuto `docs/T205C_measurements_spb7b.csv`, produrre:

- Tabella side-by-side `slope / intercept / E_per_token / max_mem`
  Qwen-3B vs SpB-7B.
- Plot sovrapposto `cost_pred_vs_measured_qwen_vs_spb7b.png`
  (4 serie: Qwen pred, Qwen meas, SpB pred, SpB meas).
- Nota nel README principale: aggiornare la riga
  "T205-C slope = 0.982" con "(Qwen 3B backend)" e aggiungere la riga
  SpB-7B solo se `slope` è confermato anche lì.

## 6. Stato task

| Sotto-task | Stato |
|---|---|
| Harness scritto | ✅ 2026-08-12 |
| `--no-cache` flag implementato | ✅ 2026-08-12 (T-SPB-0B-fix) |
| `n_tokens_in` in metadata | ✅ 2026-08-12 (T-SPB-2-fix) |
| Sidecar avviato + run eseguito | ❌ pending operatore |
| CSV + plot prodotti | ❌ pending run |
| Aggiornamento T205_status.md | ❌ pending risultati |

**Cosa blocca la chiusura del task**: GPU WSL2 + sidecar cache-less.
Tutti i prerequisiti software sono ora soddisfatti; l'unico blocker
è l'esecuzione fisica del run.

## 7. Cosa è cambiato 2026-08-12 (T-SPB-0B-fix + T-SPB-2-fix)

### `spiking_brain_server/server.py`

- Nuovo env var `SPB_NO_CACHE` (default `False`) letto a inizio modulo.
- Nuovo CLI flag `--no-cache` in `main()`.
- Nuova funzione `_generate_cache_less(model, tokenizer, inputs,
  n_tokens, coherence)` che esegue `n_tokens` forward singoli
  senza `past_key_values`, riprocessando l'intera sequenza a ogni
  step. Implementa repetition_penalty, top_p, temperature coerenti
  con la path cached.
- `_think_sync` ora sceglie automaticamente il path in base a
  `CACHE_LESS`.
- `HealthResponse.cache_less: bool` esposto in `/health`.
- `ThinkResponse.metadata.n_tokens_in` (int) e `cache_less` (bool)
  aggiunti a `/think`.

### `q_speace/spiking_brain/client.py`

- `_parse_think_result` chiama `metadata.setdefault("n_tokens_in", 0)`
  per tollerare sidecar legacy che non scrivono il campo.

### `tests/test_spiking_brain.py`

- Nuovo test `test_http_client_think_default_n_tokens_in_zero_on_legacy_sidecar`:
  payload senza `n_tokens_in` → parsing OK con default 0.
- Nuovo test `test_http_client_think_preserves_n_tokens_in_from_metadata`:
  payload con `n_tokens_in=7` e `cache_less=true` → metadata preservata.