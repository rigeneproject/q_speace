<#
.SYNOPSIS
    Motore di Diagnostica per Manutenzione Correttiva di SPEACE
.DESCRIPTION
    Analizza log, processi, snapshot e stato del sistema per diagnosticare
    guasti, errori, bug e anomalie. Identifica la causa radice e
    raccomanda azioni correttive.
.PARAMETER AutoRepair
    Se specificato, tenta la riparazione automatica delle anomalie rilevate.
.PARAMETER Focus
    Area di focus della diagnostica: all, runtime, memoria, file, processi
.PARAMETER MaxErrors
    Numero massimo di errori da analizzare (default: 100)
#>

param(
    [switch]$AutoRepair,
    [ValidateSet("all", "runtime", "memoria", "file", "processi", "log")]
    [string]$Focus = "all",
    [int]$MaxErrors = 100
)

$ScriptRoot = Split-Path -Parent $PSCommandPath
$ModuleRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSCommandPath))
$ProjectRoot = Split-Path -Parent $ModuleRoot
$LogDir = Join-Path -Path $ProjectRoot -ChildPath "data\logs\manutenzione\correttiva"
$ReportDir = Join-Path -Path $ProjectRoot -ChildPath "reports\manutenzione\correttiva"
$DiagnosiDir = Join-Path -Path $ProjectRoot -ChildPath "data\diagnosi"

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null
New-Item -ItemType Directory -Path $DiagnosiDir -Force | Out-Null

$LogFile = Join-Path -Path $LogDir -ChildPath "diagnostica_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$ReportFile = Join-Path -Path $ReportDir -ChildPath "diagnosi_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
$DiagnosiFile = Join-Path -Path $DiagnosiDir -ChildPath "diagnosi_$(Get-Date -Format 'yyyyMMdd_HHmmss').md"

$diagnosi = @{
    Timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff")
    Focus = $Focus
    AutoRepair = $AutoRepair.IsPresent
    Anomalie = @()
    Diagnosi = @()
    Raccomandazioni = @()
    AzioniCorrettive = @()
    Esito = "OK"
}

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss.fff') [$Level] $Message" | Out-File -FilePath $LogFile -Encoding utf8 -Append
    $color = switch ($Level) {
        "ERROR"   { "Red" }
        "WARN"    { "Yellow" }
        "OK"      { "Green" }
        "DIAG"    { "Cyan" }
        "FIX"     { "Magenta" }
        default   { "Gray" }
    }
    Write-Host "$(Get-Date -Format 'HH:mm:ss') [$Level] $Message" -ForegroundColor $color
}

function Add-Anomalia {
    param([string]$Area, [string]$Tipo, [string]$Gravita, [string]$Descrizione, [string]$CausaProbabile = "", [string]$Raccomandazione = "", [PSCustomObject]$Dettagli = $null)
    $a = @{
        Timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff")
        Area = $Area
        Tipo = $Tipo
        Gravita = $Gravita
        Descrizione = $Descrizione
        CausaProbabile = $CausaProbabile
        Raccomandazione = $Raccomandazione
        Dettagli = $Dettagli
    }
    $diagnosi.Anomalie += $a
    $color = switch ($Gravita) {
        "critico" { "Red" }
        "alto" { "Yellow" }
        "medio" { "DarkYellow" }
        "basso" { "Gray" }
        default { "Gray" }
    }
    Write-Log "[$Gravita] $Area/$($Tipo): $Descrizione" -Level $(if ($Gravita -in @("critico","alto")) { "ERROR" } else { "WARN" })
    return $a
}

