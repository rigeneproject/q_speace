# T-HOME-02 — Integrazione fisiologica PSN → Drive

> Stato: SPEC / non implementato · Priorità: media · Modalità: agentic
> Predecessore: T-HOME-01 · Successore: T-HOME-03

## 1. Motivazione

`PhysiologicalSignalBus` (PSN, `cellular_brain/psn/`) è creato in
orchestrator.py:656 con `epigenetic_signals` disponibili, ma è consumato **solo
dai metrics del CognitiveObservatory/OCCAP** (analisi/osservabilità).
Nessun segnale fisiologico raggiunge `GlobalHomeostaticDrive` o la selezione
delle azioni. Questo è il punto d'aggancio naturale per i futuri segnali
robotici (batteria, temperatura, integrità strutturale) senza toccare
l'attuazione.

La verifica dinamica QH-01 ha inoltre evidenziato un **confound strutturale**:
`orchestrator.py:1202-1203` mappa lo stesso `mean_energy` su due drive
(`survival = 1 - E`, `efficiency = E`). Ogni perturbazione energetica muove
sempre due drive contemporaneamente; l'adapter deve permettere sorgenti
indipendenti per ablazione pulita.

## 2. Obiettivo

Un adapter che instradi i segnali fisiologici validati della PSN come sorgenti
di modulazione dei drive, con normalizzazione, timestamp e gestione dei dati
mancanti.

## 3. Design

### 3.1 Adapter `PhysioDriveAdapter`

- Input: stream PSN (segnali constitutional + epigenetici).
- Output: valori pronti per `GlobalHomeostaticDrive.update_drive(name, value)`.
- Trasformazioni per segnale:
  - normalizzazione nell'intervallo atteso del drive;
  - `timestamp` e staleness: segnale più vecchio di `max_age` → valore tenuto
    (hold) o degradato verso il setpoint, secondo policy configurata;
  - dato mancante: valore hold + flag `stale` esposto ai metric;
  - clamp sui limiti di modulazione (nessun segnale singolo può saturare la
    funzione obiettivo).
- Mappatura sorgente→drive **configurabile**: default mantiene la mappatura
  attuale (`orchestrator.py:1200-1203`) per retrocompatibilità; le sorgenti PSN
  si aggiungono come input secondari con peso limitato.

### 3.2 Disaccoppiamento del confound energetico

Esporre la possibilità di alimentare `survival` da una sorgente dedicata
(integrità/danno) distinta da `mean_energy`, così che QH-01 possa perturbare un
drive per volta. La mappatura attuale resta il default.

## 4. Invarianti

- L'adapter **legge** dalla PSN e **scrive** solo su `update_drive()`: nessun
  percorso diretto segnale→attuatore.
- Segnali non registrati in ontologia PSN (`is_signal_registered`) sono
  rifiutati: nessun input non validato entra nella regolazione.
- I limiti di modulazione sono parametri configurati nel genome/config, non
  valori hard-coded nel circuito cognitivo.

## 5. Criteri di accettazione

1. Variazioni controllate di un segnale PSN producono modifiche misurabili e
   riproducibili nei drive corrispondenti (≥ 5 run).
2. Segnale stale/assente → comportamento di hold documentato e testato, senza
   errori né salti discontinui.
3. Con tutte le sorgenti PSN assenti, il comportamento del sistema è
   **identico** allo stato pre-T-HOME-02 (retrocompatibilità bit a bit sui
   moltiplicatori).
4. Clamping verificato: un segnale fuori scala non produce moltiplicatori
   fuori dai range dichiarati.

## 6. Task checklist

- [ ] T-HOME-02.1 — spec review
- [ ] T-HOME-02.2 — implementazione `PhysioDriveAdapter`
- [ ] T-HOME-02.3 — policy staleness/hold + test
- [ ] T-HOME-02.4 — sorgente `survival` disaccoppiata da `mean_energy` (flag)
- [ ] T-HOME-02.5 — test retrocompatibilità (PSN vuota → output identico)
- [ ] T-HOME-02.6 — integrazione orchestrator dietro flag dedicato
