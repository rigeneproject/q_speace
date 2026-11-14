# T218 — q_speace-v0 e Transduction Bridge: specifica tecnica di implementazione

**Stato:** proposta (agentic mode) — 14 novembre 2026
**Derivata da:** `Paradigm_6_0_Revised.md` + `Paradigm_6_0_Peer_Review.md`
**Chiude:** R1–R7, L1–L6 della peer review; fornisce gli allegati operativi richiesti da MAT-M1–M3, SYS-C1–C5, GOV-G1–G6, EXP-M1–M6, EDT-E1–E3.
**Normativa:** i termini **MUST / SHOULD / MAY** definiscono condizioni per un prototipo conforme. Nessun requisito afferma che un'implementazione esistente li soddisfi.

---

## 1 Scopo e dominio

Questo documento definisce la prima realizzazione eseguibile e verificabile dell'architettura
Paradigm 6.0: **q_speace-v0** (configurazione congelata del supervisore adattivo) e
**Bridge-v0** (contratto di transduzione locale), istanziati su **un solo dominio**.

**Dominio scelto: microrete energetica simpatetica simulata** (R1, E2).
Motivo della scelta: dinamica nota, bilancio fisico (potenza, non exergia generica) banalmente
contabilizzabile, attuatori continui con limiti chiari, servizio misurabile (energia non servita),
e precedenti di controllo predittivo con vincoli che rendono il confronto con le baseline onesto.

Non è incluso in questo ciclo: deployment, dati umani reali, topologie planetarie, hardware fisico.
Il piano di assimilazione resta regolato da `T217_SAFE_ASSIMILATION_LIFECYCLE_SPEC.md`.

## 2 Invariants (non negoziabili)

1. Nessuna affermazione di coscienza, esperienza soggettiva o competenza etica della macchina.
2. Entanglement solo come risorsa computazionale (no-communication theorem); comunicazione
   solo via scambio esplicito di messaggi.
3. Ogni concetto biologico/quantistico introduce in q_speace-v0 **MUST** passare il filtro BCEL
   (`q_speace/bcel/catalog.py`) prima di entrare nel codice di produzione.
4. Nessun backend quantistico reale senza `QuantumGeneSet.noise_model` configurato e gate
   energetico/Sevo attivo. q_speace-v0 è a simulazione pura: nessun backend reale nel ciclo.
5. Il proponente (q_speace) non **MUST** poter mai modificare: i propri permessi, il validatore,
   la policy dei limiti, il meccanismo di rollback.

## 3 Configurazione congelata q_speace-v0

Chiude **R1** (EXP-M1, EDT-E1/E2/E5) e **E5** (nucleo obbligatorio vs estensioni).

### 3.1 Nucleo obbligatorio (BRACCIO TRATTAMENTO del confronto H1)

| Componente | Definizione congelata |
|---|---|
| Stato | `[V_bus(t), P_load(t), SoC_batt(t), θ_phase(t)]` stimato da osservazioni rumorose |
| Osservazioni | timestamp, unità, stima d'incertezza per canale; canali critici **mai** compressi da solo anomaly-detector (§2.1 Revised) |
| Predittore | filtro di Kalman esteso su orizzonte H_pred = 10 step di controllo |
| Regola di proposta | perturbazione dei parametri `p = [P_max_batt, V_setpoint, droop_gain]` guidata dal gradiente della previsione d'errore di servizio, proiettata sull'insieme ammissibile (§4.1) |
| Memoria | buffer circolare di 256 finestre di telemetria, nessun apprendimento fuori linea |
| Frequenze | controllo locale 100 Hz (Macro); proposta supervisoria 0,1 Hz (q_speace); validazione su evento |
| Apprendimento | nessuno: v0 non aggiorna il proprio modello; solo stato e proposte |

### 3.2 Estensioni opzionali (fuori da H1; roadmap ablation T218-T09)

Spiking networks, Digital DNA, epigenetica computazionale, rappresentazioni quantum-inspired,
coordinamento di fase (§7 Revised). Ogni estensione **MUST** dichiarare: meccanismo ipotizzato,
costo computazionale, esperimento che ne giustificherebbe l'inclusione. "Quantum-inspired" senza
operazione concreta è vietato come claim; esiste in `q_speace/quantum/` solo come simulazione
classica di ampiezze (BCEL: superposition = *functional*; entanglement = *accidental*).