# === DIAGNOSTICA RUNTIME ===
function Diagnostica-Runtime {
    Write-Log "Diagnostica runtime..." -Level "DIAG"
    $snapshotPath = Join-Path -Path $ProjectRoot -ChildPath "data\runtime\latest_snapshot.json"
    if (-not (Test-Path $snapshotPath)) {
        Add-Anomalia -Area "Runtime" -Tipo "snapshot_mancante" -Gravita "critico" -Descrizione "Snapshot runtime non trovato" -Raccomandazione "Avviare SPEACE o ripristinare da checkpoint"
        return
    }
    try {
        $snapItem = Get-Item $snapshotPath -ErrorAction Stop
        $snapAge = [math]::Round(((Get-Date) - $snapItem.LastWriteTime).TotalMinutes, 1)
        if ($snapAge -gt 30) {
            Add-Anomalia -Area "Runtime" -Tipo "snapshot_vecchio" -Gravita "alto" -Descrizione "Snapshot ha ${snapAge}min (>30min)" -CausaProbabile "Runtime bloccato o arrestato" -Raccomandazione "Verificare processo SPEACE, riavviare se necessario"
        }

        # Tenta lettura health con gestione errori
        try {
            $snap = Get-Content $snapshotPath -Raw -ErrorAction Stop | ConvertFrom-Json
            if ($snap.health -ne $null -and $snap.health -lt 0.5) {
                Add-Anomalia -Area "Runtime" -Tipo "salute_bassa" -Gravita "critico" -Descrizione "Salute organismo: $($snap.health)" -CausaProbabile "Degradazione sistema" -Raccomandazione "Eseguire recupero da checkpoint o riavvio controllato"
            }
        } catch {
            Add-Anomalia -Area "Runtime" -Tipo "errore_lettura_snapshot" -Gravita "medio" -Descrizione "Errore lettura snapshot: $_" -Raccomandazione "Verificare integrita file snapshot"
        }
    } catch {
        Add-Anomalia -Area "Runtime" -Tipo "errore_lettura_snapshot" -Gravita "medio" -Descrizione "Errore lettura snapshot: $_" -Raccomandazione "Verificare integrita file snapshot"
    }
}

# === DIAGNOSTICA MEMORIA ===
function Diagnostica-Memoria {
    Write-Log "Diagnostica memoria..." -Level "DIAG"
    try {
        $processi = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -match "speace|continuous_organism" }
        foreach ($p in $processi) {
            $memMB = [math]::Round($p.WorkingSetSize / 1MB, 1)
            if ($memMB -gt 2000) {
                Add-Anomalia -Area "Memoria" -Tipo "consumo_elevato" -Gravita $(if ($memMB -gt 4000) { "critico" } else { "alto" }) -Descrizione "PID $($p.ProcessId): ${memMB}MB RAM" -CausaProbabile "Memory leak o accumulo dati" -Raccomandazione "Verificare memory_leak_auditor, considerare riavvio"

                $memLogPath = Join-Path -Path $ProjectRoot -ChildPath "data\runtime\memory_history.jsonl"
                if (Test-Path $memLogPath) {
                    $memHistory = Get-Content $memLogPath -Tail 20 -ErrorAction SilentlyContinue | ForEach-Object { $_ | ConvertFrom-Json -ErrorAction SilentlyContinue }
                    if ($memHistory.Count -gt 5) {
                        $growth = ($memHistory[-1].rss_mb - $memHistory[0].rss_mb)
                        if ($growth -gt 500) {
                            Add-Anomalia -Area "Memoria" -Tipo "crescita_memoria" -Gravita "alto" -Descrizione "Crescita +${growth}MB in $($memHistory.Count) campioni" -CausaProbabile "Memory leak confermato" -Raccomandazione "Riavvio necessario, analizzare history per pattern"
                        }
                    }
                }
            }
        }
        $totalPythonMem = [math]::Round((@(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq "python.exe" }) | Measure-Object -Property WorkingSetSize -Sum).Sum / 1MB, 1)
        if ($totalPythonMem -gt 8192) {
            Add-Anomalia -Area "Memoria" -Tipo "memoria_totale_elevata" -Gravita "critico" -Descrizione "${totalPythonMem}MB totale processi Python" -Raccomandazione "Arrestare processi non necessari, riavviare SPEACE"
        }
    } catch {
        Write-Log "Errore diagnostica memoria: $_" -Level "WARN"
    }
}

