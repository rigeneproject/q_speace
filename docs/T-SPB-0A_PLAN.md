# T-SPB-0A — SpikingBrain Standalone: Verifica pesi + bug SDPA

**Status**: agentic (planning)
**Data**: 2026-08-10
**Predecessore**: T205-C completato (`docs/T205_status.md`)
**Successore previsto**: T-SPB-1 (SpikingBrain 1B standalone)

## 1. Scopo

Prima di scrivere qualsiasi nuova integrazione, **verificare cosa è
realmente eseguibile** sull'hardware WSL2 / RTX 3060 6 GB e fissare
il bug SDPA-varlen che blocca qualsiasi forward di qualità sul
checkpoint `maujim/spikingbrain-v1-7b-base`.

Questo ticket è **solo verifica + fix mirato**, non disegna
un'Adapter. L'architettura del `SpikingBrainCognitiveInterface`
(T-SPB-4) è documentata ma rimandata.

## 2. Cosa è già in piedi (survey 2026-08-10)

### Sidecar (`spiking_brain_server/`)
- `server.py:1141` — FastAPI :8001, carica `maujim/spikingbrain-v1-7b-base`
  via HF + bitsandbytes NF4; `/think`, `/health`; meta-path hook
  per SDPA fallback (`server.py:195–749`).
- `instruction_server.py:195` — Qwen2.5-3B-Instruct NF4 via T207.
- `install.sh`, `download_model.sh`, `download_instruction_model.sh`,
  `install_cuda.sh`, `install_pip.sh` — bootstrap WSL2.
- `_apply_mask_fix.py`, `_debug_unpad.py`, `_smoke_forward.py`,
  `_probe_4bit.py`, `_auth_check.py`, `_poll_health.py`,
  `smoke_test.sh` — probe diagnostici.
- `_t205_measure.py`, `_t205_run.sh`, `_t205_check.sh`,
  `_t205_start.ps1`, `_t205_smoke.py` — harness T205-C.

### Cortex binding (`q_speace/spiking_brain/`)
- `cortex.py:50–261` — `SpikingBrainCortex` con `tick()` →
  cost → Sevo → coherence → ILF update.
- `factory.py:55–68` — default = stub; `Q_SPEACE_BRAIN_ENDPOINT`
  per HTTP client.
- `client.py:80–118` — `HTTPSpikingBrainClient` async httpx.
- `stub.py:61, 171` — `StubSpikingBrain` (W8ASpike) + `StubSpikingBrainV2`
  (DSSA).
- `types.py` — `ThinkResult`.
- `evaluation.py:23–48` — `calibration_report` (Brier/ECE).

### Test offline (`tests/`)
- `test_spiking_brain.py:353` — 24 test (factory, stub, cortex,
  mock HTTP, server importability).
- `test_spiking_brain_evaluation.py:28` — 3 test calibration.
- `test_spiking.py:193` — 21 test T202 numpy.
- `test_orchestrator_spiking.py` — T204 (4 test).
- **Live sidecar test skippati per default** (`test_spiking_brain.py:312, 330`).

### BCEL (`q_speace/bcel/catalog.py`)
10 voci spike/brain/corteccia presenti, incluso:
- "Brain area as cognitive subdivision" (functional)
- "SpikingBrain-7B / SpB2.0 model identity" (accidental)
- "DSSA dual-path activation coding (SpB2.0)" (functional)

### Repos vendor (`sppeace_anemos_spikingbrain/`)
- `SpikingBrain-7B-main/` — `hf_7B_model`, `W8ASpike`,
  `vllm_hymeta`, `docker_build/patch_fla_bitnet.py`.
- `SpikingBrain2.0-main/` — `spb2`, `MoBA`,
  `flash-linear-attention_dev`.
- `SpikingBrain.pdf`, `docs/2604.22575v1.pdf` (SpB2.0), `docs/Spiking Brain.pdf`.

## 3. I 10 gap reali

| # | Gap | Severità |
|---|---|---|
| 1 | Pesi SpikingBrain non verificabili da Windows PowerShell (WSL2 mount isolato) | Bloccante |
| 2 | Forward SDPA rotto: `window_attention.py:259` mask shape `(B,H,q_len,head_dim)` invece di `(B,H,q_len,k_len)` | Bloccante |
| 3 | Sliding-window kv-cache degrada `pérdida`/`adultes` (incompatibilità fla × transformers 4.55) | Funzionale |
| 4 | Nessuna `SpikingBrainCognitiveInterface` formalizzata (no streaming/tool/retrieval) | Architetturale |
| 5 | Nessun memory subsystem in `q_speace/` (no working/episodic/retrieval) | Funzionale |
| 6 | Default backend = stub finché `Q_SPEACE_BRAIN_ENDPOINT` non settato | Documentazione |
| 7 | Test live skippati + bug → mai esercitato end-to-end in CI | Qualità |
| 8 | No `qspace brain run` driver in `cli.py` (solo `tick`/REPL one-shot) | UX |
| 9 | `calibration_report` mai chiamato dal cortex (BCEL functional non enforced) | Validazione |
| 10 | SpB2.0-5B non pubblicamente scaricabile (ago 2026); solo stub | Esterno |

