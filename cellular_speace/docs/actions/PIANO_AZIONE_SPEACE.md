# 🎯 PIANO D'AZIONE SPEACE — 2026-06-12

> Versione: 1.0  
> Autore: Codex (analisi automatica della repo `cellular_speace`)  
> Stato: approvato e in esecuzione

## 1. Sintesi dello stato

| Indicatore | Valore |
|---|---|
| File totali (esclusi cache/git/work) | 2.602 |
| Dimensione totale | 1.265,74 MB (di cui 1.181 MB in JSONL) |
| File Python | 1.011 (7,69 MB) |
| File Markdown | 125 (1,08 MB) |
| Test Python | 361 |
| File con `class Config:` Pydantic legacy | 0 (già migrato) |
| File con `datetime.utcnow` | 0 |
| File con `except: pass` silenziosi | 103 (segnalati ma non bloccanti) |
| Broadcast AGI seriale | False (presenza di `for aid, agent in _agents.items():` con `agent.chat(message)` bloccante) |
| Broadcast AGI parallelo con `asyncio.gather` | False |
| Runtime plugin (SubsystemPlugin/Scheduler/Context) | Presente |
| Coordinators (Memory/Evolution/Metabolism/...) | 9 presenti |
| Species Orientation YAML | Presente e valido |
| Capability gaps scaffolding (Cognitive Genome, Evolution Genes) | Presenti |
| `max_tokens` di default AgentConfig | 4096 |
| Tag git più recenti | `v0.3.25-t41` … `v0.1.0-mvp` |

## 2. Domini di intervento

| # | Dominio | Stato attuale | Azione |
|---|---|---|---|
| D1 | **Kernel / Hardening** | orchestrator 140 kB, EventBus già osservabile, Pydantic v2 ok | Smoke test integrazione + verifica indici O(1) su NeuralCircuit |
| D2 | **Orchestrator decomposition** | SpeaceKernel + 9 SubsystemCoordinator + SubsystemScheduler già presenti | Verificare che `CellularBrainOrchestrator` li attivi davvero; smoke test end-to-end |
| D3 | **AGI Team throughput** | broadcast seriale in `api_broadcast`, `max_tokens=4096` | Parallelizzare con `asyncio.to_thread` + gathering, portare `max_tokens` a 8192, retry su troncati, metriche durata |
| D4 | **DNA / Digital DNA** | species_orientation.yaml presente; default_genome.yaml deve referenziarlo | Aggiungere blocco `species_orientation` al default_genome.yaml + validatore |
| D5 | **Capability gaps** | `cognitive_genome.py` e `evolution_genes.py` esistenti | Aggiungere scaffolding `failure_memory.py` + `object_centric_representation.py` con test minimi |
| D6 | **Test suite** | 361 test esistenti | Aggiungere test mirati per i moduli toccati |
| D7 | **Documentazione** | `docs/diagnosi_speace.md` esistente, 125 .md | Aggiornare diagnosi/AGI plan/roadmap; generare report finale in `outputs/` |
| D8 | **Audit / reports** | 11.193 file in `reports/`, già avviato `reports/actions/01_repo_audit` | Generare `02_kernel_smoketest`, `03_agi_throughput`, `04_capability_scaffolding`, `05_test_results`, `06_actions_report` |

## 3. Sequenza di esecuzione

1. **T1** Audit automatico del repository (conteggi, dimensioni, debito tecnico) — `01_repo_audit/`
2. **T2** Verifica smoke del kernel (NeuralCircuit O(1), EventBus, Pydantic v2, Runtime Plugin) — `02_kernel_smoketest/`
3. **T3** Decomposizione orchestrator: import test + uso coordinators — incluso in T2
4. **T4** AGI Team: parallelizza broadcast, `max_tokens` 8192, retry, metriche — `03_agi_throughput/`
5. **T5** Species Orientation integrato in `default_genome.yaml` + validatore — `04_species_orientation/`
6. **T6** Capability gaps scaffolding (Failure Memory, Object-Centric Representation) + test — `05_capability_scaffolding/`
7. **T7** Pytest mirato sui moduli toccati — `06_test_results/`
8. **T8** Documentazione aggiornata + report finale in `outputs/`
9. **T9** Riepilogo esecutivo e consegna all'utente

## 4. Criteri di successo

- Tutti i moduli toccati importano correttamente (`python -c "..."` verde).
- I test mirati passano.
- `reports/actions/` contiene cartelle `01_*` … `06_*` con file `.json` o `.md`.
- `outputs/` contiene un report finale leggibile dall'utente.
- Nessuna regressione sul runtime esistente (orchestrator, AGI team, runtime engine).
