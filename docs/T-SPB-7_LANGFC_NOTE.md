# T-SPB-7 — Architettura vs attività: la LangFC come evidenza empirica

**Status**: agentic (planning)
**Data**: 2026-08-24
**Predecessore**: T-SPB-0A (forward confermato), T-SPB-0B (cache-less), T-SPB-2 (harness pronto), T-SPB-3-C (audit trail shipped)
**Successore previsto**: T-SPB-8 (Cognitive Network Tomography), T-SPB-9 (Functional Network Plasticity Operator)

> **Epistemic note (2026-08-24).** Questo addendum NON
> introduce nuovi claim di natura biologica sul progetto
> SPEACE. È una nota di lavoro che: (1) registra un dato
> empirico recente rilevante per il modello architetturale;
> (2) precisa la *distinzione architettura / attività* che
> il modello già assume implicitamente; (3) identifica un
> gap specifico (stabilità longitudinale) da colmare in
> T-SPB-10. Non è un'analisi secondaria del paper né una
> review della letteratura: è un allineamento tra la
> letteratura biologica più recente e la terminologia
> già usata in `bcel/catalog.py`, `routing.py`,
> `spiking_brain/cortex.py`.

## 1. Riferimento bibliografico

Shain, C. & Fedorenko, E. (2026). *A language network in the
individualized functional connectomes of 1199 human brains doing
arbitrary tasks.* **Nature Communications** 17, article 8180.
DOI: 10.1038/s41467-026-75745-8.
URL: https://www.nature.com/articles/s41467-026-75745-8

Dati verificati dal paper:

- **1.957 sessioni fMRI** da **1.199 individui unici** (≈ 1.63
  sessioni/individuo in media). Non "1.900 scansioni": ogni
  sessione può contenere più acquisizioni.
- Metodo: **individualized functional connectomics (iFC)**, due
  ordini di grandezza in più rispetto a qualunque studio iFC
  precedente sul linguaggio.
- Risultato principale: identificata una rete (**LangFC**) che è
  - *left-hemisphere-dominant e frontotemporale*
  - **stabile entro individuo** ma **variabile tra individui**
  - **selettiva per il linguaggio** e *doubly dissociable* da reti
    vicine
  - **robusta alla granularità di parcellazione**
  - **rilevabile anche da task non linguistici** e da dati fMRI
    arbitrari

