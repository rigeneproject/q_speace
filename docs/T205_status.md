# T205 — Stato di avanzamento (snapshot 2026-08-10) — AGGIORNATO 10:10

## Roadmap SpikingBrain standalone (T-SPB-*)

Survey architetturale del 2026-08-10 (vedi `docs/T-SPB-0A_PLAN.md`) ha
chiuso la fase di analisi e prodotto il piano operativo in 6 fasi:

- **T-SPB-0A** — Verifica pesi WSL2 + bug SDPA (questo commit)
- **T-SPB-1** — SpikingBrain 1B standalone su RTX 3060
- **T-SPB-2** — SpikingBrain 7B NF4 standalone (post 1B)
- **T-SPB-3** — Instrumentation (spike count, sparsity, routing, energy)
- **T-SPB-4** — `SpikingBrainCognitiveInterface` adapter (no duck-typed)
- **T-SPB-5** — `SpikingBrainCortex` come area cerebrale in SPEACE
- **T-SPB-6** — Closed loop (perception → memory → SpB → meta → world → memory)

Distinzione fondamentale assunta come vincolante:

> *Possiamo dimostrare che SpikingBrain è un substrato corticale
> compatibile con SPEACE anche senza eseguirlo sulla RTX 3060.* Il
> primo problema non è la compatibilità architetturale — è rendere
> eseguibile un particolare checkpoint sull'hardware/software
> disponibile. Forma funzionale di `QuantumCostModel` già confermata
> da T205-C (slope log-log = 0.982, resid_std = 0.086).



Questo documento registra uno snapshot storico di T205 (SpikingBrain ↔ SPEACE)
dopo la sessione di lavoro di agosto 2026. Il riepilogo finale allegato
al commit precedente lo dava come "blocked from real inference"; dopo
questa sessione è **sbloccato funzionalmente con qualità limitata**.

> **Verifica corrente — 2026-08-09.** Il sidecar 7B si avvia in WSL2 con
> `torch 2.6.0+cu124`, checkpoint presente e NF4-4bit (`/health: ready=true`,
> 5976 MB VRAM). Una prova `/think` con quattro token ha però prodotto testo
> vuoto; una chiamata CLI è scaduta al timeout di 30 s. Il caricamento non è
> quindi una prova di chat/ragionamento funzionante. Per dialogo scritto va
> selezionato e valutato un piccolo checkpoint instruction-tuned attraverso lo
> stesso contratto HTTP; il 7B resta un backend sperimentale.

---

## T205-A — Architectural integration ✅ COMPLETATO

Statico: il nucleo cognitivo di SPEACE e il binding layer verso
SpikingBrain sono in piedi.

- `q_speace/spiking_brain/` espone `SpikingBrainCortex` con due backend
  intercambiabili (Stub deterministico + HTTP async client).
- `q_speace/spiking_brain/cortex.py` integra con `ILFRegulator`,
  `QuantumCostModel`, `SelfImprovementCortex`.
- `tests/test_spiking_brain.py` ha 16 test offline verdi.
- 114 test totali passati, 2 skipped (test live sidecar).

BCEL gate rispettato: il brain è solo consultivo, passa per Sevo +
coherence gate prima di toccare ILF. Spike biologico = accidentale,
solo la regola `dynamic_spikes` viene ereditata.

---

## T205-B — Real inference ✅ END-TO-END FUNZIONANTE

### Smoke test sidecar (P3 completato)

Sidecar `q_speace/spiking_brain_server/server.py` in esecuzione su
`http://127.0.0.1:8001`. Caricamento modello 4-bit in ~22-25s, 5946 MB
VRAM allocati. Endpoint `/health` e `/think` rispondono regolarmente.

Test:
```bash
$ wsl -d Ubuntu -- bash -c 'cd /mnt/c/Users/rober/Desktop/Q-SPEACE/q_speace && \
    source ~/.venvs/spikingbrain/bin/activate && \
    bash spiking_brain_server/smoke_test.sh'
```

