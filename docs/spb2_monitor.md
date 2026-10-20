# SpikingBrain 2.0 — Monitor rilascio pubblico HuggingFace

**Status**: monitoring (open loop)
**Data creazione**: 2026-08-12
**Obiettivo**: tenere traccia del rilascio pubblico di SpikingBrain 2.0
su HuggingFace, dove oggi è assente o richiede account cinese.

## 1. Stato al 2026-08-12

- **arXiv**: paper SpikingBrain 2.0 pubblicato (arXiv:2604.22575).
- **HuggingFace**: nessun repo pubblico `BICLab/SpikingBrain-2-*`
  identificato a questa data.
- **ModelScope.cn**: il checkpoint 5B base/instruct/think è presente,
  ma il download richiede un account ModelScope verificato con
  telefono cinese (+86). Procedura fuori portata per la maggior parte
  degli sviluppatori non-residenti.
- **Stub locale**: `StubSpikingBrainV2` (`q_speace/spiking_brain/stub.py`)
  mima la distribuzione di belief più piatta e la plasticità a decadimento
  più rapido di DSSA/MoBA, ma **non** esegue il kernel dual-path reale.

## 2. URL canonici da controllare mensilmente

| Risorsa | URL |
|---|---|
| HuggingFace org | https://huggingface.co/BICLab |
| Repo v1 (7B base) | https://huggingface.co/maujim/spikingbrain-v1-7b-base |
| Ricerca repo v2 | https://huggingface.co/models?search=spikingbrain-2 |
| Paper arXiv | https://arxiv.org/abs/2604.22575 |
| Repo GitHub v2 | https://github.com/BICLab/SpikingBrain-2 |

## 3. Procedura di verifica mensile

Ad ogni primo del mese (o quando si riapre un ticket T-SPB-*):

1. `curl -fsSL https://huggingface.co/api/models?author=BICLab | jq '.[] | {id, lastModified, gated}'`
2. Annotare eventuali nuovi modelli in tabella sotto.
3. Se compare `BICLab/SpikingBrain-2-*-base` pubblico:
   - Aprire ticket `T-SPB-7` (real V2 binding).
   - Adattare `HTTPSpikingBrainClient` per caricare il nuovo endpoint
     (la firma `/think` non cambia).
   - Aggiornare `q_speace/spiking_brain/factory.py` per selezionare
     il backend V2 reale quando disponibile.
4. Se invece il modello resta solo ModelScope: annotare l'ostacolo
   e rinviare al mese successivo.

## 4. Workaround finché V2 è bloccato

- Stub V2 in numpy puro (`StubSpikingBrainV2`).
- Backend Qwen2.5-3B-Instruct NF4 via T207 (opera sullo stesso
  contratto HTTP, indipendente dal backend).
- Forma funzionale `QuantumCostModel` (T205-C, slope 0.982) già
  validata sul backend Qwen 3B; la firma numerica sarà trasferibile
  al V2 reale senza modifiche al `SpikingBrainCortex`.

## 5. Storico verifiche

| Data | Esito | Note |
|---|---|---|
| 2026-08-12 | Nessun rilascio pubblico | ModelScope solo, account +86 richiesto |

## 6. Trigger di chiusura

Questo documento resta aperto fino a quando uno dei seguenti non si
verifica:

- [ ] Rilascio pubblico HuggingFace di `BICLab/SpikingBrain-2-5B-base`.
- [ ] Decisione architetturale di abbandonare SpikingBrain 2.0 in
      favore di un altro substrato (es. SpikeGPT, RWKV-7, BrainCog).
- [ ] Account ModelScope.cn con verifica +86 ottenuto → download
      manuale → conversione a repo HF interno.

---

**Perché esiste**: SpikingBrain 2.0 (DSSA, MoBA, dual-path FP8/int8) è
l'unico substrato corticale con separazione esplicita "high-confidence
FP8 / low-confidence INT8" che potrebbe agire da segnale di
metacognizione computazionale — non biologica — in SPEACE. Finché non
è eseguibile, il percorso resta modellato ma non misurato sul backend
reale.