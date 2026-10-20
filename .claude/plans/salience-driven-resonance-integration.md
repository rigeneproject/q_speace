# Piano: Salience-Driven Resonance Integration

## Obiettivo

Colmare il gap piú rilevante emerso dall'analisi dei meccanismi biologici in SPEACE: la mancanza di un **coordinamento temporale globale guidato dalla salienza**. Il cervello biologico non ha solo oscillatori e neuromodulatori, ma una **rete della salienza** che decide quali segnali meritano attenzione e quindi quali circuiti devono entrare in risonanza.

Il piano aggiunge una `SalienceNetworkLayer` esplicita, la collega a `DMNSwitchingEngine`, `ThalamicRelayEngine`, `GlobalWorkspace` e al routing inter-regionale, e ne verifica il funzionamento con test unitari e di integrazione.

---

## Stato attuale riassunto

- `FunctionalResonanceLayer`, `PhaseLockingEngine`, `ResonanceField` e `FrequencyOscillator` esistono e sono giá collegati al `RegionSignalRouter` tramite `_frl_routing_multipliers`.
- `DMNSwitchingEngine`, `ThalamicRelayEngine`, i 4 circuiti neuromodulatori e `GABAergicModulator` esistono e sono giá istanziabili nell'`orchestrator`, ma disabilitati di default.
- Manca un **modulo salienza** che aggregi: interocezione, errore predittivo, novitá e arousal neuromodulatorio.
- I test per i moduli dinamici avanzati (`DMNSwitchingEngine`, `ThalamicRelayEngine`, `GABAergicModulator`, `SalienceNetworkLayer`) non esistono.

---

## File da toccare

### Nuovi file

1. `speace_core/cellular_brain/dynamics/salience_network_layer.py`
   - Implementa `SalienceNetworkLayer` e `SalienceState`.
2. `tests/dynamics/test_salience_network_layer.py`
   - Test unitari del nuovo layer.
3. `tests/dynamics/test_orchestrator_salience_integration.py`
   - Test di integrazione con orchestrator + FRL + DMN + Talamo + Salience.

### File esistenti da modificare

4. `speace_core/cellular_brain/memory/morphology_events.py`
   - Aggiungere `SALIENCE_BURST`, `SALIENCE_DIP`, `SALIENCE_NETWORK_UPDATED`.
5. `speace_core/orchestrator.py`
   - Aggiungere flag `salience_network_enabled`.
   - Istanziare `_salience_network` in `model_post_init`.
   - In `_tick` calcolare input di salienza e passarli al layer.
   - Usare l'output di salienza come `salience_signal` per `DMNSwitchingEngine`.
   - Inoltrare la salienza a `ThalamicRelayEngine` (come parametro opzionale di `attention_focus`) e a `GlobalWorkspace` tramite broadcast.
   - Esportare `global_salience` in `_build_subsystem_context`.

---

## Design di `SalienceNetworkLayer`

### Input

| Segnale | Fonte nell'orchestrator | Peso default |
|---|---|---|
| `interoceptive_salience` | `metrics.noise_level` o derivato da stress/energia | 0.20 |
| `prediction_error` | `_predictive_coding.get_free_energy()` se abilitato | 0.25 |
| `novelty_signal` | Variazione di `coherence_phi` tra tick | 0.20 |
| `neuromodulator_arousal` | `_noradrenergic_modulator.state.noradrenaline_level` | 0.20 |
| `unexpected_event` | Input esterno (default 0) | 0.15 |

### Output

- `global_salience: float` in `[0, 1]`.
- `dominant_source: str` — canale con contributo maggiore.
- `salience_vector: Dict[str, float]` — contributi per canale.
- `state: SalienceState` — snapshot persistente.

### Comportamento

- `tick(...)` calcola i contributi pesati, normalizza in `[0,1]`, aggiorna uno smoothing EMA e, se la salienza supera soglie, emette eventi su `MorphologicalMemory`.
- Smoothing EMA evita oscillazioni troppo brusche (`alpha=0.3`).
- I pesi sono configurabili via `__init__` per consentire future calibrazioni.