Fonte secondaria per il comunicato stampa: EurekAlert!
"Potential language-specific brain network identified"
(https://www.eurekalert.org/news-releases/1139675).
Dati e codice pubblicati: Stanford Digital Repository
(https://doi.org/10.25740/xj129pm0893),
codice generale (https://github.com/coryshain/parcellate),
codice specifico (https://github.com/coryshain/langlocFC).

## 2. La distinzione architettura / attività

Il risultato più rilevante per SPEACE non è la *localizzazione*
della rete linguistica — è la separazione tra due livelli che la
letteratura classica spesso confondeva:

```
LIVELLO 1 — ARCHITETTURA FUNZIONALE
    pattern persistente di connettività funzionale (iFC)
    identificabile indipendentemente dall'attivazione momentanea
    stabile entro individuo, variabile tra individui

LIVELLO 2 — ATTIVITÀ MOMENTANEA
    engagement delle aree durante un compito specifico
    transitorio, task-dipendente, misurato da BOLD signal
    classico
```

Il paper mostra che LangFC esiste come *configurazione* (livello
1) anche quando il soggetto non sta svolgendo alcun compito
linguistico (livello 2). Questa separazione era già implicita in
Fedorenko et al. (2010) — le aree linguistiche sono
*task-negative* in compiti non linguistici — ma la novità è che
*la rete come pattern di connettività* è ora identificabile senza
un language localizer dedicato.

## 3. Rilevanza per SPEACE

Il modello SPEACE già assume implicitamente questa distinzione
in tre punti documentati:

1. **`q_speace/bcel/catalog.py:172`** — la voce "Brain area as
   cognitive subdivision" (functional) dichiara che
   `SpikingBrainCortex` è *una* area cognitiva (think / reason /
   verbalize / metacognize), con ILF + Sevo + cost gate come
   mediatore talamico. Quindi la modularità è *già* espressa
   come configurazione distribuita, non come posizione fissa.

2. **`q_speace/routing.py:103-125`** — `EventRouter` instrada
   `text_input` all'area "language", `quantum_state`
   all'area "quantum", `spike_train` all'area "spiking". Le aree
   sono *configurazioni funzionali* identificate dal *tipo di
   evento*, non localizzate staticamente. Il default fallback è
   "native" (orchestrator general-purpose tick). Quindi
   l'architettura è *già* un set di reti funzionali attivate da
   pattern di stimolo, non moduli a slot fisso.

3. **`q_speace/spiking_brain/cortex.py:50-261`** — il
   `SpikingBrainCortex.tick()` orchestra cost → Sevo → coherence
   → ILF update come una *pipeline configurabile*, non una
   sequenza cablata.

### 3.1 Cosa il paper *NON* dice (over-claim da evitare)

- Il paper **NON** dice che "ogni funzione cognitiva è una rete
  distribuita senza modularità". Dice che LangFC è *selettiva*
  e *doubly dissociable* da reti vicine. La modularità resta;
  cambia la granularità (da "area di Broca" a "configurazione
  di connettività identificabile individualmente").
- Il paper **NON** dimostra stabilità longitudinale (mesi /
  anni). Lo scope è cross-task, non cross-time. Questo è un
  gap reale — vedi §5.
- Il paper **NON** è una prova che SPEACE sia "come il
  cervello". È un dato biologico che restringe lo spazio delle
  architetture cognitive plausibili a quelle in cui *esiste
  una distinzione architettura / attività*. SPEACE soddisfa
  questa condizione per costruzione; non per analogia.

## 4. Implicazione operativa: perché serve T-SPB-8

L'audit trail `BrainAuditLog` (T-SPB-3-C, shipped) registra già
per ogni `apply_to_ilf`:

- `agent_id`, `backend`, `prompt_hash`, `result_text_excerpt`,
  `result_confidence`, `belief` (vettore),
- `coherence_phi_pre`, `coherence_phi_post`, `sevo`,
  `energy_w`, `approved`, `reason`.

Questo è un audit **passivo**: registra ciò che è successo, non
ricostruisce *la struttura funzionale* che ha reso possibili quei
cambiamenti. Il paper Shain & Fedorenko mostra che la struttura
*può essere identificata anche senza un task dedicato* — quindi
è lecito chiedersi: può essere identificata anche *dall'audit
log di operazione normale*?

Questa è la domanda operativa che motiva **T-SPB-8 — Cognitive
Network Tomography**: produrre una `FunctionalNetworkMap`
ricostruita da co-attivazioni registrate nel JSONL, senza
iniettare task linguistici dedicati. La analogia con la LangFC
biologica è suggestiva ma **non va elevata a parità di
metodo**: Shain & Fedorenko misurano correlazioni BOLD tra
voxel anatomici; la tomography SPEACE misurerà co-attivazione
tra aree software (routing targets, brain areas BCEL). Sono
*entrambe* mappe di rete funzionale; sono *diversi* i segnali
fisici sottostanti.

## 5. Gap: stabilità longitudinale

Il paper copre detection cross-task ma **non** la stabilità
della rete su scale temporali lunghe (settimane, mesi). Questo
è rilevante per due ragioni in SPEACE:

1. **Diagnostica**: se la FunctionalNetworkMap ricostruita da
   T-SPB-8 *drifts* tra sessioni, è un indicatore che il
   sistema non ha ancora trovato una configurazione stabile
   (rumore plastico >> segnale plastico).
2. **Confronto con il dato biologico**: nel cervello umano, la
   LangFC è "stabile entro individuo" — è esattamente la
   proprietà che rende la network-detection senza localizer
   *utile in pratica* (neurochirurgia, neuroprotesi). Se
   SPEACE non avesse una proprietà analoga, la tomography
   sarebbe inutile a fini diagnostici.

**T-SPB-10 — Studio stabilità longitudinale reti cognitive**
(misurato via Jaccard overlap tra `FunctionalNetworkMap` a
sessioni 1, 100, 500, 1000 in simulazione sintetica) è
progettato per colmare questo gap. Non è una replica del
dato biologico; è una verifica che lo strumento diagnostico
abbia senso prima di usarlo in produzione.

## 6. Ancoraggio ad AACM (Rule 7 e Rule 10)

La distinzione architettura / attività si lega naturalmente a
due regole del paper AACM (`docs/aacm_paper_en.md`):

- **Rule 7 (stratified legitimation)** richiede che l'ammissione
  di una decisione sia sostenuta da *K ≥ 2 canali indipendenti*
  di evidenza. La LangFC, identificata da task non linguistici,
  è un *secondo canale* di evidenza per la presenza di una
  capacità cognitiva — distinto dal canale "il modello parla".
  Due canali indipendenti, evidence kinds distinti: la regola è
  soddisfatta per costruzione.
- **Rule 10 (distributed control redundancy)** richiede
  `Omega ≥ Omega_min` come invariante meccanico. Se la
  FunctionalNetworkMap mostra che *una sola area* (es. solo
  "language") riceve tutto il routing, `Omega → 0` e il sistema
  è Rule-10-fragile. La tomography è quindi anche uno
  *strumento di audit di Rule 10*.

## 7. Cosa NON è in questo addendum

- **Nessuna modifica al codice.** Questo è un addendum
  documentale. Le modifiche operative sono in T-SPB-8, T-SPB-9,
  T-SPB-10.
- **Nessun claim su analogia cervello-SPEACE.** Il paper
  fornisce *evidenza biologica* per una proprietà
  architetturale (architettura distinta da attività). SPEACE
  soddisfa questa proprietà per costruzione; non per
  corrispondenza neurologica. Il BCEL rule "no claim of
  consciousness / subjective thought" (vedi
  `bcel/catalog.py:86-88`) rimane intatto.
- **Nessuna generalizzazione cross-substrate.** Il paper copre
  il linguaggio; non tutte le funzioni cognitive. La distinzione
  architettura/attività è *una* proprietà che Shain & Fedorenko
  mostrano per il linguaggio; non è dimostrata per ogni
  funzione cognitiva.

## 8. File impattati

- `docs/T-SPB-7_LANGFC_NOTE.md` — questo file (nuovo).
- `docs/T205_status.md` — roadmap aggiornata per includere
  T-SPB-7 / 8 / 9 / 10.
- Cross-reference futuri: `T-SPB-8_LANGFC_NOTE.md` (quando
  T-SPB-8 sarà implementato) dovrà citare questo addendum come
  premessa architetturale.

## 9. Out of scope (rinviato)

- Studio sperimentale della stabilità longitudinale della
  LangFC biologica (richiede dataset fMRI longitudinali —
  es. HCP, UK Biobank — e accesso a infrastructure di
  neuroimaging non disponibile nel progetto).
- Confronto quantitativo tra `FunctionalNetworkMap` SPEACE e
  LangFC biologica (richiede definizione di una metrica di
  similarità cross-domain non ovvia e probabilmente non
  significativa — sono segnali fisici diversi).
