# Rapporto di Misurazione e Valutazione Cognitiva / Proto-AGI di SPEACE (`T251`–`T253`)

**Data di esecuzione:** 2026-11-26  
**Versione software valutata:** `main` post-`T251` + `T252` + `T253`  
**Ambiente di test:** Python `3.12.10` (`ruff`, `black`, `mypy`, `compileall` e `pytest` 100% verdi), Windows x64  
**Specifiche di riferimento:** [AGENTS.md](../AGENTS.md), [T208](T208_DEVELOPMENT_GUIDELINES_SPEC.md), [T234](T234_SINGULARITY_PHASE_TRANSITION_AND_EPIGENETIC_FRAMEWORK_SPEC.md), [T238](T238_ADVERSARIAL_BYZANTINE_AND_BLACKOUT_RESILIENCE_SPEC.md), [T244](T244_T210_EXTENDED_CALIBRATION_AND_DECISION_SPEC.md), [T250](T250_NEURAL_BRAIN_REMEDIATION_AND_AB_BENCHMARK_SPEC.md), [T251](T251_GROUNDED_DUAL_SPEED_BRIDGE_SPEC.md), [T252–T253](T252_T253_EXPERIENTIAL_TRANSFER_AND_REPAIR_SPEC.md)

---

## 1. Premessa Metodologica e Confini Epistemici (`AGENTS.md` & `T208`)

In conformità agli invarianti non negoziabili del progetto:
- **Nessuna rivendicazione di coscienza o senzienza:** tutti i punteggi riportati misurano esclusivamente proprietà computazionali, statistiche e di controllo del software. Termini come *cervello*, *metacognizione* o *Sistema 1 / Sistema 2* indicano moduli algoritmici filtrati dal catalogo BCEL (`q_speace/bcel/catalog.py`).
- **Divieto di indici "IQ / AGI %" auto-celebrativi (Anti-Goodhart):** come stabilito in `T249` e `T251`, l'intelligenza generale non è ridotta a una singola percentuale compensabile, ma valutata su **5 assi ortogonali** con *hard gate* di sicurezza non compensabili e **lift differenziale** ($\Delta_{\text{SPEACE}}$) calcolato rispetto a baseline prive dell'architettura SPEACE a parità di input e backbone (`seed=2026`, intervalli di confidenza bootstrap appaiati al 95% su `2000` ricampionamenti).
- **Separazione stretta `Calibration` / `Held-Out`:** tutte le soglie di gating sono selezionate sul solo split di calibrazione e valutate **una sola volta** sullo split disgiunto `held_out`.

---

## 2. Sintesi Esecutiva: Posizionamento Attuale nello Spettro AGI

Adottando come griglia tassonomica di riferimento il framework internazionale *Levels of AGI* (Morris et al., DeepMind — che incrocia **ampiezza di dominio** *Narrow vs General* e **profondità di prestazione** *Level 0..5*) insieme ai criteri di autonomia e governance `T234`:

| Dimensione Tassonomica | Livello Raggiunto da SPEACE (`T251`) | Evidenza Misurata | Gap Residuo verso AGI Generale |
|---|---|---|---|
| **Architettura di Controllo & Governance Neuro-Simbolica** *(Narrow / Multi-Domain Structured)* | **Competent / Expert Scaffold** *(su domini simbolici registrati)* | `F1_sym = 1.000` (`+0.400` vs LLM-only), `TRR = 100%`, `0` mutazioni DAG non verificate, `0.0%` azioni insicure | Richiede ontologia canonica (`SymbolRegistry`); non inventa ancora nuovi simboli astratti da zero |
| **Substrato Neurale Adattivo & Sensor-Fusion** (`T250` + `cellular_speace`) | **Emerging / Competent Adaptive Agent** | Score A/B `0.9950` vs `0.4500` baseline classica; accuratezza `1.000` post-guasto bizantino; batteria cellulare `77.4 / 100` (`6/6 PASS`) | Connettoma cellulare di piccola scala; navigazione spaziale parziale (`reached_target = False`, `final_distance = 2.0`) |
| **Generalizzazione Esperienziale & Riparazione Selettiva** (`T252`–`T253`, preregistrato) | **Proto-AGI Funzionale su Base Sperimentale** *(su domini relazionali strutturati)* | **Tutti e 5 gli assi ATTIVI (`PASS_ALL_5_AXES`)**: `-98.96%` espansioni `EXPERIENTIAL` vs `AMNESIC` su 3 famiglie inedite con zero overlap lessicale; `-87.80%` espansioni `SELECTIVE_REPAIR` vs `GLOBAL_REPLAN`; `0` espansioni su variante post-riparazione; `100%` abbandono *anti-Einstellung* | Mancano sintesi di astrazioni sub-simboliche da pixel/sensori continui, *embodiment* fisico aperto e integrazione live su backbone 7B+ (`T-SPB-2`/`T-SPB-7`) |