# === DIAGNOSTICA FILE ===
function Diagnostica-File {
    Write-Log "Diagnostica file..." -Level "DIAG"
    try {
        $logDir = Join-Path -Path $ProjectRoot -ChildPath "data\logs"
        if (Test-Path $logDir) {
            $allLogs = Get-ChildItem -LiteralPath $logDir -Recurse -Filter "*.log" -ErrorAction SilentlyContinue
            $hugeLogs = $allLogs | Where-Object { $_.Length -gt 100MB }
            foreach ($log in $hugeLogs) {
                Add-Anomalia -Area "File" -Tipo "log_enorme" -Gravita "medio" -Descrizione "$($log.Name): $([math]::Round($log.Length/1MB,1))MB" -Raccomandazione "Archiviare o pulire file di log"
            }
            $corruptedLogs = $allLogs | Where-Object { $_.Length -eq 0 -and $_.LastWriteTime -gt (Get-Date).AddHours(-1) }
            foreach ($log in $corruptedLogs) {
                Add-Anomalia -Area "File" -Tipo "log_vuoto" -Gravita "basso" -Descrizione "$($log.Name): file vuoto nonostante scrittura recente" -Raccomandazione "Verificare permessi scrittura"
            }
        }
        $dataDir = Join-Path -Path $ProjectRoot -ChildPath "data"
        if (Test-Path $dataDir) {
            $jsonFiles = Get-ChildItem -LiteralPath $dataDir -Recurse -Filter "*.json" -ErrorAction SilentlyContinue
            $invalidJson = @()
            foreach ($f in $jsonFiles | Select-Object -First 200) {
                try {
                    $content = Get-Content $f.FullName -Raw -ErrorAction Stop
                    if ($content.Length -gt 0) {
                        $null = $content | ConvertFrom-Json -ErrorAction Stop
                    }
                } catch {
                    if ($f.Length -gt 100) {
                        $invalidJson += $f.FullName
                    }
                }
            }
            if ($invalidJson.Count -gt 0) {
                Add-Anomalia -Area "File" -Tipo "json_invalido" -Gravita "medio" -Descrizione "$($invalidJson.Count) file JSON non validi" -CausaProbabile "Scrittura interrotta o corruzione dati" -Raccomandazione "Ripristinare file da backup o checkpoint"
            }
        }
    } catch {
        Write-Log "Errore diagnostica file: $_" -Level "WARN"
    }
}

# === DIAGNOSTICA PROCESSI ===
function Diagnostica-Processi {
    Write-Log "Diagnostica processi..." -Level "DIAG"
    try {
        $pythonProcs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq "python.exe" }
        $speaceProcs = $pythonProcs | Where-Object { $_.CommandLine -match "speace|continuous_organism|evolution" }

        if ($speaceProcs.Count -eq 0) {
            Add-Anomalia -Area "Processi" -Tipo "nessun_processo" -Gravita "critico" -Descrizione "Nessun processo SPEACE in esecuzione" -Raccomandazione "Avviare SPEACE tramite avvio_cloud.bat o avvio_locale.bat"
        } elseif ($speaceProcs.Count -gt 5) {
            Add-Anomalia -Area "Processi" -Tipo "troppi_processi" -Gravita "medio" -Descrizione "$($speaceProcs.Count) processi SPEACE attivi (attesi 1-3)" -CausaProbabile "Processi orfani o zombie" -Raccomandazione "Eseguire cleanup_zombie_speace.ps1"
        }

        $zombieProcs = $pythonProcs | Where-Object {
            try { $_.CreationDate -and ([System.Management.ManagementDateTimeconverter]::ToDateTime($_.CreationDate)) -lt (Get-Date).AddHours(-12) } catch { $false }
        }
        if ($zombieProcs.Count -gt 0) {
            Add-Anomalia -Area "Processi" -Tipo "zombie" -Gravita "alto" -Descrizione "$($zombieProcs.Count) processi non rispondenti da +12h" -Raccomandazione "Terminare processi zombie: $($zombieProcs.ProcessId -join ',')"
        }

        $oldPythons = $pythonProcs | Where-Object {
            try { $_.CreationDate -and ([System.Management.ManagementDateTimeconverter]::ToDateTime($_.CreationDate)) -lt (Get-Date).AddDays(-7) } catch { $false }
        }
        if ($oldPythons.Count -gt 0) {
            Add-Anomalia -Area "Processi" -Tipo "processi_vecchi" -Gravita "basso" -Descrizione "$($oldPythons.Count) processi Python attivi da +7 giorni" -Raccomandazione "Verificare se sono ancora necessari"
        }
    } catch {
        Write-Log "Errore diagnostica processi: $_" -Level "WARN"
    }
}