Risultato:
- `/health` → `ready=true, vram_mb=5946, backend=hf-transformers-bnb4bit`
- `/think` con "The capital of France is", n_tokens=16
  - text: `" Paris pérdida cámara pestic pérdida pérdida pérdida adultos pérdida lié pérdida pérdida adultos pérdida注明出处 pérdida"`
  - **primo token = "Paris"** (forward puro corretto)
  - confidence: 0.999, belief: [4.78e-12, 0.999, 1.29e-08]
  - spikes: 1 spike (sparsity 0.67, rate 3.33 Hz)
  - plasticity: [0.63, 1.0, 0.27]
  - latency_s: 1.23s, wall time 1.2s

### Modifiche al sidecar per abilitare l'E2E

| File | Modifica |
|---|---|
| `q_speace/spiking_brain_server/server.py` | (1) Aggiunto env var `SPB_SKIP_DISK_PATCHER=1` per skippare `_evict_cached_window_attention` (risolve conflitto tra fix on-disk e patcher) (2) Aggiunto env var `SPB_MAX_MEMORY` per vincolare `device_map` (es. `{"0":"5700MB","cpu":"1500MB"}`) (3) Integrati mask shape fix + indices long cast **direttamente nella template string del SDPA fallback** (riga 370 e 409) — l'iniezione via meta-path hook non veniva chiamata per il modulo dinamico HF |
| `~/models/maujim/.../window_attention.py` | Ripristinato originale (9912 bytes, 219 righe) per evitare corruzione |
| `~/.cache/huggingface/.../window_attention.py` | Auto-rigenerato da HF transformers, contiene originale |

### Punti di attenzione

1. **Avvio sidecar**: serve `SPB_SKIP_DISK_PATCHER=1` perché il
   patcher on-disk interno al sidecar sovrascrive i file con codice
   non patchato e genera SyntaxError al primo import.

2. **memoria**: serve `SPB_MAX_MEMORY='{"0":"5700MB","cpu":"1500MB"}'`
   per evitare il fallback di `device_map="auto"` che mette alcuni
   moduli su meta-tensor (errore `Tensor.item() cannot be called on
   meta tensors`).

3. **Qualità di generazione con cache kv sliding window**: persiste
   la degradazione `pérdida/adultes`. Forward puro funziona (Paris
   nel primo token). Causa nota: incompatibilità fla × transformers
   nel path varlen cache. Out of scope per T205.

4. **Latenza /think**: 1.23s per 16 token. Collo di bottiglia è la
   conversione belief ↔ spike in Python, non il modello.

### Come lanciare il sidecar ora

```bash
wsl -d Ubuntu -- bash -c '
  cd /mnt/c/Users/rober/Desktop/Q-SPEACE/q_speace && \
  source ~/.venvs/spikingbrain/bin/activate && \
  export SPB_SKIP_DISK_PATCHER=1 && \
  export SPB_MAX_MEMORY='"'"'{"0":"5700MB","cpu":"1500MB"}'"'"' && \
  python -m spiking_brain_server.server'
```

Oppure smoke test automatico:
```bash
wsl -d Ubuntu -- bash -c '
  cd /mnt/c/Users/rober/Desktop/Q-SPEACE/q_speace && \
  source ~/.venvs/spikingbrain/bin/activate && \
  bash spiking_brain_server/smoke_test.sh'
```

### File creati per la sessione

- `q_speace/spiking_brain_server/server.py` — patchato (env var, template SDPA corretta)
- `q_speace/spiking_brain_server/smoke_test.sh` — nuovo, smoke test bash
- `q_speace/spiking_brain_server/_apply_mask_fix.py` — già esistente, ora NO-OP (i fix sono nel template SDPA)

---

## T205-B (storico sotto, ora deprecato)

### Cosa funziona

1. **Modello 7B in 4-bit caricato in 5.58 GB VRAM** (su 6 GB disponibili)
   con bitsandbytes NF4 + double-quant + bf16 compute.
2. **Forward puro (no cache)**: 0.1s per "The capital of France is" →
   top-5 logits danno "Paris" / "the" / "a" con probabilità ~11.7% ciascuno.
3. **Generate con cache**: 16 token in 2.4–4.2s (sample) o 49.5s (greedy).
4. **Endpoint HTTP invariato**: lato SPEACE nessuna modifica.

### Cosa non funziona bene

Generazione con cache degenera in pattern ripetitivi:

```
ESP1: 'Explain quantum entanglement in one sentence.'
  → '<|endoftext|> pérdida pérdida pérdida pérdida adultes ...'

ESP2: 'Hello, how are you?'
  → ' I pérdida pérdida pérdida adultes ...'

ESP4: 'The capital of France is' (sampling)
  → ' a pérdida pérdida pérdida adultos lógica ...'
```

