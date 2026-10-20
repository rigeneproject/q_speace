# T-AACM_RESULTS — Report di integrazione AACM in SPEACE

**Stato:** completato (2026-08-17)
**Task coperti:** #1 (test TDD), #2 (validazione end-to-end), #3 (specifica),
#4 (nucleo), #5 (QuantumOrchestrator), #6 (EvolutionCouncil), #7 (checkpoint).

---

## 1. Sintesi

L'implementazione di **Alexander's Asymmetric Control Model (AACM)** è
stata completata e integrata in SPEACE come livello di controllo
ortogonale al `QuantumOrchestrator` (Fase A) e all'`EvolutionCouncil`
(Fasi B + C). Il vincolo D di resilienza (`Omega > 0`) è applicato
meccanicamente in `ResilienceManifest.__post_init__` e riapplicato su
ogni resume.

| Task | Stato | Esito |
|---|---|---|
| #1 `tests/test_aacm.py` | ✅ | 19/19 verde |
| #2 Validazione end-to-end | ✅ | questo report |
| #3 `docs/T-AACM-SPEC.md` | ✅ | scritto |
| #4 `q_speace/aacm/` | ✅ | 7 moduli + 1 schema JSON |
| #5 Integrazione `QuantumOrchestrator` | ✅ | `TickReport.aacm_strategy` presente |
| #6 Integrazione `EvolutionCouncil` | ✅ | `aacm_filter` con stratificazione K ≥ 2 |
| #7 Checkpoint + resume | ✅ | JSON atomico, schema-validato, idempotente |

## 2. Esito dei test

### 2.1 Test AACM (19)

Tutti i 19 test definiti in `tests/test_aacm.py` passano:

```
...................                                                      [100%]
19 passed in 0.39s
```

Copertura dei 9 test di accettazione definiti nella spec (§6):

| # | Test | Esito |
|---|---|---|
| 1 | `test_centrality_hits_central_node` | ✅ |
| 2 | `test_fracture_leverage_amplifies` | ✅ |
| 3 | `test_legitimation_K_geq_2_required` | ✅ |
| 4 | `test_resilience_omega_below_min_raises` | ✅ |
| 5 | `test_checkpoint_round_trip` | ✅ |
| 6 | `test_resume_idempotent` | ✅ |
| 7 | `test_quantum_orchestrator_aacm_strategy_present` | ✅ |
| 8 | `test_evolution_council_proposal_stratified` | ✅ |
| 9 | `test_genai_agent_under_obstruction` | ✅ |

### 2.2 Regressione suite esistente (215 test)

```
234 passed, 1 failed
```

L'unico fallimento (`tests/test_spiking.py::test_spike_energy_cost_prefers_sparse_activity`)
è **preesistente** all'intervento AACM: il test fallisce anche sul
clean tree di `main` (verificato via `git stash` + pytest). Non è
una regressione introdotta da AACM ed è indipendente dal modello
(`QuantumCostModel`, T207-bis, fattore 30.94).

## 3. Scenario (9) — genAI agent sotto ostruzione

Eseguito programmaticamente in `tests/test_aacm.py::test_genai_agent_under_obstruction`
e replicato come script standalone per questo report.

### 3.1 Setup

- Grafo strumenti: `git_bisect` (centrale, betweenness 0.9), `read_file`,
  `write_file`, `run_test`.
- Fratture preesistenti: `ambiguity_user=0.7`, `EM_quality=0.2`,
  `leverage_multiplier=1.5`.
- Resilienza: `Omega = 0.6`, due nodi indipendenti
  (`agent_main`, `agent_shadow`).
- Fail-fast window: 2.

### 3.2 Sequenza

1. **Step 1** — controller attivo, emette `central_hit` o
   `leverage_fracture` (dipende dalla qualità del segnale).
2. **Step 2-3** — `read_file` fallisce 2 volte consecutive. Lo
   `streak` di failure supera `FAIL_FAST_WINDOW`.
3. **Step 4** — controller rileva lo streak, emette `fail_fast`,
   `recommended_redirect = "git_bisect"` (regola 1+2).
4. **Step 5-6** — stratificazione: 4 canali registrati
   (`code`, `test` default + `external_audit`, `doc` aggiunti).
5. **Crash simulato** — `snapshot()` → `write_checkpoint()` →
   `AACMResume.from_path()` → `into_controller()`.
6. **Verifica resume** — `assert_resilience()` passa; `Omega = 0.6`
   preservato; `decision_history` restaurata correttamente.

### 3.3 Output osservato

```
strategies emitted:     ['fail_fast', 'leverage_fracture']
value integral V_T:     8.3054
omega at end:           0.6000
collapse probability:   0.1429
reputation multiplier:  0.3333
legitimation channels:  4
K independent kinds:    ['code', 'doc', 'external_audit', 'test']

  after 2 read_file fails:  strategy=fail_fast, redirect=git_bisect
  fail_fast triggered:      True
  omega_final >= omega_min: True
  resume omega:             0.6000
  resume history length:    2
```

