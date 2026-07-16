# Report Ciclo IDO: ido-209ecf2e

**Avviato:** 2026-06-14T12:45:33.611878
**Completato:** 2026-06-14T12:46:16.353958
**Durata:** 42.7s
**Health score:** 1.000 → 0.957 (-0.043)

## 1. Ispezione
- Componenti ispezionati: 24
- Totale findings: 1017
- Durata: 42.4s

### Stato componenti

- **speace_core_root**: degraded (score=0.19) - 0C 8E 32W
- **memory**: degraded (score=0.89) - 0C 1E 3W
- **evolution**: healthy (score=0.99) - 0C 0E 0W
- **runtime**: healthy (score=0.99) - 0C 0E 0W
- **scripts**: healthy (score=0.99) - 0C 0E 5W
- **regulation**: healthy (score=0.99) - 0C 0E 0W
- **self_improvement**: healthy (score=0.99) - 0C 0E 0W
- **istruttore**: healthy (score=0.99) - 0C 0E 3W
- **dna**: healthy (score=0.99) - 0C 0E 0W
- **docs**: healthy (score=0.99) - 0C 0E 0W
- **tests**: healthy (score=0.99) - 0C 0E 7W
- **monitoring**: healthy (score=0.99) - 0C 0E 21W
- **evolution_daemon**: healthy (score=0.99) - 0C 0E 180W
- **cognition**: healthy (score=0.99) - 0C 0E 0W
- **autonomic**: healthy (score=1.0) - 0C 0E 0W
- **regions**: healthy (score=1.0) - 0C 0E 0W
- **immune**: healthy (score=1.0) - 0C 0E 0W
- **sleep**: healthy (score=1.0) - 0C 0E 0W
- **metabolism**: healthy (score=1.0) - 0C 0E 0W
- **organism**: healthy (score=1.0) - 0C 0E 0W
- **organism_observer**: healthy (score=1.0) - 0C 0E 0W
- **ilf**: healthy (score=1.0) - 0C 0E 0W
- **cells**: healthy (score=1.0) - 0C 0E 0W
- **dynamics**: healthy (score=1.0) - 0C 0E 0W

## 2. Diagnosi
- Diagnosi totali: 8
- Health score sistema: 0.9567
- Durata: 0.0s

### Diagnosi emesse

- **[#warning]** scripts: elevato numero di warning (5)
  - subprocess execution
  - __import__() - dynamic import
  - __import__() - dynamic import

- **[#warning]** tests: elevato numero di warning (7)
  - __import__() - dynamic import
  - eval() - code injection risk
  - eval() - code injection risk

- **[#warning]** monitoring: elevato numero di warning (21)
  - __import__() - dynamic import
  - __import__() - dynamic import
  - __import__() - dynamic import

- **[#warning]** evolution_daemon: elevato numero di warning (180)
  - subprocess execution
  - subprocess execution
  - subprocess execution

- **[#error]** speace_core_root: errori ricorrenti di categoria structural
  - Errore di sintassi Python (C:\cellular_speace\speace_core\cellular_brain\benchmark\neurofunctional_benchmark.py)
  - Errore di sintassi Python (C:\cellular_speace\speace_core\orchestrator.py)
  - Errore di sintassi Python (C:\cellular_speace\speace_core\cellular_brain\benchmark\neurofunctional_benchmark.py)

- **[#warning]** speace_core_root: elevato numero di warning (32)
  - subprocess execution
  - subprocess execution
  - subprocess execution

- **[#warning]** Marker TODO/FIXME/HACK diffusi in 14 componenti
  - Marker: BUG: f actions:
                    logger.debug(
                        "Adattament
  - Marker: TODO: zione evolutiva.

        Questo è il metodo principale chiamato ad ogni ciclo.

  - Marker: TODO: zione evolutiva.

        Questo è il metodo principale chiamato ad ogni ciclo.


- **[#error]** Pattern di sicurezza rischiosi in 7 componenti
  - __import__() - dynamic import
  - __import__() - dynamic import
  - __import__() - dynamic import

## 3. Ottimizzazione
- Azioni totali: 3
- Applicate: 0
- Fallite: 0
- Saltate: 0
- Durata: 0.3s

### Azioni applicate


## 4. Azioni prioritarie

1. Revisionare structural in speace_core_root
2. Eseguire test mirati sui moduli interessati
3. Revisionare eval/exec/subprocess per sicurezza
4. Valutare se i pattern sono necessari o sostituibili
5. Pianificare pulizia tecnica (tech debt)
6. Prioritizzare warning in scripts
7. Prioritizzare warning in tests
8. Prioritizzare warning in monitoring
9. Prioritizzare warning in evolution_daemon
10. Prioritizzare warning in speace_core_root

## 5. Trend

- **timestamp**: 2026-06-14T12:46:16.029072
- **total_components**: 24
- **healthy**: 22
- **degraded**: 2
- **critical**: 0
- **error**: 0
- **total_findings**: 1017
- **severity_breakdown**:
  - info: 537
  - error: 9
  - warning: 251
- **category_breakdown**:
  - code-quality: 518
  - structural: 9
  - security: 251
  - data: 19

---
*Generato da /loop IDO Cycle ido-209ecf2e*