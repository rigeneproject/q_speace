# /loop — Agente ispettivo-diagnostico-ottimizzativo autonomo per SPEACE

Ciclo **IDO** continuo: **I**spezione → **D**iagnosi → **O**ttimizzazione dell'intero sistema SPEACE.

## Architettura

```
/loop/
  agentic_loop.py      Orchestratore principale del ciclo IDO
  inspector.py         Fase 1: Ispezione sistemica di tutti i componenti
  diagnostician.py     Fase 2: Diagnosi cause radice e pattern sistemici
  optimizer.py         Fase 3: Correzioni automatiche e proposte
  reporters.py         Generazione report JSON/Markdown
  models.py            Modelli dati (dataclass)
  config.py            Configurazione percorsi e parametri
  utils.py             Utility condivise (analisi codice, import check)
  loop.md              Questa documentazione
  avvio_loop.bat       Avvio loop continuo
  avvio_loop_chat.bat  Avvio modalita chat interattiva
  avvio_loop_once.bat  Avvio singolo ciclo
```

## Ciclo IDO

### Fase 1 — Ispezione (Inspector)

Scansiona in parallelo **24 componenti** del sistema SPEACE:

| Componente | Cosa controlla |
|---|---|
| `cells` | Cellule neurali (neuroni, sinapsi, astrociti, microglia, etc.) |
| `regulation` | Motori di regolazione (omeostasi, plasticita, neurogenesi, apoptosis) |
| `regions` | Regioni cerebrali (rete, routing, stabilita) |
| `memory` | Sistemi di memoria (morfologica, episodica, semantica, associativa) |
| `cognition` | Cognizione (workspace, linguaggio, pianificazione, ragionamento) |
| `dynamics` | Dinamiche neurali (oscillatori, accoppiamento, codifica predittiva) |
| `autonomic` | Sistema nervoso autonomo (battito, riflessi, drive) |
| `self_improvement` | Auto-miglioramento (loop, sandbox, patch executor) |
| `immune` | Sistema immunitario digitale |
| `metabolism` | Metabolismo energetico |
| `sleep` | Ciclo sonno-veglia |
| `organism` | Integrazione organismo |
| `runtime` | Runtime continuo (loop, health, checkpoint, recovery) |
| `monitoring` | Monitoraggio (alert, anomalie, dashboard, report) |
| `organism_observer` | OFG (grafo funzionale, topologia, metriche) |
| `evolution` | Motore evolutivo (controller, fitness, cicli) |
| `ilf` | Campo informazionale logico |
| `evolution_daemon` | Demone evolutivo (14-task cycle) |
| `speace_core_root` | File radice (orchestrator, cli, event_bus) |
| `scripts` | Script di automazione |
| `tests` | Suite di test |
| `docs` | Documentazione |
| `dna` | DNA/genoma (genoma YAML, validatori, modelli) |
| `ispettore` | Ispettore manutentore esistente |

Ogni file viene controllato per:
- **Sintassi Python** (AST parse)
- **Importabilita** (import reale)
- **Marker** TODO/FIXME/HACK/XXX
- **Pattern pericolosi** (eval, exec, subprocess, pickle, credentiali hardcoded)
- **Import mancanti** (analisi statica AST)
- **Integrita JSON/YAML** (dati e genoma)

### Fase 2 — Diagnosi (Diagnostician)

Analizza cross-componente:
- **Diagnosi per componente**: problemi critici, errori ricorrenti, warning diffusi
- **Diagnosi cross-componente**: marker diffusi, pattern di sicurezza, import non funzionanti
- **Diagnosi architetturale**: componenti in stato critico/degradato, pattern sistemici
- **Health score complessivo**: media pesata degli score dei componenti
- **Azioni prioritarie**: lista ordinata per severita

### Fase 3 — Ottimizzazione (Optimizer)

- **Correzioni rapide**: fix automatici per problemi strutturali
- **Fix print() → logging.info()**: refactoring automatico con backup
- **Fix JSON**: tentativo di riparazione file JSON malformati
- **Proposte strutturali**: suggerimenti per componenti con health score basso
- **Backup automatici**: tutti i file modificati vengono salvati in `data/loop/backups/`

## Utilizzo

### Loop continuo (consigliato)

```bash
python -m loop.agentic_loop --interval 300
```

### Singolo ciclo (CI/CD, audit)

```bash
python -m loop.agentic_loop --once
```

### Modalita chat interattiva

```bash
python -m loop.agentic_loop --chat
```

Comandi: `/scan /status /report /history /exit`

### Solo analisi (dry-run)

```bash
python -m loop.agentic_loop --once --dry-run
```

## Integrazione con SPEACE

Il loop IDO si integra con l'ecosistema SPEACE esistente:

- **Evolution Daemon**: puo attivare il loop come task aggiuntivo del ciclo evolutivo
- **Ispettore esistente**: il loop ne analizza lo stato e ne suggerisce ottimizzazioni
- **Monitoring**: i report IDO sono accessibili via dashboard
- **Orchestrator**: il loop puo leggere lo stato dell'orchestratore per ispezioni live

## Output

Ogni ciclo produce in `data/loop/reports/ido_YYYYMMDD_HHMMSS/`:
- `cycle_full.json` — Report completo in JSON
- `report.md` — Report leggibile in Markdown
- `summary.json` — Sommario compatto

Stato persistito in `data/loop/state/loop_state.json`.