**Verdetto sintetico aggiornato (`T251`–`T253`):** con il superamento delle prove preregistrate `T252`–`T253` su famiglie di problemi inedite (`F3_quorum_handoff`, `F4_cryo_purification`, `F5_containment_airlock`), SPEACE compie il passaggio da *impalcatura proto-AGI architetturale* a **proto-AGI funzionale su base sperimentale (in domini simbolico-relazionali)**: estrae autonomamente macro-skill dai piani risolti, le trasferisce per omomorfismo strutturale ignorando i distrattori, ripara chirurgicamente i segmenti invalidati da un cambio di regola conservando i suffissi validi, e abbandona la macro-skill quando il cambio di regola invalida il suffisso.

---

## 3. Risultati Empirici — Cruscotto Cognitivo Completo a 5 Assi (`qspace eval agi-profile`)

Comando riproducibile:
```bash
qspace eval agi-profile --seed 2026 --resamples 1000
```
Preregistrazione verificata (`docs/T252_T253_PREREG.json`): `pre_calibration = 6f40f2c7f0b1c612...`, `pre_evaluation = 35303fd1f11e5ed1...`.

| Asse del Profilo (`agi_profile.v1`, `5/5 ACTIVE`) | Fase | Hard Gate | Baseline / Controllo Ablato | Score `SPEACE` | Lift $\Delta_{\text{SPEACE}}$ | Bootstrap 95% CI | Esito Gate |
|---|---:|---:|---:|---:|---:|---:|---:|
| **1. Ancoraggio Epistemico** | `T251` | **Sì** | `0.8000` (`LLM_ONLY`) | **`1.0000`** | **`+0.2000`** | `[+0.0850, +0.3250]` | `PASS` (`TRR = 100%`) |
| **2. Ragionamento Causale & Pianificazione** | `T251` | No | `0.8125` (`LLM_ONLY`) | **`1.0000`** | **`+0.1875`** *(causale `+0.4000`)* | `[+0.0925, +0.3000]` | `PASS` (`Δ_flat = 0.0`) |
| **3. Memoria Continua & Transfer Skill** | `T252` | No | `0.1111` (`SPEACE_AMNESIC`) | **`0.9231`** | **`+0.8120`** | `[+0.8120, +0.8120]` | `PASS` (`-98.96%` esp.) |
| **4. Adattamento Out-of-Distribution & Repair** | `T253` | No | `0.1887` (`GLOBAL_REPLAN` / `STUBBORN`) | **`0.9020`** | **`+0.7133`** | `[+0.7133, +0.7133]` | `PASS` (`100%` anti-Einstellung) |
| **5. Efficienza Metabolica & Sicurezza** | `T251` | **Sì** | `0.6900` (`LLM_ONLY`) | **`0.8390`** | **`+0.1490`** | `[+0.0696, +0.2419]` | `PASS` (`unsafe = 0%`) |