# === DIAGNOSTICA LOG ===
function Diagnostica-Log {
    Write-Log "Diagnostica log errori..." -Level "DIAG"
    try {
        $logDirs = @(
            "$ProjectRoot\data\logs"
            "$ProjectRoot\data\monitoring"
            "$ProjectRoot\data\agi_team"
        )
        $erroriGravi = @()
        $errorCount = 0
        foreach ($dir in $logDirs) {
            if (-not (Test-Path $dir)) { continue }
            $recentFiles = Get-ChildItem -LiteralPath $dir -Recurse -Filter "*.log" -ErrorAction SilentlyContinue |
                Where-Object { $_.LastWriteTime -gt (Get-Date).AddHours(-2) }
            foreach ($file in $recentFiles) {
                $lines = Get-Content -LiteralPath $file.FullName -Tail 1000 -ErrorAction SilentlyContinue
                foreach ($line in $lines) {
                    if ($line -match "ERROR|FATAL|CRITICAL|Traceback \(most recent call last\)|Exception:") {
                        $errorCount++
                        if ($errorCount -le $MaxErrors) {
                            $erroriGravi += "  [$($file.Name)] $line"
                        }
                    }
                }
            }
        }
        if ($errorCount -gt 0) {
            $gravita = if ($errorCount -gt 50) { "critico" } elseif ($errorCount -gt 10) { "alto" } else { "medio" }
            Add-Anomalia -Area "Log" -Tipo "errori_recenti" -Gravita $gravita -Descrizione "$errorCount errori nelle ultime 2 ore" -Raccomandazione "Analizzare log per pattern ricorrenti" -Dettagli @{Errori = $erroriGravi | Select-Object -First 20}
        } else {
            Write-Log "Nessun errore nei log recenti" -Level "OK"
        }
    } catch {
        Write-Log "Errore diagnostica log: $_" -Level "WARN"
    }
}

# === GENERAZIONE RACCOMANDAZIONI ===
function Genera-Raccomandazioni {
    Write-Log "Generazione raccomandazioni..." -Level "DIAG"
    $anomalieCritiche = $diagnosi.Anomalie | Where-Object { $_.Gravita -in @("critico", "alto") }
    if ($anomalieCritiche.Count -eq 0) {
        $diagnosi.Raccomandazioni += "Nessuna anomalia critica. Sistema apparentemente sano."
        return
    }
    foreach ($a in $anomalieCritiche) {
        if ($a.Raccomandazione) {
            $diagnosi.Raccomandazioni += "[$($a.Gravita.ToUpper())] $($a.Area): $($a.Raccomandazione)"
        }
    }
    $areeCritiche = ($anomalieCritiche | Group-Object Area).Name
    foreach ($area in $areeCritiche) {
        $count = ($anomalieCritiche | Where-Object { $_.Area -eq $area }).Count
        $diagnosi.Raccomandazioni += "Area '$area' ha $count anomalie critiche. Prioritizzare intervento."
    }
}

