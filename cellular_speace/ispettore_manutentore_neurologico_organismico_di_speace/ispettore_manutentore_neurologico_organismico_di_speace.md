# Agentic AI ispettore_manutentore_neurologico_organismico_di_speace

Situato nella directory `C:\cellular_speace\ispettore_manutentore_neurologico_organismico_di_speace`

## Architettura

```
C:\cellular_speace\ispettore_manutentore_neurologico_organismico_di_speace\
├── ispettore_manutentore_neurologico_organismico_di_speace.md   # Documentazione
├── opencode.json                                                 # Configurazione LLM Cloud (DeepSeek V4 Flash Free)
├── opencode.local.json                                           # Configurazione LLM Locale (gemma4:12b via Ollama)
├── avvio_cloud.bat                                               # Avvio con LLM Cloud
├── avvio_locale.bat                                              # Avvio con LLM Locale
├── avvio_chat.bat                                                # Avvio modalità chat con Roberto (owner)
├── ispettore_core.ps1                                            # Engine principale (loop, scansione, diagnosi, chat)
├── register_startup.bat                                          # Registrazione avvio Windows (richiede admin)
├── register_startup.ps1                                          # Script PowerShell per registrazione startup
└── remove_startup.bat                                            # Rimozione avvio Windows
```

## Descrizione

L'Agentic AI "ispettore_manutentore_neurologico_organismico_di_speace" è un sistema agentico con funzione di ispezione, diagnosi e ottimizzazione per rilevazione, correzione di errori, problemi, bug nella struttura e nel funzionamento dei componenti del cervello e organismo di SPEACE,
e di tutti gli strumenti funzionali al miglioramento di SPEACE come il team agentico AGI "speace_agi_team", ecc., e ottimizzazione dell'intero sistema.

## Capacità

- **Lettura e analisi** di tutti i file della directory `cellular_speace`
- **Modifica dei file** e creazione di nuovi file
- **Ricerca web** per aggiornamenti e informazioni
- **Sub-agents in parallelo** per ispezione multi-area simultanea
- **Chat interattiva** con l'owner Roberto
- **Manutenzione preventiva**: Controlli periodici programmati via cron per verificare lo stato di SPEACE ed evitare blocchi improvvisi
- **Manutenzione correttiva**: Interventi tempestivi per diagnosticare e riparare guasti, correggere errori, problemi, bug già avvenuti

## Architettura agentica

1. **Interpretazione dell'intento**: capire un obiettivo macro fornito dall'utente senza bisogno di istruzioni passo-passo
2. **Pianificazione autonoma**: scomporre l'obiettivo principale in sotto-attività necessarie
3. **Uso di strumenti**: accesso a software e tool per compiere azioni concrete, API, ricerche web, modifiche file
4. **Riflessione e correzione**: valuta i propri errori, corregge la strategia in tempo reale senza intervento umano

## Modalità di esecuzione

| Comando | Descrizione |
|---------|-------------|
| `avvio_cloud.bat` | Avvio con DeepSeek V4 Flash Free (cloud) |
| `avvio_locale.bat` | Avvio con gemma4:12b (locale Ollama) |
| `avvio_chat.bat` | Modalità dialogo interattivo con Roberto |
| `register_startup.bat` | Registra nelle app di avvio Windows |
| `remove_startup.bat` | Rimuove dalle app di avvio Windows |

## Parametri del core engine

```
ispettore_core.ps1 -Mode <mode> [-ConfigPath <path>] [-ScanInterval <sec>] [-NoLoop]

Mode:
  inspect   - Loop continuo di ispezione/diagnosi/ottimizzazione (default)
  chat      - Modalità interattiva di dialogo con Roberto
  once      - Esecuzione singola (ispezione + report)
  supervise - Supervisione sub-agents e coordinamento
```

## Aree monitorate

- `speace_core` - Cervello di SPEACE
- `speace_agi_team` - Team agentico AGI
- `data` - Dati e checkpoint
- `scripts` - Script di sistema
- `tests` - Suite di test
- `docs` - Documentazione
- `reports` - Report generati

## Diagnostica file

L'ispettore rileva automaticamente:
- Codice pericoloso (eval/exec)
- TODO/FIXME lasciati nel codice
- Uso di print() invece di logging
- File JSON non validi
- File eccessivamente grandi (>2000 linee)
- File vuoti
- Errori di lettura

## Modelli

### Cloud (default)
- Provider: OpenCode Zen
- Modello: DeepSeek V4 Flash Free
- API Key: configurata in `opencode.json`

### Locale
- Provider: Ollama
- Modello: gemma4:12b
- Endpoint: http://localhost:11434

## Avvio automatico Windows

L'ispettore puo essere registrato come app di avvio di Windows (Task Manager > App di avvio):
1. Eseguire `register_startup.bat`
2. Selezionare modalita cloud o locale
3. Riavviare il computer per testare

Durante la registrazione viene creato anche `watcher_restart.bat`, un watcher che
controlla ogni 30 secondi se l'Ispettore e in esecuzione e lo riavvia in caso di arresto.

Per rimuovere: `remove_startup.bat` o Task Manager > App di avvio > Disabilita

## Core Python Agent

`ispettore_agent.py` e il motore principale Agentic AI:

```
python ispettore_agent.py [--mode cloud|local] [--chat] [--once] [--use-llm] [--use-subagents]
```

Parametri:
- `--mode cloud|local`: LLM cloud (DeepSeek V4 Flash Free via OpenCode Zen) o locale (gemma4:12b Ollama)
- `--chat`: modalita dialogo interattiva con Roberto
- `--once`: esegue un solo ciclo di scansione/report
- `--use-llm`: abilita analisi LLM a ogni ciclo
- `--use-subagents`: abilita sub-agents in parallelo su ogni file
- `--scan-interval N`: intervallo in secondi tra cicli (default 60)
- `--no-auto-fix`: disabilita correzioni automatiche
- `--no-web`: disabilita ricerca web

## Configurazione LLM

- `opencode.json`: configurazione LLM Cloud (DeepSeek V4 Flash Free via OpenCode Zen, API key inclusa)
- `opencode.local.json`: configurazione LLM Locale (gemma4:12b via Ollama)