---

## Integrazione nell'orchestrator

### Nuovo flag

```python
salience_network_enabled: bool = False
_salience_network: "SalienceNetworkLayer | None" = None
_last_global_salience: float = 0.0
```

### In `model_post_init`

```python
if self.salience_network_enabled:
    from speace_core.cellular_brain.dynamics.salience_network_layer import SalienceNetworkLayer
    self._salience_network = SalienceNetworkLayer()
```

### In `_tick`

1. Dopo il calcolo di `metrics` (o prima dei neuromodulatori, per poterlo usare anche da loro):
   - raccogliere `prediction_error`, `novelty`, `noradrenaline_level`, `interoceptive_proxy`.
   - chiamare `self._salience_network.tick(...)`.
   - salvare `self._last_global_salience = state.global_salience`.
2. Passare `salience_signal=self._last_global_salience` a `DMNSwitchingEngine.tick()`.
3. Aumentare `attention_focus` di `ThalamicRelayEngine.tick()` proporzionalmente alla salienza (clampato).
4. Se `global_workspace_enabled`, fare broadcast di un vettore 64D che codifichi la salienza, in modo che il workspace possa usarla per l'attention routing.

### In `_build_subsystem_context`

Aggiungere `global_salience` al dizionario di contesto per i coordinatori.

---

## Test

### Unitari (`tests/dynamics/test_salience_network_layer.py`)

1. `test_zero_input_produces_low_salience` — tutti gli input 0 → `global_salience < 0.1`.
2. `test_high_prediction_error_increases_salience` — prediction_error=1.0 → salienza alta.
3. `test_high_noradrenaline_increases_salience` — noradrenaline=0.9 → salienza alta.
4. `test_dominant_source_detection` — verifica che `dominant_source` identifichi il canale piú forte.
5. `test_events_logged_on_burst_and_dip` — verifica eventi `SALIENCE_BURST`/`SALIENCE_DIP` in `MorphologicalMemory`.

### Integrazione (`tests/dynamics/test_orchestrator_salience_integration.py`)

1. `test_salience_network_enables_and_initializes` — abilitare flag, chiamare `model_post_init`, verificare che `_salience_network` esista.
2. `test_tick_with_salience_network_does_not_crash` — eseguire `orch._tick()` con salience, FRL, DMN, Talamo e neuromodulatori abilitati.
3. `test_salience_drives_dmn_switching` — forzare prediction_error alto o NE alto, eseguire tick, verificare che `_dmn_switching.state.salience_signal > 0`.
4. `test_salience_broadcast_to_workspace` — abilitare `global_workspace_enabled`, eseguire tick, verificare che il workspace abbia ricevuto un broadcast dal salience layer.
5. `test_salience_events_persisted` — verificare che `MorphologicalMemory` contenga eventi `SALIENCE_NETWORK_UPDATED`.

### Regressioni

- Eseguire `pytest tests/dynamics/ tests/regions/ tests/regulation/ tests/cells/` per garantire che le modifiche all'`orchestrator.py` e a `morphology_events.py` non rompano test esistenti.

---

## Criteri di successo

- [ ] `SalienceNetworkLayer` importabile, testato e con API stabile.
- [ ] `MorphologyEventType` esteso con eventi salienza senza errori di serializzazione.
- [ ] L'orchestrator permette di abilitare `salience_network_enabled` e di eseguire tick senza crash.
- [ ] Quando abilitata, la salienza influenza `DMNSwitchingEngine` e `GlobalWorkspace`.
- [ ] Tutti i test nuovi passano e i test di regressione non falliscono.

---

## Ordine di implementazione

1. Implementare `SalienceNetworkLayer`.
2. Aggiungere eventi a `MorphologyEventType`.
3. Integrare il layer nell'orchestrator (flag, init, tick, context).
4. Scrivere i test unitari.
5. Scrivere i test di integrazione.
6. Eseguire suite di regressione e correggere eventuali problemi.
