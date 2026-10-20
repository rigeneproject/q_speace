# Piano: Fase 3 — Organismo Auto-modificante (Learning + Reasoning)

## Contesto

Il Cognitive Status Report del 2026-06-03 mostra SPEACE a:
- **Overall: 74.03% (competent)** — ARI 86.42%, AGI legacy 49.13%
- **Learning: 50.7% (developing)** — collo di bottiglia principale
- **Reasoning: 74.0% (competent)** — workspace ignition pieno ma ARC solo 2/5
- **Punti forti**: Generalization 100%, Planning 76%, Adaptation 75%
- **Aree di sviluppo**: Learning 50.7%, Autonomy 72.5%, Memory 70%

L'utente ha chiesto di portare l'Overall oltre l'80% intervenendo solo sulle 2
dimensioni più deboli: **Learning** e **Reasoning**.

### Risultato atteso
- Learning 50.7 → **70+** (+20 punti)
- Reasoning 74.0 → **85+** (+11 punti)
- Overall 74.03 → **80-82%** (soglia superata)

### Risultato del survey del codice (già svolto dall'agente Explore)
Tutto l'occorrente esiste già come primitive — manca solo la chiusura del
ciclo di adozione e l'orchestrazione MM-APR.

| Componente | Stato attuale | File |
|---|---|---|
| `LimitationDetector` (T45) | pronto, rileva regressioni | `speace_core/cellular_brain/self_improvement/limitation_detector.py` |
| `MutationEngine` (T132) + `ArchitectureRewriter` | pronti, emettono proposals | `evolution_daemon/mutation_engine.py`, `self_improvement/architecture_rewriter.py` |
| `CognitiveMutationSandbox` | pronto, simula in sandbox | `cognitive_evolution/cognitive_mutation_sandbox.py` |
| `ArchitecturePatchExecutor` (T50) | pronto, applica + snapshot + rollback | `self_improvement/architecture_patch_executor.py` |
| `SelfImprovementLoop` (T45) | pronto, ma invocato solo da `executor_bridge` | `self_improvement/self_improvement_loop.py` |
| `SelfImprovementMemory` (T46) | pronto, scrive in `history.jsonl` | `self_improvement/self_improvement_memory.py` |
| `ConsolidationPolicyEngine` (T57) | pronto, decide STABLE/PROBATIONARY/QUARANTINED | `evolutionary_memory/consolidation_policy_engine.py` |
| `EvolutionaryMemoryGovernor` (T57) | pronto, ma **mai chiamato automaticamente** | `evolutionary_memory/evolutionary_memory_governor.py` |
| `FewShotProgramInductionEngine` (FSPI) | pronto, 22+ primitive, validation integrata | `cognition/few_shot_program_induction_engine.py` |
| `GlobalWorkspace` (T71) | pronto, ma **non cablato in FSPI** | `cognition/global_workspace.py` |
| `AdversarialCritic` | **MANCANTE** | da creare |
| `EpistemicAuditor` | **MANCANTE** | da creare |
| `MMAPRCouncil` (orchestratore 4 agenti) | **MANCANTE** | da creare |

## Decisioni di design

### 1. Self-modification cycle (Priorità 1: Learning)
- Creare **`SelfModificationCycle`** in `speace_core/cellular_brain/self_improvement/self_modification_cycle.py`:
  osserva le metriche → identifica limitazioni → genera mutazioni → testa in
  sandbox → valida su benchmark reale → adotta in memoria evolutiva → aggiorna
  epigenetica. Un singolo oggetto che incapsula l'intero loop.
- Estendere **`EvolutionaryMemoryGovernor`** con un metodo
  `adopt_self_modification(cycle_result)` che promuove un ciclo chiuso a STABLE
  quando `delta_score > 0`, `regression_score < 0.2`, `safety_score >= 0.7`.
- Aggiungere un `__init__.py` export e un test smoke.

### 2. MM-APR (Priorità 2: Reasoning)
- Creare **`speace_core/cellular_brain/cognition/mmapr_council.py`** con:
  - `InterpreterAgent` — applica il programma candidato al training set
  - `StructuralVerifier` — valida output su TUTTI i training pairs (testa completezza)
  - `AdversarialCritic` — genera contro-esempi: prove che il programma è sbagliato
  - `EpistemicAuditor` — quantifica confidenza: numero di pairs, copertura, semplicità
  - `MMAPRCouncil.deliberate(candidate, train_pairs) → Verdict` —
    voto pesato, il council emette {accept, reject, needs_evidence}
