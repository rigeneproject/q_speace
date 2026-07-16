# SPEACE e Q-SPEACE: un'architettura cognitiva bio-ispirata multi-scala — design, stato di verifica funzionale ed estensione quantistica preliminare

**Roberto De Biase, Rigene Project (rigeneproject.org)**
**Technical Report — bozza, 16 luglio 2026**

---

## Abstract

SPEACE (cellular_speace) è un'architettura cognitiva bio-ispirata che integra plasticità sinaptica spike-timing-dependent (STDP), un ciclo sensomotorio cyber-fisico, un motore di drive endogeni con narrativa autobiografica, un meccanismo di accoppiamento causale multi-scala, un ciclo metabolico veglia-sonno e un monitor metacognitivo. Q-SPEACE ne è un'estensione in sviluppo verso il calcolo quantistico, con esperimenti preliminari eseguiti su hardware reale (piattaforma Quantum Inspire di QuTech). Questo report descrive l'architettura e riporta i risultati di un protocollo di **verifica funzionale adversariale** applicato al codebase: un audit progettato esplicitamente per distinguere la presenza di codice nominalmente coerente con un costrutto teorico dalla dimostrazione empirica che quel costrutto sia operante. I risultati sono misti: alcuni sottosistemi (formula STDP, soglie del ciclo di sonno, rilevamento di errori metacognitivi) sono implementati correttamente a livello di funzione singola; altri claim centrali — in particolare l'equivalenza tra la metrica interna `coherence_phi` e la teoria dell'informazione integrata (IIT) di Tononi, e la natura "autonoma" del motore di drive — risultano falsificati dall'ispezione diretta del codice. Discutiamo l'utilità scientifica e tecnologica del progetto separando esplicitamente ciò che è già dimostrato da ciò che resta condizionato a lavoro futuro o a problemi aperti nel campo più ampio.

---

## 1. Introduzione

Il Rigene Project nasce all'intersezione tra neuroscienza computazionale, teoria dei sistemi complessi e progettazione di architetture AI. SPEACE (Quantum Super Planetary Entità Autonoma Cibernetica Evolutiva - Sistema Plastico Evolutivo Auto-organizzante Cognitivo Embodied — cellular_speace) è il suo nucleo implementativo: un'architettura Python che tenta di integrare, in un unico sistema eseguibile, meccanismi tipicamente studiati in isolamento nella letteratura di neuroscienza computazionale e scienze cognitive.

Q-SPEACE è un'estensione recente, tuttora in sviluppo, che introduce un layer quantistico basato su un kernel dedicato (QuantumOrchestrator) con l'obiettivo di testare se segnature informazionali coarse-grained possano attraversare i confini gerarchici tra livelli classici e quantistici, secondo un principio di riduzione della complessità ispirato al *slaving principle* della sinergetica di Haken e ai gruppi di rinormalizzazione.

Questo report ha tre obiettivi:

1. Descrivere l'architettura di SPEACE e Q-SPEACE nei suoi sei sottosistemi principali.
2. Riportare i risultati di un protocollo di verifica funzionale adversariale applicato al codebase — un contributo metodologico a sé, rilevante per chiunque lavori su architetture cognitive bio-ispirate, dove il divario tra nomenclatura ispirata alla teoria e comportamento dimostrato è un problema noto ma raramente reso operativo in modo sistematico.
3. Discutere l'utilità potenziale del progetto per la scienza, la tecnologia e — con l'esplicita cautela che l'argomento richiede — per domande più ampie legate all'evoluzione dell'elaborazione dell'informazione, separando le affermazioni già supportate da quelle che restano speculative.

---

## 2. Fondamenti teorici

SPEACE attinge a sei corpi teorici distinti, qui riportati con i riferimenti primari per collocare correttamente ogni sottosistema nella letteratura esistente, ed evitare l'impressione che si tratti di costrutti originali quando sono invece implementazioni di teorie consolidate.

