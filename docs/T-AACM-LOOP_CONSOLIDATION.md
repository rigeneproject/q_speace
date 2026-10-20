# T-AACM-LOOP Consolidation — Indice dei deliverable

**Status:** consolidato (2026-08-23)
**Origine:** conversione delle 10 regole AACM in un modulo di
automiglioramento iterato (Opzione B + C + D della proposta
iniziale). Tutto il codice è ancorato a componenti esistenti
verificati di SPEACE (`EvolutionCouncil.aacm_filter`,
`AACMController`, `LegitimationChannelRegistry`).

---

## Specifica

- `docs/T-AACM-LOOP_SPEC.md` — specifica ingegneristica (499 righe)

## Codice

- `q_speace/aacm/loop.py` — orchestratore, dataclass, helper, gate MM-ARP-Ω-modulato, checkpoint/resume
- `q_speace/aacm/loop_constants.py` — costanti del loop (separate da quelle del controller AACM)
- `q_speace/aacm/executor.py` — `WorktreeExecutor` reale (apply diff, misurazione subprocess, rollback)
- `q_speace/aacm/pr_helper.py` — `create_pr` via `gh` (opt-in, mai auto)
- `q_speace/aacm/__main__.py` — CLI: `--once`, `--max-iterations`, `--worktree`, `--create-pr-on-success`, `--pr-base`, `--dry-run`
- `q_speace/aacm/data/validation_set.json` — 10 task placeholder su 5 task_type
- `q_speace/aacm/__init__.py` — export dei simboli pubblici del loop e dell'executor
- `q_speace/aacm/checkpoint.py` — esteso con `aacm.cp.1+loop.1`
- `q_speace/orchestrator.py` — hook opt-in `attach_loop` / `detach_loop` / `attached_loop` (non auto-invoca)

## Test

- `tests/test_aacm_loop.py` — 28 test (19 di accettazione spec §10 + D2 + D3 + sanity)
- `tests/test_aacm_executor.py` — 5 test (dry-run, apply+rollback, end-to-end, real exec time, failing subprocess)
- `tests/test_aacm_orchestrator_integration.py` — 4 test (attach/detach, invarianza "loop mai auto-invocato")
- `tests/test_aacm_pr_helper.py` — 5 test (build body, gh-missing skip, frozen dataclass)
- `tests/test_aacm.py` (preesistente) — 19 test AACM, nessuna regressione

**Totale AACM-related: 61 test, 61 verdi.**
**Suite completa: 398/399 (1 failure preesistente in test_spiking.py, non correlata).**

## Mapping regole → implementazione

| Regola | Implementazione |
|---|---|
| R1 (nodo centrale) | `LoopIteration.central_target` in `loop.py` |
| R2 (fail-fast) | `consecutive_failures` in `AACMLoop` |
| R3 (fratture) | `iteration.targeted_fracture` |
| R4 (sostituire vertici) | `ModuleReplacementProposal` con gate K≥2 |
| R5 (degradazione) | `evaluate_fallback_eligibility` con soglia 0.4 su validation set |
| R6 (reputazione) | `ReputationRegistry` con decadimento esponenziale |
| R7 (K≥2 canali) | `_assert_path_not_prohibited` + `aacm_min_evidence_kinds=2` (riusato) |
| R8 (auto-sostenibile) | `_refresh_infrastructure` ogni N iterazioni |
| R9 (no single point) | Invariante strutturale (test 4 di orch_integration) |
| R10 (ridondanza distribuita) | `assert_resilience` + soglia Ω-modulata |

## Cosa NON è stato fatto (limiti dichiarati)

- **Nessuna auto-merge.** La PR è sempre draft, opt-in.
- **Nessuna firma crittografica sui checkpoint.** T-AACM-2.x futuro.
- **L'executor misura solo `execution_time_s` reale.** Altri tipi di metrica usano fallback esistenza.
- **`Phi` resta proxy** (vedi T-AACM-SPEC §9).
- **Convergenza non dimostrata** — è un'ipotesi architetturale coerente con AACM, non una proprietà garantita.
- **Nessuna interazione con il LLM** — opera solo su moduli Python.

## Uso

```bash
# Dry-run, nessuna modifica
python -m q_speace.aacm --dry-run --max-iterations 3

# Esecuzione reale su worktree
python -m q_speace.aacm \
  --worktree /path/to/worktree \
  --validation-set /path/to/validation_set.json \
  --max-iterations 10

# Dopo un run andato a buon fine, apri PR draft
python -m q_speace.aacm \
  --worktree /path/to/worktree \
  --create-pr-on-success \
  --pr-base main
```

> **Canonical invocation:** la CLI vive in `q_speace/aacm/__main__.py`,
> quindi si invoca come `python -m q_speace.aacm`. **Non** usare
> `python -m q_speace.aacm.loop` (è il modulo, non un entry point).

Da Python:

```python
from q_speace.aacm import AACMLoop, ModuleReplacementProposal

loop = AACMLoop(worktree=Path("/tmp/wt"), omega=0.6, max_iterations=10)

def my_propose(iteration, context):
    return ModuleReplacementProposal(...)

result = loop.run(propose_fn=my_propose)
print(result.stop_reason, result.iterations_run)
```