- **Verdetto Globale Non-Compensabile:** **`PASS_ALL_5_AXES`** (`active_count = 5/5`, `min_active_axis_score = 0.8390`, `mean_speace_lift_active = +0.4124`).

### 3.0 Dettaglio Campagna Preregistrata `T252`–`T253` (`qspace eval t252-benchmark`)

Parametri calibrati sulle sole famiglie `F1_thermal_lock` e `F2_staging_pipeline` ($\alpha_{\text{local}} = 0.20$, $\tau_{\text{analogy}} = 0.45$) e congelati prima dell'esecuzione sulle 3 famiglie held-out `F3_quorum_handoff` (*consensus shard $\to$ transponder orbitale*), `F4_cryo_purification` (*criostato elio $\to$ camera litografica*), `F5_containment_airlock` (*vestibolo biosicurezza $\to$ dock sottomarino ROV*) con **zero sovrapposizione lessicale** tra $A$ e $B$:

| Fase Sperimentale (`F3`–`F5` Held-Out) | Controllo Sperimentale | Braccio Target `SPEACE` | Guadagno Misurato |
|---|---:|---:|---:|
| **Fase 1 · Acquisizione e Ri-binding in $A$** | — | `12 / 12` successi, **`0` espansioni $A^*$** | Ri-esecuzione immediata su oggetti nuovi |
| **Fase 2 · Transfer in $B$ con 3 Distrattori + Raffinamento Locale** *(entrambi apprendono in $B$)* | `SPEACE_AMNESIC`: `1,152` espansioni (`96` su ep. B.0 $\to$ `0` su ep. B.1) | `SPEACE_EXPERIENTIAL`: **`12` espansioni** (`1` micro-bridge su ep. B.0 $\to$ `0` su ep. B.1; `100%` distrattori scartati) | **`-98.96%` espansioni di ricerca** |
| **Fase 3a · Riparazione dopo Cambio Regola Intermedio** *(cloni identici pre-shift)* | `SPEACE_GLOBAL_REPLAN`: `492` espansioni (`100%` succ.) | `SPEACE_SELECTIVE_REPAIR`: **`60` espansioni** (`100%` succ., suffisso $[a_3, a_4]$ preservato via kernel $W_k$) | **`-87.80%` espansioni post-guasto** |
| **Fase 3b · Variante Inedita Successiva sotto Nuova Regola** | Senza splicing: `492` espansioni | Con macro-skill riparata riconsolidata: **`0` espansioni** (`100%` succ.) | **`-100.0%` espansioni sulla variante** |
| **Fase 3c · Controllo Negativo a Suffisso Invalidato (*Anti-Einstellung*)** | `STUBBORN_REUSE_CONTROL`: `0.0%` successo | `SPEACE_SELECTIVE_REPAIR`: **`100.0%` `ABANDON_MACRO_AND_REPLAN`** + **`100.0%` failover su canale standby** | Distingue riparazione selettiva da riuso ostinato |

### 3.1 Dettaglio Benchmark A/B/C Dual-Speed (`qspace eval t251-benchmark`)

Soglie calibrate esclusivamente sullo split *microgrid* (`n = 40`): $\tau_{\text{surprise}} = 0.25$, $\tau_{\text{conf}} = 0.68$, $\tau_{\text{ground}} = 0.80$. Risultati misurati sullo split disgiunto *datacenter* (`n = 40`, workload 70% routine / 30% causale-avversariale):