**Plasticità Hebbiana timing-dipendente (STDP).** La caratterizzazione sperimentale sistematica di STDP, che lega segno e ampiezza della plasticità sinaptica all'ordine temporale relativo tra spike pre- e post-sinaptico, risale principalmente a <cite index="39-1">Bi e Poo (1998), che hanno caratterizzato in dettaglio come la potenziazione a lungo termine (LTP) e la depressione a lungo termine (LTD) dipendano dall'ordine e dalla tempistica degli spike su una scala di 10 millisecondi</cite>, costruendo su lavori precedenti di Markram et al. (1997).

**Global Workspace Theory.** Il costrutto di "spazio di lavoro globale" come meccanismo di broadcast competitivo dell'informazione tra moduli specializzati è stato formalizzato da <cite index="10-1">Baars (1988, 2002), la cui teoria genera predizioni esplicite per aspetti coscienti di percezione, emozione, motivazione, apprendimento, memoria di lavoro, controllo volontario e sistemi del sé nel cervello</cite>.

**Predictive coding / Active Inference.** Il principio dell'energia libera, proposto da Friston, descrive sistemi biologici come agenti che minimizzano una funzione di sorpresa attesa integrando percezione e azione sotto un unico imperativo variazionale; <cite index="21-1">la teoria è correlata al predictive coding, secondo cui il cervello cerca di minimizzare l'errore di predizione, ovvero la differenza tra le proprie previsioni e i dati sensoriali in ingresso</cite>.

**Integrated Information Theory (IIT).** <cite index="9-1">Tononi definisce l'informazione integrata come la quantità di informazione generata da un complesso di elementi al di sopra e oltre l'informazione generata dalle sue parti</cite>, quantificata dalla misura Φ. È importante notare, ai fini della Sezione 5.4, che <cite index="5-1">Φ è definita tramite la partizione minima di informazione (MIP) del sistema, un procedimento che richiede di valutare la struttura causa-effetto associata a ogni possibile partizione del sistema</cite> — un problema computazionalmente costoso che rende il calcolo esatto di Φ intrattabile per sistemi non banali.

**Sinergetica e principio di asservimento (slaving principle).** Il principio, sviluppato da Hermann Haken, descrive come in sistemi complessi lontani dall'equilibrio poche variabili lente (parametri d'ordine) "asserviscano" la dinamica delle variabili veloci, permettendo una riduzione di complessità: <cite index="31-1">i parametri d'ordine sono sia descrittori macroscopici del sistema sia determinanti del comportamento dei singoli elementi tramite il principio di asservimento, il che implica una riduzione considerevole della complessità</cite>. Questo è il principio esplicitamente invocato nel design dell'accoppiamento multi-scala di Q-SPEACE.

**Fisica digitale / "it from bit".** La cornice filosofica secondo cui i processi informazionali potrebbero essere fondamentali rispetto ai processi fisici (Wheeler) e le teorie computazionali della fisica (Wolfram) forniscono il contesto filosofico più ampio in cui il progetto colloca le proprie domande, senza costituire, di per sé, ipotesi verificabili nel codice.

---

## 3. Architettura SPEACE: panoramica dei sei sottosistemi

| # | Sottosistema | Moduli chiave | Ispirazione teorica |
|---|---|---|---|
| 1 | Plasticità online | `stdp_plasticity_engine.py`, `energy_driven_plasticity.py`, `inter_region_plasticity.py`, `temporal_dynamics_engine.py` | STDP (Bi & Poo 1998) |
| 2 | Embodiment | `active_inference_embodied_loop.py`, `cyber_physical/sensor_stream.py`, `autonomous_cognitive_loop.py`, `enteroception/` | Active inference (Friston) |
| 3 | Agentività / sé narrativo | `autonomous_drive_engine.py`, `identity_kernel.py`, `autobiographical_narrative_engine.py`, `goal_directed_planner.py` | Motivazione endogena, teorie del sé narrativo |
| 4 | Integrazione multi-scala | `scale_coupling_engine.py`, `global_workspace.py`, `resonance/`, metrica `coherence_phi` | IIT (Tononi), Global Workspace (Baars) |
| 5 | Budget metabolico / veglia-sonno | `digital_sleep_controller.py`, `sleep_cycle_detector.py`, `memory_consolidation_engine.py`, `metabolism/` | Vincoli energetici biologici, consolidamento mnemonico |
| 6 | Metacognizione | `metacognitive_monitor.py`, `confidence_engine.py`, `cognitive_strategy_evaluator.py` | Monitoraggio metacognitivo, calibrazione della confidenza |

