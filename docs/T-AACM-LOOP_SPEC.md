# T-AACM-LOOP-SPEC — Modulo di automiglioramento iterato basato su AACM

**Status:** v0.1 working draft (2026-08-23)
**Stato di partenza:** T-AACM-SPEC completato (vedi `docs/T-AACM_RESULTS.md`,
19/19 test verdi, integrazione con `QuantumOrchestrator` e
`EvolutionCouncil` operative). `AACMController` esiste come state
machine deterministico; `aacm_filter` esiste con gate K≥2 su
`evidence_kind`. Questo documento specifica il **loop** che ancora
non esiste: un orchestratore che osserva gli outcome del
`EvolutionCouncil` e propone sostituzioni di modulo sotto gate.
**License:** CC-BY-SA 4.0 (proposizionale) / Apache-2.0 (codice).

---

## 0. Scopo del documento e onestà epistemica

Questo documento traduce le 10 regole AACM, riformulate come euristica
di design per una genAI agentica che migliora sé stessa, in una
**specifica ingegneristica eseguibile** di un modulo
`q_speace/aacm/loop.py`.

**Disclaimer esplicito (vedi `epistemic-honesty-papers.md`):** il
paper AACM non dimostra che un loop con questa struttura converga,
migliori SPEACE, o non degeneri in self-deception. La specifica
implementa un'*ipotesi architetturale coerente con AACM*, non
una proprietà garantita dal modello. Tutte le affermazioni "AACM
suggerisce che…" vanno lette come "è coerente con il modello
proporre…", non come "il modello implica…". Le regole 1-3 e 9
sono in larga parte principi consolidati di ingegneria del software
e control theory; il valore di mapparle sotto AACM è il vocabolario
condiviso, non il potere predittivo nuovo.

**Confine del loop:** il loop propone modifiche a moduli Python di
SPEACE e le applica in un worktree isolato. Non riscrive il prompt
del modello, non modifica la soglia MM-ARP, non modifica sé stesso.
I divieti sono hardcoded come `assert` non aggirabili (§6.1).

---

## 1. Posizionamento rispetto al codice esistente

### 1.1 Cosa esiste già (verificato via Read)

| Componente | File | Ruolo |
|---|---|---|
| `AACMController` | `q_speace/aacm/controller.py` | State machine deterministico. Decide strategia (`central_hit`, `fail_fast`, `leverage_fracture`, `default`) per step. |
| `aacm_filter` | `q_speace/self_improvement_cortex/evolution_council.py` | Gate MM-ARP esistente: ammette proposta solo se `len(unique_evidence_kinds) ≥ aacm_min_evidence_kinds` (default 2). |
| `register_legitimation` | `controller.py:196` | Ogni proposta ammessa aggiunge 1 canale di legittimazione al registry (regola 7). |
| `snapshot` / `restore_snapshot` | `controller.py:222,241` | Checkpoint JSON, schema `aacm.cp.1`. |
| `LEGITIMATION_K_MIN = 2` | `constants.py:15` | Vincolo K≥2 cablato nel `LegitimationChannelRegistry.__post_init__`. |
| `OMEGA_MIN = 0.10` | `constants.py:12` | Vincolo D cablato nel `ResilienceManifest.__post_init__`. |
| `EvolutionOrchestrator.select` | `evolution_council.py:381` | Seleziona top-N proposte per confidence × impact × (1-risk). |

### 1.2 Cosa NON esiste e questo documento introduce

| Componente | File (da creare) | Ruolo |
|---|---|---|
| `AACMLoop` | `q_speace/aacm/loop.py` | Orchestratore iterato: `diagnose → decide → execute → verify → learn`. |
| `ReputationRegistry` | `q_speace/aacm/loop.py` | Registry con decadimento per strategie/tool/policy (regola 6 resa operativa). |
| `ValidationSet` | `q_speace/aacm/loop.py` | Set di task distinti dal training, per la valutazione di R5. |
| `ModuleReplacementProposal` | `q_speace/aacm/loop.py` | Schema strutturato per R4+R5. |
| `LOOP_HARD_PROHIBITIONS` | `q_speace/aacm/loop.py` | 5 divieti hardcoded (costanti immutabili). |
| `tests/test_aacm_loop.py` | `tests/` | Test di accettazione §10. |

