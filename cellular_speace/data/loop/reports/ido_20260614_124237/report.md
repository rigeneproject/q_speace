# Report Ciclo IDO: ido-28b91a05

**Avviato:** 2026-06-14T12:33:02.177795
**Completato:** 2026-06-14T12:42:37.573182
**Durata:** 575.4s
**Health score:** 1.000 → 0.037 (-0.963)

## 1. Ispezione
- Componenti ispezionati: 24
- Totale findings: 136679
- Durata: 574.5s

### Stato componenti

- **autonomic**: degraded (score=0.0) - 0C 0E 171W
- **immune**: degraded (score=0.0) - 0C 0E 98W
- **regions**: degraded (score=0.0) - 0C 0E 610W
- **sleep**: degraded (score=0.0) - 0C 0E 58W
- **metabolism**: degraded (score=0.0) - 0C 0E 241W
- **organism**: degraded (score=0.0) - 0C 0E 341W
- **memory**: degraded (score=0.0) - 0C 0E 625W
- **organism_observer**: degraded (score=0.0) - 0C 0E 463W
- **evolution**: degraded (score=0.0) - 0C 0E 1650W
- **ilf**: degraded (score=0.0) - 0C 0E 441W
- **evolution_daemon**: degraded (score=0.0) - 0C 0E 15200W
- **speace_core_root**: error (score=0.0) - 0C 0E 0W
- **scripts**: degraded (score=0.0) - 0C 0E 392W
- **monitoring**: degraded (score=0.0) - 0C 0E 20328W
- **dna**: degraded (score=0.0) - 0C 0E 296W
- **istruttore**: degraded (score=0.0) - 0C 0E 107W
- **cells**: degraded (score=0.0) - 0C 0E 3225W
- **regulation**: degraded (score=0.0) - 0C 0E 5760W
- **tests**: degraded (score=0.0) - 0C 0E 4253W
- **self_improvement**: degraded (score=0.0) - 0C 0E 15640W
- **dynamics**: degraded (score=0.0) - 0C 0E 4947W
- **runtime**: degraded (score=0.0) - 0C 0E 5642W
- **cognition**: degraded (score=0.0) - 0C 0E 55478W
- **docs**: healthy (score=0.9) - 0C 0E 0W

## 2. Diagnosi
- Diagnosi totali: 27
- Health score sistema: 0.0375
- Durata: 0.3s

### Diagnosi emesse