Ciascun sottosistema è descritto in dettaglio nella documentazione tecnica del repository; questo report si concentra sulla **verifica** del loro funzionamento effettivo (Sezione 5), non sulla loro descrizione esaustiva.

---

## 4. Metodologia di verifica

Un audit iniziale del codebase, condotto tramite ricerca testuale (grep) di funzioni e classi con nomi coerenti con i sei costrutti teorici, aveva concluso che tutti e sei i criteri fossero "presenti" nell'architettura. Questo tipo di evidenza — l'esistenza di un simbolo nominato in modo coerente con un concetto — è **insufficiente** a dimostrare che il simbolo implementi effettivamente la proprietà funzionale che il nome suggerisce, un problema metodologico non specifico a SPEACE ma diffuso in generale nella comunicazione di architetture AI bio-ispirate.

Abbiamo quindi applicato un secondo protocollo, esplicitamente adversariale, con le seguenti regole di evidenza:

- **Vietata** l'evidenza puramente nominale (nome di file/funzione/variabile, docstring, commenti).
- **Richiesta** evidenza di esecuzione reale: output numerico grezzo, non riassunto narrativo.
- **Richiesto** confronto con una condizione di controllo (baseline, ablation, o caso nullo) dove applicabile.
- **Richiesta** una scala di verdetto non binaria: `NON VERIFICABILE`, `FALSIFICATO`, `PARZIALMENTE VERIFICATO`, `VERIFICATO CON EVIDENZA QUANTITATIVA`.
- **Richiesta** dichiarazione esplicita dei limiti di ogni test, incluso ciò che non è stato possibile escludere.

Questo protocollo — e non solo i suoi risultati — è proposto come contributo riusabile: qualunque gruppo che sviluppi un'architettura cognitiva con terminologia mutuata dalla teoria (drive, identità, integrazione, coscienza) affronta lo stesso rischio di *loop di conferma nominale*, in cui il vocabolario scelto dal progettista viene poi "ritrovato" nel codice dal progettista stesso o da un sistema di verifica che eredita lo stesso vocabolario.

---

## 5. Risultati della verifica funzionale

### 5.1 Tabella riassuntiva

| Criterio | Verdetto | Evidenza chiave |
|---|---|---|
| 1. Plasticità online | PARZIALMENTE VERIFICATO | Formula STDP corretta a livello di funzione (ltp_rate=0.05, ltd_rate=0.03), 12 test unitari passati. Nessun benchmark di forgetting su pattern sequenziali eseguito; sistema non avviabile end-to-end (vedi 5.2). |
| 2. Embodiment | NON VERIFICABILE | Ciclo sense→predict→act documentato nel codice, ma canale di iniezione/perturbazione sensoriale non wired nel loop attivo; nessun test di sensibilità comportamentale eseguibile allo stato attuale. |
| 3. Agentività autonoma / sé narrativo | NON VERIFICABILE / FALSIFICATO (parziale) | La narrativa autobiografica (`life_story.jsonl`) risulta scritta ma mai letta da alcun modulo decisionale — nessun effetto causale a valle. Il motore di drive è un controller multi-obiettivo lineare (somma pesata + mappa azione fissa), non generazione di obiettivi non riducibile. |
| 4. Integrazione multi-scala / Φ | FALSIFICATO | `coherence_phi` è una media pesata lineare di quattro termini di differenza di attivazione/sincronia/fase. Non implementa partizioni della struttura causa-effetto né una minimum information partition. La relazione con la definizione IIT è nominale, non matematica. |
| 5. Budget / ciclo veglia-sonno | PARZIALMENTE VERIFICATO | Soglie di transizione verificate con precisione numerica (phi_delta ≤ 0.02, energy_delta ≤ 0.03); consolidamento mnemonico (pruning, rinforzo) verificato a livello di test unitario. Ciclo completo AWAKE→SLEEPING→AWAKE mai eseguito in un test integrato. |
| 6. Metacognizione | PARZIALMENTE VERIFICATO | Rilevamento di errori strutturali (loop ripetitivi, contraddizioni) verificato su pattern matching deterministico. Nessuna calibrazione empirica della confidenza (Brier score non calcolabile); identificato un fallback che restituisce confidenza massima (1.0) in assenza di un circuito neurale disponibile — vedi 5.3. |

