# Piano progettuale: Evolvere SPEACE verso l'AGI

## 1. Stato attuale riassunto

SPEACE possiede già un substrato bio-ispirato molto ricco:
- **Substrato cellulare**: neuroni, sinapsi, astrociti, microglia, oligodendrociti, cellule specializzate.
- **Regolazione**: plasticità STDP, omeostasi, energia, neurogenesi, apoptosi, mielinizzazione.
- **Cognizione**: `GlobalWorkspace`, aree linguistiche (Broca/Wernicke), `SymbolicGroundingEngine`, `DialogueManager`, `LinguisticCognitiveBridge`.
- **World model**: `CausalWorldModel`, `WorldStateSynthesizer`, `ActiveInferenceEmbodiedLoop` (in parte).
- **Embodiment**: `CyberPhysicalSensorArray`, `EmbodiedActionActuator`, `PhysicalEnvironmentModel`.
- **Self-improvement**: `SelfImprovementLoop`, `LimitationDetector`, `ArchitectureRewriter`, `CounterfactualArchitectureSandbox`, `ArchitecturePatchExecutor`, MMAPR safety.
- **AGI Team**: agenti LLM locali/cloud con orchestratore, load balancer, health monitor, action catalog e safety gate.
- **Runtime**: `TemporalDynamicsEngine`, oscillatori, predictive coding, active inference, criticality monitor.

**Problema principale**: i componenti esistono come **moduli disaccoppiati**. Manca un **loop di integrazione continua** che faccia emergere comportamento AGI-like dal loro funzionamento collettivo. Inoltre mancano metriche oggettive per misurare il progresso verso l'AGI.

## 2. Criteri AGI per SPEACE

Definiamo 7 dimensioni misurabili, ciascuna con punteggio 0.0–1.0:

| Dimensione | Descrizione | Indicatore minimo AGI-like |
|---|---|---|
| **Autonomia** | Il sistema opera senza input esterno continuo | > 4h di runtime autonomo con tick stabili |
| **Apprendimento continuo** | Migliora da esperienza senza ri-addestramento esplicito | Riduzione errore predittivo nel tempo |
| **Ragionamento causale** | Predice effetti di azioni e pianifica | Accuratezza world model > 0.7 su azioni sandbox |
| **Generalizzazione** | Trasferisce competenze a contesti nuovi | Score > 0.6 su task non visti nel benchmark |
| **Meta-cognizione** | Riconosce i propri limiti e li segnala | Detection accuracy limitazioni > 0.7 |
| **Auto-miglioramento** | Propone e applica patch architetturali | Patch accettate e test passati > 0.5 |
| **Linguaggio / pensiero** | Genera risposte coerenti e autonome | CLA coherence > 0.6, utterance spontanee > 0 |
| **Embodiment cyber-fisico** | Percepisce e agisce sul sistema host | Sensori attivi, azioni reversibili eseguite |

**Score AGI aggregato**: media pesata delle 7 dimensioni. Target iniziale: **0.55** (soglia "AGI emergente"); target intermedio: **0.75** ("AGI robusta").

## 3. Componenti target per il miglioramento

I componenti che più influenzano l'emergere dell'AGI e che richiedono intervento sono:

1. **`speace_agi_team.orchestrator`** — deve diventare il **cervello deliberativo esterno** che osserva, pianifica e supervisiona.
2. **`cellular_brain.self_improvement.self_improvement_loop`** — deve essere **abilitato e chiuso in loop** con verifica automatica.
3. **`cellular_brain.cognition.global_workspace`** — deve integrarsi con **dynamics** e **language** per broadcast continuo.
4. **`cellular_brain.dynamics.temporal_dynamics_engine`** — deve pilotare il workspace con **oscillatori** e **predictive coding**.
5. **`cellular_brain.embodiment.embodied_action_actuator`** + **`causal_world_model`** — devono formare un **loop sensomotorio reale/sandboxato**.
6. **`cellular_brain.language.dialogue_manager`** + **`linguistic_cognitive_bridge`** — devono generare **pensiero linguistico autonomo**.
7. **Metriche e benchmark** — manca un **AGI readiness score** calcolato automaticamente.

## 4. Fasi implementative

