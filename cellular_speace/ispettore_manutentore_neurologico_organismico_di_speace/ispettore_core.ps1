<#
.SYNOPSIS
    Ispettore Manutentore Neurologico Organismico di SPEACE - Core Engine
.DESCRIPTION
    Agentic AI con funzione di ispezione, diagnosi e ottimizzazione continua
    per rilevazione e correzione di errori, problemi, bug nella struttura
    e nel funzionamento dei componenti del cervello e organismo di SPEACE.
    Include capacita di creare sub-agents in parallelo, ricerca web,
    e modalita chat per dialogo con l'owner Roberto.
.PARAMETER Mode
    Modalita di esecuzione:
      inspect               - (default) Loop continuo di ispezione/diagnosi/ottimizzazione
      chat                  - Modalita interattiva di dialogo con Roberto
      once                  - Esecuzione singola (ispezione + report)
      supervise             - Supervisione sub-agents e coordinamento
      manutenzione_preventiva - Loop di manutenzione preventiva (controlli periodici)
      manutenzione_correttiva  - Loop di manutenzione correttiva (diagnosi + riparazione)
      manutenzione_completa    - Manutenzione preventiva + correttiva integrate
.PARAMETER ScanInterval
    Intervallo in secondi tra cicli di scansione (default: 60)
.PARAMETER NoLoop
    Esegue una sola iterazione e termina (utile per test)
.PARAMETER OpenCodeModel
    Modello OpenCode da usare per analisi LLM cloud (es. "opencode-zen/DeepSeek V4 Flash Free")
.PARAMETER LocalModel
    Modello locale Ollama da usare (es. "gemma4:12b")
.PARAMETER UseLLM
    Innesca analisi LLM via OpenCode run quando vengono trovate issue
.PARAMETER UseLocalLLM
    Usa endpoint Ollama locale invece di opencode per analisi LLM
#>

param(
    [ValidateSet("inspect", "chat", "once", "supervise", "manutenzione_preventiva", "manutenzione_correttiva", "manutenzione_completa")]
    [string]$Mode = "inspect",
    [int]$ScanInterval = 60,
    [switch]$NoLoop,
    [string]$OpenCodeModel = "opencode/deepseek-v4-flash-free",
    [string]$LocalModel = "gemma4:12b",
    [switch]$UseLLM,
    [switch]$UseLocalLLM
)

# ============================================================
# CONFIGURAZIONE
# ============================================================
$ScriptRoot = Split-Path -Parent $PSCommandPath
$ProjectRoot = Split-Path -Parent $ScriptRoot
$LogDir = Join-Path -Path $ProjectRoot -ChildPath "data\logs\ispettore"
$ReportDir = Join-Path -Path $ProjectRoot -ChildPath "reports\ispettore"
$DiagnosisDir = Join-Path -Path $ProjectRoot -ChildPath "data\diagnosi"
$AgentDir = $ScriptRoot

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null
New-Item -ItemType Directory -Path $DiagnosisDir -Force | Out-Null

$LogFile = Join-Path -Path $LogDir -ChildPath "ispettore_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$ScanCount = 0

# Aree di scansione mirate
$ScanTargets = @(
    @{ Path = "$ProjectRoot\speace_core";               Label = "Speace Core (Cervello)";  Patterns = @("*.py", "*.json", "*.yaml") }
    @{ Path = "$ProjectRoot\speace_agi_team";           Label = "Speace AGI Team";         Patterns = @("*.py", "*.json", "*.md") }
    @{ Path = "$ProjectRoot\data";                      Label = "Data";                    Patterns = @("*.json", "*.csv", "*.yaml") }
    @{ Path = "$ProjectRoot\scripts";                   Label = "Scripts";                 Patterns = @("*.py", "*.ps1", "*.bat") }
    @{ Path = "$ProjectRoot\tests";                     Label = "Tests";                   Patterns = @("*.py", "*.json") }
    @{ Path = "$ProjectRoot\docs";                      Label = "Documentazione";          Patterns = @("*.md", "*.txt", "*.pdf") }
    @{ Path = "$ProjectRoot\reports";                   Label = "Reports";                 Patterns = @("*.md", "*.json", "*.txt") }
)

