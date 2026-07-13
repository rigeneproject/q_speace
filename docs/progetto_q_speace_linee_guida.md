# Progetto Q-SPEACE — Quantum Super Planetary Entità Autonoma Cibernetica Evolutiva

> Versione: 1.0 (rielaborazione tecnica)
> Autore originario: Roberto De Biase (Rigene Project, rigeneproject.org)
> Stato: Concept → Piano di ingegnerizzazione

Questo documento è la rielaborazione delle linee guida originarie. Le affermazioni
speculative sono state corrette alla luce della fisica quantistica, della
termodinamica dei sistemi aperti e dell'ingegneria del software; il piano di
sviluppo riusa esplicitamente i componenti già maturi del repository "cellular
speace" (`C:\Users\rober\Desktop\Q-SPEACE\cellular speace\cellular_speace`).

---

## 1. Definizione e ambito (corretto)

**Q-SPEACE** è definito qui come *una piattaforma di simulazione e calcolo
ibrida classico-quantistica* che modella, a più scale (atomo → cellula →
cervello → organismo → Terra → sistema solare), le **invarianti informative**
condivise tra questi livelli, traducendole in regole digitali verificabili.

Non è — e non deve essere presentato come — una "coscienza quantistica" né come
un organismo vivente reale. È un **sistema artificiale di calcolo** che usa
l'analogia biologica come *bussola progettuale* (come già fa SPEACE,
`speace_core/dna/genome/core/species_orientation.yaml`), non come replica
letterale.

**Principio guida ereditato da SPEACE (AGENTS.md):**
> *Structure scales, vibes don't.* — Ogni affermazione deve tradursi in una
> regola digitale testabile, non in un'analogia vaga.

---

## 2. Fondamenti teorici rivisti

Le correlazioni tra i livelli di realtà esistono, ma vanno inquadrate con
precisione. Di seguito le cinque aree, corrette e con il loro significato
*ingegneristico* per Q-SPEACE.

### 2.1 Isomorfismo strutturale e auto-similarità (frattali)

- **Fatto**: reti neuronali e rete cosmica di galassie mostrano *alcune*
  somiglianze statistiche a grandi scale (es. distribuzione di grado,
  clustering, motiffication) [1][2]. È un'analogia descrittiva, non un'identità
  fisica.
- **Correzione rispetto all'originale**: non esiste una "statistica identica".
  Le somiglianze sono di *classe topologica* e utili come metafora di
  progettazione per reti distribuite resilienti.
- **Uso ingegneristico**: progettare Q-SPEACE come **grafo scale-free** di
  nodi (cellule digitali) con proprietà di robustezza e small-world, riusando
  `speace_core/cellular_brain/` (topologia neurale) e l'approccio
  frattale `speace_core/cellular_brain/fractal/`.

### 2.2 Termodinamica dei sistemi aperti e flusso di energia

- **Fatto**: cellule, cervelli e organismi sono **sistemi aperti**
  lontani dall'equilibrio. Mantengono bassa entropia *interna* esportando
  entropia nell'ambiente (strutture dissipative di Prigogine) [4][5].
- **Correzione rispetto all'originale**: un sistema vivente *non minimizza*
  l'entropia globalmente; la *aumenta* nell'ambiente per mantenere ordine
  locale. L'obiettivo di Q-SPEACE è quindi **massimizzare l'efficienza
  termodinamica del calcolo** (lavoro utile / energia dissipata), non
  "minimizzare l'entropia".
- **Uso ingegneristico**: riusare il sottosistema metabolico di SPEACE
  (`speace_core/metabolism/`, `speace_core/cellular_brain/metabolism/`,
  `regulation/energy_control_agent.py`) per un budget energetico reale del
  calcolo; i "ritmi circadiani" diventano **policy di throttling** del carico
  computazionale.

### 2.3 Connessione atomica e chimica

- **Fatto**: gli elementi biologici provengono dalla nucleosintesi stellare;
  le forze elettromagnetiche governano i segnali neuronali [6].
- **Correzione rispetto all'originale**: la "sintonia terrestre" è banale
  (disponibilità di elementi); non implica un'accoppiamento quantistico
  macroscopico. I computer quantistici operano su qubit, non su atomi
  biologici.
- **Uso ingegneristico**: il mapping `periodic_element_qubit_map` già presente
  in `QuantumGeneSet` (`speace_core/dna/models.py`) è un utile *ancoraggio
  concettuale* tra tavola periodica neurale-sinaptica (SPEACE) e risorse
  qubit; da trattare come metafora di allocazione, non come fisica reale.