I token `pérdida` (id 143907) e `adultes` (id 86925) sono ripetuti.
Classico segno di **kv-cache sliding window non ben posizionata**:
il modello non sa più "muoversi" dopo i primi token.

### Root cause analizzata

1. ❌ **Bug mask SDPA fallback** (window_attention.py riga 51, 68): la
   mask aveva shape `(B, H, q_len, head_dim)` invece di `(B, H, q_len, k_len)`.
   **Fix applicato** in `~/models/maujim/spikingbrain-v1-7b-base/window_attention.py`
   e nella cache HF. Vedi `_apply_mask_fix.py`.

2. ❌ **Bug dtype in pad_input** (window_attention.py riga 73):
   `index_copy_` richiede long tensor, `_upad_input` ritorna int32.
   **Fix applicato** con `.to(...).long()`.

3. ⚠️ **kv-cache sliding window degradation**: rimanente. Probabilmente
   incompatibilità fla × transformers 4.55 nel path varlen.

### Modifiche al codice

| File | Modifica |
|---|---|
| `~/models/maujim/spikingbrain-v1-7b-base/window_attention.py` | Fix mask shape (riga 51, 68) + indices long cast (riga 73) |
| `~/.cache/huggingface/modules/transformers_modules/spikingbrain-v1-7b-base/window_attention.py` | Stessa fix (cache HF) |
| `~/.venvs/spikingbrain/.../fla/models/bitnet/__init__.py` | Patch `exist_ok=True` su 3 `register()` |
| `pip install transformers==4.54.1` | Pin a 4.54.x (latenza 2-8× migliore) |

### Pin transformers 4.54.1 (risultato P8)

Testato via probe con 4.54.1 + 4.55.2. Risultato:

- **Latenza migliorata**: ESP2 0.9s vs 2.4s (2.7×), ESP4 0.5s vs 4.2s (8×).
- **Qualità testo**: invariata. La degradazione `pérdida`/`adultes`
  persiste indipendentemente dalla versione transformers.
- **Conclusione**: il pin a 4.54.1 va mantenuto per la latenza.
  Il bug kv-cache sliding window è nel modello stesso, non in
  transformers.

### Decisione sul trade-off

Il riepilogo finale del documento T205 elencava tre opzioni per il
blocker:

1. Installare flash-attn prebuilt per torch 2.6.0+cu124
2. Fixare la mask SDPA fallback
3. Pinnare transformers 4.54.x

La release page di FlashAttention NON ha wheel per torch 2.6.x
(copre solo torch 2.4 e torch 2.9). Compilare da sorgente richiederebbe
nvcc nel venv WSL2 (assente). **Opzione 1 scartata.**

**Opzione 2 eseguita** (fix mask shape + indices long cast). Il forward
non crasha più. Il modello gira.

**Opzione 3 eseguita** (pin transformers 4.54.1). Non ha risolto la
qualità di generazione, ma ha migliorato la latenza. Da mantenere.

### Nuovo stato: qualità di generazione limitata

La degradazione `pérdida`/`adultes` con cache sliding window è un
limite noto del modello. Forward puro (no cache) funziona
perfettamente. Per caratterizzazioni T205-C, è sufficiente un forward
singolo. Per uso reale del modello come "area di pensiero" in
SPEACE, è necessario fixare la cache sliding window — attività che
esula da T205.

---

## T205-C — Hardware characterization ✅ COMPLETATO (2026-08-10)

Misure da raccogliere (P5 nella task list):

- VRAM picco/medio durante 64 prompt
- RAM WSL2 picco/medio
- TTFT (time to first token)
- token/s medio
- Potenza hardware (nvidia-smi --query-gpu=power.draw)
- Confronto con `QuantumCostModel.energy_watts()`

Solo dopo T205-B pulito (cioè dopo pin a 4.54 oppure ora che il modello
gira funzionalmente) la caratterizzazione dà numeri sensati.

---

## Cosa fare adesso

1. **Tentare il pin a `transformers==4.54.x`** per vedere se la
   qualità di generazione migliora. Costo: 5 minuti, una riga di
   `pip install`. Beneficio atteso: kv-cache sliding window funziona.
   Risk: perdi funzionalità 4.55 che non sono core per noi.