# === AZIONI CORRETTIVE ===
function Invoke-AzioniCorrettive {
    param([array]$Anomalie)
    Write-Log "Avvio azioni correttive automatiche..." -Level "FIX"
    $azioni = @()
    foreach ($a in $Anomalie) {
        if ($a.Gravita -notin @("critico", "alto")) { continue }
        switch ($a.Tipo) {
            "nessun_processo" {
                Write-Log "Tentativo avvio SPEACE..." -Level "FIX"
                $batPath = Join-Path -Path $ModuleRoot -ChildPath "avvio_locale.bat"
                if (Test-Path $batPath) {
                    Start-Process -FilePath $batPath -WorkingDirectory $ModuleRoot -WindowStyle Minimized
                    $azioni += "Avviato SPEACE: $batPath"
                }
            }
            "zombie" {
                Write-Log "Terminazione processi zombie..." -Level "FIX"
                $zombiePids = $a.Dettagli -replace '.*: ' -split ','
                foreach ($pid in $zombiePids) {
                    try {
                        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                        $azioni += "Terminato PID $pid"
                    } catch {
                        Write-Log ("Impossibile terminare PID $($pid): $_") -Level "WARN"
                    }
                }
            }
            "troppi_processi" {
                Write-Log "Cleanup processi orfani..." -Level "FIX"
                $cleanupScript = Join-Path -Path $ProjectRoot -ChildPath "scripts\cleanup_zombie_speace.ps1"
                if (Test-Path $cleanupScript) {
                    & $cleanupScript
                    $azioni += "Eseguito cleanup zombie"
                }
            }
            "log_enorme" {
                Write-Log "Pulizia log enormi..." -Level "FIX"
                $logDir = Join-Path -Path $ProjectRoot -ChildPath "data\logs"
                $hugeLogs = Get-ChildItem -LiteralPath $logDir -Recurse -Filter "*.log" -ErrorAction SilentlyContinue | Where-Object { $_.Length -gt 100MB }
                foreach ($log in $hugeLogs) {
                    $archiveName = "$($log.FullName).$(Get-Date -Format 'yyyyMMdd').old"
                    Rename-Item -LiteralPath $log.FullName -NewName $archiveName -ErrorAction SilentlyContinue
                    $azioni += "Archiviato: $($log.Name) -> $archiveName"
                }
            }
        }
    }
    if ($azioni.Count -eq 0) {
        Write-Log "Nessuna azione correttiva automatica disponibile" -Level "INFO"
    } else {
        $diagnosi.AzioniCorrettive = $azioni
        foreach ($a in $azioni) {
            Write-Log "AZIONE: $a" -Level "FIX"
        }
    }
}