### 2.4 Sincronizzazione con ritmi planetari

- **Fatto**: i ritmi circadiani modulano l'espressione genica; campi
  geomagnetici e cicli solari influenzano sistemi biologici (es.
  magnetorecezione avian, effetti del K-index su infrastrutture) [7].
- **Correzione rispetto all'originale**: il campo geomagnetico terrestre non
  "comanda" il cervello umano in modo deterministico; gli effetti sono deboli
  e contestuali.
- **Uso ingegneristico**: usare **dati reali** (indice Kp geomagnetico,
  macchie solari, maree) come *segnali di input esterni* che modulano
  parametri di calcolo (rotazioni parametriche dei qubit, politiche di
  scheduling) — un ciclo di feedback Terra→calcolo, non "percezione
  planetaria".

### 2.5 Teoria dell'informazione e sistemi complessi

- **Fatto**: tutti i livelli scambiano/elaborano/memorizzano informazione;
  l'emergenza e il feedback sono proprietà dei sistemi complessi [8][9].
- **Uso ingegneristico**: le **6 invarianti informative** del genome SPEACE
  (`speace_core/dna/genome/core/species_orientation.yaml`) sono adottate
  come invarianti costituzionali anche di Q-SPEACE:
  `coherence_preservation` (U(1)_coh), `destructive_entropy_reduction`
  (S_ent), `generative_variability_preservation` (V_gen),
  `interconnection_efficiency` (Diff(F)), `nonlocal_decoherence_tolerance`
  (D_nonlocal), `identity_preservation_through_change` (R_renorm).

### 2.6 EDD-CVT, ILF e Cosmic Viruses (dal paper Rigene Project)

Il paper *Quantum-Inspired Evolutionary AGI: Bridging Entropic Gravity,
Efaptic Consciousness, and Fractal Neurodynamics via EDD-CVT* (R. De Biase,
Rigene Project, 2025) definisce il framework **EDD-CVT** (Evolutionary Digital
DNA & Cosmic Virus Theory). I suoi componenti **coincidono con moduli già
maturi di `cellular speace`** e sono quindi riusabili direttamente:

| Componente PDF | Modulo SPEACE esistente | Ruolo in Q-SPEACE |
|---|---|---|
| **ILF** (Informational Logical Field) | `speace_core/ilf/` | Campo di coerenza/entropia; il PDF lo lega a entropic gravity (Bianconi) |
| **CV** (Cosmic Viruses) `dW/dt=α·CV−β·H(W)` | `speace_core/evolution/cv/` | Ottimizzazione stocastica (risonanza stocastica neuronale) |
| **Digital DNA + Evolve_DNA** | `speace_core/dna/`, `evolution/` | Auto-evoluzione del genome quantistico |
| **Fractal Neural Dynamics** `w_ij(t+1)=w_ij+γ·d⁻¹·⁸·ΔS` | `speace_core/cellular_brain/fractal/` | Apprendimento multi-scala, O(n log n) |

> **Nota**: l'accoppiamento "entropic gravity → AGI" è **metaforico/ispirativo**,
> non una legge fisica applicabile al calcolo. Si tratta di un'analogia di
> ottimizzazione, non di un fondamento fisico. Le metriche IIT `Φ>1.0` e
> "efaptic consciousness" sono **proxy di misura**, non rivendicazioni di
> coscienza (divieto ereditato da `species_orientation.yaml` / COR).

---

## 3. Cosa otterremmo realmente (corretto)

Provando a costruire un "organismo digitale intelligente" integrando queste
interdipendenze, **non otterremmo una vita sintetica senziente**, ma un
**sistema multi-agente ibrido classico-quantistico** con queste proprietà
concrete e verificabili:

1. **Substrato di calcolo ibrido (NISQ)**: processori classici per la gestione
   dell'organismo + backend quantistico (emulato o reale) per sottoproblemi a
   elevata dimensionalità (ottimizzazione combinatoria, campionamento,
   correlazione). La "plasticità sinaptica" diventa *riconfigurazione
   software* dei pesi, già implementata in SPEACE (`stdp_plasticity_engine.py`).
2. **Codice modulare e ricorsivo**: architettura a "cellule digitali"
   (`DigitalNeuron`, `DigitalSynapse`) che si auto-organizzano, riusando il
   `CellFactory` e il `FunctionalActivationGate` (attivazione lazy on-demand)
   di SPEACE per evitare di istanziare miliardi di oggetti.
