# SPEACE Life Support

Questo documento descrive come mantenere vivo l organismo digitale SPEACE in modo
persistente, resiliente e osservabile.

## Stato riscontrato

All avvio della diagnosi SPEACE aveva gia un processo `live` attivo, ma mancava:

- un supervisore che riavviasse automaticamente i processi in caso di crash;
- una separazione tra la porta del monitor SPEACE (8787) e l interfaccia chat
  Anemos (anch essa configurata su 8787, causando conflitti);
- un file di monitoraggio (`data/monitoring/alerts.jsonl`) corrotto (5.5 MB di
  byte nulli).

## Interventi effettuati

1. **Riparazione dati corrotti**
   - Backup di `data/monitoring/alerts.jsonl`.
   - Troncamento del file corrotto a zero byte.

2. **Configurazione Anemos**
   - `speace_anemos.py` ora legge la porta da `ANEMOS_PORT` (default `8788`).
   - Endpoint LLM e modello configurabili da `.env` / `.env.example`.

3. **Supervisore resiliente**
   - Creato `scripts/speace_life_support.ps1`.
   - Avvia in un unico terminale:
     - `speace_core.cli live` (cervello/organismo 24/7);
     - `speace_anemos.py` (interfaccia web chat).
   - Riavvia automaticamente i processi se terminano.
   - Logga stdout/stderr in `data/logs/life_support/`.

## Come usare

### Avvio manuale

Da PowerShell, nella directory del progetto:

```powershell
.\scripts\speace_life_support.ps1 -RestartNow
```

Il parametro `-RestartNow` termina eventuali istanze precedenti e riavvia tutto.

### Interfacce disponibili

- **Chat Anemos**: http://127.0.0.1:8788
- **Monitor SPEACE** (se avviato con `--dashboards` o con `speace monitor`):
  http://127.0.0.1:8787

### Log

```text
data/logs/life_support/
  supervisor.log          -> log del supervisore
  speace_live.out.log     -> stdout di SPEACE live
  speace_live.err.log     -> stderr di SPEACE live
  speace_anemos.out.log   -> stdout di Anemos
  speace_anemos.err.log   -> stderr di Anemos
```

### Arresto

Chiudere la finestra del supervisore o uccidere il processo PowerShell. Lo
script ferma in modo ordinato i processi figli.

## Avvio automatico (opzionale)

Per far partire SPEACE all accensione di Windows, creare un Task Scheduler che
esegua:

```powershell
powershell -ExecutionPolicy Bypass -File C:\cellular_speace\scripts\speace_life_support.ps1
```

## Verifica di salute

Controllare che i processi siano attivi:

```powershell
Get-NetTCPConnection -LocalPort 8787,8788
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
    Where-Object { $_.CommandLine -match 'speace_core\.cli\s+live|speace_anemos\.py' }
```

Controllare che i file di stato si aggiornino, ad esempio:

```powershell
Get-ChildItem data\experience\narrative_timeline.jsonl |
    Select-Object LastWriteTime, @{N="SizeMB";E={$_.Length/1MB}}
```
