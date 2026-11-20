# T222 - Codec NCM coarse-to-fine: Fase 0 (solo codec)

**Status:** proposta sperimentale. Solo la **Fase 0** è approvata come perimetro
di lavoro; le Fasi 1-2 sono *Future work - non approvato*.
**Data:** 2026-11-20.
**Ambito:** valutazione di un codec a quantizzazione residua multiscala
(coarse-to-fine) accanto a `dynamic_spikes`, su segnali sintetici.
**Riferimento esterno:** Kumbong, Khare, Arora, Mirhoseini, Re, "Next-Concept
Modeling: Fast, Parallel Coarse-to-Fine Text Generation", arXiv:2610.14162
(9 ottobre 2026). T222 **non** importa il generatore, il tokenizer o i pesi NCM.

**Non-obiettivi (vincolanti):**
- nessuna claim di AGI, comprensione concettuale, coscienza o vantaggio quantistico;
- nessun generatore gerarchico, nessun training di rete, nessun confronto di NFE
  in Fase 0 (vedi Fase 1, non approvata);
- nessuna integrazione AACM (Fase 2, non approvata);
- nessuna modifica a `q_speace/quantum/`;
- nessun backend quantistico reale, nessuna dichiarazione che un gate esecutivo
  su backend reale sia attivo.

---

## 1. Questione falsificabile (Fase 0)

> Su segnali sintetici held-out, un codec a quantizzazione residua multiscala
> conserva l'informazione richiesta da una sonda a valle, quantifica il degrado
> dovuto alla riduzione dei livelli e alla corruzione dei codici, e produce un
> bilancio di costo riproducibile rispetto alla baseline `dynamic_spikes`.

La Fase 0 misura **proprietà del codec**, non capacità generative. Un buon errore
di ricostruzione non prova che il codec conservi l'informazione utile al
comportamento del sistema: per questo la sonda a valle è parte del DoD.

### 1.1 Cosa non viene dimostrato in Fase 0

- che il sistema sappia **predire** codici non ancora noti (richiede un generatore);
- che il costo per valutazione del codec sia comparabile agli NFE del transformer NCM;
- che "concetto" significhi idea, semantica o facoltà cognitiva;
- che la struttura multiscala riduca working set o joule fisici in generale.

---

## 2. Stato verificato del repository (2026-11-20)

Elementi citati dalla specifica, verificati nel workspace corrente:

| Elemento | Posizione | Comportamento rilevante |
|---|---|---|
| `dynamic_spikes` | `q_speace/spiking/encoder.py:36` | soglia `mean(|x|)/k`, output intero sparso, `num_spikes`, `sparsity` |
| `LevelSignature` | `q_speace/fractal_qca_cascade.py:24` | firma coarse-grained `(coherence_phi, entropy_s, sigma)` |
| Accoppiamento tra livelli | `q_speace/fractal_qca_cascade.py:6-9, 89-92` | solo tramite firme coarse-grained |
| `coherence_phi` | `q_speace/fractal_qca.py:94-99` | `1 - S/max_entropy` |
| `Sevo` | `q_speace/metabolism/cognitive_cost_model.py:68` | `Sevo = DeltaU / DeltaS_info`, target `> 1.5` |
| Costo energetico | `q_speace/metabolism/cognitive_cost_model.py:49-65` | stima parametrica, non misura fisica |
| `noise_model` | `q_speace/genome/quantum_genes.py:31,38` | campo di configurazione validato |
| Invariante backend | `docs/T217_SAFE_ASSIMILATION_LIFECYCLE_SPEC.md` sez. 2.3 | invariante documentato |

**Nota sul gate:** `noise_model` è oggi un campo di configurazione; il backend
reale (T5) non è implementato. T222 preserva l'invariante documentato e **non**
dichiara che un controllo esecutivo sul backend sia attivo.

Nessun modulo codec NCM è presente nel repository alla data della specifica.

---

## 3. BCEL gate

| Concetto | Classe | Regola digitale mantenuta |
|---|---|---|
| "Concetto" come idea/semantica | **accidentale** | rimosso: resta un codice discreto appreso che può conservare struttura globale |
| Quantizzazione residua multiscala | **funzionale** | gerarchia di codebook residui, `x_k = x_{k-1} - reconstruction_k` |
| Predizione parallela per livello | **funzionale** | fuori perimetro Fase 0; prevista solo come interfaccia futura |
| Coarse-to-fine come cognizione | **accidentale** | rimosso: è un ordinamento di granularità, non un processo mentale |
| `coherence_phi` come stop del raffinamento | **funzionale, ipotesi** | valutato solo in Fase 1, mai come garanzia di correttezza |

La voce va registrata in `q_speace/bcel/catalog.py` prima di qualsiasi
implementazione oltre la Fase 0.

---

## 4. Architettura Fase 0

```
segnale x (numpy)
    |-- baseline A: dynamic_spikes(x) ---------> readout -> sonda
    |-- codec B:   multiscale residual quantizer
    |                 -> codici {c_1..c_K}
    |                 -> decoder -> x_hat -> sonda (valutazione ricostruzione)
    |                 -> readout -> sonda (confronto con A)
    '-- ibrida C:  dynamic_spikes(x) -> codec residuo -> readout -> sonda
```