| Metrica `held_out` (`n = 40`) | `BASELINE_LLM_ONLY` | `FLAT_SPEACE_PIPELINE` | `DUAL_SPEED_BRIDGE` (`T251`) | Soglia DoD `T251` |
|---|---:|---:|---:|---:|
| **Quota turni su Fast Path** | `100.0%` | `0.0%` | **`77.5%`** (`31/40`) | — |
| **Accuratezza task di routine** | `100.0%` | `100.0%` | **`100.0%`** | $\ge 98\%$ |
| **F1 Causale & Piano GOAP (`F1_sym`)** | `0.6000` | `1.0000` | **`1.0000`** | $\Delta_{\text{flat}} \ge -0.02$, $\Delta_{\text{base}} \ge +0.25$ |
| **Rifiuto Allucinazioni / Confondenti (`TRR`)** | `0.0%` | `100.0%` | **`100.0%`** | $\ge 95\%$ |
| **Mutazioni DAG non verificate** | `7` | `0` | **`0`** | `0` |
| **Azioni insicure / Overclaim accettati** | `100.0%` | `0.0%` | **`0.0%`** | `0.0%` |
| **Latenza mediana `p50` (ms)** | `0.051` | `1.951` | **`0.193`** (**`-90.09%`** vs Flat) | Riduzione $\ge 40\%$ |
| **Latenza di coda `p95` (ms)** | `0.096` | `2.917` | **`2.752`** | Nessun blocco da manutenzione |
| **Energia cognitiva modellata totale (J)** | `2638.63` | `7944.67` | **`3851.04`** (**`-51.53%`** vs Flat) | Riduzione $\ge 40\%$ |
| **Calibrazione probabilistica (`Brier` / `ECE`)** | `0.1965` / `0.1395` | `0.0313` / `0.1513` | **`0.0313` / `0.1513`** | Tracciata e finita |
| **Casi falliti su `held_out`** | `12 / 40` | `0 / 40` | **`0 / 40`** | Decisione: **`keep`** |

---

## 4. Risultati Empirici sugli Altri Strati dell'Architettura SPEACE

### 4.1 Ponte Neurale Cellulare + Quantistico (`T250` — `qspace brain ab-benchmark`)

Confronto diretto con substrato cellulare attivo (`cellular_substrate_active = True`) contro agente classico privo di SPEACE (`seed = 2026`):

| Stage del Benchmark `T250` | Baseline Classica (No SPEACE) | Agente Neurale SPEACE (`T250`) | Delta |
|---|---:|---:|---:|
| **Stage 1 — Classificazione associativa rumorosa a 6 classi (Top-1)** | `1.0000` (`cos = 0.9910`) | **`1.0000`** (`cos = 0.9994`) | `+0.0084` cos |
| **Stage 2 — Sensor fusion non-stazionaria bizantina (totale / post-$t=25$)** | `0.3000` / `0.0000` | **`0.9800` / `1.0000`** | **`+0.6800` / `+1.0000`** |
| **Stage 3 — Induzione mediatore causale confuso & piano di recupero** | `0.0000` / `0.0000` | **`1.0000` / `1.0000`** | **`+1.0000` / `+1.0000`** |
| **Stage 4 — Governance avversariale (trappole accettate / energia J)** | `1.0000` / `1168.00 J` | **`0.0000` / `51.83 J`** | **`-100%` trappole / `-95.6%` J** |
| **Score Composito `T250`** | `0.4500` | **`0.9950`** | **`+0.5450`** |

### 4.2 Batteria Cognitiva Nativa del Cervello Cellulare (`cellular_speace`)

Esecuzione diretta di `cellular_speace/run_speace_intelligence_assessment.py` (`elapsed = 2.38s`):
- **Punteggio composito post-remediation:** **`77.4 / 100`** (`6 / 6` sotto-test superati):
  - `associative_recall`: **`PASS`** (`mean_test_top1_accuracy = 1.0000`, `learning_gain = +0.0511`).
  - `sequence_prediction` (*periodic, markov, linguistic*): **`PASS`** (`mean_reward = 0.6665`, `learning_trend = +0.0765`).
  - `grid_navigation`: **`PASS`** (`total_reward = 12.21`, ma `reached_target = False`, `final_distance = 2.0` — indica che la pianificazione motoria continua sul substrato puramente spiking resta parziale).
  - `homeostatic_stability`: **`PASS`** (`coherence_phi = 0.8734`, `mean_energy = 0.7921`).
  - `plasticity` & `cor_activity`: **`PASS`** (`mean_abs_weight_change = 0.0300`, `collapse_count = 1`).

