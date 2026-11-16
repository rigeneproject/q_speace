# QH-01 — Verifica dinamica dell'omeostasi attuale

> Data: 2026-11-16 · Modalità: diagnostica read-only, nessuna modifica al codice
> Scope: `cellular_speace/speace_core/` (esclusi duplicati in `.claude/worktrees/`)
> Method: (1) audit statico (grep + lettura, call-site di produzione);
> (2) sonda componente-level su `GlobalHomeostaticDrive` + `ActionBias` +
> `ActiveInferenceEngine`; (3) sonda end-to-end su `CellularBrainOrchestrator`
> (15 tick, MVP, 80 neuroni, deficit energetico forzato e ripristinato).

## 1. Audit statico — mappa delle connessioni

### 1.1 Connessioni reali verificate

| Flusso | Stato | Evidenza |
|---|---|---|
| HomeostasisEngine → sistema | Integrato | orchestrator.py:480; `SystemMetrics` consumato da 8 moduli (region_signal_router, sleep_cycle_detector, apoptosis_engine, energy_control_agent, confidence_engine, …) |
| SystemMetrics → GlobalHomeostaticDrive | Integrato | orchestrator.py:1200-1203; anche substrate_coordinator.py:403-406 |
| Drive → modulazione parametri | Parziale | orchestrator.py:1206-1217 applica solo plasticity/exploration; **energy_supply_multiplier e stability_multiplier calcolati ma mai consumati** |
| ActiveInference → Actuator | Inline, incompleto | orchestrator.py:1453-1465; **beliefs vuoti nel percorso MVP** → `step()` ritorna None |
| Physiome/PSN → sistema | Solo osservabilità | orchestrator.py:656; consumato solo da CognitiveObservatory/OCCAP |
| drives/action_bias (T-HDAS) | **Non cablato** | zero call-site in produzione |
| embodiment/active_inference_embodied_loop (T-AIEL) | **Non cablato** | istanziato solo in tests/test_continuous_substrate.py:258 |
| autonomic/autonomic_nervous_system + AutonomousDriveEngine | **Non cablato** | solo import auto-referenziali; `monitoring/energy_drive_rewriter.py` si definisce "workaround" |

## 2. Verifica dinamica componente-level

Perturbazioni controllate; alimentazione identica a orchestrator.py:1200-1203.

| Scenario | expl | stab | surv | eff | plast_M | expl_M | esup_M | stab_M |
|---|---|---|---|---|---|---|---|---|
| A baseline (noise=.5 phi=.8 E=.8) | 0.00 | 0.30 | -0.00 | 0.20 | 1.00 | 1.00 | 0.90 | 1.15 |
| B deficit (noise=.5 phi=.8 E=.15) | 0.00 | 0.30 | **+0.97** | **-0.45** | **0.39** | **0.55** | **1.21** | 1.15 |
| C rumore alto (noise=1.0) | +0.50 | 0.30 | -0.00 | 0.20 | 1.46 | 1.46 | 0.90 | 1.15 |
| D coerenza bassa (phi=.1) | 0.00 | -0.40 | -0.00 | 0.20 | 1.00 | 1.00 | 0.90 | 0.81 |

Polarità corretta: deficit → survival ↑, soppressione plasticità/esplorazione.

### 2.1 ActionBias vs percorso produttivo (set d'azioni sintetico, 7 azioni)

| Scenario | Produzione (solo EFE) | + ActionBias (wiring proposto) |
|---|---|---|
| A baseline | hibernate | hibernate |
| B deficit | hibernate | **request_sleep** (flip) |
| C rumore alto | hibernate | hibernate |
| D coerenza bassa | hibernate | hibernate |

Lo stesso ambiente con stato interno diverso produce decisioni diverse solo
quando ActionBias è cablato — dimostrazione meccanica del valore del wiring
T-HOME-01. Caveat: distribuzioni di outcome sintetiche (non quelle dell'
orchestrator); test fuori-tree, deterministico, singolo run.

## 3. Verifica dinamica end-to-end (CellularBrainOrchestrator reale)

| Fase | survival | efficiency | plasticity_M | exploration_M | energy_supply_M | AI beliefs |
|---|---|---|---|---|---|---|
| 1 baseline (5 tick) | -0.2127 | +0.3418 | 0.5379 | 0.5379 | 0.8355 | {} |
| 2 deficit E=0.10 (5 tick) | **+0.96** | **-0.44** | **0.1663** | **0.2469** | **1.2068** | {} |
| 3 ripristino E=0.90 (5 tick) | -0.15 | +0.30 | 0.5379 | 0.5379 | 0.8543 | {} |

Il circuito drive → moltiplicatori → parametri dei neuroni è **operante e
reversibile** nel percorso produttivo. `ActiveInferenceEngine` è invece
**morto** in questa configurazione (nessuno stato/azione registrato).

## 4. Finding aggiuntivi

1. **Confound strutturale**: `mean_energy` pilota survival ed efficiency
   simultaneamente (orchestrator.py:1202-1203); ogni perturbazione energetica
   muove due drive. Per ablazioni pulite serve una sorgente `survival`
   disaccoppiata (T-HOME-02.4).
2. **Semantica energy_supply**: sale col deficit (0.90 → 1.21) — boost
   compensativo; ma non ha consumer nel percorso orchestrator. Semantica da
   fissare prima del wiring (T-HOME-01.5).
3. **Python 3.12 vs 3.13+**: `vfs_engine.py:220` usa
   `Path.is_file(follow_symlinks=...)` (API 3.13+); `build_mvp` crasha su
   3.12 mentre pyproject dichiara `python_version = "3.12"`. Il probe gira
   su Python 3.14.
4. **PATH inquinato**: un checkout vecchio
   (`C:\Users\rober\Desktop\cellular_speace_opus\36\cellular_speace`) è nel
   sys.path di sistema; rischio di import da copia stantia in script fuori dal
   repo. Da rimuovere dal PATH di sistema.

## 5. Conclusioni e handoff

- Endogeneità del segnale: **parziale** (drive da metriche interne, non eventi
  esterni).
- Endogeneità motivazionale: **non dimostrata** (AutonomousDriveEngine non
  cablato).
- Endogeneità comportamentale: **incompleta** (drive non influenzano la
  selezione azioni — ActionBias non cablato).
- L'omeostasi computazionale (Config B) è operante e reversibile; la
  configurazione C (predittiva/evolutiva) è assente.

Follow-up: T-HOME-01 (wiring), T-HOME-02 (PSN→drive), T-HOME-03
(omeostasi predittiva). Nessuna valutazione d'integrazione host prima del
percorso T217.