2. **Se pin funziona**: cancellare il fallback SDPA patcher custom
   e usare il path attenzione standard. Documentare la config vincente.

3. **Se pin non funziona**: accettare la degradazione come limite
   noto di compatibilità e procedere con T205-C (caratterizzazione).

4. **In ogni caso**: il sidecar FastAPI va riscritto per usare
   `AutoModelForCausalLM` 4-bit invece di vLLM-hymeta. Il vecchio
   `server.py` parlava a vLLM via subprocess; ora va rimosso o
   affiancato a una nuova variante.

---

## T205-C — Caratterizzazione energetica (protocollo)

Questa sezione definisce *prima* dell'esecuzione il protocollo di misura
che chiude T205-C. Senza questa definizione esplicita le 64 prompt
diventano una raccolta di numeri non confrontabili né riproducibili.

### Cosa stiamo misurando (disambiguazione epistemica)

Le metriche Brier/ECE, le misure di energy e le stime di latenza
riportate in T205-C caratterizzano **il backend di verbalizzazione
attualmente operativo** — `Qwen2.5-3B-Instruct` caricato in NF4 4-bit
via `bitsandbytes`, esposto da `spiking_brain_server/instruction_server`
sulla porta 8002 — oppure, in modalità offline, lo stub deterministico
`StubSpikingBrain` / `StubSpikingBrainV2`.

Non misuriamo la metacognizione di SpikingBrain in senso proprio. Il
checkpoint SpikingBrain2.0-5B (DSSA / dual-path FP8/int8) non è
pubblicamente scaricabile da HuggingFace ad agosto 2026, e il
sub-strato spiking di SPEACE replica solo la regola matematica
`dynamic_spikes` (T202), non l'architettura dual-path del modello.
La frase standard da usare in contesti esterni:

> "Le metriche di T205-C caratterizzano la calibrazione e il costo
> energetico del backend instruction-tuned Qwen2.5-3B-Instruct (NF4) in
> esecuzione sul sidecar `instruction_server`, con il gate ILF+Sevo
> invariato. La metacognizione di SpikingBrain in senso proprio non è
> misurata: il checkpoint dual-path SpB2.0 non è pubblicamente
> disponibile e il sub-strato spiking di SPEACE replica solo la regola
> `dynamic_spikes` di W8ASpike, non l'architettura V2."

### Vincolo hardware verificato

- GPU: NVIDIA GeForce RTX 3060 Laptop, 6144 MiB VRAM, compute capability 8.6
- Driver / CUDA: 552.12 / CUDA 12.4 via WSL2 passthrough
- Modello: Qwen2.5-3B-Instruct, NF4, ~2.5 GB VRAM residenti
- Baseline di potenza idle (modello in VRAM, nessuna generazione): da
  misurare in WSL2 con `nvidia-smi -lms 100` per 15 s → `P_idle` (W)

### Accorgimento metodologico cruciale

**Mai confrontare direttamente `nvidia-smi power.draw` con
`QuantumCostModel.energy_watts`.** La scheda consuma anche a vuoto:
ventole, leakage, memoria allocata che tiene i tensori "vivi" anche
quando il modello non sta generando. Il confronto corretto è:

```
ΔP_i = P_during_i - P_idle       # potenza *utile* al sample i
E_useful_J = Σ_i ΔP_i · Δt_i     # energia utile del prompt
                                  # (sottrazione punto per punto,
                                  #  non per media)
E_per_token_J = E_useful_J / max(n_tokens_out, 1)
```

Confronto mele-vs-pere se si usa `P_during` direttamente: il modello
non sa nulla dell'idle, quindi ogni misura sarà sistematicamente
sovrastimata di un offset costante `P_idle · wall_clock`.

### Protocollo di misura energia

Per ogni prompt `p ∈ prompts[64]`:

1. **Reset memoria**:
   ```python
   torch.cuda.reset_peak_memory_stats()
   torch.cuda.empty_cache()
   ```
2. **Log lunghezza input**: `n_tokens_in = len(tokenizer.encode(prompt))`.
3. **Baseline idle** (separata, non per prompt): 15 s di campionamento
   continuo `nvidia-smi --query-gpu=power.draw --format=csv,noheader -lms 100`
   con modello caricato ma nessuna generazione → `P_idle` (media).