### 3.3 Matrice di confronto con i precedenti (chiude R1 e E1)

| Dimensione | Simplex / Neural Simplex [S1, E-R2] | Predictive safety filter [S2] | Runtime assurance NASA [S3] | **Bridge-v0** |
|---|---|---|---|---|
| Autorità esecutiva | controllore di riserva fidato | controllore nominale + filtro | switch verified/unverified | controlleri Macro deterministici + validatore indipendente |
| Filtro su | azioni del controllore avanzato | input rispetto a vincoli di stato | componenti degradati | **parametri del supervisore** (non azioni di controllo) |
| Distribuzione | singolo impianto | singolo impianto | singolo veicolo/impianto | **rete di celle** con coordinamento tra pari |
| Contabilità esternalità | no | no | no | **sì** (sezione 7) |
| Governance policentrica | no | no | no | **sì** (sezione 9) |

Differenza verificabile rivendicata: **il Bridge filtra aggiornamenti di parametri di un
supervisore distribuito su una rete di celle con contabilità causale di esternalità e governance
policentrica** — nessuno dei precedenti combina questi quattro elementi. H1/H2/H3 testano
proprio questa combinazione, non l'esistenza di un supervisore adattivo in sé.

## 4 Contratto Bridge-v0

Chiude **R2** (SYS-C1, C2, C4, C5; GOV-G2) e **R3** (SYS-C3; GOV-G3).

### 4.1 Screening dei parametri (risolve L1, MAT-M1, SYS-C6)

L'operazione di §2.2 Revised è precisata come **due stadi sequenziali con esiti prescritti**:

```
F_i^k = P_i ∩ { p : ||p − p_i^k||_{S_i} ≤ Δ_i }        (norma pesata, S_i dichiarata)
1. F_i^k vuoto            → RIFIUTO (motivo: AMMISSIBILE_VUOTI), esito registrato
2. p_cand = Π_{F_i^k}(p̃) → proiezione sull'intersezione (sempre esistente: F chiuso limitato)
3. F_i^k non convesso     → p_cand = argmin deterministico per lessicografia (regola dichiarata)
4. cambio di policy P_i   → migrazione: se p_i^k ∉ F_i^{k+1}, fallback a ultima config certificata
```

Il candidato fuori budget **non può** emergere: la proiezione avviene sull'intersezione, non su
P_i. Test obbligatorio: P=[0,10], p^k=0, proposta=10, Δ=1 → esito ammissibile p_cand=1
(registrato con ragione), mai 10.

### 4.2 Macchina a stati degli aggiornamenti (risolve C3, GOV-G3)

Ogni proposta è un messaggio `UpdateProposal` con campi obbligatori:

```
proposal_id        UUIDv4 (idempotenza)
base_epoch         epoca policy alla quale la validazione si applica
param_hash         SHA256 del vettore p_cand
scope              {cella singola | insieme accoppiato dichiarato}
dependencies       lista di proposal_id che devono attivarsi nello stesso epoch
validation_attest  firma del validatore su (proposal_id, param_hash, base_epoch)
expiry             deadline di attivazione
```

**Macchina a stati:** `PROPOSED → VALIDATED → ACTIVATED | REJECTED | EXPIRED | ABORTED`.
Proprietà richieste e verificate dal protocollo di riferimento:

- **Idempotenza:** riapplicare `ACTIVATE(proposal_id)` con stesso param_hash è no-op; con hash
  diverso è errore bloccante. Duplicazione e riordino dei messaggi non alterano lo stato finale.
- **Fencing:** un'epoca di policy revocata rifiuta attivazioni; il vecchio validatore non può
  riattivarsi dopo la promozione del successore (numero di fencing monotonico).
- **Crash recovery:** lo stato `ACTIVATED` è persistito prima dell'applicazione all'attuatore;
  al riavvio, ripresa dal journal, senza doppia attivazione.
- **Attivazioni parziali accoppiate:** due celle che consumano 0,4 ciascuna sotto un limite
  comune 1,0, con incrementi +0,15 ciascuna, **NON** possono attivarsi indipendentemente
  (0,4+0,15)·2 = 1,1 > 1,0. Protocollo di riferimento: commit a due fasi sull'insieme accoppiato
  dichiarato nel campo `scope`; oppure dimostrazione esplicita che le combinazioni asincrone
  ammesse restano sicure. Il controesempio è un test primitive obbligatorio (T218-T05).