## 4. Cose da fare in T-SPB-0A (questo ticket)

### 4.1 Verifica WSL2 (no codice)

```bash
wsl -d Ubuntu -- bash -lc '
  echo "=== venv ==="
  ls ~/.venvs/spikingbrain/bin/activate 2>&1 || echo "venv MISSING"
  echo "=== SpikingBrain-7B weights ==="
  ls -la ~/models/maujim/spikingbrain-v1-7b-base/ 2>&1 | head -20
  echo "=== Qwen2.5-3B weights ==="
  ls -la ~/models/qwen2.5-3b-instruct/ 2>&1 | head -10
  echo "=== sidecar live? ==="
  curl -s http://127.0.0.1:8001/health 2>&1 | head -3
  curl -s http://127.0.0.1:8002/health 2>&1 | head -3
'
```

Esiti attesi:

- `venv` esiste → ambiente pronto.
- `~/models/maujim/spikingbrain-v1-7b-base/` esiste con
  `config.json`, `modeling_*.py`, `tokenizer*`, pesi shard → 7B
  scaricato.
- `~/models/qwen2.5-3b-instruct/` esiste → T207 pronto.
- `/health:8001` = 503 o errore SDPA → conferma bug.
- `/health:8002` = `ready=true` → T207 OK (già validato in T205-C).

### 4.2 Fix bug SDPA (uno dei due)

**Opzione A — Mask shape fix (preferita, locale):**

Ripulire il template SDPA fallback in `server.py:259` perché la
mask abbia shape `(B, H, q_len, k_len)` e dtype `bool`. Il fix
T205-B ha rotto la cache sliding window; questo è il fix
*diretto* sul bug primario che il meta-path hook lascia passare.

**Test di accettazione**: dopo fix, il primo forward con cache
genera almeno 4 token senza ripetere `pérdida`/`adultes` per
i primi 16 token di un prompt "The capital of France is".

**Opzione B — Flash-attn prebuilt (scartata se A funziona):**

`pip install flash-attn --no-build-isolation` con wheel per
`torch==2.6.0+cu124` + `python==3.12` + `cuda==12.4`. La release
ufficiale copre solo torch 2.4 e 2.9; servirebbe un build
custom o downgrade a torch 2.4.

**Opzione A è preferita** perché:
- evita nvcc/compilazione;
- evita downgrade di torch;
- fissa la root cause, non lo symptomo.

### 4.3 BCEL — nessuna nuova voce

T-SPB-0A è solo verifica + fix runtime. Le voci BCEL
esistenti ("SpikingBrain-7B model identity" accidental,
"Brain area as cognitive subdivision" functional) già
descrivono lo stato.

### 4.4 Quality gates

- [ ] `wsl -d Ubuntu -- bash -lc 'curl -s http://127.0.0.1:8001/health'`
      → `ready=true` (post-fix)
- [ ] `wsl -d Ubuntu -- bash -lc 'curl -s -X POST http://127.0.0.1:8001/think -H "Content-Type: application/json" -d "{\"prompt\":\"The capital of France is\",\"n_tokens\":16}"'`
      → testo non-vuoto, nessuna ripetizione `pérdida`/`adultes`
- [ ] `pytest tests/test_spiking_brain.py -x` verde
- [ ] `pytest tests/test_spiking_brain.py -x --run-live` (con `Q_SPEACE_BRAIN_ENDPOINT`)
      → i 2 test live passano

### 4.5 Out of scope

- Adapter / CognitiveInterface (T-SPB-4)
- Memory subsystem (T-SPB-5)
- SpB2.0-5B (richiede checkpoint privato)
- 1B vs 7B (T-SPB-1)

## 5. Rischi aperti

- **WSL2 mount**: se la VM è spenta / `~/.venvs/spikingbrain`
  non esiste, T-SPB-0A è bloccato fino a ripristino ambiente.
- **flash-attn**: wheel prebuilt assente per torch 2.6 → opzione B
  richiede build 30-60 min, opzione A è locale.
- **Modello degradato**: anche con fix mask, la cache sliding
  window fla × transformers 4.55 può restare instabile. In
  quel caso, fallback a forward singolo (no cache) per uso
  pratico, modello rimane "sperimentale".

## 6. File-level diff summary per T-SPB-0A

Da committare solo dopo esecuzione:

- `spiking_brain_server/server.py` — fix SDPA mask shape (opzione A)
  o `requirements.txt` con flash-attn (opzione B).
- `docs/T-SPB-0A_PLAN.md` — questo documento (già committato).
- `docs/T205_status.md` — riferimento a T-SPB-0A.

Nessun cambio in `q_speace/` (la `SpikingBrainCortex` non
tocca il runtime SpikingBrain).