Il codec è un **adattatore opzionale** accanto a `dynamic_spikes`; non lo
sostituisce e non ne modifica il comportamento di default.

### 4.1 Moduli previsti (solo dopo approvazione della Fase 0)

- `q_speace/spiking/ncm_codec.py` - quantizzatore residuo, codebook, encode/decode.
- `tests/test_ncm_codec.py` - test di ricostruzione, ablazione, corruzione, probe.

Nessuna dipendenza nuova: solo `numpy`.

---

## 5. Confronto tra le tre configurazioni

La sonda a valle deve ricevere un **readout della stessa forma** in tutte le
configurazioni, altrimenti il confronto non è valido.

| Config | Input alla sonda | Nota |
|---|---|---|
| A - spike | vettore di statistica spike (rate per canale, conteggi, sparsity) | uno spike non ricostruisce direttamente `x`: va dichiarato il readout, non assunto |
| B - codec | reconstruction `x_hat` (per la prova di ricostruzione) e readout dai codici | due valutazioni distinte, registrate separatamente |
| C - spike+codec | readout dal codec applicato agli spike | verifica se la combinazione conserva informazione utile |

Regola: se un readout non è definibile per una configurazione, la configurazione
va esclusa o marcata "non confrontabile", non adattata a posteriori.

---

## 6. Preregistrazione (obbligatoria prima del run di valutazione)

Le soglie si fissano **prima** del run di valutazione e si salvano in un file
versionato, ad esempio `docs/T222_PREREG.json`. Campi minimi:

```json
{
  "seed_split": 0,
  "seed_codebook": 0,
  "n_train": null,
  "n_eval": null,
  "distributions": [],
  "levels_K": [],
  "codebook_sizes": [],
  "holdout_rule": "codebook e soglie costruiti senza segnali di eval",
  "probe": {"name": null, "metric": null, "threshold": null},
  "degradation": {"max_relative_loss_per_level": null},
  "cost": {"max_relative_cost_vs_baseline": null},
  "corruption": {"levels_tested": [], "max_relative_loss": null},
  "calibration_run_id": null,
  "eval_run_id": null
}
```

### 6.1 Regola di calibrazione

Se i dati non bastano a fissare una soglia:

1. si esegue un **run di calibrazione** su una partizione separata;
2. si aggiorna il prereg **prima** del run di valutazione;
3. il run di calibrazione **non** può dichiarare superato il DoD.

Nessuna soglia può essere scelta dopo aver visto i risultati di valutazione.

### 6.2 Partizione held-out riproducibile

- split deterministico da seed documentato;
- distribuzioni e generatori dei segnali dichiarati nel prereg;
- i codebook e le soglie sono costruiti **solo** su train/calibration;
- i segnali di valutazione non contribuiscono a codebook, normalizzazioni o
  iperparametri;
- il file di split (seed, indici, hash) è versionato con la specifica.

### 6.3 Protocollo di blocco (`lock_sha256`)

Il blocco è **per sezione** (`pre_calibration`, `pre_evaluation`), non per file:
così `pre_evaluation` può essere completata dopo la calibrazione senza
invalidare `pre_calibration`.

Serializzazione canonica:

- UTF-8 senza BOM;
- `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)`;
- input: la sezione come oggetto JSON, con il solo campo di **primo livello**
  `lock_sha256` rimosso;
- tutti gli altri campi partecipano all'hash, inclusi `locked` e i campi annidati.

Procedura:

1. completare la sezione;
2. impostare `locked: true`;
3. calcolare `sha256(canonical_json(section))` e scrivere l'esadecimale in
   `lock_sha256`;
4. verifica: rimuovere `lock_sha256`, ri-serializzare, ricalcolare l'hash e
   confrontare in tempo costante.

Campi esclusi: esclusivamente `lock_sha256` della sezione. `pre_calibration` non
include `pre_evaluation` e viceversa. L'integrità dello split held-out non è
coperta dalla sezione: è coperta da `heldout.manifest_sha256`.

Implementazione: `q_speace/spiking/prereg_lock.py`.

---

## 7. Registri di metrica (separati)

| Registro | Contenuto | Obbligo |
|---|---|---|
| Ricostruzione | errore per livello, errore totale, confronto con baseline | sempre |
| Compito | metrica della sonda su held-out | sempre |
| Degrado | perdita con `K' < K` livelli | sempre |
| Corruzione | perdita con codici alterati per livello | sempre |
| Costo interno | operazioni, tempo, `Sevo` | sempre |
| Joule stimati | `QuantumCostModel.energy_joules` | sempre, etichettati "stimati" |
| Joule misurati | misura fisica con metodo e intervallo | "non misurati" se assenti |

### 7.1 Sevo e DeltaS_info

`Sevo = DeltaU / DeltaS_info`:

- `DeltaS_info <= 0` e `DeltaU > 0` -> `-inf` (passo disordinante, rifiutato);
- `DeltaS_info <= 0` e `DeltaU <= 0` -> `0.0`;
- valori prossimi a zero vanno riportati con epsilon e numero di casi;
- il conteggio dei casi `DeltaS_info <= 0` fa parte del report.

Una variazione di Sevo o di NFE non dimostra una variazione di joule: i tre
registri non vanno mai fusi in un unico punteggio.

---

## 8. Test obbligatori

1. **Ricostruzione**: errore su held-out, per livello e totale.
2. **Ablazione livelli**: degrado con meno livelli, con soglia preregistrata.
3. **sensibilità alla corruzione**: alterazione di codici a livelli diversi e
   misura del degrado. Questo test misura la **sensibilità del codec**; la
   robustezza ottenuta addestrando il generatore con codici sostituiti resta
   attività futura non approvata.
4. **Sonda a valle**: perturbazione da rilevare o vincolo da soddisfare, con
   readout confrontabile tra A/B/C.
5. **riproducibilità**: stesso seed e stesso split producono lo stesso report.
6. **Non-regressione**: `dynamic_spikes` e i suoi test restano invariati.

---

## 9. Criteri di accettazione (DoD Fase 0)

La Fase 0 è superata solo se, su held-out e con soglie preregistrate:

- la sonda a valle supera la soglia dichiarata in almeno una configurazione
  codec-based, con readout comparabile alla baseline;
- il degrado con meno livelli resta entro la soglia preregistrata;
- la sensibilità alla corruzione è quantificata e riportata per livello;
- il costo interno è riproducibile e confrontato con la baseline;
- Sevo, joule stimati e joule misurati sono registrati separatamente, con
  "non misurati" dove applicabile;
- il report è ricostruibile da codice, seed, split e configurazione versionati.

Un run di calibrazione, un risultato inconcludente o un readout non comparabile
**non** soddisfano il DoD.

---

## 10. Invarianti

1. Nessuna affermazione di coscienza quantistica o soggettivita.
2. L'entanglement resta solo una risorsa computazionale; nessun uso comunicativo.
3. Nessun backend quantistico reale senza `QuantumGeneSet.noise_model`
   configurato e gate energetico/Sevo. T222 non implementa e non dichiara attivo
   tale gate.
4. Il codec non modifica `q_speace/quantum/` e non introduce dipendenze.
5. Gli output generativi, se introdotti in futuro, restano proposte non fidate.
6. Gli esiti favorevoli valgono solo per il perimetro e l'artefatto qualificati.

---

## 11. Future work - non approvato

Queste sezioni descrivono direzione, non autorizzazione. Richiedono una nuova
decisione esplicita e una specifica separata.

### Fase 1 - generatore gerarchico (non approvato)

Solo dopo Fase 0 positiva: generatore che predice i codici livello per livello,
confronto di NFE, latenza ed energia con una baseline **funzionante** sullo
stesso compito (non uno stub). Politiche di stop a confronto: livelli fissi,
soglia `coherence_phi`, errore di validità. Metrica decisionale: livelli
risparmiati rispetto alla perdita di qualità, inclusi gli arresti prematuri.
La robustezza da training con codici corrotti appartiene a questa fase.

### Fase 2 - integrazione AACM (non approvato)

Solo se la Fase 1 mostra un guadagno rispetto alle alternative già presenti.
Richiede BCEL aggiornato, test dedicati e nessuna modifica al layer quantistico.
`coherence_phi` resta un segnale sperimentale, non una garanzia.

---

## 12. Stato delle attività

| attività | Stato |
|---|---|
| Specifica Fase 0 | questa proposta |
| Preregistrazione | bozza in `docs/T222_PREREG.json`; sezioni non ancora bloccate |
| Implementazione codec | `q_speace/spiking/ncm_codec.py` |
| Blocco prereg | `q_speace/spiking/prereg_lock.py` (protocollo sez. 6.3) |
| Harness calibrazione | `q_speace/spiking/ncm_calibration.py`; solo train+calibration |
| Test | `tests/test_ncm_codec.py`, `tests/test_ncm_calibration.py`, `tests/test_prereg_lock.py` |
| Run ufficiale di calibrazione | non eseguito: richiede il blocco di `pre_calibration` |
| Registro task | `docs/T222_TASKS.md` |
| Fase 1 | non approvata |
| Fase 2 | non approvata |

### 12.1 Verifica corrente (2026-11-20)

```bash
python -m pytest tests/test_ncm_codec.py tests/test_ncm_calibration.py tests/test_prereg_lock.py -q --no-cov
python -m ruff check q_speace/spiking q_speace/bcel/catalog.py
python -m mypy q_speace/spiking/ncm_codec.py q_speace/spiking/ncm_calibration.py q_speace/spiking/prereg_lock.py
```

Esito: 27 test T222 passati; suite completa 552 passed, 3 skipped; `mypy`
pulito sui tre moduli. Il run ufficiale resta bloccato finché `pre_calibration`
non è completata e bloccata secondo la sezione 6.3.