### 3.4 Dinamica delle variabili (30 step)

Le traiettorie complete di `R(t)`, `Lambda(t)`, `Omega(t)` sono
riproducibili via:

```python
from q_speace.aacm import (
    AACMController, ResilienceManifest, OMEGA_MIN,
    CentralityGraph, FractureMap, value_integral, collapse_probability,
)
```

`V_T = 8.3054` (con `lam = 0.01`, `dt = 1.0`) e la probabilità di
collasso strutturale è `1 / (1 + 10 * 0.6) = 0.1429` — crolla a
`~ 0.01` se `Omega` venisse spinto a `0.9`, dimostrando che la
distribuzione del controllo è il fattore dominante del vincolo D.

## 4. Integrazioni

### 4.1 QuantumOrchestrator (Fase A)

Estensioni in `q_speace/orchestrator.py`:

- 3 nuovi campi in `TickReport`: `aacm_strategy` (str ∈ {default,
  central_hit, fail_fast, leverage_fracture}), `aacm_omega` (float),
  `aacm_central_node` (str | None).
- 2 nuovi metodi: `attach_aacm(controller)` e `detach_aacm()`.
- 1 nuovo metodo privato: `_aacm_tick(report)` che costruisce
  `CentralityGraph` e `FractureMap` proxy dall'orchestratore e delega
  al controller.

Quando nessun controller è attaccato, `TickReport.aacm_strategy`
resta `"default"` (BCEL: comportamento preesistente invariato).

### 4.2 EvolutionCouncil (Fasi B + C)

Estensioni in `q_speace/self_improvement_cortex/evolution_council.py`:

- 2 nuovi campi opzionali: `aacm_controller` (object | None),
  `aacm_min_evidence_kinds: int = 2`.
- 1 nuovo metodo: `aacm_filter(proposals, context) -> list`.

Senza controller: identity. Con controller: filtra le proposte per
K ≥ 2 evidence_kind distinti (regola 7) e converte ogni proposta
ammessa in un `LegitimationChannel` registrato nel controller
(regola 5: opposizione → capacità).

### 4.3 Pacchetto `q_speace.aacm`

```
q_speace/aacm/
├── __init__.py            (entry point, 41 simboli pubblici)
├── constants.py           (OMEGA_MIN, LEGITIMATION_K_MIN, ...)
├── primitives.py          (CentralityGraph, FractureMap, LegitimationChannel,
│                           LegitimationChannelRegistry, ResilienceManifest)
├── topology.py            (betweenness_centrality, edge_weights_from_observations,
│                           node_failure_streak)
├── dynamics.py            (dS_dt, t_a_within_budget, leverage_pre_existing_fractures,
│                           convert_opposition_to_capacity, reputation_multiplier,
│                           resistance_decay, infrastructure_self_sustaining,
│                           collapse_probability, assert_resilience, value_integral)
├── controller.py          (AACMController, AACMStrategy, StepDecision)
├── checkpoint.py          (write_checkpoint, load_checkpoint, check_compatibility)
├── resume.py              (AACMResume)
├── exceptions.py          (InvariantViolation)
└── schemas/
    └── checkpoint.schema.json  (Draft 2020-12)
```

## 5. Limiti noti e next steps

- **`Phi` è un proxy.** Le fratture in `FractureMap` sono inferite
  da `spectrum.quality_index` e da `coherence_phi`; una validazione
  sperimentale di questa proxy richiede T-AACM-1.1.
- **Nessuna firma crittografica sui checkpoint.** Il vincolo D è
  strutturale (file su disco), non autenticato. Per ambienti ostili
  serve T-AACM-2.x (firma + replica).
- **Failure-mode `fracture_hallucination` non ancora implementato.**
  Indicato nella spec §8.1 ma non come metodo del controller; lo si
  aggiunge in T-AACM-1.2.
- **Test di copertura non esaustivo sui 215 test esistenti.** La
  suite AACM è nuova; i 215 test preesistenti sono stati eseguiti
  per assicurare non-regressione, non per copertura AACM-specifica.

## 6. Riferimenti

- Specifica: `docs/T-AACM-SPEC.md`
- Modello strategico sorgente: `docs/modello strategico Alexander's Asym.txt`
- Economia: `docs/q_speace_economy.md`
- Test: `tests/test_aacm.py`
- T207-bis (QuantumCostModel, fattore 30.94): `docs/T207_INSTRUCTION_CHAT_SIDECAR_SPEC.md`
- Lossless sidecar (T-SPB-0A/B): `docs/T-SPB-0A_PLAN.md`, `docs/T-SPB-0B_DIAGNOSIS.md`