# === MAIN ===
try {
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "DIAGNOSTICA - MANUTENZIONE CORRETTIVA SPEACE" -ForegroundColor Cyan
    Write-Host "Focus: $Focus | AutoRepair: $($AutoRepair.IsPresent)" -ForegroundColor Cyan
    Write-Host "Log: $LogFile" -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""

    if ($Focus -in @("all", "runtime")) { Diagnostica-Runtime }
    if ($Focus -in @("all", "memoria")) { Diagnostica-Memoria }
    if ($Focus -in @("all", "file")) { Diagnostica-File }
    if ($Focus -in @("all", "processi")) { Diagnostica-Processi }
    if ($Focus -in @("all", "log")) { Diagnostica-Log }

    Genera-Raccomandazioni

    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "RIEPILOGO DIAGNOSI" -ForegroundColor Cyan
    Write-Host "Anomalie trovate: $($diagnosi.Anomalie.Count)" -ForegroundColor $(if ($diagnosi.Anomalie.Count -eq 0) { "Green" } else { "Yellow" })
    $countCrit = @($diagnosi.Anomalie | Where-Object { $_.Gravita -eq "critico" }).Count
    $countAlto = @($diagnosi.Anomalie | Where-Object { $_.Gravita -eq "alto" }).Count
    $countMedio = @($diagnosi.Anomalie | Where-Object { $_.Gravita -eq "medio" }).Count
    $countBasso = @($diagnosi.Anomalie | Where-Object { $_.Gravita -eq "basso" }).Count
    Write-Host "  Critiche: $countCrit" -ForegroundColor Red
    Write-Host "  Alte: $countAlto" -ForegroundColor Yellow
    Write-Host "  Medie: $countMedio" -ForegroundColor DarkYellow
    Write-Host "  Basse: $countBasso" -ForegroundColor Gray
    Write-Host "================================================================" -ForegroundColor Cyan

    if ($AutoRepair -and $diagnosi.Anomalie.Count -gt 0) {
        Write-Host ""
        Write-Host "--- AZIONI CORRETTIVE AUTOMATICHE ---" -ForegroundColor Magenta
        Invoke-AzioniCorrettive -Anomalie $diagnosi.Anomalie
    }

    $diagnosi.Esito = if ($countCrit -gt 0) { "CRITICO" } elseif ($countAlto -gt 0) { "ATTENZIONE" } elseif ($countMedio -gt 0) { "MEDIO" } else { "OK" }
    try {
        $diagnosi | ConvertTo-Json -Depth 4 -ErrorAction Stop | Out-File -FilePath $ReportFile -Encoding utf8 -ErrorAction Stop
        Write-Log "Report diagnostica salvato: $ReportFile" -Level "OK"
    } catch {
        Write-Log "Impossibile salvare report JSON: $_" -Level "ERROR"
        $fallback = Join-Path -Path $ReportDir -ChildPath "diagnosi_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
        "Diagnosi non serializzabile.`n$($diagnosi | Out-String)" | Out-File -FilePath $fallback -Encoding utf8
    }

    $md = @"
# Diagnostica Correttiva SPEACE

**Data:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
**Focus:** $Focus
**AutoRepair:** $($AutoRepair.IsPresent)

## Riepilogo
- Anomalie totali: $($diagnosi.Anomalie.Count)
- Critiche: $countCrit | Alte: $countAlto | Medie: $countMedio | Basse: $countBasso
- Esito: **$($diagnosi.Esito)**

## Anomalie

"@
    foreach ($a in $diagnosi.Anomalie) {
        $gravitaIcon = switch ($a.Gravita) { "critico" { "[CRITICO]" } "alto" { "[ALTO]" } "medio" { "[MEDIO]" } "basso" { "[BASSO]" } }
        $md += "### $gravitaIcon [$($a.Gravita.ToUpper())] $($a.Area) / $($a.Tipo)`n`n"
        $md += "- **Descrizione:** $($a.Descrizione)`n"
        if ($a.CausaProbabile) { $md += "- **Causa probabile:** $($a.CausaProbabile)`n" }
        if ($a.Raccomandazione) { $md += "- **Raccomandazione:** $($a.Raccomandazione)`n" }
        $md += "`n"
    }
    if ($diagnosi.AzioniCorrettive.Count -gt 0) {
        $md += "## Azioni Correttive Eseguite`n`n"
        foreach ($a in $diagnosi.AzioniCorrettive) {
            $md += "- [OK] $a`n"
        }
        $md += "`n"
    }
    if ($diagnosi.Raccomandazioni.Count -gt 0) {
        $md += "## Raccomandazioni`n`n"
        foreach ($r in $diagnosi.Raccomandazioni) {
            $md += "- $r`n"
        }
        $md += "`n"
    }
    $md += @"

---
*Report generato dall'Ispettore Manutentore Neurologico Organismico di SPEACE - Modulo Diagnostica Correttiva*
"@
    $md | Out-File -FilePath $DiagnosiFile -Encoding utf8
    Write-Log "Diagnosi Markdown salvata: $DiagnosiFile" -Level "OK"

} catch {
    Write-Log "ERRORE FATALE: $_" -Level "ERROR"
    Write-Host "[FATALE] $_" -ForegroundColor Red
    exit 1
}