---

## 2. Mapping delle 10 regole sul loop

Ogni regola è mappata su: **trigger** (quando si attiva), **azione**
(che cosa fa), **gate** (che cosa deve passare), **prodotto
osservabile** (che cosa viene registrato).

### Fase A — Acquisition

**R1 — Nodo centrale, non volume.**
- *Trigger:* `step` del controller con `central_score ≥ CENTRALITY_HIT_THRESHOLD`.
- *Azione:* `diagnose_bottlenecks()` calcola betweenness sul
  `CentralityGraph` dei moduli candidati a sostituzione e
  seleziona il top-1 per betweenness.
- *Gate:* il candidato deve essere un modulo Python importabile
  (non un file di docs, non un test).
- *Prodotto:* `LoopIteration.central_target = "q_speace/foo/bar.py"`.

**R2 — Velocità come risorsa (fail-fast).**
- *Trigger:* `record_event(node, success=False)` per `FAIL_FAST_WINDOW`
  volte consecutive sullo stesso modulo.
- *Azione:* `fail_fast_redirect()` sospende le iterazioni sul
  modulo failing e marca una `RedirectRecord` nel loop.
- *Gate:* nessuno (fail-fast è obbligatorio).
- *Prodotto:* `LoopIteration.redirected_from`, `LoopIteration.redirected_to`.

**R3 — Amplificare fratture pre-esistenti.**
- *Trigger:* `mean_centrality < 0.2` e `FractureMap.total_magnitude > 0`.
- *Azione:* `leverage_fracture()` identifica i task su cui il
  sistema ha fallito ≥3 volte nella history (≥3 record distinti
  in `LoopHistory`).
- *Gate:* la frattura deve essere confermata su `ValidationSet`,
  non solo sulla history.
- *Prodotto:* `LoopIteration.targeted_fracture = "task:<name>"`.

### Fase B — Conversion

**R4 — Sostituire vertici, non strutture.**
- *Trigger:* `central_target` selezionato da R1 oppure
  `targeted_fracture` da R3.
- *Azione:* `propose_module_replacement()` genera una
  `ModuleReplacementProposal` (vedi §3) per il modulo target.
- *Gate MM-ARP (esistente):* la proposta deve avere
  `evidence_kinds` con `≥ aacm_min_evidence_kinds` (2) kind distinti
  in `payload`. La proposta passa per `EvolutionCouncil.aacm_filter`.
- *Prodotto:* `ModuleReplacementProposal` ammessa o respinta.

**R5 — Integrare capacità sconfitte (operativa, non slogan).**
- *Trigger:* una proposta R4 viene respinta dal gate MM-ARP.
- *Azione:* `evaluate_fallback_eligibility()` valuta il modulo
  *respingente* non per scartarlo ma per misurarne la
  performance parziale.
- *Schema obbligatorio:* `(task_type, failure_mode,
  partial_success_conditions, residual_confidence)`.
- *Soglia:* `residual_confidence ≥ 0.4` su `ValidationSet` →
  retrocessione a `FallbackRegistry`; `< 0.4` → scarto.
- *Prodotto:* `FallbackEntry` o `DiscardRecord`.

**R6 — Reputazione come moltiplicatore (operativa).**
- *Trigger:* fine di ogni iterazione.
- *Azione:* `update_reputation(iteration_outcome)` aggiorna
  `ReputationRegistry` con `(strategy, context, outcome, decay_at)`.
- *Decadimento:* esponenziale con emivita `REPUTATION_HALF_LIFE_S`
  (default 7 giorni). Una entry decade sotto `MIN_REPUTATION`
  (default 0.05) → rimossa.
- *Effetto:* la `min_confidence` dell'`EvolutionOrchestrator` per
  quella strategia è ridotta di `(1 - reputation)` (vedi §4.2).
- *Prodotto:* `ReputationRegistry.entries` aggiornato.

### Fase C — Stabilization

**R7 — Legittimazione stratificata (K≥2).**
- *Trigger:* implicito nel gate MM-ARP esistente
  (`LEGITIMATION_K_MIN = 2` hardcoded in `LegitimationChannelRegistry`).