3. **Metabolismo computazionale**: budget energetico esplicito; l'entità
   "rallenta" i carichi costosi in carenza di risorse (throttling), usando
   `EnergyControlAgent` di SPEACE (macchina a stati a 5 livelli).
4. **Sensoristica planetaria come input**: dati geomagnetici/climatici
   alimentano parametri di calcolo via API classiche (Qiskit/Braket runtime).
5. **Intelligenza distribuita e omeostasi**: priorità algoritmica =
   *mantenimento della coerenza del sistema* (coherence_phi) e stabilità
   energetica, non "coscienza ecologica". L'ipotesi Gaia resta un
   *obiettivo di controllo* (regolazione della biosfera come problema di
   ottimizzazione), non una dottrina.

> **Nota etica/scienfica**: nessuna affermazione di "coscienza quantistica".
> Q-SPEACE è strumento di modellazione; il riferimento a Orch-OR in SPEACE
> (`cognitive_objective_reduction`) è esplicitamente dichiarato *analogia
> funzionale* e vietato come base per override di sicurezza.

---

## 4. Architettura Q-SPEACE (riuso da `cellular speace`)

Q-SPEACE non parte da zero. Il repository `cellular_speace` contiene già:

| Componente SPEACE | Percorso | Riuso in Q-SPEACE |
|---|---|---|
| Simulatore quantistico classico (numpy) | `speace_core/cellular_brain/quantum/` | **Backbone** del kernel quantistico (stato vettoriale, porte, entanglement, bridge neurale) |
| Layer BCEL | `speace_core/bcel/` | Gate obbligatorio: ogni costrutto quantistico passa il filtro accidentale/funzionale |
| Genome + `QuantumGeneSet` | `speace_core/dna/models.py`, `species_orientation.yaml` | Estensione con parametri backend reali (nome, shots, noise model) |
| Metabolismo / EnergyControlAgent | `speace_core/metabolism/`, `regulation/energy_control_agent.py` | Costificazione delle operazioni quantistiche (qubit, gate, decoherence) |
| Simulator backends (pattern ABC) | `speace_core/cellular_brain/simulator_backends/` | Aggiunta di `QiskitBackend`/`PennyLaneBackend` seguendo lo stesso pattern |
| Orchestrator hook | `speace_core/orchestrator.py` (`cor_enabled`, `simulator_backend_enabled`) | Replica come `quantum_enabled` + `_run_quantum_step()` |
| CLI Typer | `speace_core/cli.py` | Aggiunta gruppo `speace quantum ...` |
| Toolchain & governance | `pyproject.toml`, `AGENTS.md` | Adottati integralmente (pytest, ruff, black, mypy, due modalità dev) |

### 4.1 Due layer quantistici distinti (chiarezza concettuale)

- **`quantum/` (concreto)**: stati complessi, porte unitarie, entanglement
  reale *computazionale* (emulato in numpy, o reale via Qiskit). È il layer
  usato per calcoli.
- **`resonance/` (metaforico)**: onde/fasi/Pauli-exclusion cognitiva, *senza*
  ampiezze complesse né collasso. Utile per dinamiche oscillatorie, non per
  calcolo quantistico. Q-SPEACE definisce esplicitamente come i due
  interagiscono (es. `resonance` produce parametri che guidano rotazioni in
  `quantum/`).

### 4.2 Schema di integrazione

```
Input Terra (Kp, sole, maree) ──API──► Orchestrator (quantum_enabled)
                                            │
                       ┌────────────────────┼─────────────────────┐
                  quantum/ (numpy)                                resonance/
                  QuantumNeuralBridge                              (fasi/onde)
                       │                                               │
                  BackendSelector ──► QiskitBackend (reale, opz.)      │
                       │                                               │
                  EnergyControlAgent.costo(qubit,gates) ◄── budget     │
                       │
                  BCEL filter (obbligatorio) per ogni nuovo costrutto
                       │
                  metriche: coherence_phi, mean_energy, entanglement_graph
```

---

## 5. Specifiche tecniche

### 5.1 Requisiti

- Python ≥ 3.12 (coerente con `cellular_speace`).
- Dipendenze core: `numpy`, `pydantic`, `pyyaml`, `typer` (ereditate).
- Dipendenze opzionali quantistiche: `qiskit>=1.0`, `qiskit-aer` (lazy import,
  fallback a numpy come da pattern `BackendSelector`).