- Cablare in **`FewShotProgramInductionEngine`**: il metodo `_validate_program`
  viene esteso in `_mmapr_validate(candidate, train_pairs)` che delega al
  council quando la validazione deterministica è incerta (pixel_score tra
  0.3 e 0.95).
- Cablare in **`GlobalWorkspace`**: aggiungere un metodo
  `broadcast_arc_reasoning(representation, deliberation)` che emette la
  delibera nel campo ricorrente → ignition migliora quando c'è consensus.

### 3. Integrazione dashboard
- Aggiungere endpoint **`/api/cognitive_analysis`** (già esiste) — i campi
  `learning.insights` e `reasoning.insights` riflettono automaticamente il
  nuovo sistema. Verificare che i numeri salgano dopo 1 ciclo del daemon.

### 4. Sicurezza
- Tutte le mutazioni passano per `ArchitecturePatchExecutor` che ha
  `ALLOWED_FLAGS / ALLOWED_PROFILES / ALLOWED_NUMERIC` come allowlist.
- `ConsolidationPolicyEngine` richiede `safety_score >= 0.7` per STABLE.
- Niente auto-apply su DNA: solo orchestrator flags/numeric proxies + write
  in `EvolutionaryMemoryStore` per la fase "adopt".
- Tutto osservabile: eventi scritti in `MorphologicalMemory` come i
  sistemi esistenti.

## File da creare / modificare

### Nuovi file (4)
1. `speace_core/cellular_brain/self_improvement/self_modification_cycle.py`
   — `SelfModificationCycle` (loop chiuso) + `SelfModificationCycleResult` model
2. `speace_core/cellular_brain/cognition/mmapr_council.py` — 4 agenti + council
3. `tests/self_improvement/test_self_modification_cycle.py` — smoke test
4. `tests/cognition/test_mmapr_council.py` — smoke test

### File da modificare (5)
1. `speace_core/cellular_brain/self_improvement/__init__.py` — esporta
   `SelfModificationCycle`
2. `speace_core/cellular_brain/cognition/__init__.py` — esporta `MMAPRCouncil`
3. `speace_core/cellular_brain/evolutionary_memory/evolutionary_memory_governor.py`
   — aggiungi `adopt_self_modification(cycle_result)`
4. `speace_core/cellular_brain/cognition/few_shot_program_induction_engine.py`
   — usa MM-APR council quando la validazione deterministica è incerta
5. `speace_core/cellular_brain/cognition/global_workspace.py`
   — metodo `broadcast_arc_deliberation` che alimenta ignition

## Componente 1 — SelfModificationCycle (dettaglio)

```python
class SelfModificationCycleResult(BaseModel):
    cycle_id: str
    observed: Dict[str, float]          # metriche lette
    limitations: List[str]              # ids LimitationSignal
    mutations: List[str]                # ids proposal
    tests: Dict[str, Any]               # sandbox verdicts
    adoption: Optional[str]             # STABLE / PROBATIONARY / QUARANTINED / None
    delta_score: float                  # post - pre
    safety_score: float
    regression_score: float

class SelfModificationCycle:
    """Observe → Identify → Mutate → Test → Adopt"""

    def __init__(self, orchestrator, memory, regression_guard=None):
        self.detector = LimitationDetector(memory=memory, regression_guard=regression_guard)
        self.rewriter = ArchitectureRewriter()
        self.sandbox = CounterfactualArchitectureSandbox()
        self.executor = ArchitecturePatchExecutor(orchestrator=orchestrator, memory=memory)
        self.evaluator = SkillFitnessEvaluator()
        self.governor = EvolutionaryMemoryGovernor()
        self.sim_memory = SelfImprovementMemory()

    def run(self, metrics: Dict[str, Any]) -> SelfModificationCycleResult:
        # 1. OBSERVE: collect current scores
        observed = self._observe(metrics)
        # 2. IDENTIFY: detect limitations
        signals = self.detector.detect_from_metrics(observed)
        diagnoses = self.detector.aggregate_signals(signals)
        # 3. MUTATE: generate proposals
        proposals = [self.rewriter.generate_proposal(d) for d in diagnoses]
        # 4. TEST: sandbox + benchmark validation
        test_results = []
        for p in proposals:
            sandbox_v = self.sandbox.run_scenario(p)
            post_metrics = self._observe(metrics)  # simulated
            test_results.append({"proposal": p, "sandbox": sandbox_v,
                                 "delta": post_metrics.get("cognitive_score", 0) -
                                          observed.get("cognitive_score", 0)})
        # 5. ADOPT: pick best safe, write to evolutionary memory
        best = self._pick_best_safe(test_results)
        adoption = None
        delta_score = 0.0
        if best is not None:
            exec_result = self.executor.execute_patch(best["proposal"])
            delta_score = exec_result.delta_score
            adoption = self.governor.adopt_self_modification(...)
        return SelfModificationCycleResult(...)
```