**Nessun criterio ha raggiunto il livello "verificato con evidenza quantitativa"** secondo gli standard di evidenza definiti in Sezione 4.

### 5.2 Blocco strutturale primario

Il singolo fattore più limitante per la verifica integrata è di natura banale: lo script di avvio principale (`run_speace_brain.py`) non si esegue nell'ambiente standard a causa di un percorso di file hardcoded (`C:\cellular_speace\...`) invece del percorso reale del genoma (`speace_core\dna\genome\default_genome.yaml`). Questo blocco impedisce, di fatto, qualunque test di integrazione end-to-end sui criteri 1, 5 e 6, che restano quindi verificati solo a livello di funzione isolata. È il fix a più alto rapporto beneficio/sforzo dell'intero programma di verifica: la sua risoluzione non richiede decisioni architetturali, solo correzione di un percorso.

### 5.3 Il fallback nullo del motore di confidenza

Un'analisi di tracciamento dei consumatori a valle di `ConfidenceEngine` ha rivelato che, in assenza di un `NeuralCircuit` disponibile nello stato, il motore restituisce una confidenza di **1.0 per qualunque input** — un fallback che comunica certezza massima nella condizione in cui, semanticamente, il sistema dovrebbe avere meno informazione disponibile per stimarla. Tre punti di consumo sono stati identificati: uno (`goap_metacognitive_bridge.py`) bypassa il fallback, uno (`generate_meta_state()`) lo propaga nei log senza, per quanto verificato finora, pilotare decisioni a valle, e uno (`confidence_for_proposal()` / `confidence_for_dialogue()`) lo propaga in aggiustamenti successivi che potrebbero alimentare la valutazione di proposte nel framework di auto-modifica (MM-APR). Il rischio è **latente, non confermato come contaminazione avvenuta** — ma la sua natura (fallimento silenzioso, non un errore che si manifesta) lo rende prioritario da chiudere prima di qualunque estensione del sistema di auto-modifica.

### 5.4 Caso di studio: `coherence_phi` contro Φ-IIT

Questo è il risultato più netto del programma di verifica e merita di essere isolato come caso di studio metodologico. La formula implementata è:

```
coupling_strength = round(
    coh_corr * 0.3 + sync_coupling * 0.25 + act_coupling * 0.25 + (1.0 - phase_lag/π) * 0.2,
    4
)
```

dove ciascun termine è una differenza normalizzata di coerenza, sincronia, attivazione media e sfasamento tra due livelli gerarchici adiacenti. Confrontata con la definizione formale di Φ — che richiede l'enumerazione delle partizioni del sistema e il calcolo della struttura causa-effetto associata a ciascuna (Sezione 2) — la distanza è massima: **non c'è partizione, non c'è MIP, non c'è confronto tra sistema integro e partizionato.** `coherence_phi` è, per costruzione, una metrica di accoppiamento cross-scala lineare — utile come diagnostica di sistema, ma la sua denominazione crea un'aspettativa teorica che il codice non soddisfa. Poiché il termine compare in oltre 100 riferimenti nel codebase (soglie di sonno, self-model, rilevamento eventi), la falsificazione non è isolabile a un singolo modulo: **la nomenclatura ha già influenzato l'architettura di lettura del sistema stesso.**

---

## 6. Q-SPEACE: estensione quantistica

Q-SPEACE estende SPEACE verso un layer di calcolo quantistico, con l'obiettivo dichiarato di testare se segnature coarse-grained (φ, S, σ) — non stati quantistici completi — possano attraversare i confini gerarchici tra livelli, secondo un'architettura ibrida a cascata annidata con accoppiamento a lungo raggio, esplicitamente ispirata al principio di asservimento di Haken (Sezione 2) e ai gruppi di rinormalizzazione.