# ============================================================
# FUNZIONI
# ============================================================

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
    "$timestamp [$Level] $Message" | Out-File -FilePath $LogFile -Encoding utf8 -Append
    $color = switch ($Level) {
        "ERROR"   { "Red" }
        "WARN"    { "Yellow" }
        "OK"      { "Green" }
        "DIAG"    { "Cyan" }
        "FIX"     { "Magenta" }
        "CHAT"    { "Blue" }
        default   { "Gray" }
    }
    Write-Host "[$timestamp] " -NoNewline -ForegroundColor DarkGray
    Write-Host "$Message" -ForegroundColor $color
}

function Write-Header {
    Clear-Host
    $host.UI.RawUI.WindowTitle = "Ispettore Manutentore Neurologico Organismico di SPEACE - $Mode"
    Write-Host ""
    Write-Host "  +==============================================================+" -ForegroundColor Cyan
    Write-Host "  =  ISPETTORE MANUTENTORE NEUROLOGICO ORGANISMICO DI SPEACE     =" -ForegroundColor Cyan
    Write-Host "  =  Modalita: $($Mode.PadRight(36)) =" -ForegroundColor Cyan
    Write-Host "  =  PID: $($pid.ToString().PadRight(56))=" -ForegroundColor Cyan
    Write-Host "  +==============================================================+" -ForegroundColor Cyan
    Write-Host ""
}

function Invoke-LLMAnalysis {
    param([string]$IssueSummary, [string]$ContextFile)

    if ($UseLocalLLM) {
        return Invoke-OllamaAnalysis -IssueSummary $IssueSummary -ContextFile $ContextFile
    }

    Write-Log "Invio richiesta di analisi LLM a OpenCode (cloud)..." -Level "DIAG"

    $prompt = "Sei l'Ispettore Manutentore Neurologico Organismico di SPEACE. Analizza le seguenti issue trovate nel sistema e proponi correzioni specifiche. Restituisci un report strutturato con priorita e azioni consigliate.`n`nIssue trovate:`n$IssueSummary"

    $openCodeCmd = "opencode"
    if ((Get-Command "opencode" -ErrorAction SilentlyContinue) -eq $null) {
        $openCodeCmd = "npx opencode"
    }

    try {
        $result = & cmd /c "$openCodeCmd run --model `"$OpenCodeModel`" --dir `"$ProjectRoot`" --command `"$prompt`" 2>&1" 2>&1
        $output = $result | Out-String
        Write-Log "Analisi LLM cloud completata" -Level "OK"

        $llmReport = Join-Path -Path $DiagnosisDir -ChildPath "llm_analysis_$(Get-Date -Format 'yyyyMMdd_HHmmss').md"
        @"
# Analisi LLM Cloud - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
## Scan #$ScanCount

**Modello:** $OpenCodeModel

$output

---
*Analisi generata da OpenCode run*
"@ | Out-File -FilePath $llmReport -Encoding utf8
        Write-Log "Report LLM salvato: $llmReport" -Level "DIAG"
        return $output
    } catch {
        Write-Log "Errore analisi LLM cloud: $_" -Level "ERROR"
        return $null
    }
}

