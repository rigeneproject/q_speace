# T-HOME-03 — Omeostasi predittiva con modulazione epigenetica (Config C)

> Stato: SPEC / non implementato · Priorità: media · Modalità: agentic
> Predecessore: T-HOME-01 (wiring), T-HOME-02 (PSN)

## 1. Motivazione

La verifica dinamica QH-01 ha stabilito che:

- **Config A** (drive con setpoint/weight statici): operante.
- **Config B** (drive ricalcolati ogni tick dallo stato fisiologico corrente):
  già operante — `orchestrator.py:1200-1204` ricalcola i drive da `SystemMetrics`
  interne; polarità verificata dinamicamente (deficit → survival +0.96,
  plasticità 0.538 → 0.166, ritorno reversibile a baseline).
- **Config C** (drive predittivi, memoria, epigenetica): **assente**.

Il salto richiesto non è più wiring ma funzionamento nuovo: il sistema deve
anticipare il proprio deterioramento, non solo reagire.

## 2. Formalizzazione

```
D_i(t) = f_i(x_t, x̂_t+k, M_t, E_t)

a*_t = argmin_{a ∈ A_safe} [ G(a|s_t) + λ_t · H(a|s_t) ]

λ_t = g(x_t, x̂_t+k, M_t, E_t)
```

- `D_i` — drive i-esimo (esistente in `GlobalHomeostaticDrive`).
- `x_t` — stato fisiologico corrente (già presente).
- `x̂_t+k` — **stato futuro previsto** (nuovo: modello di consumo energetico,
  trend di degrado; candidato: riutilizzo del world model del loop embodied).
- `M_t` — memoria delle perturbazioni (nuovo: storia dei deficit e delle
  strategie di regolazione adottate, persistente su disco come
  `AutonomousDriveEngine._history_path`).
- `E_t` — stato epigenetico (nuovo per i drive: modulazione persistente dei
  setpoint/weight in funzione della storia — aggancio a T-HOME-02 e alle
  `epigenetic_signals` della PSN).
- `H(a|s_t)` — costo omeostatico previsto dell'azione (già esistente come
  bias in `ActionBias`, da estendere con componenti predittive).
- `A_safe` — ammissibilità secondo la governance deterministica (invariante).

Nota: verificare che l'EFE esistente (`active_inference_engine.py:47-80`)
non includa già termini omeostatici prima di sommare `H` (rischio
doppio conteggio). All'ispezione attuale l'EFE è puro (surprise − epistemic
value), quindi la somma è corretta, ma la verifica va ripetuta dopo T-HOME-01.

## 3. Esperimento QH-01 (protocollo preregistrato)

### 3.1 Configurazioni

| Config | Drive | Sorgenti |
|---|---|---|
| A | statici | setpoint/weight fissi, nessun update per tick |
| B | dinamici correnti | `SystemMetrics` per tick (stato attuale) |
| C | predittivi | B + `x̂_t+k`, `M_t`, `E_t` |

Condizioni iniziali, capacità di controllo e risorse **comparabili** fra
configurazioni. Nessuna configurazione riceve più informazione esterna.

### 3.2 Scenari

- Deficit energetico graduale (slope noto) e improvviso (step).
- Perturbazioni di rumore e coerenza.
- Scenari **non visti** in calibrazione (riservati alla valutazione).

### 3.3 Metriche

| Metrica | Definizione operativa |
|---|---|
| Anticipazione | tempo di reazione prima della soglia critica |
| Resilienza | recupero (tempo e ampiezza) dopo perturbazione |
| Adattamento | miglioramento fra episodi ripetuti |
| Autonomia | frazione di decisioni originate dallo stato interno (e non da input esterni coevi) |

### 3.4 Ablazioni (obbligatorie per l'attribuzione causale)

- C senza predizione (solo B + memoria + epigenetica).
- C senza memoria (solo predizione + epigenetica).
- C senza epigenetica (solo predizione + memoria).
- B senza drive (controllo: nessun flip atteso).

Il contributo di ciascun meccanismo è dichiarato solo se isolabile
dall'ablazione corrispondente.

### 3.5 Criterio di accettazione

La configurazione C supera B sulle metriche predefinite negli scenari non
visti, con ablazioni che isolano il contributo di previsione, memoria ed
epigenetica. Risultato preregistrato nel report prima dell'esecuzione.

## 4. Invarianti

- Come T-HOME-01: GenAI/active-inference propone, attuazione governata;
  i vincoli di sicurezza non sono mai oggetto di apprendimento o
  modulazione epigenetica (`A_safe` non è modificabile dai drive).
- Nessun claim di esperienza soggettiva o "istinto sentito": la
  documentazione descrive regolazione comportamentale, non qualia.

## 5. Task checklist

- [ ] T-HOME-03.1 — spec review + preregistrazione protocollo
- [ ] T-HOME-03.2 — modello di previsione `x̂_t+k` (riuso world-model o nuovo)
- [ ] T-HOME-03.3 — memoria perturbazioni persistente
- [ ] T-HOME-03.4 — modulazione epigenetica dei setpoint/weight (limitata,
      con clamp e audit)
- [ ] T-HOME-03.5 — estensione `H` con componenti predittive + test
      anti-doppio-conteggio con EFE
- [ ] T-HOME-03.6 — harness QH-01 A/B/C + ablazioni
- [ ] T-HOME-03.7 — esecuzione, report preregistrato, revisione indipendente
      (per eventuale promozione: percorso T217)
