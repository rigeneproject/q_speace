# W8ASpike-7B int8 — Procedura di acquisizione da ModelScope.cn

**Status**: blocked on operator credentials
**Data creazione**: 2026-08-12
**Vincolo**: account ModelScope verificato con telefono +86

## 1. Cosa è W8ASpike-7B int8

Variante quantized a 8 bit del checkpoint
`maujim/SpikingBrain-7B-base` pubblicata su ModelScope.cn
(dove è canonical, non su HuggingFace). Rispetto alla versione
float16/BF16 già clonata in
`speace_anemos_spikingbrain/SpikingBrain-7B-main/`, occupa
**~7 GB** (contro ~14 GB) — comunque sopra i 6 GB della RTX 3060
Laptop, quindi va comunque caricato in NF4 o spezzato.

## 2. Perché ci interessa

- Drop-in replacement del sidecar `spiking_brain_server/server.py`.
- Kernel W8ASpike in `W8ASpike/quant_linear.py` (int8 × spike sparse)
  è il riferimento architetturale originale che il protocollo
  `SpikingBrainCognitiveInterface` modella — eseguirlo nativamente
  (anziché lo stub numpy) chiude il cerchio T205 → T-SPB-4.
- Int8 riduce la perdita di qualità rispetto a NF4 4-bit (T-SPB-0A).

## 3. Procedura (richiede utente)

1. **Ottenere un account ModelScope.cn verificato +86**:
   - https://www.modelscope.cn → Sign Up → Bind Phone (+86).
   - Richiesto: numero cinese o account Alipay/WeChat con KYC.
   - Tempo: minuti se hai già numero, ore se devi procurartelo.

2. **Installare ModelScope SDK**:

   ```bash
   pip install modelscope
   ```

3. **Login e download**:

   ```python
   from modelscope import snapshot_download
   path = snapshot_download(
       "AI-ModelScope/SpikingBrain-7B",
       revision="int8",       # se esiste; altrimenti 'master'
       cache_dir="/mnt/c/Users/rober/Desktop/Q-SPEACE/q_speace/models",
   )
   print(path)
   ```

4. **Verificare struttura**:

   ```
   models/AI-ModelScope/SpikingBrain-7B/
   ├── config.json
   ├── tokenizer.json
   ├── tokenizer_config.json
   ├── model.safetensors           # o model.bin
   ├── model-00001-of-00003.safetensors  # shards
   ├── W8ASpike/quant_linear.py    # kernel int8
   └── ...
   ```

5. **Riconfigurare `server.py`**:

   ```python
   # in spiking_brain_server/server.py
   MODEL_REPO = os.environ.get(
       "SPB_MODEL_PATH",
       str(REPO_ROOT / "models" / "AI-ModelScope" / "SpikingBrain-7B"),
   )
   ```

6. **Test sidecar**:

   ```bash
   python server.py --port 8001 &
   curl http://localhost:8001/health
   # {"ready": true, "model": "W8ASpike-7B-int8", "vram_mb": ~5800}
   ```

## 4. Workaround se l'account +86 non è ottenibile

- Mantenere l'attuale sidecar NF4 4-bit con bug cache sliding
  window; eseguire **solo** in cache-less mode (T-SPB-0B fix,
  10× più lento ma testo pulito).
- Backend Qwen 3B (T207) resta come fallback production-ready
  sullo stesso contratto HTTP.
- Stub numpy (`StubSpikingBrain` / `StubSpikingBrainV2`) per test/CI.

## 5. Rischi / note di licenza

- License BICLab per `SpikingBrain-7B`: verificare su
  https://arxiv.org/abs/2509.05276 e sul repo HuggingFace.
  Ad oggi (2026-08-12) la license è research-only sul paper; il
  repo HF è `apache-2.0` o simile — controllare prima di qualsiasi
  uso commerciale.
- ModelScope applica le stesse condizioni del repo HuggingFace,
  ma con EULA cinese: di fatto identico per il download.
- L'uso del checkpoint int8 NON dà diritto a ridistribuirlo
  convertito in NF4 o altri formati senza il consenso esplicito
  degli autori.

## 6. Cosa NON è ancora pronto

- Flag `--no-cache` in `server.py` (anche qui serve per evitare la
  degradazione cache sliding window).
- Test di integrazione `pytest tests/test_spiking_brain_integration.py`
  che verifichi che il client HTTP punti al nuovo endpoint e che
  `backend_name == "W8ASpike-7B-int8"` o equivalente.
- Aggiornamento `q_speace/spiking_brain/factory.py` se si vuole che
  `make_spiking_brain()` selezioni automaticamente il backend
  in base a `Q_SPEACE_BRAIN_MODEL=int8`.

## 7. Stato task

| Sotto-task | Stato |
|---|---|
| Account +86 ottenuto | ❌ pending utente |
| Modello scaricato in `models/` | ❌ pending account |
| Sidecar aggiornato per int8 | ❌ pending modello |
| Test integrazione | ❌ pending sidecar |
| `factory.py` seleziona int8 | ❌ pending test |

**Cosa blocca la chiusura**: account utente con telefono +86
verificato su ModelScope.cn. Nessuna riga sopra è eseguibile da
questa sessione senza tale credenziale.