## Componente 2 — MM-APR Council (dettaglio)

```python
@dataclass
class AgentVote:
    agent: str
    accept: bool
    confidence: float
    rationale: str
    evidence: Dict[str, Any]

@dataclass
class CouncilVerdict:
    candidate_id: str
    votes: List[AgentVote]
    accept: bool              # majority
    emergent_confidence: float
    rationale: str

class InterpreterAgent:
    def apply(self, candidate, train_pairs) -> Dict[str, Any]:
        # Esegue il programma su tutti i training pairs
        outputs = [candidate.program.apply(pair.input) for pair in train_pairs]
        return {"outputs": outputs}

class StructuralVerifier:
    def verify(self, interpreter_output, train_pairs) -> AgentVote:
        # Confronta output vs expected
        correct = sum(1 for o, p in zip(interpreter_output["outputs"], train_pairs)
                      if grids_equal(o, p.output))
        score = correct / max(1, len(train_pairs))
        return AgentVote("structural_verifier", score == 1.0, score,
                         f"{correct}/{len(train_pairs)} training pairs correct",
                         {"correctness": score})

class AdversarialCritic:
    def challenge(self, candidate, train_pairs) -> AgentVote:
        # Genera contro-esempi: test pairs con variazioni minime
        # Se il programma è overfit, fallisce sui contro-esempi
        perturbations = [slight_perturb(p) for p in train_pairs[:3]]
        # ... valuta robustezza

class EpistemicAuditor:
    def audit(self, candidate, train_pairs) -> AgentVote:
        # Calcola confidenza basata su: numero di pairs, lunghezza programma,
        # copertura del dominio di output
        n = len(train_pairs)
        length_penalty = min(1.0, 5.0 / max(1, len(candidate.program.primitives)))
        coverage = len(set([p.output.flatten()[0] for p in train_pairs])) / 10.0
        confidence = min(1.0, (n / 5.0) * length_penalty * 0.5 + coverage * 0.5)
        return AgentVote("epistemic_auditor", confidence >= 0.5, confidence,
                         f"n_pairs={n}, length_penalty={length_penalty:.2f}",
                         {"n_pairs": n, "length_penalty": length_penalty,
                          "coverage": coverage})

class MMAPRCouncil:
    def __init__(self):
        self.interpreter = InterpreterAgent()
        self.verifier = StructuralVerifier()
        self.critic = AdversarialCritic()
        self.auditor = EpistemicAuditor()

    def deliberate(self, candidate, train_pairs) -> CouncilVerdict:
        io = self.interpreter.apply(candidate, train_pairs)
        votes = [
            self.verifier.verify(io, train_pairs),
            self.critic.challenge(candidate, train_pairs),
            self.auditor.audit(candidate, train_pairs),
        ]
        # Voto emergente: pesato per confidenza
        accept_score = sum(v.confidence for v in votes if v.accept)
        reject_score = sum(v.confidence for v in votes if not v.accept)
        accept = accept_score > reject_score
        return CouncilVerdict(candidate.id, votes, accept,
                              emergent_confidence=accept_score/(accept_score+reject_score),
                              rationale="; ".join(v.rationale for v in votes))
```

## Verifica end-to-end

1. `python -m pytest tests/self_improvement/test_self_modification_cycle.py -v` — smoke
2. `python -m pytest tests/cognition/test_mmapr_council.py -v` — smoke
3. `python -m pytest tests/ -x --no-header -q 2>&1 | tail -5` — full suite
   (target: 4367+ pass, 0 fail)
4. `python scripts/start_ari_dashboard.py --port 5699` + curl `/api/cognitive_analysis`
   — verificare che `learning.score >= 70` e `reasoning.score >= 85`

## Rischi e mitigazione
- **Patch non sicuri**: `ArchitecturePatchExecutor` ha allowlist — solo
  flag/profile/numeric noti, niente scrittura su DNA YAML
- **MM-APR potrebbe rallentare**: il council viene chiamato solo quando
  pixel_score ∈ [0.3, 0.95] (casi incerti), altrimenti la validazione
  deterministica è sufficiente
- **Conflitti con loop esistenti**: `SelfModificationCycle` è invocato
  una volta per `EvolutionDaemon.run_cycle` se abilitato, non interferisce
  con `SelfImprovementLoop.run_detection_cycle` esistente