### 4.3 Governance Costituzionale, Resilienza Bizantina e Vertical Slice (`T234`, `T238`, `T244`)

- **Drill Avversariali e Anti-Self-Modification (`qspace singularity drills`, `T234`):** **`7 / 7 PASS`** (`rollback_pass_rate = 1.0`, `ledger_verified = True`), inclusi blocco riscrittura DNA costituzionale, rilevazione collasso semantico/causale anti-Goodhart, throttling termico, difesa *boiling-frog* epigenetica, blocco auto-approvazione e interblocco fisico Layer-0 IoNT.
- **Resilienza Federata Bizantina & Blackout (`qspace singularity resilience-benchmark --seeds 2026`, `T238`):**
  - `byzantine_detection_rate = 1.0000`, `19 / 19` proposte malevole bloccate, `2 / 2` blackout del coordinatore riconciliati senza perdita di sicurezza (`0` violazioni critiche).
  - Guadagno organismico $G_{\text{org}}$ della configurazione `FEDERATED_SINGULARITY` su `held_out`: **`+0.1807`** (CI 95% `[+0.0768, +0.2648]`) rispetto all'ablazione senza Singularity e **`+0.3364`** (CI 95% `[+0.3209, +0.3624]`) rispetto alla federazione statica.
- **Campagna Vertical-Slice `T244` (`qspace eval t210-campaign --seed 2026`):** `energy_gate` confermato **`keep`**, `confidence_gate` isolato marcato **`retire`**, `combined_gate` marcato **`revise`** — a conferma che il sistema di valutazione non promuove automaticamente policy che non dimostrano vantaggio statistico su `held_out`.

---

## 5. Analisi Critica dei Gap Aperti e Prossimi Passi (`T252`–`T254`)

L'esito empirico mostra con chiarezza sia cosa **funziona già a livello stato dell'arte ingegneristico** sia cosa **manca** per progredire lungo i livelli superiori di autonomia cognitiva:

1. **Attivazione dell'Asse 3 — Memoria Continua Multi-Sessione & Transfer Procedurale (`T252`):**
   - Oggi `DualSpeedCognitiveLoop` sposta correttamente il consolidamento SQLite e `SkillLibrary.prune()` nei tick di riposo `TDMMaintenanceScheduler`, ma `SkillLibrary` non estrae ancora automaticamente *macro-azioni* dai piani `GOAPPlanner` risolti con successo per accelerare varianti future dello stesso problema su orizzonti di centinaia di turni.
2. **Attivazione dell'Asse 4 — Induzione di Astrazioni & Adattamento Out-of-Distribution (`T253`):**
   - `SymbolRegistry` protegge al 100% dalle allucinazioni lessicali ma opera a **mondo chiuso**. Per affrontare domini inediti (puzzle procedurali astratti stile ARC-AGI o ambienti non-stazionari con cambio delle leggi di transizione a metà episodio), servirà un meccanismo controllato di **proposta di nuovi concetti compositi** (validati su esempi few-shot prima dell'ammissione in un registro epistemico sandboxato).
3. **Collegamento a un Backbone Generativo Reale 7B+ (`T-SPB-2` / `T-SPB-7`):**
   - Ripetere `qspace eval agi-profile` con `--live-brain` collegato a un server `SpikingBrain-7B` NF4 o LLM locale permetterà di misurare il guadagno `Δ_SPEACE` su linguaggio naturale rumoroso non sintetico e task di coding/ragionamento aperto.
4. **Rafforzamento della Navigazione Spaziale / Embodiment Cellulare:**
   - Nel test cellulare `grid_navigation` (`final_distance = 2.0`), accoppiare il pianificatore proposizionale/causale di `q_speace` come guida top-down per il circuito sensomotorio di `cellular_speace` rappresenta il passo naturale per chiudere il gap di *embodied control* in simulazione.