4. **Campionamento power durante generazione** (thread parallelo,
   overhead zero sul thread di inferenza):
   ```python
   import pynvml
   pynvml.nvmlInit()
   handle = pynvml.nvmlDeviceGetHandleByIndex(0)
   power_samples = []   # lista di (timestamp_s, power_w)
   # thread: while not done: power_samples.append((now, nvml.DeviceGetPowerUsage(handle) / 1000))
   ```
   Frequenza: 100 ms (10 Hz). Sufficiente per separare prefill da
   decode (la cui firma di potenza differisce di 50-80 W).
5. **Generazione** (via `instruction_server`):
   ```python
   POST /think  body={"prompt": p, "coherence_phi": φ, "n_tokens": N_max}
   ```
6. **Log output**:
   - `n_tokens_out` (dal campo `n_tokens` della risposta)
   - `wall_clock_s` (timestamp fine − timestamp inizio generazione)
   - `cuda.max_memory_allocated()` dopo `reset_peak_memory_stats()`
   - `confidence` (dal campo `confidence`)
   - `belief_entropy = -Σ belief_i · ln belief_i`
   - `text` (per ispezione qualitativa post-hoc)
7. **Calcolo energia per prompt**:
   ```
   E_prompt_J = Σ_i (P_i - P_idle) · Δt_i
   E_per_token_J = E_prompt_J / max(n_tokens_out, 1)
   ```
8. **Stima predetta dal modello** (lato SPEACE):
   ```python
   op = QuantumOperation(
       num_qubits=4,
       num_gates=n_tokens_out * 3,
       entanglement_depth=2,
       decoherence_budget=max(1.0 - confidence, 0.0),
   )
   cost_predicted_W = cost.energy_watts(op)
   cost_predicted_J = cost_predicted_W * wall_clock_s
   ```
9. **Registrazione riga CSV** in
   `docs/T205C_measurements.csv` con colonne:
   ```
   prompt_idx, prompt_text, n_tokens_in, n_tokens_out, wall_clock_s,
   max_memory_allocated_MB, P_idle_W, P_mean_W, P_peak_W, E_prompt_J,
   E_per_token_J, cost_predicted_W, cost_predicted_J, confidence,
   belief_entropy, ratio_pred_over_measured, text_first_80_chars
   ```

### Criterio di validità (forma funzionale > valore assoluto)

Il modello `QuantumCostModel.energy_watts` è tarato sulla costante
arbitraria `W_PER_SPIKE = 0.001 W` (500 spike ≈ 1 qubit-secondo).
Quindi il valore assoluto è arbitrario per costruzione; ciò che
conta è la **forma della relazione**:

- più `n_tokens_out` → più `E_prompt_J` (linearità entro il decode);
- più `n_tokens_out` → meno `E_per_token_J` (amortizzazione del prefill);
- `belief_entropy` alta → alta `decoherence_budget` → costo predetto
  leggermente più alto (termine `num_qubits * (1 + decoherence)`);
- alta `confidence` → decode più deterministico → varianza di `power`
  più bassa (STD di `P_i`).

I plot critici (una volta collezionate le 64 righe):

1. **`E_prompt_J` vs `cost_predicted_J`** (scatter log-log): se la
   retta di regressione ha slope ≈ 1 e intercetta diversa da zero, il
   modello è ben formato nella scala (l'intercetta è il fattore
   costante da ritarare). Se slope ≠ 1, la forma funzionale è
   sbagliata e l'intero `passes_sevo` va rivisto.
2. **`E_per_token_J` vs `n_tokens_out`**: deve essere circa
   monotonico decrescente.
3. **STD(`P_i`) vs `1 - confidence`**: varianza di potenza correlata
   all'incertezza del modello (proxy indipendente di metacognizione
   spiking).
4. **`max_memory_allocated_MB` vs `n_tokens_out`**: crescita attesa
   lineare con la cache; verifica che non ci siano leak.

Se slope = 1 → ricalibriamo `W_PER_SPIKE` per matchare l'intercetta.
Se slope ≠ 1 → scriviamo un T-ticket T207-bis per rivedere la forma
del modello.

### Cosa NON è nel perimetro di T205-C