- **Membership vs rilevazione vs quarantena:** distinti e con autorità distinte (GOV-G3).
  Quarantena: durata limitata, revoca documentata, canale di ricorso.

### 4.3 Contratto di validazione indipendente (risolve C4, G2)

- **Confine di fiducia:** validatore su processo/indirizzo di memoria separato, credenziali
  separate, chiavi di firma proprie, aggiornamento del validatore solo via canale di
  manutenzione con doppia firma (policy owner + safety officer).
- **Il proponente non deve poter**: saturare il validatore (budget CPU/tempo riservato),
  aggirarlo via altro endpoint (unico punto d'attuazione), leggere le chiavi del validatore.
- **Modello di compromissione dichiarato:** compromissione di (a) q_speace, (b) un account di
  manutenzione, (c) una fonte di aggiornamento — ciascuna da sola **non deve** permettere
  attuazione fuori da `P_i`. Compromissione simultanea di tutte le autorità è fuori modello.
- **Dati obsoleti:** validazione eseguita su stime con età ≤ t_max_oss; età superiore → fallback.
- **Rollback ≠ recupero fisico (C2):** il ripristino di `p_i^k` è distinto dalla transizione del
  controllore e dal recupero dell'impianto. Comando di rollback **deve** passare per guardie di
  commutazione (regione di recuperabilità dello stato corrente) e mai chiamato "safe" se si
  limita a ricaricare il vecchio file. Test: rollback dopo accumulo su integratori.

### 4.4 Contratto di sicurezza con osservazione e latenza (risolve C1)

Per il dimostratore, il certificato di invarianza condizionale di §2.3 Revised si istanzia come:

- modello di misura con errore limitato: `|x̂(t−τ) − x(t)| ≤ ε_obs` per τ ≤ τ_max;
- il validatore verifica il comando sull'**insieme raggiungibile** calcolato da x̂ con
  propagazione ε_obs e τ_max fino all'istante d'attuazione (Tube-MPC o alternativa dichiarata);
- perdita totale di osservabilità ≠ errore di stima limitato: transizione a modalità conservativa
  dichiarata, non a "sicurezza asserita";
- separazione esplicita tra garanzia di **sicurezza** (stato dentro X_safe) e garanzia di
  **servizio** (floors): quando le risorse non bastano, la seconda cede per prima, con
  escalation dichiarata (non inversamente).

## 5 Correzioni al punteggio e alla contabilità

Chiude **L1/L4**, **MAT-M2/M4/M5/M6**, **GOV-G4**.

### 5.1 Monotonicità (L4)

La proprietà di §5.2 Revised viene denominata esattamente: *monotonicità a coordinate fissate e
assenza di cancellazione moltiplicativa*. Non è un divieto di trade-off. Test distinti (T218-T07):
monotonicità isolata (∂U/∂h ≤ 0), trade-off consentito (aumento danno + aumento beneficio
→ punteggio maggiore è legittimo), violazione inderogabile (danno non compensabile resta
vincolo esterno allo score, mai penalità scalabile con beneficio).

### 5.2 Aggregazione additiva e invarianza di suddivisione (M2)

- Densità di beneficio/danno `u(z)` su misura additiva μ (persone, aree, unità di servizio);
  `ρ_i·U_i` definito come integrale di u su μ, con `ρ_i ≥ 0`.
- Variabili intrinsecamente intensive (es. efficienza): mai mediate su partizioni diverse senza
  dichiarare la sensibilità.
- Test obbligatorio (dal controesempio M2): due regioni di pari peso, fisica 0 e 1,
  normalizzazione b(x)=x² → punteggio fine e aggregato devono coincidere entro tolleranza
  dichiarata, oppure la spec riporta l'errore di discretizzazione come risoluzione dipendente.
- **Danni cumulativi (G4):** finestra cumulativa per gruppo di soggetti protetti; una sequenza di
  azioni ognuna entro i limiti istantanei che supera il limite cumulativo dichiarato **deve** essere
  bloccata o escalation, indipendentemente dal punteggio totale.

### 5.3 Exergia e riferimento termodinamico (M4)

- Ambiente di riferimento **comune e stazionario** fissato nel pilota (T0, P0, composizione);
  flussi di confine con unità e convenzione di segno dichiarate.
- Soglia di attività rinominata `ᎊX_min` (watt), distinta da stock `X_i` (joule).
- Verifica di chiusura: somma dei bilanci di tutte le celle → scambi interni cancellati;
  restano variazione di stock, scambi esterni, distruzione.

### 5.4 Diagnostici di fase (M5)

Pesi `w_ij ≥ 0` enunciati **nel punto d'uso** del modulo di fase (non solo in §8.2);
`s_i/d_i` interpretabile in [0,1] solo con anche `w_ij ≤ 1`. Processo congiunto dei rumori W_i
dichiarato; fasi modulo 2π. Garanzie da Laplaciani simmetrici non trasferite al modulo di fase.

## 6 Valore causale certificato (risolve R4, MAT-M3, EXP-M4)

- **Quantità bersaglio V\*** definita per ogni stima: intervento a (durata, policy successiva),
  baseline π₀, popolazione Ω, orizzonte H, misura ρ.
- Scomposizione esplicita, senza doppio conteggio:
  `ε = ε_model + ε_spaziale + ε_temporale + ε_stat(1−δ)`.
- Certificato: `|V̂ − V*_{Ω,H}| ≤ ε_model + ε_stat` e `V* − V*_{Ω,H} ≥ −ε_tail` (coda spazio-tempo).
- Errori opposti sulle due traiettorie (modulo ε ciascuna → errore fino a 2ε) **devono** essere
  rilevati dal test T218-T08, che verifica la copertura del limite dichiarato.
- **Effetti post-H:** ogni azione riporta la valutazione "esterna all'orizzonte" se il modello
  prevede effetti non trascurabili oltre H; l'orizzonte non può essere scelto per far scomparire
  un danno differito.
- Identificazione causale da dati osservazionali reali: **fuori ambito di questo ciclo**;
  la garanzia vale sul simulatore con interventi definiti, dichiarato come tale.

## 7 Protocollo sperimentale preregistrabile (risolve R6, EXP-M1–M6)

### 7.1 Disegno

| Elemento | Decisione (prima dei dati) |
|---|---|
| Dominio | microrete 19 celle (poi 37 per scalabilità) |
| Bracci | (a) controllo locale fisso, (b) supervisione adattiva convenzionale (baseline), (c) q_speace-v0 |
| Baseline "strongest" | selezionata su scenari di tuning **non** sovrapposti ai test finali |
| Endpoint primario H1 | energia cumulativa non servita per traiettoria (non "recovery time OR shortfall") |
| Criterio di sicurezza | non-inferiorità sul numero di violazioni di X_safe per traiettoria |
| Margine di interesse | preregistrato nel documento di preregistrazione (file `EXP-T218-prereg.md`) |
| Unità statistica | **traiettoria completa della rete**; repliche: ≥ N per analisi di potenza preregistrata |
| Accoppiamento | stessi disturbi esogeni tra bracci; flussi casuali politici separati |
| Confronti multipli | correzione preregistrata (Holm) |
| Fallimenti | report separato: casi non recuperati, non determinabili, crash dei bracci |

### 7.2 H2 senza circolarità (EXP-M5)

Suite di proposte etichettata da **riferimento indipendente dal validatore valutato**: casi
analiticamente risolvibili + esplorazione esaustiva su reti piccole + simulatore di riferimento
distinto dal modello del decisore (chiude anche la circularità di EXP-M4: modello del controllore
≠ simulatore di valutazione ≠ eventuali dati osservati). Metriche preregistrate: falsi accettati
dannosi, falsi rifiuti, astensioni, latenza, utilità degli aggiornamenti consentiti. Il sistema
"rifiuta tutto" **deve** fallire il criterio di utilità; "accetta tutto" **deve** fallire quello di
protezione. H4 riformulato come contrasto componente vs **sostituto convenzionale funzionante**
con effetto incrementale preregistrato (L5).

## 8 Governance e privacy del pilota (risolve R7, G1, G3, G5, G6, E3)

### 8.1 Contratto di governance minimo (G1)

Per il dominio microrete: ruoli (policy owner, safety officer, operatore di cella, rappresentante
degli interessati), categorie di decisioni non delegabili (pesi α/β, soglie di servizio, diritti),
autorità di risoluzione per decisioni incompatibili tra celle (precedenza dichiarata:
sicurezza > servizio protetto > obiettivi economici), tempi di risposta massimi, regola
provvisoria durante ricorsi, motivazione registrata. Esercitazione obbligatoria: conflitto tra
due celle con carenza fisicamente inevitabile, decisione entro tempo dichiarato (T218-T12).

### 8.2 Matrice requisito–minaccia–controllo–evidenza (G6, E3)

Vedi sezione 10. Nessun gate chiuso solo da punteggio positivo; conformità documentale,
tecnica e prestazionale sono tre tracce distinte.

### 8.3 Privacy (G5)

Inventario dati + flussi + retention + accessi del dataset sintetico; nessun dato umano reale nel
ciclo. Test di ricostruzione/linkage sul dataset dimostrativo con risultati e limiti espliciti.
Differential privacy solo dove documentata (unità protetta, budget, costo di utilità); mai
applicata in modo da invalidare silenziosamente stime di sicurezza.

## 9 Matrice di conformità

| ID | Requisito | Livello | Artefatto | Verifica | Trace review |
|---|---|---|---|---|---|
| BR-01 | Schema `UpdateProposal` + macchina a stati | MUST | `q_speace/bridge/protocol.py` | pytest idempotenza/fencing/crash | R3, C3 |
| BR-02 | Screening due stadi con intersezione | MUST | `q_speace/bridge/screening.py` | test controesempio [0,10] | L1, M1, C6 |
| BR-03 | Attestazione firma validatore | MUST | `q_speace/bridge/validator.py` | test bypass + compromissione account | C4, G2 |
| SAF-01 | Certificato su insieme raggiungibile con ε_obs, τ_max | MUST | `q_speace/bridge/safety_contract.py` | test dati obsoleti/latenza | C1 |
| SAF-02 | Rollback con guardie di recuperabilità | MUST | `q_speace/self_improvement_cortex/rollback.py` (est.) | test rollback post-accumulo | C2 |
| SAF-03 | Precedenza sicurezza > servizio protetto | MUST | policy dichiarata nel dominio | test scarsità prolungata | C5, G1 |
| SCO-01 | Monotonicità a coordinate fissate | MUST | `q_speace/economy/aggregation.py` (est.) | 3 test di §5.1 | L4, M6 |
| SCO-02 | Aggregazione additiva su μ | MUST | `q_speace/economy/aggregation.py` (est.) | test suddivisione b(x)=x² | M2 |
| SCO-03 | Limite cumulativo per gruppo | MUST | `q_speace/economy/admission.py` (est.) | test concentrazione danni | G4 |
| CAU-01 | Certificato V* con ε scomposto | MUST | `q_speace/economy/vtec.py` (est.) | test copertura errori opposti | R4, M3 |
| EXP-01 | Preregistrazione congelata | MUST | `docs/EXP-T218-prereg.md` | hash del file nel repository | R6 |
| EXP-02 | Suite H2 etichettata indipendente | MUST | `tests/validator_labels/` | rifiuta-tutto fallisce utilità | EXP-M5 |
| GOV-01 | Contratto di governance compilato | MUST | `docs/GOV-T218-pilot.md` | esercitazione conflitto | G1 |
| GOV-02 | Matrice requisito–evidenza–responsabile | MUST | questo documento, sezione 10 | revisione a due revisori | E3, G6 |
| PRV-01 | Inventario dati + test linkage | MUST | `docs/PRV-T218-data-map.md` | test ricostruzione | G5 |
| BCEL-01 | Catalogo BCEL per Bridge-v0 | MUST | `q_speace/bcel/catalog.py` (est.) | py_compile + ruff | invariant 3 |

## 10 Task

Ogni task: agentic mode (spec esiste in questo documento; BCEL dove indicato; test; pytest+ruff+black+mypy sui file toccati).

| ID | Task | Dipende da | Accettazione |
|---|---|---|---|
| T218-T01 | Definire `bridge/protocol.py`: dataclass `UpdateProposal`, macchina a stati, journal persistente, idempotenza, fencing | — | pytest: duplicazione, riordino, crash-recovery, doppia attivazione |
| T218-T02 | Definire `bridge/screening.py`: due stadi §4.1 con norma pesata S_i e regola lessicografica | T01 | test controesempio proiezione; F vuoto; P non convesso; migrazione policy |
| T218-T03 | Definire `bridge/validator.py`: attestazioni firmate, confine di fiducia, budget anti-saturazione | T01 | test bypass, compromissione account manutenzione, valutatore non risponde |
| T218-T04 | Estendere `safety_contract.py`: insieme raggiungibile con ε_obs e τ_max, modalità conservativa | T02 | test latenza > soglia → fallback tempestivo documentato |
| T218-T05 | Test primitive accoppiate: controesempio 0,4/0,15/1,0 con commit a due fasi | T01 | traccia riproducibile; nessun 1,1 approvato; esiti degradati dichiarati |
| T218-T06 | Estendere `rollback.py` con guardie di recuperabilità e distinzione ripristino/commutazione/recupero | — | test rollback dopo accumulo integrale; nessun "safe" per solo file reload |
| T218-T07 | Estendere `aggregation.py`: U additivo su μ, monotonicità, test suddivisione, finestre cumulative | — | 3 test SCO-01 + test b(x)=x² + test G4 concentrazione |
| T218-T08 | Estendere `vtec.py`: V* con ε scomposto, effetti post-H, test copertura con errori opposti | — | copertura del limite verificata su verità nota nel simulatore |
| T218-T09 | Plant microrete 19 celle + 3 bracci + harness preregistrato; ablation framework per estensioni | T01–T04 | 19 celle eseguibili; configurazioni congelate con hash |
| T218-T10 | Suite etichette H2 indipendente dal validatore valutato | T03 | rifiuta-tutto fallisce utilità; accetta-tutto fallisce protezione |
| T218-T11 | Scrivere `EXP-T218-prereg.md` (endpoint, margine, potenza, regole decisionali) e congelare l'hash | T09 | hash registrato; nessuna modifica post-dati senza versione |
| T218-T12 | Scrivere `GOV-T218-pilot.md` + esercitazione di conflitto e falsa accusa; `PRV-T218-data-map.md` | — | esercitazione documentata con esito entro tempo dichiarato |
| T218-T13 | Estendere `bcel/catalog.py` con le equivalenze di Bridge-v0 (analogie: accidental; regole matematiche: functional) | — | py_compile, ruff, revisione a due revisori |

**Ordine consigliato** (dalla review, §Ordine): T01→T02→T03→T04→T05 (contratto Bridge),
in parallelo T06/T07/T08 (correzioni contabilità), poi T09→T10→T11 (protocollo sperimentale),
T12/T13 trasversali. Il confronto bibliografico (matrice §3.3) accompagna la definizione del
contributo, non la segue.

## 11 Criterio di successo del ciclo

Due gruppi indipendenti che implementano questo documento devono poter: (a) costruire
Bridge-v0 e q_speace-v0 equivalenti; (b) eseguire lo stesso esperimento preregistrato;
(c) interpretare l'esito con la stessa regola. Il mancato raggiungimento di H1 rispetto alla
baseline più forte **conta contro** l'architettura aggiunta — è questa la falsificabilità richiesta.

## 12 Registro revisioni

| Versione | Data | Note |
|---|---|---|
| 1 | 2026-11-14 | Prima stesura; deriva da Paradigm_6_0_Revised + peer review multilivello; chiude R1–R7/L1–L6 |
| 1.1 | 2026-11-14 | Quattro perfezionamenti tecnici di basso livello: (R1) canonicalizzazione IEEE 754 di `param_hash` — quantizzazione round(p,9), normalizzazione ±0.0, serializzazione big-endian `>f8` (`canonical_param_hash`); (R2) tie-break lessicografico con banda `ε_tie = 1e-12` su insiemi non convessi (`select_projection_tie_break`); (R3) timeout senza coordinatore nel commit a due fasi con `expire_on_timeout` e rilascio immediato della capacità riservata; (R4) bumpless transfer nel rollback — guardia slew-rate inverter e riallineamento dell'integratore (`bumpless_realignment`) |