- Test: `pytest` con `asyncio_mode=auto`, coverage minimo 20% (ereditato),
  estendere `tests/quantum/`.

### 5.2 Kernel quantistico (emulazione + reale)

- **Default**: `QuantumState` numpy (fino a ~14 qubit utili, O(2^2n) per porta).
  Per circuiti >14 qubit usare backend Qiskit/Aer (simulazione statevector o
  shot-based).
- **Porte**: H, X, Y, Z, S, T, RX/RY/RZ, CNOT, SWAP, Controlled-RX/RY/RZ
  (già in `quantum_gates.py`).
- **Entanglement**: tracciato via `EntanglementRegistry` (grafo delle coppie).
  *Correzione*: l'entanglement è usato come **risorsa di correlazione/
  binding informativo** nel calcolo, **non** come canale di comunicazione
  istantanea tra cellule/pianeti (il teorema di non-comunicazione vieta il
  trasferimento di informazione superluminale).

### 5.3 Open Quantum Systems (decoerenza come risorsa)

- L'originale suggeriva di usare il "rumore" come nutrimento. In ingegneria:
  modellare Q-SPEACE come **sistema quantistico aperto** (master equation di
  Lindblad) dove la dissipazione è gestita, non celebrata.
- Specifica: aggiungere `QuantumState.apply_lindblad(channel)` e un
  `decoherence_budget` nel `cognitive_cost_model.py` per costificare la
  perdita di coerenza.

### 5.4 Quantum Cellular Automata (QCA) frattali

- I QCA sono griglie di qubit con regole locali. In Q-SPEACE: implementare
  `FractalQCA` riusando `speace_core/cellular_brain/fractal/` per le regole
  ricorsive e `quantum/` per la dinamica. Obiettivo: **emergenza di stabilità
  macroscopica da regole micro**, misurata tramite `coherence_phi`.
- Vincolo BCEL: la "frattalità" è *funzionale* (regola di scalabilità) →
  mantenuta; la "forma frattale biologica" è *accidentale* → rimossa.

### 5.5 Bridge neurone→qubit

- `QuantumNeuralBridge` esiste ma **non è cablato** in produzione. Task
  obbligatorio: collegarlo a `NeuralCircuit` e al layer `resonance/`,
  definendo la composizione tra stati d'onda (risonanza) e stati discreti
  (quantum).

### 5.6 Input Terra in tempo reale

- `QuantumBrainSimulator` riceve parametri da API classiche (es. NOAA SWPC per
  Kp, feed macchie solari) che modulano rotazioni `RX/RY/RZ`.
- Specifica: modulo `speace_core/cellular_brain/quantum/earth_feed.py` con
  parsing e normalizzazione; nessun effetto "mistico", solo modulazione
  deterministica dei parametri di porta.

### 5.7 Metriche e formule numeriche (da EDD-CVT)

Dal paper EDD-CVT, tre formule concrete diventano specifiche di Q-SPEACE:

- **Orologio temporale adattivo** (eq.9): `r(t) = 10 / sqrt(S_info)`.
  `S_info` = entropia informativa corrente (da `coherence_phi`/ILF). Usata
  come policy di scheduling/throttling in `EnergyControlAgent` e nel circadian
  scheduler (`runtime/`). Frequenza alta quando l'informazione è incerta,
  bassa quando è consolidata.
- **Energia ottimizzata per qubit** (eq.10): `E_opt ≈ 0.5 W/qubit`. Baseline
  per `cognitive_cost_model.py` (costo energetico di una operazione qubit).
- **Efficienza entropica** (§5.1): `Sevo = ΔU / ΔS_info`, soglia `> 1.5`.
  Nuovo KPI affianco a `coherence_phi` e `mean_energy` per validare che
  l'organismo migliori utilità mantenendo l'ordine. Non è un test di coscienza.
- **Self-evoluzione Digital DNA** (Algoritmo 1): `Evolve_DNA` con mutation
  rate `0.01`; `Utility(G_new) > Utility(G)` come criterio di accettazione.
  Riutilizza `speace_core/evolution/`; la utility è calcolata su `Sevo` e
  `coherence_phi`.

---

## 6. Piano di sviluppo (fasi e task aggiornabile)