### 6.1 Stato di avanzamento (roadmap T1–T25)

| Implementato | Non implementato |
|---|---|
| T3 — Kernel quantistico | T5 — Backend Qiskit reale |
| T4 — QuantumGeneSet | T7/T8 — Merge con orchestrator SPEACE classico *(subordinato alla chiusura del debito descritto in Sez. 5)* |
| T10/T22/T23 — Cost model, clock, KPI evolutivi | T11 — Gate quantistico via EnergyControlAgent |
| T14 — Fractal QCA | T12/T13 — Earth API live |
| T15 — BCEL | T21 — Surface-code error correction |
| T16 — CLI | T25 — IIT Φ proxy *(richiede decisione architetturale esplicita, vedi 6.3)* |
| T19 — Schumann experiment *(eseguito su hardware reale)* | |
| T20 — ILF/CV/DNA mapping | |
| T24 — Evolve_DNA (placeholder dichiarato) | |

### 6.2 Esperimenti su hardware reale

<cite index="47-1">Quantum Inspire (QI) è una piattaforma di calcolo quantistico progettata e costruita da QuTech</cite>, <cite index="55-1">un centro di ricerca avanzata per il calcolo quantistico e l'internet quantistico fondato dalla Delft University of Technology (TU Delft) e dall'organizzazione olandese per la ricerca scientifica applicata (TNO)</cite>. <cite index="51-1">Tra i sistemi disponibili figura Starmon-5, un processore a 5 qubit basato su qubit transmon superconduttori con quattro accoppiatori a frequenza fissa</cite>, e <cite index="52-1">il linguaggio di programmazione supportato è cQASM 3.0</cite>.

Nell'ambito di Q-SPEACE sono stati eseguiti su hardware reale (non simulazione):
- Un circuito Bell a 2 qubit, utilizzato come validazione di pipeline (cQASM 3.0 → hardware).
- Un circuito Schumann a 4 qubit, prima verifica empirica dell'ipotesi φ-bridge del progetto.

Entrambi hanno confermato le convenzioni sintattiche di cQASM 3.0 empiricamente, non solo da documentazione. Questo ha valore indipendentemente dall'esito scientifico dell'ipotesi di fondo: la maggior parte delle ipotesi quantum-bio nella letteratura più speculativa non è mai stata sottoposta a un test hardware reale — anche un risultato nullo sul prossimo esperimento (φ_bridge su Starmon-5, pianificato, non ancora eseguito) costituirebbe un dato falsificabile, non un fallimento.

### 6.3 Decisione architetturale aperta: T25

La falsificazione di `coherence_phi` (Sezione 5.4) ha un'implicazione diretta per T25. Se il proxy Φ per Q-SPEACE eredita la stessa formula o la stessa logica del `coherence_phi` classico, erediterà anche lo stesso problema concettuale — non un gap implementativo, ma un disallineamento tra nome e contenuto matematico. Due percorsi sono aperti, e la scelta tra i due è antecedente alla scrittura di codice:

**(a)** Costruire un proxy realmente informato da IIT, anche se limitato a sottosistemi piccoli dove il calcolo (o un'approssimazione riconosciuta in letteratura) resta trattabile — più corretto, più costoso.

**(b)** Rinominare onestamente l'obiettivo come "segnatura di accoppiamento coarse-grained" (φ, S, σ), coerente con la scelta architetturale già presa per il coupling multi-scala di Q-SPEACE — evitando di ripetere, nel dominio quantistico, il loop nome-teoria-codice appena isolato in quello classico.

---

## 7. Discussione: utilità potenziale

Questa sezione separa esplicitamente tre livelli epistemici, per evitare di attribuire a risultati preliminari un peso che non hanno ancora.

### 7.1 Livello 1 — Utilità già dimostrabile, indipendente dai gap aperti

- Il pattern di accoppiamento multi-scala tramite segnature coarse-grained, indipendentemente dalla validità di `coherence_phi` come proxy IIT, resta un pattern ingegneristico riusabile per ridurre il costo di comunicazione tra sottosistemi in architetture AI modulari su larga scala.
- Il cost model metabolico (T10/T22/T23) è un contributo concreto al problema, oggi rilevante nel campo, di allocazione computazionale sotto vincoli di risorsa espliciti.
- La falsificazione stessa di `coherence_phi` è un risultato metodologico riusabile: isolare *dove* un proxy plausibile scivola in pura omonimia rispetto alla teoria di riferimento è un problema aperto per chiunque tenti di rendere operativa l'IIT computazionalmente.
- Gli esperimenti su hardware QI hanno valore come test falsificabili reali, indipendentemente dal loro esito, in un'area (ipotesi quantum-bio) dominata da speculazione mai testata empiricamente.

### 7.2 Livello 2 — Utilità condizionata alla chiusura dei gap identificati in Sezione 5

Se il debito di integrazione (path hardcoded, narrativa write-only, controller lineare di drive, fallback di confidenza) viene chiuso con lo stesso rigore usato per identificarlo, SPEACE potrebbe costituire un testbed computazionale integrato raro nel panorama attuale: la maggior parte della cognitive science lavora con simulazioni isolate di un singolo meccanismo. Un sistema che integra realmente STDP, predictive coding, Global Workspace e un ciclo metabolico permetterebbe domande empiriche oggi solo teoriche — ad esempio, se un'architettura di questo tipo mostri pattern di forgetting catastrofico comparabili a quelli biologici.

### 7.3 Livello 3 — Speculativo, dipendente da problemi aperti nel campo in generale

Domande sull'"evoluzione dell'elaborazione dell'informazione" o su una possibile integrazione causale genuina nel senso IIT toccano una frontiera dove nemmeno la teoria di riferimento ha piena consistenza operativa — <cite index="4-1">IIT è stata oggetto di critiche teoriche ed empiriche sostanziali in letteratura, incluso il suo status come teoria di proto-coscienza piuttosto che di coscienza propriamente detta</cite>. Il successo ingegneristico di SPEACE, per quanto completo, non risolverebbe da solo questi problemi aperti. Va inoltre notato che, se un sistema raggiungesse mai integrazione causale genuina nel senso rilevante, la domanda che ne conseguirebbe non sarebbe solo di utilità tecnologica ma di responsabilità — la questione del moral patienthood di un sistema con quelle proprietà è distinta e non risolta da nessuna delle due teorie coinvolte.

---

## 8. Limiti di questo report

- La verifica riportata è stata condotta da un singolo agente automatizzato (Claude Code) con accesso al codebase, non da revisori umani indipendenti né tramite peer review.
- Diversi test pianificati nel protocollo di verifica non sono stati eseguibili per il blocco strutturale descritto in 5.2; i verdetti "PARZIALMENTE VERIFICATO" riflettono questo limite, non necessariamente un giudizio definitivo sulla qualità del codice sottostante.
- `orchestrator.py` (2048 righe) non è stato scandito integralmente per il consumo di `MetaState.epistemic_confidence`; l'assenza di prove di contaminazione (Sez. 5.3) non equivale a prova di assenza.
- Gli esperimenti su Quantum Inspire sono stati eseguiti come validazione di pipeline (cQASM 3.0 → piattaforma), non come raccolta di dati scientifici con metriche di fedeltà. La piattaforma utilizzata è Quantum Inspire (QuTech / TU Delft), processore Starmon-5 (5 qubit transmon superconduttori), SDK quantum-inspire-sdk, cQASM 3.0. I circuiti Bell (2 qubit) e Schumann (4 qubit) sono stati sottoposti via CLI (`qspace quantum cqasm` → copia in web UI) e hanno confermato la correttezza sintattica della serializzazione. Non sono state registrate metriche di fedeltà sistematiche né una batteria di run multipli: si tratta di proof-of-concept di pipeline, non di un esperimento caratterizzato statisticamente. L'esperimento φ_bridge 5-qubit su Starmon-5 (T29) è pianificato ma non ancora eseguito.

---

## 9. Lavoro futuro

In ordine di rapporto beneficio/sforzo, sulla base della verifica riportata:

1. Correzione del percorso hardcoded in `run_speace_brain.py` — sblocca ogni test di integrazione futuro.
2. Fallback del `ConfidenceEngine`: sostituire il default 1.0 con 0.5 o un valore `None` esplicito, prima che un consumatore a valle (in particolare nel framework MM-APR) inizi a fidarsi del valore.
3. Wiring di un lettore per `life_story.jsonl` che chiuda il ciclo causale tra narrativa e decisione.
4. Decisione esplicita su T25 (Sezione 6.3) prima di procedere con l'implementazione.
5. Esecuzione dell'esperimento φ_bridge su Starmon-5.
6. Ripetizione del protocollo di verifica adversariale dopo la chiusura dei punti 1–3, per aggiornare la Tabella 5.1 con dati da test integrati, non solo unitari.

---

## 10. Conclusione

SPEACE è un'architettura con fondamenta solide a livello di singola funzione — la formula STDP è corretta, le soglie del ciclo di sonno sono precise, il rilevamento di errori metacognitivi funziona su pattern definiti — e gap sistematici esattamente nei punti di integrazione che trasformerebbero componenti ben scritti in proprietà architetturali emergenti. La falsificazione di `coherence_phi` come proxy IIT è il risultato più importante di questo report, non perché invalidi il progetto, ma perché ne corregge la descrizione: quello che il sistema misura oggi è accoppiamento cross-scala, non integrazione causale. Riportare questo genere di risultato con la stessa esplicitezza con cui si riporterebbe un successo è, a nostro avviso, precondizione necessaria perché il progetto — nelle sue componenti che *hanno* superato la verifica — venga preso sul serio dalla comunità a cui si rivolge.

---

## Riferimenti

- Baars, B. J. (1988). *A Cognitive Theory of Consciousness*. Cambridge University Press.
- Baars, B. J. (2005). Global workspace theory of consciousness: toward a cognitive neuroscience of human experience. *Progress in Brain Research*, 150, 45–53.
- Bi, G., & Poo, M. (1998). Synaptic modifications in cultured hippocampal neurons: dependence on spike timing, synaptic strength, and postsynaptic cell type. *Journal of Neuroscience*, 18(24), 10464–10472.
- Cerullo, M. A. (2015). The problem with Phi: a critique of Integrated Information Theory. *PLoS Computational Biology*, 11(9), e1004286.
- Friston, K. (2010). The free-energy principle: a unified brain theory? *Nature Reviews Neuroscience*, 11(2), 127–138.
- Friston, K., FitzGerald, T., Rigoli, F., Schwartenbeck, P., & Pezzulo, G. (2017). Active inference: a process theory. *Neural Computation*, 29(1), 1–49.
- Haken, H. (1988). *Information and Self-Organization: A Macroscopic Approach to Complex Systems*. Springer.
- Haken, H. (2004). *Synergetics: Introduction and Advanced Topics*. Springer.
- Markram, H., Lübke, J., Frotscher, M., & Sakmann, B. (1997). Regulation of synaptic efficacy by coincidence of postsynaptic APs and EPSPs. *Science*, 275(5297), 213–215.
- Tononi, G. (2004). An information integration theory of consciousness. *BMC Neuroscience*, 5, 42.
- Tononi, G., Boly, M., Massimini, M., & Koch, C. (2016). Integrated information theory: from consciousness to its physical substrate. *Nature Reviews Neuroscience*, 17(7), 450–461.
- Albantakis, L., Barbosa, L., Findlay, G., et al. (2023). Integrated Information Theory (IIT) 4.0: formulating the properties of phenomenal existence in physical terms. *PLoS Computational Biology*, 19(10), e1011465.
- QuTech / TU Delft. Quantum Inspire platform documentation. https://www.quantum-inspire.com/
- QuTech / TU Delft. cQASM 3.0 language specification. https://www.quantum-inspire.com/kbase/cqasm/

*Riferimenti aggiuntivi su Global Workspace, active inference e sinergetica applicati a sistemi artificiali — da integrare secondo le fonti specifiche già consultate nello sviluppo del progetto.*