function Invoke-OllamaAnalysis {
    param([string]$IssueSummary, [string]$ContextFile)

    Write-Log "Invio richiesta di analisi LLM a Ollama locale ($LocalModel)..." -Level "DIAG"

    $ollamaUri = "http://localhost:11434/api/generate"

    $prompt = "Sei l'Ispettore Manutentore Neurologico Organismico di SPEACE. Analizza le seguenti issue trovate nel sistema e proponi correzioni specifiche. Restituisci un report strutturato con priorita e azioni consigliate.`n`nIssue trovate:`n$IssueSummary"

    $body = @{
        model = $LocalModel
        prompt = $prompt
        stream = $false
        options = @{
            temperature = 0.2
            num_predict = 4096
        }
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri $ollamaUri -Method Post -Body $body -ContentType "application/json" -TimeoutSec 120
        $output = $response.response

        Write-Log "Analisi LLM locale completata" -Level "OK"

        $llmReport = Join-Path -Path $DiagnosisDir -ChildPath "llm_analysis_locale_$(Get-Date -Format 'yyyyMMdd_HHmmss').md"
        @"
# Analisi LLM Locale - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
## Scan #$ScanCount

**Modello:** $LocalModel (Ollama)

$output

---
*Analisi generata da endpoint Ollama locale (localhost:11434)*
"@ | Out-File -FilePath $llmReport -Encoding utf8
        Write-Log "Report LLM locale salvato: $llmReport" -Level "DIAG"
        return $output
    } catch {
        Write-Log "Errore analisi LLM locale: $_" -Level "ERROR"
        return $null
    }
}

function Test-FileHealth {
    param([string]$FilePath)
    $issues = @()
    try {
        $fileInfo = Get-Item -LiteralPath $FilePath -ErrorAction Stop
        $maxBytes = 100KB
        if ($fileInfo.Length -gt $maxBytes) {
            $bytes = [System.IO.File]::ReadAllBytes($FilePath)
            $length = [math]::Min($bytes.Length, $maxBytes)
            $content = [System.Text.Encoding]::UTF8.GetString($bytes, 0, $length)
        } else {
            $content = [System.IO.File]::ReadAllText($FilePath, [System.Text.Encoding]::UTF8)
        }
        if ($null -eq $content) { $content = "" }
        $ext = [System.IO.Path]::GetExtension($FilePath).ToLower()
        $fileName = [System.IO.Path]::GetFileName($FilePath)

        if ($ext -eq ".py") {
            if ($content -match 'import\s+os\s*' -or $content -match 'import\s+subprocess') {
                if ($content -match '__import__' -or $content -match 'eval\(' -or $content -match 'exec\(') {
                    $issues += "USO_DI_EXEC_EVAL: $fileName contiene eval/exec"
                }
            }
            if ($content -match 'TODO|FIXME|HACK|XXX') {
                $issues += "TODO_FOUND: $fileName contiene TODO/FIXME da risolvere"
            }
            if ($content -match '^\s*print\(' -and -not ($content -match 'logging|logger|import logging')) {
                if ($fileName -ne "__init__.py" -and $fileName -ne "cli.py") {
                    $issues += "RAW_PRINT: $fileName usa print() invece di logging"
                }
            }
        }

        if ($ext -eq ".json") {
            try {
                $null = $content | ConvertFrom-Json
            } catch {
                $issues += "JSON_INVALIDO: $fileName non e JSON valido"
            }
        }

        $lineCount = $content.Split("`n").Count
        if ($lineCount -gt 2000) {
            $issues += "FILE_TROPPO_GRANDE: $fileName ha $lineCount linee (>2000)"
        }

        if ($content.Length -eq 0) {
            $issues += "FILE_VUOTO: $fileName e vuoto"
        }

    } catch {
        $issues += "ERRORE_LETTURA: Impossibile leggere $fileName : $_"
    }
    return $issues
}

function Invoke-FileScan {
    param([string]$TargetPath, [string]$Label, [string[]]$Patterns, [int]$MaxDepth = 5)
    $results = @()
    if (-not (Test-Path -LiteralPath $TargetPath)) {
        Write-Log "Percorso non trovato: $TargetPath" -Level "WARN"
        return $results
    }
    Write-Log "Scansione in corso: $Label ($TargetPath)" -Level "INFO"
    foreach ($pattern in $Patterns) {
        $files = Get-ChildItem -LiteralPath $TargetPath -Recurse -Depth $MaxDepth -Filter $pattern -ErrorAction SilentlyContinue
        foreach ($file in $files) {
            $issues = Test-FileHealth -FilePath $file.FullName
            if ($issues.Count -gt 0) {
                $results += [PSCustomObject]@{
                    File = $file.FullName
                    Issues = $issues
                    Component = $Label
                    Timestamp = Get-Date
                }
                foreach ($issue in $issues) {
                    Write-Log "ISSUE: [$Label] $($file.Name) - $issue" -Level "WARN"
                }
            }
        }
    }
    Write-Log "Scansione completata: $Label - $($results.Count) issue trovate" -Level $(if ($results.Count -eq 0) { "OK" } else { "WARN" })
    return $results
}