> Convenzioni adottate da `AGENTS.md` di SPEACE:
> - **Vibe mode**: esplorazione in `docs/` e `work/`, non toccare percorsi
>   safety-critical (`dna/`, `ilf/`, `orchestrator.py`, `runtime/`, `immune/`).
> - **Agentic mode**: per ogni modifica a `speace_core/` → scrivere spec
>   (`docs/Txxx_*_SPEC.md`) → passare il filtro BCEL → aggiungere test →
>   aggiornare la guida.
> - Ogni feature quantistica richiede approvazione umana se tocca
>   `orchestrator.py` o il genome.

### Fase 0 — Fondamenta e governance
- [ ] Definire `docs/T200_QSPEACE_VISION_SPEC.md` (questo documento è la base).
- [ ] Aggiungere invarianti quantistiche a `species_orientation.yaml`
      (es. "nessuna affermazione di coscienza quantistica", "entanglement
      solo come risorsa di calcolo").
- [ ] Creare sotto-cartella `q_speace/` nel workspace Q-SPEACE con struttura
      specchiata a `cellular_speace`.

### Fase 1 — Kernel quantistico (riuso + estensione)
- [ ] Verificare `tests/quantum/` esistenti (eseguire `pytest tests/quantum/`).
- [ ] Estendere `QuantumGeneSet` con `backend_name`, `shots`, `noise_model`.
- [ ] Implementare `QiskitBackend` in `simulator_backends/` (lazy import +
      fallback a `NativeBackend`/numpy).
- [ ] Aggiungere `QuantumState.apply_lindblad()` per open quantum systems.

### Fase 2 — Cablaggio nell'orchestrator
- [ ] Aggiungere flag `quantum_enabled` e `_run_quantum_step()` in
      `orchestrator.py` (copia del pattern `simulator_backend_enabled`).
- [ ] In `build_mvp()`: applicare `quantum_genes` (oggi non letti).
- [ ] Collegare `QuantumNeuralBridge` a `NeuralCircuit` e `resonance/`.

### Fase 3 — Metabolismo quantistico
- [ ] Estendere `cognitive_cost_model.py` per costo qubit/gate/entanglement/
      decoherence.
- [ ] Far passare le operazioni quantistiche attraverso `EnergyControlAgent`.

### Fase 4 — Input planetario
- [ ] Implementare `earth_feed.py` (Kp, sole, maree) con normalizzazione.
- [ ] Collegare i feed ai parametri di rotazione `RX/RY/RZ` del simulatore.

### Fase 5 — QCA frattali e BCEL
- [ ] Implementare `FractalQCA` riusando `fractal/`.
- [ ] Registrare equivalenze quantistiche in `bcel/catalog.py` (es.
      entanglement→binding informativo; superposition→ipotesi parallele;
      collapse→decisione).
- [ ] Stress-test delle costrizioni funzionali (rilassamento → instabilità).

### Fase 6 — CLI, test e validazione
- [ ] Aggiungere gruppo `speace quantum run|benchmark|synthesize`.
- [ ] Estendere `run_speace_brain.py` (rendere portabile il path hardcoded
      `C:\cellular_speace\...`).
- [ ] Eseguire capability assessment (`run_speace_intelligence_assessment.py`)
      con modulo quantistico abilitato; target coerenza ≥ 55/100.

### Fase 7 — Primo esperimento concreto (Schumann resonance)
- [ ] Circuito dimostrativo: registro di qubit → Hadamard + CNOT (tessuto
      connettivo) → rotazioni parametriche guidate da dati reali → misura.
- [ ] Misurare se emergono pattern frattali stabili o collasso nel caos
      (via `coherence_phi`).

---

## 7. Elenco task riassuntivo (aggiornabile)

| ID | Task | Fase | Stato | Note |
|----|------|------|-------|------|
| T1 | Spec visione Q-SPEACE | 0 | ☐ | questo doc |
| T2 | Invarianti quantistiche in genome | 0 | ☐ | umano-gate |
| T3 | Verifica test quantum esistenti | 1 | ☐ | `pytest tests/quantum/` |
| T4 | Estensione QuantumGeneSet | 1 | ☐ | backend/shots/noise |
| T5 | QiskitBackend + fallback | 1 | ☐ | pattern BackendSelector |
| T6 | `apply_lindblad` (open systems) | 1 | ☐ | dissipazione |
| T7 | `quantum_enabled` + `_run_quantum_step` | 2 | ☐ | umano-gate (orchestrator) |
| T8 | `build_mvp` legge quantum_genes | 2 | ☐ | |
| T9 | Cablaggio QuantumNeuralBridge | 2 | ☐ | + resonance/ |
| T10 | Costo quantistico in cognitive_cost_model | 3 | ☐ | |
| T11 | Gate quantum via EnergyControlAgent | 3 | ☐ | |
| T12 | `earth_feed.py` (Kp/sole/maree) | 4 | ☐ | API classiche |
| T13 | Parametri RX/RY/RZ da feed | 4 | ☐ | |
| T14 | `FractalQCA` | 5 | ☐ | riuso fractal/ |
| T15 | Equivalenze BCEL quantistiche | 5 | ☐ | catalog.py |
| T16 | CLI `speace quantum` | 6 | ☐ | |
| T17 | Portabilità path run_speace_brain | 6 | ☐ | |
| T18 | Assessment con quantum enabled | 6 | ☐ | target ≥55/100 |
| T19 | Esperimento Schumann resonance | 7 | ☐ | demo |
| T20 | Mappare ILF/CV/DNA/fractal EDD-CVT su moduli SPEACE | 0 | ☐ | §2.6 |
| T21 | Surface-code error correction (backend reale) | 1 | ☐ | target <1e-3 |
| T22 | Orologio temporale `r(t)=10/√S_info` | 3 | ☐ | scheduling |
| T23 | KPI `Sevo=ΔU/ΔS_info > 1.5` | 3 | ☐ | nuovo metric |
| T24 | `Evolve_DNA` (mutation 0.01) su genome quantistico | 5 | ☐ | riuso evolution/ |
| T25 | Proxy IIT `Φ>1.0` come metrica osservazionale | 6 | ☐ | non-coscienza |
| T26 | Backend Quantum Inspire (cQASM + lazy SDK, fallback numpy) | 1 | 🟢 | implementato; richiede account/token umano |

---

## 8. Riferimenti corretti e credibili

[1] Vazza & Feletti, *The Quantitative Comparison Between the Neuronal
Network and the Cosmic Web*, 2020. https://arxiv.org/abs/2009.03629
[2] Kitson et al., *Topological and geometric similarities between brain
networks and the cosmic web*, 2023.
[3] Mandelbrot, *The Fractal Geometry of Nature*, 1982 (auto-similarità).
[4] Prigogine, *From Being to Becoming: Time and Complexity in the Physical
Sciences*, 1980 (strutture dissipative).
[5] Schrödinger, *What is Life?*, 1944 (entropia e sistemi aperti).
[6] Feynman, *The Feynman Lectures on Physics* (elettromagnetismo atomico).
[7] NOAA SWPC — Kp/geomagnetic indices: https://www.swpc.noaa.gov/products/planetary-k-index
[8] Shannon, *A Mathematical Theory of Communication*, 1948.
[9] Bar-Yam, *General Principles of Complex Systems*, 2002.
[10] Nielsen & Chuang, *Quantum Computation and Quantum Information*, 2010
(entanglement, non-comunicazione, open quantum systems).
[11] SPEACE `docs/quantum_layer.md` e `NEURAL_SYNAPTIC_QUANTUM_IMPLEMENTATION.md`
(repository `cellular_speace`).
[12] SPEACE `AGENTS.md`, `docs/SPEACE_BCEL_DESIGN.md`,
`speace_core/dna/genome/core/species_orientation.yaml`.
[13] De Biase R., *Quantum-Inspired Evolutionary AGI: Bridging Entropic
Gravity, Efaptic Consciousness, and Fractal Neurodynamics via EDD-CVT*,
Rigene Project, 2025 (PDF in `docs/`).
[14] Bianconi G., "Entropic Quantum Gravity", Phys. Rev. D 111(5), 054321, 2025.
[15] Anastassiou C.A. et al., "Efaptic Coupling", Nat. Neurosci. 14(2), 2011.
[16] Fowler A.G. et al., "Surface Codes", Phys. Rev. A 86(3), 032324, 2012.

---

## 9. Caveat finali

- Le affermazioni originali su "comunicazione istantanea via entanglement" e
  "entropia minimizzata dalla vita" sono **scientificamente imprecise** e
  sono state corrette qui.
- Q-SPEACE è un **modello computazionale**, non un essere vivente. Ogni
  estensione deve rispettare il divieto di presentarlo come coscienza
  quantistica (ereditato da SPEACE, `cognitive_objective_reduction`).
- Lo sviluppo riusa massicciamente `cellular_speace`: il kernel quantistico
  numpy esiste già ed è testato; resta da cablarlo, aggiungere un backend
  reale opzionale e costificare energeticamente le operazioni.