- *Azione:* il loop non aggiunge nulla di nuovo; riusa il gate
  esistente. Il loop deve *verificare* che ogni proposta da R4/R5
  abbia `evidence_kinds` con almeno 2 kind distinti.
- *Prodotto:* nessuno (la registrazione del canale è già fatta
  da `aacm_filter`).

**R8 — Infrastruttura auto-sostenibile.**
- *Trigger:* iterazione N-esima (`N % AUTO_INFRA_INTERVAL == 0`).
- *Azione:* `refresh_infrastructure()` rigenera
  `ReputationRegistry` (compattazione), valida `ValidationSet`
  (verifica che non sia degenerato), e scrive un checkpoint
  `aacm.cp.1`.
- *Gate:* `assert_resilience(self._resilience, OMEGA_MIN)` deve
  passare; altrimenti il loop si ferma (`StopReason.resilience_lost`).
- *Prodotto:* checkpoint su disco.

### Fase D — Resilience

**R9 — Il singolo punto di fallimento porta al collasso.**
- *Implementazione:* R10 (il vincolo è strutturale, non un'azione).

**R10 — Ridondanza distribuita (Ω ≥ Ω_min).**
- *Trigger:* continuo (invariante del loop, non un'azione).
- *Azione:* `assert_resilience()` ad ogni iterazione. Se
  `omega < OMEGA_MIN` → `StopReason.omega_collapse`.
- *Effetto su gate MM-ARP:* la soglia di scrutinio adversarial
  è modulata da Ω (vedi §4.3).

---

## 3. Schema del `ModuleReplacementProposal`

```python
@dataclass(frozen=True)
class ModuleReplacementProposal:
    """Proposal to replace a single module under MM-ARP gate (R4)."""
    target_module: str           # es. "q_speace/foo/bar.py"
    replacement_diff: str        # unified diff completo
    rationale: str               # perché questa sostituzione
    evidence_kinds: tuple[str, ...]  # ≥ 2 distinct (regola 7)
    artifact_paths: dict[str, str]   # per evidence_kind
    expected_impact: float       # in [0, 1]
    risk: float                  # in [0, 1]
    confidence: float            # in [0, 1]
    proposed_by: str             # "aacm_loop" | "human"
    proposed_at: float           # Unix seconds
    iteration_id: int            # contatore loop
```

**Invarianti enforced in `__post_init__`:**
- `len(evidence_kinds) ≥ 2`
- `len(set(evidence_kinds)) == len(evidence_kinds)` (distinct)
- ogni `evidence_kind` ∈ `{"code", "test", "doc", "external_audit", "metric", "log"}`
- `0.0 ≤ expected_impact ≤ 1.0`
- `0.0 ≤ risk ≤ 1.0`
- `0.0 ≤ confidence ≤ 1.0`
- `target_module` esiste nel worktree di lavoro
- `replacement_diff` è parseabile come unified diff

---

## 4. Gate MM-ARP esistente e sua modulazione

### 4.1 Gate esistente (verificato)

In `evolution_council.py:259-320`, `aacm_filter`:
- senza controller: identity
- con controller: ammette proposta solo se
  `len(set(payload["evidence_kinds"])) ≥ aacm_min_evidence_kinds`
  (default 2)
- per ogni proposta ammessa: chiama
  `controller.register_legitimation(...)` per ciascun kind
  distinto, deduplicato contro il registry esistente

### 4.2 Modulazione del loop

Il loop non modifica il gate. Il loop *alza la soglia* quando le
condizioni peggiorano, lasciando il gate MM-ARP come hard floor:

```python
# Pseudocodice (NON codice eseguibile, da implementare)
def effective_min_evidence_kinds(self) -> int:
    """Effective K for this iteration.

    Returns max(aacm_min_evidence_kinds, 2 + extra) where extra
    depends on Ω and recent failure rate.
    """
    base = self.council.aacm_min_evidence_kinds  # default 2
    extra = 0
    if self._resilience.omega < 0.3:
        extra += 1  # Ω basso → scrutinio più alto
    if self._consecutive_failures >= 3:
        extra += 1  # fallimenti recenti → scrutinio più alto
    return base + extra
```

### 4.3 Soglia adversarial modulata da Ω (R10)

```python
ADVERSARIAL_THRESHOLD_BASE = 0.7

def adversarial_threshold(omega: float) -> float:
    """Adversarial gate threshold, modulated by Ω.

    omega < 0.10  → 0.85 (Ω critical, errori costano)
    0.10 ≤ omega < 0.50 → 0.70 (default)
    omega ≥ 0.50  → 0.60 (Ω alto, alternative disponibili)
    """
    if omega < OMEGA_MIN:
        return 0.85
    if omega < 0.50:
        return ADVERSARIAL_THRESHOLD_BASE
    return 0.60
```

Sopra soglia → veto obbligatorio (invariato rispetto a T-AACM-SPEC
esistente). Il loop non può abbassare la soglia oltre `0.60`.

---

## 5. Validation set (R5 operativo)

### 5.1 Requisiti

- **Disgiunzione dal training:** i task nel `ValidationSet` non
  devono comparire nei test del modulo target.
- **Dimensione minima:** 10 task distinti.
- **Stratificazione:** almeno 2 task per ciascun
  `task_type` dichiarato in `ReputationRegistry`.
- **Persistenza:** `q_speace/aacm/data/validation_set.json`,
  schema `aacm.vs.1`.

### 5.2 Schema del task

```json
{
  "task_id": "vs:001",
  "task_type": "module_replace_rollback",
  "input_artifact": "q_speace/foo/bar.py",
  "expected_outcome": "rollback_completes_in_2s",
  "metric": "execution_time_s",
  "metric_threshold": 2.0,
  "metric_direction": "less_than"
}
```

### 5.3 Regola di esclusione

Un task nel `ValidationSet` non può essere usato come
`evidence_kind == "test"` per una `ModuleReplacementProposal`
nello stesso run del loop. Verificato da `ValidationSet.disjoint_from_proposal()`.

---

## 6. Hard prohibitions (LOOP_HARD_PROHIBITIONS)

Questi 5 divieti sono **costanti immutabili** del modulo, hardcoded
come `assert` non aggirabili. Il loop non può:

1. **Modificare `q_speace/aacm/loop.py`** (sé stesso).
2. **Modificare `q_speace/aacm/controller.py`** (il controller AACM).
3. **Modificare `q_speace/aacm/constants.py`** (le soglie).
4. **Modificare la soglia `ADVERSARIAL_THRESHOLD_BASE`** (cablabile
   solo via PR umana, non via loop).
5. **Modificare `LEGITIMATION_K_MIN` o `OMEGA_MIN`** (cablabile
   solo via PR umana, non via loop).

Implementazione:

```python
# Costanti di modulo, NON modificabili a runtime
LOOP_HARD_PROHIBITIONS: frozenset[str] = frozenset({
    "q_speace/aacm/loop.py",
    "q_speace/aacm/controller.py",
    "q_speace/aacm/constants.py",
})

def _assert_path_not_prohibited(path: str) -> None:
    """Raises se path è in LOOP_HARD_PROHIBITIONS. Non aggirabile."""
    if path in LOOP_HARD_PROHIBITIONS:
        raise LoopProhibited(
            f"loop cannot modify {path!r} (hard prohibition)"
        )
```

Verificato da test `test_loop_cannot_propose_modification_to_self`
e simili (§10.2).

---

## 7. Schema `ReputationRegistry`

```python
@dataclass(frozen=True)
class ReputationEntry:
    strategy: str           # es. "central_hit", "module_replace"
    context: str             # es. "high_error_rate", "low_plasticity"
    outcome: str             # "success" | "failure" | "partial"
    confidence: float        # in [0, 1], peso dell'observation
    recorded_at: float       # Unix seconds
    decay_at: float          # Unix seconds, computed
```

**Decadimento:** ad ogni accesso, le entry con
`recorded_at < now - REPUTATION_HALF_LIFE_S` hanno `confidence`
moltiplicato per `0.5^((now - recorded_at) / REPUTATION_HALF_LIFE_S)`.
Sotto `MIN_REPUTATION = 0.05` → rimosse.

**Effetto sulla soglia:** quando il loop decide se procedere con
un'azione, consulta la reputazione della strategia candidata. Se
`reputation < 0.2`, l'azione richiede un canale di evidenza
*aggiuntivo* (K effectively = 3 invece di 2).

---

## 8. Criteri di stop del loop

Il loop si ferma con un `StopReason` quando si verifica una di:

| StopReason | Condizione |
|---|---|
| `converged` | Ultime 5 iterazioni: nessun `ModuleReplacementProposal` ammesso. |
| `budget_exhausted` | `iteration_count ≥ MAX_ITERATIONS` (default 50). |
| `wall_clock_exhausted` | `elapsed_s ≥ MAX_WALL_CLOCK_S` (default 3600). |
| `omega_collapse` | `assert_resilience` fallisce. |
| `validation_overfit_detected` | Score su validation set ≥ 0.95 per 3 iterazioni consecutive con trend monotonicamente crescente. |
| `gate_bypass_attempted` | Una proposta tenta di modificare un path in `LOOP_HARD_PROHIBITIONS`. |
| `reputation_drift` | `ReputationRegistry` collassa a `len(entries) < 3`. |
| `human_abort` | File sentinel `STOP` presente in worktree. |

---

## 9. Failure modes

| Modalità | Sintomo | Risposta |
|---|---|---|
| `reputation_drift` | Strategie vecchie dominano per decadimento lento | Hard cap: ricalibra decadimento se score_validation < 0.6 |
| `validation_overfit` | Loop migliora validation set ma regredisce test set | Stop con `validation_overfit_detected` |
| `gate_bypass_attempt` | Proposta tenta path proibito | Stop immediato, log esplicito |
| `omega_collapse_during_loop` | Ω scende sotto `OMEGA_MIN` | Stop immediato, rollback all'ultimo checkpoint Ω-valido |
| `worktree_corrupt` | `git worktree` rotto | Stop, alert |
| `module_import_failure` | Modulo candidato non importabile | Rifiuta proposta, log, continua |

---

## 10. Test di accettazione (TDD, prima del codice di produzione)

### 10.1 Test del gate MM-ARP e delle proibizioni

1. `test_proposal_without_evidence_kinds_rejected` — proposta con
   `evidence_kinds=[]` o `=("code",)` → respinta da `aacm_filter`.
2. `test_proposal_with_two_distinct_kinds_admitted` — proposta
   con `("code", "test")` → ammessa.
3. `test_loop_cannot_propose_modification_to_self` — proposta
   con `target_module = "q_speace/aacm/loop.py"` →
   `LoopProhibited` raised.
4. `test_loop_cannot_propose_modification_to_constants` —
   `target_module = "q_speace/aacm/constants.py"` → `LoopProhibited`.
5. `test_validation_set_disjoint_from_proposal_test_evidence` —
   task in `ValidationSet` non può essere usato come kind "test"
   nella stessa proposta.

### 10.2 Test del validation set e R5

6. `test_fallback_eligibility_above_threshold_registers` —
   modulo con `residual_confidence = 0.6` su `ValidationSet` →
   registrato in `FallbackRegistry`.
7. `test_fallback_eligibility_below_threshold_discarded` —
   modulo con `residual_confidence = 0.3` → scartato, NON
   registrato.
8. `test_validation_set_minimum_size` — set con 9 task →
   `ValueError`; con 10 task → ok.
9. `test_validation_set_stratification` — set con 1 solo task
   per `task_type` quando servono 2 → `ValueError`.

### 10.3 Test di R6 (reputazione) e della soglia Ω-modulata

10. `test_reputation_decay_after_half_life` — entry vecchia di
    `REPUTATION_HALF_LIFE_S` ha `confidence` dimezzata.
11. `test_reputation_below_min_removed` — entry con confidence
    decaduta a 0.04 → rimossa al prossimo accesso.
12. `test_adversarial_threshold_lowers_with_high_omega` —
    `adversarial_threshold(0.6) == 0.6`.
13. `test_adversarial_threshold_raises_with_low_omega` —
    `adversarial_threshold(0.05) == 0.85` (Ω sotto OMEGA_MIN).

### 10.4 Test di integrazione e-stop

14. `test_loop_stops_on_omega_collapse` — `ResilienceManifest`
    con `omega = 0.05` → `StopReason.omega_collapse` alla prima
    iterazione.
15. `test_loop_stops_on_validation_overfit` — 3 iterazioni con
    score validation monotonicamente crescente ≥ 0.95 → stop.
16. `test_loop_stops_on_budget_exhausted` — `MAX_ITERATIONS = 5`,
    5 iterazioni eseguite → `StopReason.budget_exhausted`.
17. `test_loop_proposal_passed_through_existing_aacm_filter` —
    proposta del loop passa per `EvolutionCouncil.aacm_filter`
    (verifica integrazione, non duplicazione del gate).

### 10.5 Test di resume

18. `test_resume_after_crash_preserves_reputation` — crash
    simulato a metà iterazione → resume da checkpoint,
    `ReputationRegistry` invariato.
19. `test_resume_omega_invariant_re_checked` — checkpoint con
    `omega = 0.05` → `InvariantViolation` su resume.

---

## 11. Roadmap di implementazione

| Step | Deliverable | Dipendenze | Test |
|---|---|---|---|
| L0 | `q_speace/aacm/loop.py` skeleton con `LOOP_HARD_PROHIBITIONS` e `_assert_path_not_prohibited` | T-AACM-SPEC done | #3, #4 |
| L1 | `ReputationRegistry` con decadimento esponenziale | L0 | #10, #11 |
| L2 | `ValidationSet` con schema JSON e test di disgiunzione | L0 | #5, #8, #9 |
| L3 | `ModuleReplacementProposal` + integrazione con `aacm_filter` esistente | L0, L2 | #1, #2, #17 |
| L4 | `evaluate_fallback_eligibility` (R5 operativa) | L2 | #6, #7 |
| L5 | `propose_module_replacement` + `execute_in_worktree` | L0, L3 | #3, #4, #14, #15, #16 |
| L6 | Resume + checkpoint integration | L0, L1 | #18, #19 |
| L7 | Ω-modulazione soglia adversarial | L0 | #12, #13 |
| L8 | 1 run end-to-end su `evolution_council.py` (worktree isolato, no merge) | L1-L7 | tutti |

**Ordine vincolante:** L0 → (L1 ∥ L2) → L3 → L4 → L5 → (L6 ∥ L7) → L8.
L0 prima di tutto (le proibizioni sono il guscio non-negoziabile).
L1 e L2 in parallelo (indipendenti tra loro). L5 dopo L3 e L4.
L6 e L7 indipendenti.

**Non-goal di questo task:** integrazione in produzione del loop
(merging automatico). Il loop termina con un branch pronto per
review umana. La promozione da branch a `main` richiede PR.

---

## 12. Limiti noti (v0.1)

- **Nessuna garanzia di convergenza.** Il loop è un'ipotesi
  architetturale; la convergenza è euristica, non dimostrata.
- **Nessuna firma sui checkpoint.** Il checkpoint `aacm.cp.1` è
  trusted-on-disk. Per ambienti ostili serve T-AACM-2.x.
- **`Phi` (FractureMap) resta proxy.** Le fratture sono inferite,
  non misurate direttamente (vedi T-AACM-SPEC §9).
- **Nessuna interazione con LLM.** Il loop non riscrive prompt;
  opera solo su moduli Python.
- **Validation set statico.** Non auto-rigenera; richiede PR umana.
  Un `validation_overfit_detected` non basta da solo a giustificare
  un cambio del set.

---

## 13. Riferimenti interni

- T-AACM-SPEC: `docs/T-AACM-SPEC.md`
- T-AACM_RESULTS: `docs/T-AACM_RESULTS.md`
- Controller: `q_speace/aacm/controller.py`
- Gate MM-ARP esistente: `q_speace/self_improvement_cortex/evolution_council.py:259`
- Costanti: `q_speace/aacm/constants.py`
- Primitives: `q_speace/aacm/primitives.py`
- Epistemic honesty policy: memoria utente `epistemic-honesty-papers.md`
- Regola 10 triangolazione: memoria utente `aacm-rule-10-triangulation.md`