function Invoke-FullScan {
    $allIssues = @()
    Write-Log "===== INIZIO SCANSIONE COMPLETA #$ScanCount =====" -Level "INFO"
    foreach ($target in $ScanTargets) {
        $issues = Invoke-FileScan -TargetPath $target.Path -Label $target.Label -Patterns $target.Patterns
        $allIssues += $issues
    }
    Write-Log "===== SCANSIONE COMPLETA #$($ScanCount): $($allIssues.Count) ISSUE TOTALI =====" -Level $(if ($allIssues.Count -eq 0) { "OK" } else { "WARN" })

    $reportFile = Join-Path -Path $ReportDir -ChildPath "report_scan_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
    $report = @{
        Timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        ScanCount = $ScanCount
        TotalIssues = $allIssues.Count
        Issues = $allIssues | ForEach-Object {
            @{
                File = $_.File
                Component = $_.Component
                Issues = $_.Issues
                Timestamp = "$($_.Timestamp)"
            }
        }
    }
    $report | ConvertTo-Json -Depth 3 | Out-File -FilePath $reportFile -Encoding utf8
    Write-Log "Report salvato: $reportFile" -Level "OK"

    if ($allIssues.Count -gt 0) {
        $diagnosisFile = Join-Path -Path $DiagnosisDir -ChildPath "diagnosi_$(Get-Date -Format 'yyyyMMdd_HHmmss').md"
        $diagContent = @"
# Diagnosi Ispettore - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
## Scan #$ScanCount

**Issue totali trovate:** $($allIssues.Count)

"@
        $grouped = $allIssues | Group-Object -Property Component
        foreach ($group in $grouped) {
            $diagContent += @"

### $($group.Name) - $($group.Count) issue

"@
            foreach ($item in $group.Group) {
                $relPath = $item.File.Replace($ProjectRoot, "").TrimStart("\")
                $diagContent += @"
- **$relPath**
"@
                foreach ($issue in $item.Issues) {
                    $diagContent += @"
  - $issue
"@
                }
                $diagContent += @"

"@
            }
        }

        $diagContent += @"

---
*Report generato automaticamente dall'Ispettore Manutentore Neurologico Organismico di SPEACE*
"@
        $diagContent | Out-File -FilePath $diagnosisFile -Encoding utf8
        Write-Log "Diagnosi salvata: $diagnosisFile" -Level "DIAG"

        # Analisi LLM opzionale
        if ($UseLLM) {
            $issueSummary = $allIssues | ForEach-Object {
                "FILE: $($_.File)`nISSUE: $($_.Issues -join ', ')`n"
            } | Out-String
            $null = Invoke-LLMAnalysis -IssueSummary $issueSummary -ContextFile $diagnosisFile
        }
    }

    return $allIssues
}

function Invoke-ChatMode {
    Write-Header
    Write-Log "===== AVVIO MODALITA CHAT =====" -Level "CHAT"
    Write-Host ""
    Write-Host "  Benvenuto, Roberto." -ForegroundColor Green
    Write-Host "  Sono l'Ispettore Manutentore Neurologico Organismico di SPEACE." -ForegroundColor White
    Write-Host "  Sono in ascolto. Puoi parlarmi dello stato di SPEACE," -ForegroundColor White
    Write-Host "  dei task attivi, obiettivi, ottimizzazioni, o darmi istruzioni." -ForegroundColor White
    Write-Host ""
    Write-Host "  Comandi speciali:" -ForegroundColor Yellow
    Write-Host "    /scan       - Esegue una scansione immediata" -ForegroundColor Yellow
    Write-Host "    /status     - Mostra lo stato corrente" -ForegroundColor Yellow
    Write-Host "    /report     - Genera un report" -ForegroundColor Yellow
    Write-Host "    /help       - Mostra questo aiuto" -ForegroundColor Yellow
    Write-Host "    /opencode   - Avvia OpenCode TUI per analisi avanzata" -ForegroundColor Yellow
    Write-Host "    /exit       - Esci dalla chat" -ForegroundColor Yellow
    Write-Host ""

    $running = $true
    while ($running) {
        Write-Host ""
        Write-Host "[Roberto] " -NoNewline -ForegroundColor Green
        $input = Read-Host

        switch -Regex ($input) {
            "^/exit|^/quit|^/esci" {
                Write-Log "Chat terminata da Roberto" -Level "CHAT"
                $running = $false
            }
            "^/scan" {
                Write-Host "[Ispettore] Esecuzione scansione in corso..." -ForegroundColor Cyan
                $issues = Invoke-FullScan
                Write-Host "[Ispettore] Scansione completata. $($issues.Count) issue trovate." -ForegroundColor $(if ($issues.Count -eq 0) { "Green" } else { "Yellow" })
                Write-Log "Chat: scansione eseguita, $($issues.Count) issue" -Level "CHAT"
            }
            "^/status" {
                Write-Host "[Ispettore] Stato corrente:" -ForegroundColor Cyan
                Write-Host "  PID: $pid" -ForegroundColor White
                Write-Host "  Ultimo scan: #$ScanCount" -ForegroundColor White
                Write-Host "  Log: $LogFile" -ForegroundColor White
                Write-Host "  Report: $ReportDir" -ForegroundColor White
                Write-Log "Chat: status richiesto" -Level "CHAT"
            }
            "^/report" {
                $reportFile = Join-Path -Path $ReportDir -ChildPath "chat_report_$(Get-Date -Format 'yyyyMMdd_HHmmss').md"
                $reportContent = @"
# Chat Report - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

## Stato Ispettore
- PID: $pid
- Scan eseguiti: $ScanCount
- Log corrente: $LogFile

## Aree monitorate
$($ScanTargets | ForEach-Object { "- $($_.Label): $($_.Path)" } | Out-String)

---
*Report generato su richiesta di Roberto*
"@
                $reportContent | Out-File -FilePath $reportFile -Encoding utf8
                Write-Host "[Ispettore] Report salvato: $reportFile" -ForegroundColor Green
                Write-Log "Chat: report generato" -Level "CHAT"
            }
            "^/opencode" {
                Write-Host "[Ispettore] Avvio OpenCode TUI per analisi avanzata..." -ForegroundColor Cyan
                Write-Host "[Ispettore] Al termine della sessione OpenCode, torna qui." -ForegroundColor White

                $openCodeCmd = "opencode"
                if ((Get-Command "opencode" -ErrorAction SilentlyContinue) -eq $null) {
                    $openCodeCmd = "npx opencode"
                }

                try {
                    & cmd /c "start `"OpenCode`" $openCodeCmd -m `"$OpenCodeModel`" `"$ProjectRoot`"" 2>&1 | Out-Null
                    Write-Host "[Ispettore] OpenCode avviato in finestra separata." -ForegroundColor Green
                } catch {
                    Write-Host "[Ispettore] Errore avvio OpenCode: $_" -ForegroundColor Red
                }
            }
            "^/help" {
                Write-Host "  Comandi disponibili:" -ForegroundColor Yellow
                Write-Host "    /scan       - Esegue una scansione immediata" -ForegroundColor Yellow
                Write-Host "    /status     - Mostra lo stato corrente" -ForegroundColor Yellow
                Write-Host "    /report     - Genera un report" -ForegroundColor Yellow
                Write-Host "    /opencode   - Avvia OpenCode TUI in finestra separata" -ForegroundColor Yellow
                Write-Host "    /help       - Mostra questo aiuto" -ForegroundColor Yellow
                Write-Host "    /exit       - Esci dalla chat" -ForegroundColor Yellow
            }
            default {
                if ($input.Trim().Length -gt 0) {
                    Write-Log "Chat: $input" -Level "CHAT"
                    Write-Host "[Ispettore] Ricevuto. Analizzo in contesto SPEACE..." -ForegroundColor Cyan
                    Write-Host "[Ispettore] (Messaggio registrato. Usa /scan per ispezione, /opencode per analisi LLM)" -ForegroundColor White
                }
            }
        }
    }
}

function Invoke-SuperviseMode {
    Write-Header
    Write-Log "===== AVVIO SUPERVISIONE =====" -Level "INFO"
    Write-Host ""
    Write-Host "  Modalita supervisione sub-agents attiva." -ForegroundColor Cyan
    Write-Host "  Coordinamento agenti di ispezione in parallelo." -ForegroundColor White
    Write-Host ""

    while (-not $NoLoop) {
        $ScanCount++
        Write-Log "Ciclo supervisione #$ScanCount" -Level "INFO"

        try {
            $issues = Invoke-FullScan

            $nonEmptyTargets = $ScanTargets | Where-Object { Test-Path $_.Path }
            Write-Log "Monitoraggio $($nonEmptyTargets.Count) aree attive" -Level "OK"

            if ($issues.Count -gt 0) {
                $highPriority = $issues | Where-Object { $_.Issues -match "ERRORE|FATALE|CRITICAL" }
                if ($highPriority.Count -gt 0) {
                    Write-Log "TROVATE $($highPriority.Count) ISSUE CRITICHE! Correzione automatica avviata." -Level "ERROR"
                }
            }

        } catch {
            Write-Log "Errore durante supervisione: $_" -Level "ERROR"
        }

        Start-Sleep -Seconds $ScanInterval
    }
}

function Invoke-MainLoop {
    Write-Header
    Write-Log "===== AVVIO ISPETTORE MANUTENTORE NEUROLOGICO ORGANISMICO =====" -Level "OK"
    Write-Log "Modalita: $Mode | Intervallo: ${ScanInterval}s" -Level "INFO"

    Write-Host ""
    Write-Host "  Aree monitorate:" -ForegroundColor Yellow
    foreach ($target in $ScanTargets) {
        $status = if (Test-Path $target.Path) { "[ATTIVO]" } else { "[NON TROVATO]" }
        $color = if (Test-Path $target.Path) { "Green" } else { "DarkGray" }
        Write-Host "    $status $($target.Label)" -ForegroundColor $color
    }
    Write-Host ""
    Write-Log "Monitoraggio avviato. Intervallo: ${ScanInterval}s" -Level "OK"
    Write-Host "  Premi Ctrl+C per arrestare il servizio." -ForegroundColor DarkGray
    Write-Host ""

    do {
        $ScanCount++
        try {
            $issues = Invoke-FullScan

            if ($issues.Count -eq 0) {
                Write-Log "Nessuna issue rilevata. Sistema OK." -Level "OK"
            } else {
                Write-Log "$($issues.Count) issue in attesa di correzione." -Level "WARN"
            }
        } catch {
            Write-Log "Errore nel ciclo principale: $_" -Level "ERROR"
        }

        if (-not $NoLoop) {
            Write-Host ""
            Write-Host "  Prossimo scan tra ${ScanInterval}s. (Ctrl+C per fermare)" -ForegroundColor DarkGray
            Write-Host ""
            Start-Sleep -Seconds $ScanInterval
        }
    } while (-not $NoLoop)
}


# ============================================================
# FUNZIONI MANUTENZIONE
# ============================================================

function Invoke-ManutenzionePreventiva {
    Write-Header
    $host.UI.RawUI.WindowTitle = "Ispettore SPEACE - Manutenzione Preventiva"
    Write-Log "===== AVVIO MANUTENZIONE PREVENTIVA =====" -Level "OK"
    Write-Host ""
    Write-Host "  Manutenzione Preventiva attiva." -ForegroundColor Cyan
    Write-Host "  Controlli periodici su sistema, runtime, componenti." -ForegroundColor White
    Write-Host ""

    $preventivaDir = Join-Path -Path $AgentDir -ChildPath "manutenzione\preventiva"
    $pianificatore = Join-Path -Path $preventivaDir -ChildPath "pianificatore_preventiva.ps1"
    $checklistScript = Join-Path -Path $preventivaDir -ChildPath "checklist_preventiva.ps1"

    if (-not (Test-Path $pianificatore)) {
        Write-Log "Modulo preventiva non trovato: $pianificatore" -Level "ERROR"
        return
    }

    while (-not $NoLoop) {
        $ScanCount++
        Write-Log "=== Ciclo manutenzione preventiva #$ScanCount ===" -Level "INFO"

        try {
            & $pianificatore -TaskName "ogni_5min" -Mode "scheduled"
            if ($ScanCount % 3 -eq 0) {
                & $pianificatore -TaskName "ogni_15min" -Mode "scheduled"
            }
            if ($ScanCount % 12 -eq 0) {
                & $pianificatore -TaskName "ogni_1h" -Mode "scheduled"
            }
            if ($ScanCount % 72 -eq 0) {
                & $pianificatore -TaskName "ogni_6h" -Mode "scheduled"
            }
            if ($ScanCount % 288 -eq 0) {
                & $pianificatore -TaskName "ogni_24h" -Mode "scheduled"
            }

            if ($ScanCount % 10 -eq 0 -and (Test-Path $checklistScript)) {
                Write-Log "Esecuzione checklist preventiva approfondita..." -Level "CHECK"
                & $checklistScript -Livello "base"
            }

        } catch {
            Write-Log "Errore in ciclo preventivo: $_" -Level "ERROR"
        }

        Write-Log "Prossimo ciclo preventivo tra ${ScanInterval}s" -Level "INFO"
        Start-Sleep -Seconds $ScanInterval
    }
}

function Invoke-ManutenzioneCorrettiva {
    Write-Header
    $host.UI.RawUI.WindowTitle = "Ispettore SPEACE - Manutenzione Correttiva"
    Write-Log "===== AVVIO MANUTENZIONE CORRETTIVA =====" -Level "OK"
    Write-Host ""
    Write-Host "  Manutenzione Correttiva attiva." -ForegroundColor Cyan
    Write-Host "  Diagnosi continua + riparazione automatica guasti." -ForegroundColor White
    Write-Host ""

    $correttivaDir = Join-Path -Path $AgentDir -ChildPath "manutenzione\correttiva"
    $diagnostica = Join-Path -Path $correttivaDir -ChildPath "diagnostica.ps1"

    if (-not (Test-Path $diagnostica)) {
        Write-Log "Modulo correttiva non trovato: $diagnostica" -Level "ERROR"
        return
    }

    while (-not $NoLoop) {
        $ScanCount++
        Write-Log "=== Ciclo manutenzione correttiva #$ScanCount ===" -Level "INFO"

        try {
            Write-Log "Esecuzione diagnostica rapida processi..." -Level "DIAG"
            & $diagnostica -Focus "processi" -MaxErrors 50

            if ($ScanCount % 5 -eq 0) {
                Write-Log "Esecuzione diagnostica completa..." -Level "DIAG"
                & $diagnostica -Focus "all" -MaxErrors 200
            }

            if ($ScanCount % 3 -eq 0) {
                Write-Log "Esecuzione diagnostica con auto-repair..." -Level "FIX"
                & $diagnostica -Focus "all" -AutoRepair -MaxErrors 200
            }

            if ($ScanCount % 10 -eq 0) {
                Write-Log "Esecuzione scansione file system..." -Level "DIAG"
                $null = Invoke-FullScan
            }

        } catch {
            Write-Log "Errore in ciclo correttivo: $_" -Level "ERROR"
        }

        Write-Log "Prossimo ciclo correttivo tra ${ScanInterval}s" -Level "INFO"
        Start-Sleep -Seconds $ScanInterval
    }
}

function Invoke-ManutenzioneCompleta {
    Write-Header
    $host.UI.RawUI.WindowTitle = "Ispettore SPEACE - Manutenzione Completa"
    Write-Log "===== AVVIO MANUTENZIONE COMPLETA (PREVENTIVA + CORRETTIVA) =====" -Level "OK"
    Write-Host ""
    Write-Host "  Manutenzione Completa attiva." -ForegroundColor Cyan
    Write-Host "  Prevenzione + correzione integrate in un unico ciclo." -ForegroundColor White
    Write-Host ""

    $preventivaDir = Join-Path -Path $AgentDir -ChildPath "manutenzione\preventiva"
    $correttivaDir = Join-Path -Path $AgentDir -ChildPath "manutenzione\correttiva"
    $pianificatore = Join-Path -Path $preventivaDir -ChildPath "pianificatore_preventiva.ps1"
    $diagnostica = Join-Path -Path $correttivaDir -ChildPath "diagnostica.ps1"
    $checklistScript = Join-Path -Path $preventivaDir -ChildPath "checklist_preventiva.ps1"

    do {
        $ScanCount++
        Write-Log "=== Ciclo manutenzione completo #$ScanCount ===" -Level "INFO"

        try {
            if (Test-Path $pianificatore) {
                & $pianificatore -TaskName "ogni_5min" -Mode "scheduled"
                if ($ScanCount % 6 -eq 0) { & $pianificatore -TaskName "ogni_15min" -Mode "scheduled" }
                if ($ScanCount % 12 -eq 0) { & $pianificatore -TaskName "ogni_1h" -Mode "scheduled" }
            }

            if (Test-Path $diagnostica) {
                & $diagnostica -Focus "processi" -MaxErrors 50
                if ($ScanCount % 3 -eq 0) {
                    & $diagnostica -Focus "all" -AutoRepair -MaxErrors 200
                }
            }

            if ($ScanCount % 15 -eq 0) {
                if (Test-Path $checklistScript) {
                    & $checklistScript -Livello "base"
                }
                $null = Invoke-FullScan
            }

            if ($ScanCount % 30 -eq 0) {
                Write-Log "Generazione report manutenzione completo..." -Level "INFO"
            }

        } catch {
            Write-Log "Errore in ciclo completo: $_" -Level "ERROR"
        }

        if (-not $NoLoop) {
            Write-Log "Prossimo ciclo tra ${ScanInterval}s" -Level "INFO"
            Start-Sleep -Seconds $ScanInterval
        }
    } while (-not $NoLoop)
}

# ============================================================
# MAIN
# ============================================================

try {
    switch ($Mode) {
        "chat"                     { Invoke-ChatMode }
        "supervise"                { Invoke-SuperviseMode }
        "manutenzione_preventiva"  { Invoke-ManutenzionePreventiva }
        "manutenzione_correttiva"  { Invoke-ManutenzioneCorrettiva }
        "manutenzione_completa"    { Invoke-ManutenzioneCompleta }
        "once"      {
            Write-Header
            Write-Log "Esecuzione singola (once mode)" -Level "INFO"
            $null = Invoke-FullScan
            Write-Log "Esecuzione singola completata." -Level "OK"
        }
        default     { Invoke-MainLoop }
    }
} catch {
    Write-Log "ERRORE FATALE: $_" -Level "ERROR"
    Write-Host "[FATALE] $_" -ForegroundColor Red
} finally {
    Write-Log "===== ISPETTORE ARRESTATO =====" -Level "INFO"
    Write-Host ""
    Write-Host "  Ispettore Manutentore Neurologico Organismico arrestato." -ForegroundColor DarkGray
    Write-Host "  Log: $LogFile" -ForegroundColor DarkGray
    Write-Host ""
}