- **[#warning]** autonomic: elevato numero di warning (171)
  - Modulo non importabile
  - Modulo non importabile
  - Possibile import mancante

- **[#warning]** immune: elevato numero di warning (98)
  - Modulo non importabile
  - Modulo non importabile
  - Possibile import mancante

- **[#warning]** regions: elevato numero di warning (610)
  - Modulo non importabile
  - Modulo non importabile
  - Possibile import mancante

- **[#warning]** sleep: elevato numero di warning (58)
  - Modulo non importabile
  - Modulo non importabile
  - Possibile import mancante

- **[#warning]** metabolism: elevato numero di warning (241)
  - Modulo non importabile
  - Modulo non importabile
  - Possibile import mancante

- **[#warning]** organism: elevato numero di warning (341)
  - Modulo non importabile
  - Modulo non importabile
  - Modulo non importabile

- **[#warning]** memory: elevato numero di warning (625)
  - Modulo non importabile
  - Modulo non importabile
  - Possibile import mancante

- **[#warning]** organism_observer: elevato numero di warning (463)
  - Modulo non importabile
  - Modulo non importabile
  - Possibile import mancante

- **[#warning]** evolution: elevato numero di warning (1650)
  - Modulo non importabile
  - Modulo non importabile
  - Modulo non importabile

- **[#warning]** ilf: elevato numero di warning (441)
  - Modulo non importabile
  - Modulo non importabile
  - Possibile import mancante

- **[#warning]** evolution_daemon: elevato numero di warning (15200)
  - Possibile import mancante
  - Possibile import mancante
  - Possibile import mancante

- **[#critical]** speace_core_root: problemi critici rilevati
  - Inspection crashed: 'str' object has no attribute 'stem'

- **[#warning]** scripts: elevato numero di warning (392)
  - Modulo non importabile
  - Possibile import mancante
  - Possibile import mancante

- **[#warning]** monitoring: elevato numero di warning (20328)
  - Modulo non importabile
  - Modulo non importabile
  - Possibile import mancante

- **[#warning]** dna: elevato numero di warning (296)
  - Modulo non importabile
  - Modulo non importabile
  - Possibile import mancante

- **[#warning]** istruttore: elevato numero di warning (107)
  - Modulo non importabile
  - eval() - code injection risk
  - exec() - code injection risk

- **[#warning]** cells: elevato numero di warning (3225)
  - Modulo non importabile
  - Modulo non importabile
  - Possibile import mancante

- **[#warning]** regulation: elevato numero di warning (5760)
  - Modulo non importabile
  - Modulo non importabile
  - Possibile import mancante

- **[#warning]** tests: elevato numero di warning (4253)
  - Possibile import mancante
  - Possibile import mancante
  - Possibile import mancante

- **[#warning]** self_improvement: elevato numero di warning (15640)
  - Modulo non importabile
  - Modulo non importabile
  - Possibile import mancante

- **[#warning]** dynamics: elevato numero di warning (4947)
  - Modulo non importabile
  - Modulo non importabile
  - Possibile import mancante

- **[#warning]** runtime: elevato numero di warning (5642)
  - Modulo non importabile
  - Modulo non importabile
  - Possibile import mancante

- **[#warning]** cognition: elevato numero di warning (55478)
  - Modulo non importabile
  - Modulo non importabile
  - Possibile import mancante

- **[#warning]** Marker TODO/FIXME/HACK diffusi in 13 componenti
  - Marker: BUG: f actions:
                    logger.debug(
                        "Adattament
  - Marker: TODO: mente causato il fallimento?

        Metodo chiave per il ragionamento diagnost
  - Marker: TODO: zione evolutiva.

        Questo è il metodo principale chiamato ad ogni ciclo.


- **[#error]** Pattern di sicurezza rischiosi in 6 componenti
  - __import__() - dynamic import
  - __import__() - dynamic import
  - __import__() - dynamic import

- **[#error]** Moduli non importabili: 2463 file
  - Modulo non importabile: C:\cellular_speace\speace_core\cellular_brain\autonomic\__init__.py
  - Modulo non importabile: C:\cellular_speace\speace_core\cellular_brain\autonomic\autonomic_nervous_system.py
  - Modulo non importabile: C:\cellular_speace\speace_core\cellular_brain\autonomic\causal_adaptation_loop.py

- **[#warning]** Multipla degradazione: 22 componenti degradati
  - autonomic: score=0.0
  - immune: score=0.0
  - regions: score=0.0

## 3. Ottimizzazione
- Azioni totali: 27
- Applicate: 1
- Fallite: 0
- Saltate: 0
- Durata: 0.5s

### Azioni applicate

- ✅ Sostituiti 18 print() con logging.info()

## 4. Azioni prioritarie

1. Correggere immediatamente: Inspection crashed: 'str' object has no attribute 'stem'
2. Revisionare eval/exec/subprocess per sicurezza
3. Valutare se i pattern sono necessari o sostituibili
4. Correggere dipendenze circolari e import mancanti
5. Verificare assenza di errori di sintassi
6. Pianificare pulizia tecnica (tech debt)
7. Prioritizzare warning in autonomic
8. Prioritizzare warning in immune
9. Prioritizzare warning in regions
10. Prioritizzare warning in sleep

## 5. Trend

- **timestamp**: 2026-06-14T12:42:36.969166
- **total_components**: 24
- **healthy**: 1
- **degraded**: 22
- **critical**: 0
- **error**: 1
- **total_findings**: 136679
- **severity_breakdown**:
  - warning: 135966
  - info: 713
  - critical: 1
- **category_breakdown**:
  - code-quality: 136441
  - security: 219
  - structural: 1
  - data: 19

---
*Generato da /loop IDO Cycle ido-28b91a05*