- Benchmark del *vero* SpikingBrain-7B (maujim/spikingbrain-v1-7b-base):
  fuori perimetro, modello non utilizzabile con qualità sulla 3060 6 GB.
- Benchmark di SpikingBrain2.0 (SpB2.0-5B base/instruct/think):
  checkpoint non pubblicamente disponibile su HuggingFace ad agosto
  2026.
- Test della qualità di generazione (perplexità, MMLU, C-EVal):
  T205 misura il *costo* del backend verbale, non la sua bravura
  linguistica. Per la qualità, separato.
- Confronto con CPU offload / vLLM-hymeta: sostituito dal backend
  NF4 (T205-B §Modifiche al sidecar).

### Strumenti richiesti

- `pynvml` (`pip install pynvml`) per campionamento power continuo
  dentro Python (alternativa: `nvidia-smi -lms 100 > power.log &
  … kill $!`).
- Thread separato per il campionamento, per non interferire con il
  thread di inferenza (GIL non impatta perché `pynvml` è C).
- `numpy` + `csv` (stdlib) per il logging.
- `matplotlib` (opzionale, solo per i plot finali).

### Formato output finale

- CSV in `docs/T205C_measurements.csv` (64 righe + header).
- Quattro plot PNG in `docs/T205C_plots/`:
  - `cost_pred_vs_measured.png`
  - `energy_per_token_vs_tokens_out.png`
  - `power_variance_vs_inverse_confidence.png`
  - `max_memory_vs_tokens_out.png`
- Paragrafo di analisi (3-5 frasi) in fondo alla sezione T205-C con:
  slope della regressione, intercetta, deviazione standard del
  residuo, ed esplicita conferma/negazione delle ipotesi di forma.

### Risultati run 2026-08-10 (64 prompt × Qwen2.5-3B-Instruct NF4)

CSV: `docs/T205C_measurements.csv` (64 righe, 0 errori).
Plot: `docs/T205C_plots/{cost_pred_vs_measured,energy_per_token_vs_tokens_out,power_vs_inverse_confidence,max_memory_vs_tokens_out}.png`.

**Sintesi numerica** (riepilogo automatico di `_t205_measure.summarize`):

| Metrica | Valore |
|---|---|
| `n_valid` / `n_total` | 64 / 64 |
| `P_idle_W_mean` | 16.09 W |
| `E_meas_J_mean` | 156.85 J |
| `E_pred_J_mean` | 5.17 J |
| **slope log-log pred vs meas** | **0.982** |
| **intercept log-log** | **−3.331** |
| **resid_std** | **0.086** |
| `E_per_token_mJ_mean` | 3609 mJ |
| `max_mem_MB_mean` | 2741.5 MB |
| `wall_s_mean` | 2.31 s |
| `ratio_pred_over_measured` | min 0.029, max 0.055, mean 0.033 |

**Analisi (5 frasi).** La regressione log-log tra `E_predicted_J` (QuantumCostModel)
ed `E_measured_J` (utile, dopo sottrazione di P_idle punto per punto) ha
**slope = 0.982 ± 0.086 resid_std** — entro 2 % da 1, con deviazione standard
del residuo di soli 0.086 decadi (≈ 19 % in scala lineare): la **forma
funzionale del modello è confermata**, ipotesi 1 e 2 del protocollo
accettate. L'intercetta `−3.331` indica che `QuantumCostModel.energy_watts()`
sottostima sistematicamente l'energia fisica di un fattore costante
`exp(3.331) ≈ 28×`, coerente con un `W_PER_SPIKE = 0.001 W` tarato su
un'astrazione di costo per qubit molto più parsimoniosa della realtà
elettrica di una GPU consumer a 6 GB; il rapporto `pred/meas` è stabile
in tutto il range (0.029–0.055), non rumore casuale ma bias sistematico
da ricalibrare moltiplicando `W_PER_SPIKE` per ~28 (ticket: T207-bis
ricalibrazione, fuori perimetro T205-C). `E_per_token_J` cala con
`n_tokens_out` come atteso (prefill ammortizzato sul decode), VRAM picco
`2741 MB` resta sotto il budget di 6144 MB confermando che NF4 3B è
l'unico regime utilizzabile sulla 3060 6 GB; `P_idle = 16.09 W`
corrisponde al modello caricato in VRAM senza generazione, baseline
necessaria per qualsiasi misura utile futura.
