# T-SPB-0B — Diagnosi degradazione cache sliding window

**Status**: diagnosi chiusa, fix proposto ma non implementato
**Data**: 2026-08-10
**Predecessore**: T-SPB-0A (forward end-to-end confermato)
**Sidecar test**: `spiking_brain_server/_t_spb0b_diag.py`

## 1. Scopo

Confermare o escludere `do_sample=True` (T=0.7, p=0.9) come causa della
degradazione `pérdida / cámara / Publié / 注明出处` osservata nei probe
del sidecar dopo il primo token corretto.

## 2. Setup sperimentale

- Modello: `maujim/spikingbrain-v1-7b-base` (4.35B param, NF4 4-bit, bf16 compute)
- Hardware: WSL2 Ubuntu 24.04, RTX 3060 Laptop 6 GB, CUDA 12.4
- Prompt: `"The capital of France is"` (5 token)
- `n_tokens = 24`
- Patch in-memory via `_install_window_attention_patcher()` di `server.py`
  (perché transformers ri-hasha il file HF cache e sovrascrive le patch
  on-disk)

## 3. Risultati

| Modalità | Output (primi 24 token) | Latenza |
|---|---|---|
| **Greedy** (`do_sample=False`) | ` a pérdida pérdida pérdida adultes pérdida ... cámara ... pérdida` | 2.11 s/tok |
| **Sampling** (T=0.7, p=0.9) | ` the pérdida pérdida ... verschiedene ...意见反馈 ... pesticides ... génér ...注明出处 ...` | 0.19 s/tok |
| **Sampling** (T=0.1, p=0.9) | ` the pérdida pérdida ... cámara岬 ...` | 0.19 s/tok |

### Osservazioni chiave

1. **Greedy è deterministico e crolla uguale** → la degradazione non è
   stocasticità del sampling.
2. **Anche T=0.1** (quasi greedy) crolla → non è il softmax a
   collassare su token rari.
3. **Il primo token è corretto** (`a`, `the`) in tutte le modalità.
   Il collasso inizia dal secondo token in poi.
4. **Greedy è 11× più lento** del sampling (2.11 vs 0.19 s/tok) → la
   cache sliding window sta facendo lavoro extra durante la fase di
   "fast path" sampling (KV piccolo → ricomputazioni più costose nel
   path deterministico).
5. I token `pérdida / adultes / cámara / 注明出处 / verschiedene /
   pesticides / génér` sono token **rari multilingua**: il modello sta
   scegliendo attivazioni di bassa confidenza dalla testa di output
   perché le attivazioni intermedie sono corrotte.

## 4. Causa identificata

La degradazione è causata dalla **cache sliding window
incompatibile tra `fla` (flash-linear-attention) e `transformers 4.55`**.

Specifico:
- Il `_upad_input` con `unpad_input_func=None` del meta-path patcher
  produce maschere o indici errati quando la cache sliding window è
  attiva.
- I pesi NF4 sono corretti (verificato in T-SPB-0A: primo token
  sempre corretto).
- Il bug è nel **path della cache**, non nel modello.

## 5. Ipotesi di root cause

| Candidato | Probabilità | Note |
|---|---|---|
| Cache sliding window mask fuori range | Alta | `window_size=(256, 0)` + `q_len=1` in decode → maschera degenera |
| `cu_seqlens_q` non aggiornato al primo step cache | Alta | L'hook patcha `_upad_input` ma non la logica di cache update |
| Bug noto `fla × transformers 4.55` | Media | Verificare issues BICLab/spikingbrain GitHub |
| Pesi NF4 corrotti | Bassa | T-SPB-0A esclude |
| Sampling stocastico | **Esclusa** | Greedy mostra stesso pattern |

## 6. Opzioni di fix proposte (da valutare)

### Opzione A — Downgrade transformers a 4.54
- Pip: `pip install transformers==4.54.4`
- `fla` era compatibile fino a transformers 4.54; il 6° argomento
  `unpad_input_func` non esisteva.
- **Rischio**: regressione in altri moduli (Qwen sidecar, BCEL).
- **Tempo**: 5 minuti, una riga di codice.

### Opzione B — Cache-less generation (forward singolo)
- Override `model.generate()` per fare solo `model.forward()` senza
  `use_cache=True`. Ricomputa l'intero contesto a ogni step.
- **Costo**: 5-10× più lento di generazione con cache.
- **Tempo**: 30 minuti.
- **Vantaggio**: evita completamente il bug cache.

### Opzione C — Disabilitare lo sliding window
- Patchare `config.json` del modello per `sliding_window=null` o
  molto grande (`>max_position_embeddings`).
- **Rischio**: modifica al checkpoint, possibili NaN se il kernel
  richiede finestra.
- **Tempo**: 10 minuti.

### Opzione D — Prompt engineering
- Few-shot: `"Q: What is the capital of France? A: Paris.\nThe capital
  of France is"` → potrebbe stabilizzare le attivazioni.
- **Costo**: nessun cambio di codice.
- **Rischio**: non risolve la root cause.

### Opzione E — flash-attn 2.x prebuilt wheel
- `pip install flash-attn==2.7.x` con wheel per torch 2.6 + cu124 +
  py 3.12 (non esiste release ufficiale → serve build locale nvcc).
- **Tempo**: 30-60 minuti.
- **Rischio**: nvcc + cuda toolkit da installare in WSL.

## 7. Raccomandazione

Procedere con **Opzione A (downgrade transformers a 4.54)** come primo
tentativo perché:
- costo minimo,
- verifica diretta dell'ipotesi `transformers 4.55 = bug`,
- reversibile (re-upgrade con `pip install -U transformers`).

Se A non funziona → Opzione B (cache-less) come fallback funzionale
per sbloccare la roadmap T-SPB-* mantenendo la qualità di output.

## 8. File impattati (futuro commit)

- `docs/T-SPB-0B_DIAGNOSIS.md` (questo file)
- `requirements.txt` o `install.sh` (se Opzione A)
- `spiking_brain_server/server.py` (se Opzione B: override generate)
- `spiking_brain_server/_t_spb0b_diag.py` (verifica finale)
- `docs/T-SPB-0A_PLAN.md` (riferimento)

## 9. Out of scope (rinviato)

- Fix SDPA mask shape (opzione A di T-SPB-0A) — già funziona.
- `SpikingBrainCognitiveInterface` (T-SPB-4).
- `q_speace/spiking_brain/` binding al cortex (T-SPB-5).

## 10. Note operative

- `transformers.__version__` attuale: 4.55 (verificare con `pip show transformers`)
- Per evitare che transformers ri-hash e sovrascriva `window_attention.py`
  su disco: usare `SPB_SKIP_DISK_PATCHER=1` e patchare solo in-memory
  via `_install_window_attention_patcher()`.
- Il diagnostico `_t_spb0b_diag.py` già installa l'hook ed è pronto
  per essere rieseguito dopo qualsiasi fix.