# T-HOME-01 — Chiusura del circuito comportamentale omeostatico

> Stato: IMPLEMENTATO (2026-11-16) · Priorità: alta · Modalità: agentic
> Predecessore logico: T-HDAS (`action_bias`), T-AIEL (`active_inference_embodied_loop`)
> Successore: T-HOME-02 (integrazione PSN), T-HOME-03 (omeostasi predittiva)

## 1. Motivazione

L'audit statico + verifica dinamica del 2026-11-16
(`docs/QH01_dynamic_verification_2026-11-16.md`) hanno stabilito che:

1. **`ActiveInferenceEmbodiedLoop` non è in produzione.** È istanziato solo in
   `tests/test_continuous_substrate.py:258`. L'orchestrator usa un ciclo inline
   semplificato (orchestrator.py:1453-1465) senza audit trail né world-model
   prediction.
2. **`ActionBias` non è in produzione.** Zero call-site fuori dal proprio
   modulo: i drive modulano plasticità/esplorazione ma **non influenzano la
   selezione fra azioni candidate**. La verifica dinamica ha mostrato che il
   percorso produttivo attuale (solo EFE) sceglie la stessa azione in tutti gli
   scenari perturbati, mentre la combinazione EFE + bias omeostatico flippera
   da `hibernate` a `request_sleep` sotto deficit energetico.
3. **`ActiveInferenceEngine` è morto nel percorso MVP.** Creato ma senza
   stati/azioni registrati (`beliefs == {}` in tutte le fasi del probe):
   `step()` ritorna `None` e il ramo d'azione del circuito non si chiude.
4. **Due dei quattro moltiplicatori del drive sono calcolati ma mai consumati**
   nel percorso orchestrator (orchestrator.py:1206-1217 applica solo
   `plasticity_multiplier` e `exploration_multiplier`;
   `energy_supply_multiplier` e `stability_multiplier` sono morti).

## 2. Obiettivo

Chiudere il circuito:

```
SystemMetrics → GlobalHomeostaticDrive → ActionBias
    → ActiveInference (EFE base) → ActiveInferenceEmbodiedLoop
    → EmbodiedActionActuator (sandbox + audit) → feedback
```

senza introdurre nuova logica omeostatica: solo wiring di componenti già
esistenti e testati.

## 3. Cambiamenti richiesti

| # | Cambiamento | Riferimento |
|---|---|---|
| 1 | Sostituire il ciclo inline orchestrator.py:1453-1465 con `ActiveInferenceEmbodiedLoop` (recupera audit trail + world-model prediction) | `embodiment/active_inference_embodied_loop.py` |
| 2 | Iniettare `ActionBias.select_from_active_inference` nella selezione azioni: combined = `-EFE + bias` | `drives/action_bias.py:189-202` |
| 3 | Registrare stati/azioni reali su `ActiveInferenceEngine` nel percorso MVP (oggi `beliefs == {}`) | orchestrator.py:788-789 |
| 4 | Decidere il destino di `energy_supply_multiplier` e `stability_multiplier`: consumarli dove sensato o eliminarli dalla firma | orchestrator.py:1206-1217 |
| 5 | Fissare la semantica di `energy_supply_multiplier` (boost compensativo su deficit — verificato dinamicamente: 0.90 → 1.21 su E=0.15) prima che acquisti consumer | `dynamics/global_homeostatic_drive.py:122` |

## 4. Invarianti (non negoziabili)

- La GenAI/active-inference **propone**; l'attuazione resta governata da
  `EmbodiedActionActuator.propose_action` (sandboxed, audited) e dalla
  governance deterministica. Nessun bypass (T210: "GenAI proposes; the
  deterministic layer executes").
- I bias omeostatici modificano *cosa viene proposto*, mai *cosa viene
  eseguito* dall'hardware.
- Nessuna modifica a `species_orientation.yaml` né ai sistemi di safety.

## 5. Criteri di accettazione

1. A parità di osservazioni esterne, una perturbazione controllata dello stato
   interno (`mean_energy`, `noise_level`, `coherence_phi`) cambia la
   preferenza fra azioni candidate quando previsto dai bias, e **non** la
   cambia quando i drive sono disabilitati (controllo d'ablazione).
2. Il flip comportamentale è riproducibile su ≥ 5 run con seed diversi.
3. Ogni azione proposta attraversa `EmbodiedActionActuator.propose_action` e
   compare nell'audit trail; nessun nuovo percorso d'attuazione.
4. `pytest` passa su `tests/` toccati; nessun test esistente indebolito.
5. La sonda dinamica QH-01 (Parte 2) eseguita **in-tree** mostra flip
   comportamentale coerente col pre-wiring atteso.

## 6. Test

- Unit: selezione combinata (`-base + bias`) con drive perturbati.
- Unit: sostituzione del loop inline (stesse azioni proposte, audit popolato).
- Integrazione: `run_ticks` con flag abilitati, perturbazione energia,
  snapshot di drive/moltiplicatori/azioni/veto a ogni tick.
- Ablazione: flag `homeostatic_drive_enabled=False` → nessun flip.

## 7. Task checklist

- [x] T-HOME-01.1 — spec review + BCEL (nessun nuovo costrutto bio: wiring puro)
- [x] T-HOME-01.2 — registrazione stati/azioni `ActiveInferenceEngine` in MVP
- [x] T-HOME-01.3 — sostituzione loop inline con `ActiveInferenceEmbodiedLoop`
- [x] T-HOME-01.4 — iniezione `ActionBias` nella selezione
- [x] T-HOME-01.5 — decisione + implementazione su moltiplicatori morti
- [x] T-HOME-01.6 — test unit + integrazione + ablazione
- [x] T-HOME-01.7 — riesecuzione sonda QH-01 in-tree, confronto pre/post
  (`tests/embodiment/test_qh01_post_wiring_probe.py`: modulazione omeostatica
  invariata rispetto all'audit QH-01 §3; nuovi osservabili attivi — bias
  decision registrato durante i tick, beliefs AI MVP popolati) — riesecuzione sonda QH-01 in-tree, confronto pre/post