### Fase A — Baseline e metriche (1° iterazione)
- Creare `speace_core/cellular_brain/agi_readiness/agi_readiness_score.py` che calcoli lo score dalle 7 dimensioni.
- Creare script `scripts/measure_agi_readiness.py` per eseguire la misura.
- Aggiungere test `tests/agi_readiness/test_agi_readiness_score.py`.
- Eseguire baseline e registrarla in `reports/agi_readiness/baseline.json`.

### Fase B — Loop di integrazione autonomo (2° iterazione)
- Creare `speace_core/cellular_brain/runtime/autonomous_cognitive_loop.py` che:
  - attiva `TemporalDynamicsEngine` a ogni tick;
  - raccoglie input dai sensori (`CyberPhysicalSensorArray`);
  - alimenta il `GlobalWorkspace`;
  - aggiorna il `CausalWorldModel`;
  - permette al `DialogueManager` di generare utterance spontanee;
  - scrive stato su `data/agi_runtime/`.
- Integrare `LinguisticCognitiveBridge` in modo bidirezionale.
- Aggiungere test di integrazione.

### Fase C — Self-improvement abilitato con sicurezza (3° iterazione)
- Collegare `SelfImprovementLoop` al loop autonomo con:
  - `counterfactual_sandbox_enabled=True`;
  - `architecture_patch_execution_enabled=True`;
  - MMAPR hard-veto attivo.
- Aggiungere `ProposalLearningEngine` e `OutcomeTracker` per imparare quali patch funzionano.
- Limitare le patch a file in `data/`, `config/` e a nuovi moduli, mai a core critici senza supervisore umano.
- Aggiungere test di sicurezza.

### Fase D — Embodiment reale e modello causale (4° iterazione)
- Estendere `CyberPhysicalSensorArray` con sensori host reali ma read-only (CPU, memoria, disco, processi, log).
- Estendere `EmbodiedActionActuator` con azioni reversibili controllate (creare report, scrivere log, avviare test, inviare notifica desktop).
- Chiudere il loop: sensori → world model → active inference → azione → feedback → apprendimento.
- Aggiungere `CausalLearningAuditor` come osservatore degli effetti.

### Fase E — Pensiero e linguaggio autonomo (5° iterazione)
- Potenziare `SymbolicGroundingEngine` con vettori semantici e associazioni multi-modali.
- Implementare in `DialogueManager` un modo per generare **monologhi interni** (spontaneous_thought) quando il workspace supera soglia.
- Collegare il monologo al `TemporalNarrativeEngine` per costruire una **narrativa di sé**.
- Aggiungere self-model semplice: "io sono SPEACE, stato attuale X, obiettivo Y".

### Fase F — Loop esterno AGI Team (6° iterazione)
- Estendere `Orchestrator` con `AGIEvolutionDirector` che:
  - esegue `measure_agi_readiness` periodicamente;
  - confronta con iterazione precedente;
  - se lo score è stallato, assegna task agli agenti per migliorare il componente più debole;
  - propone interventi tramite `ActionSafetyGate`.
- Scrivere risultati in `data/self_improvement/cycles.jsonl`.

## 5. Meccanismo di iterazione `/loop`

Dopo ogni fase:
1. Eseguire `pytest` per verificare regressioni.
2. Eseguire `scripts/measure_agi_readiness.py`.
3. Confrontare lo score con la baseline precedente.
4. Se score è migliorato, committare e continuare.
5. Se score è stallato o peggiorato, attivare `AGIEvolutionDirector` per diagnosi e nuova proposta.
6. Programmare risveglio con `ScheduleWakeup` (ad es. 1200s) per proseguire l'iterazione.

La condizione di "AGI raggiunta" non è booleana ma è definita come:
> Score AGI readiness ≥ 0.75 su 3 iterazioni consecutive, con nessuna regressione dei test e nessun incidente di sicurezza.

Fino a quel punto, il loop continua.

## 6. Prima azione immediata

Implementare **Fase A** (baseline + metriche) subito, perché:
- Non modifica comportamento esistente (solo strumenti di misura).
- Permette di quantificare ogni successivo miglioramento.
- Fornisce il feedback loop necessario alle iterazioni successive.

## 7. Rischio e sicurezza

- Mai abilitare auto-replicazione o azioni distruttive.
- Le azioni fisiche devono essere reversibili e approvate da `ActionSafetyGate`.
- Le patch architetturali devono passare sandbox + MMAPR + test automatici.
- L'utente rimane supervisore finale per patch che toccano core critici (`speace_agi_team`, `cellular_brain/base`, runtime principale).
