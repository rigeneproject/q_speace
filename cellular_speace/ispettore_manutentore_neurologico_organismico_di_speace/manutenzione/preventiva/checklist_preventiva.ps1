<#
.SYNOPSIS
    Checklist di Manutenzione Preventiva per SPEACE
.DESCRIPTION
    Esegue una serie di controlli approfonditi sullo stato di SPEACE.
    Puo essere eseguito manualmente o schedulato.
.PARAMETER Livello
    Livello di profondita dei controlli: base, esteso, completo
.PARAMETER OutputDir
    Directory per il report (default: reports/manutenzione/preventiva)
#>

param(
    [ValidateSet("base", "esteso", "completo")]
    [string]$Livello = "completo",
    [string]$OutputDir = ""
)

$ScriptRoot = Split-Path -Parent $PSCommandPath
$ModuleRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSCommandPath))
$ProjectRoot = Split-Path -Parent $ModuleRoot

if (-not $OutputDir) {
    $OutputDir = Join-Path -Path $ProjectRoot -ChildPath "reports\manutenzione\preventiva"
}
$LogDir = Join-Path -Path $ProjectRoot -ChildPath "data\logs\manutenzione\preventiva"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

$LogFile = Join-Path -Path $LogDir -ChildPath "checklist_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$ReportFile = Join-Path -Path $OutputDir -ChildPath "checklist_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
$ReportMdFile = Join-Path -Path $OutputDir -ChildPath "checklist_$(Get-Date -Format 'yyyyMMdd_HHmmss').md"

$checks = @()
$warnings = @()
$errors = @()
$startTime = Get-Date

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss.fff') [$Level] $Message" | Out-File -FilePath $LogFile -Encoding utf8 -Append
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARN"  { "Yellow" }
        "OK"    { "Green" }
        "CHECK" { "Cyan" }
        default { "Gray" }
    }
    Write-Host "$(Get-Date -Format 'HH:mm:ss') [$Level] $Message" -ForegroundColor $color
}

function Add-CheckResult {
    param([string]$Category, [string]$Name, [string]$Status, [string]$Detail = "")
    $check = [PSCustomObject]@{
        Timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff")
        Category = $Category
        Name = $Name
        Status = $Status
        Detail = $Detail
    }
    [void]($script:checks += $check)
    $icon = switch ($Status) {
        "OK"   { "[OK]" }
        "WARN" { "[!]" }
        "FAIL" { "[X]" }
        "INFO" { "[i]" }
        default { "[ ]" }
    }
    Write-Host "  $icon $Category / $Name" -NoNewline
    if ($Status -eq "OK") { Write-Host " - $Detail" -ForegroundColor Green }
    elseif ($Status -eq "WARN") { Write-Host " - $Detail" -ForegroundColor Yellow; [void]($script:warnings += "$Category / $Name - $Detail") }
    elseif ($Status -eq "FAIL") { Write-Host " - $Detail" -ForegroundColor Red; [void]($script:errors += "$Category / $Name - $Detail") }
    else { Write-Host " - $Detail" -ForegroundColor Gray }
    return $check
}

# === CHECKLIST ===

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "CHECKLIST MANUTENZIONE PREVENTIVA SPEACE" -ForegroundColor Cyan
Write-Host "Livello: $Livello" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. CONTROLLI DI SISTEMA
Write-Host "--- SISTEMA ---" -ForegroundColor Magenta
try {
    $os = Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue
    $uptime = if ($os) { [math]::Round(((Get-Date) - $os.LastBootUpTime).TotalHours, 1) } else { "N/A" }
    Add-CheckResult -Category "Sistema" -Name "Uptime" -Status $(if ($uptime -ne "N/A" -and $uptime -lt 720) { "OK" } else { "WARN" }) -Detail "${uptime}h"

    $cpu = Get-CimInstance Win32_Processor -ErrorAction SilentlyContinue
    $cpuLoad = if ($cpu) { $cpu[0].LoadPercentage } else { 0 }
    Add-CheckResult -Category "Sistema" -Name "CPU" -Status $(if ($cpuLoad -lt 85) { "OK" } elseif ($cpuLoad -lt 95) { "WARN" } else { "FAIL" }) -Detail "${cpuLoad}%"

    $ramFree = if ($os) { [math]::Round($os.FreePhysicalMemory / 1MB, 1) } else { 0 }
    $ramTotal = if ($os) { [math]::Round($os.TotalVisibleMemorySize / 1MB, 1) } else { 0 }
    $ramPct = if ($ramTotal -gt 0) { [math]::Round((1 - $ramFree/$ramTotal)*100, 1) } else { 0 }
    Add-CheckResult -Category "Sistema" -Name "RAM" -Status $(if ($ramPct -lt 90) { "OK" } else { "WARN" }) -Detail "${ramPct}% used (${ramFree}GB free / ${ramTotal}GB)"

    $disks = Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" -ErrorAction SilentlyContinue
    foreach ($disk in $disks) {
        $pct = [math]::Round((($disk.Size - $disk.FreeSpace) / $disk.Size) * 100, 1)
        $label = if ($disk.DeviceID -eq $ProjectRoot[0] + ":") { "Disco sistema" } else { "Disco $($disk.DeviceID)" }
        Add-CheckResult -Category "Sistema" -Name $label -Status $(if ($pct -lt 90) { "OK" } elseif ($pct -lt 95) { "WARN" } else { "FAIL" }) -Detail "${pct}% used ($([math]::Round($disk.FreeSpace/1GB,1))GB free)"
    }
} catch {
    Add-CheckResult -Category "Sistema" -Name "HealthCheck" -Status "FAIL" -Detail $_.Exception.Message
}

# 2. CONTROLLI PROCESSI SPEACE
Write-Host "--- PROCESSI SPEACE ---" -ForegroundColor Magenta
try {
    $pythonProcs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -eq "python.exe" }
    $speaceProcs = $pythonProcs | Where-Object { $_.CommandLine -match "speace|continuous_organism" }
    if ($speaceProcs) {
        foreach ($p in $speaceProcs) {
            $memMB = [math]::Round($p.WorkingSetSize / 1MB, 1)
            $cpuMs = 0
            try { $cpuMs = $p.UserModeTime + $p.KernelModeTime } catch {}
            Add-CheckResult -Category "Processi" -Name "PID $($p.ProcessId)" -Status $(if ($memMB -lt 2000) { "OK" } else { "WARN" }) -Detail "Memoria: ${memMB}MB"
        }
    } else {
        Add-CheckResult -Category "Processi" -Name "SPEACE Runtime" -Status "WARN" -Detail "Nessun processo SPEACE attivo"
    }

    $totalMem = [math]::Round(($pythonProcs | Measure-Object -Property WorkingSetSize -Sum).Sum / 1MB, 1)
    Add-CheckResult -Category "Processi" -Name "Memoria totale Python" -Status $(if ($totalMem -lt 4096) { "OK" } else { "WARN" }) -Detail "${totalMem}MB totale"
} catch {
    Add-CheckResult -Category "Processi" -Name "ProcessCheck" -Status "WARN" -Detail $_.Exception.Message
}

# 3. CONTROLLI RUNTIME
Write-Host "--- RUNTIME ---" -ForegroundColor Magenta
try {
    $snapshotPath = Join-Path -Path $ProjectRoot -ChildPath "data\runtime\latest_snapshot.json"
    if (Test-Path $snapshotPath) {
        $snapContent = Get-Content $snapshotPath -Raw -ErrorAction Stop
        $snapAge = [math]::Round(((Get-Date) - (Get-Item $snapshotPath).LastWriteTime).TotalMinutes, 1)
        $snapOk = $snapAge -lt 10
        Add-CheckResult -Category "Runtime" -Name "Snapshot" -Status $(if ($snapOk) { "OK" } else { "WARN" }) -Detail "Eta: ${snapAge}min"
        try {
            $snap = $snapContent | ConvertFrom-Json
            if ($snap.tick -ne $null) {
                Add-CheckResult -Category "Runtime" -Name "Tick" -Status "INFO" -Detail "Tick #$($snap.tick)"
            }
        } catch {
            Add-CheckResult -Category "Runtime" -Name "Snapshot JSON" -Status "WARN" -Detail "Formato JSON non valido"
        }
    } else {
        Add-CheckResult -Category "Runtime" -Name "Snapshot" -Status "FAIL" -Detail "File non trovato: $snapshotPath"
    }

    $alertPath = Join-Path -Path $ProjectRoot -ChildPath "data\monitoring\alerts.jsonl"
    if (Test-Path $alertPath) {
        $alerts = Get-Content $alertPath -Tail 20 -ErrorAction SilentlyContinue
        $criticalAlerts = $alerts | Where-Object { $_ -match '"severity":"critical"' }
        Add-CheckResult -Category "Runtime" -Name "Alert critici" -Status $(if ($criticalAlerts.Count -eq 0) { "OK" } else { "WARN" }) -Detail "$($criticalAlerts.Count) alert critici recenti"
    } else {
        Add-CheckResult -Category "Runtime" -Name "Alert" -Status "INFO" -Detail "File alert non trovato"
    }
} catch {
    Add-CheckResult -Category "Runtime" -Name "RuntimeCheck" -Status "WARN" -Detail $_.Exception.Message
}

# 4. CONTROLLI COMPONENTI
if ($Livello -in @("esteso", "completo")) {
    Write-Host "--- COMPONENTI ---" -ForegroundColor Magenta
    $dirs = @(
        @{Path = "speace_core"; Label = "Cervello SPEACE"; Critical = $true},
        @{Path = "speace_agi_team"; Label = "Team AGI"; Critical = $true},
        @{Path = "evolution_daemon"; Label = "Demone Evolutivo"; Critical = $true},
        @{Path = "scripts"; Label = "Scripts"; Critical = $false},
        @{Path = "data\runtime"; Label = "Dati Runtime"; Critical = $true},
        @{Path = "data\monitoring"; Label = "Dati Monitoraggio"; Critical = $true},
        @{Path = "data\logs"; Label = "Log"; Critical = $false},
        @{Path = "tests"; Label = "Test Suite"; Critical = $false}
    )
    foreach ($dir in $dirs) {
        $fullPath = Join-Path -Path $ProjectRoot -ChildPath $dir.Path
        $exists = Test-Path $fullPath
        $status = if ($exists) { "OK" } elseif ($dir.Critical) { "FAIL" } else { "WARN" }
        $detail = if ($exists) {
            $items = @(Get-ChildItem -LiteralPath $fullPath -Recurse -ErrorAction SilentlyContinue)
            "$($items.Count) files"
        } else {
            "Directory non trovata"
        }
        Add-CheckResult -Category "Componenti" -Name $dir.Label -Status $status -Detail $detail
    }
}

# 5. ERRORI RECENTI
Write-Host "--- LOG ERRORS ---" -ForegroundColor Magenta
try {
    $logDir = Join-Path -Path $ProjectRoot -ChildPath "data\logs"
    if (Test-Path $logDir) {
        $recentLogs = Get-ChildItem -LiteralPath $logDir -Recurse -Filter "*.log" -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -gt (Get-Date).AddHours(-1) }
        $totalErrors = 0
        foreach ($log in $recentLogs) {
            $errCount = (Get-Content -LiteralPath $log.FullName -ErrorAction SilentlyContinue | Where-Object { $_ -match "ERROR|FATAL|CRITICAL|Traceback" }).Count
            $totalErrors += $errCount
        }
        Add-CheckResult -Category "Errori" -Name "Ultima ora" -Status $(if ($totalErrors -eq 0) { "OK" } elseif ($totalErrors -lt 10) { "WARN" } else { "FAIL" }) -Detail "$totalErrors errori"
    }
} catch {
    Add-CheckResult -Category "Errori" -Name "LogCheck" -Status "WARN" -Detail $_.Exception.Message
}

# 6. FILE INTEGRITY (solo completo)
if ($Livello -eq "completo") {
    Write-Host "--- FILE INTEGRITY ---" -ForegroundColor Magenta
    try {
        $checkFiles = @(
            "speace_core\cli.py",
            "speace_core\orchestrator.py",
            "speace_agi_team\orchestrator.py",
            "scripts\continuous_organism.py",
            "scripts\speace_gateway.ps1"
        )
        foreach ($relPath in $checkFiles) {
            $fullPath = Join-Path -Path $ProjectRoot -ChildPath $relPath
            if (Test-Path $fullPath) {
                $size = (Get-Item $fullPath).Length
                Add-CheckResult -Category "Integrita" -Name $relPath -Status $(if ($size -gt 0) { "OK" } else { "FAIL" }) -Detail "$([math]::Round($size/1KB,1))KB"
            } else {
                Add-CheckResult -Category "Integrita" -Name $relPath -Status "FAIL" -Detail "File non trovato"
            }
        }
    } catch {
        Add-CheckResult -Category "Integrita" -Name "IntegrityCheck" -Status "WARN" -Detail $_.Exception.Message
    }

    Write-Host "--- DISCO DATI ---" -ForegroundColor Magenta
    $dataDir = Join-Path -Path $ProjectRoot -ChildPath "data"
    if (Test-Path $dataDir) {
        $dataSize = [math]::Round(((Get-ChildItem -LiteralPath $dataDir -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum) / 1GB, 2)
        $dataCount = (Get-ChildItem -LiteralPath $dataDir -Recurse -ErrorAction SilentlyContinue).Count
        Add-CheckResult -Category "Dati" -Name "Dimensione totale" -Status $(if ($dataSize -lt 50) { "OK" } else { "WARN" }) -Detail "${dataSize}GB ($dataCount files)"
        $oldFiles = Get-ChildItem -LiteralPath $dataDir -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) }
        Add-CheckResult -Category "Dati" -Name "File vecchi (+30g)" -Status "INFO" -Detail "$($oldFiles.Count) files"
    }
}

# 6. CAPACITÀ E MEccanismi AVANZATI
if ($Livello -in @("esteso", "completo")) {
    Write-Host "--- CAPACITÀ E MEccanismi AVANZATI ---" -ForegroundColor Magenta
    try {
        $assessmentDir = Join-Path $ProjectRoot "reports\assessment"
        if (Test-Path $assessmentDir) {
            $assessmentFiles = Get-ChildItem -LiteralPath $assessmentDir -Filter "capability_assessment_*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
            if ($assessmentFiles.Count -gt 0) {
                $latest = $assessmentFiles[0]
                $ageMin = [math]::Round(((Get-Date) - $latest.LastWriteTime).TotalMinutes, 1)
                $assessment = Get-Content $latest.FullName -Raw | ConvertFrom-Json
                $score = $assessment.composite_score
                Add-CheckResult -Category "Capacita" -Name "Assessment report" -Status $(if ($score -ge 30) { "OK" } else { "WARN" }) -Detail "Score: $score/100 (eta ${ageMin}min)"
            } else {
                Add-CheckResult -Category "Capacita" -Name "Assessment report" -Status "WARN" -Detail "Nessun report di assessment trovato"
            }
        } else {
            Add-CheckResult -Category "Capacita" -Name "Assessment report" -Status "WARN" -Detail "Directory reports/assessment non trovata"
        }

        $envDir = Join-Path $ProjectRoot "reports\environment"
        if (Test-Path $envDir) {
            $envFiles = Get-ChildItem -LiteralPath $envDir -Filter "run_*.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
            if ($envFiles.Count -gt 0) {
                $latestEnv = $envFiles[0]
                $envAge = [math]::Round(((Get-Date) - $latestEnv.LastWriteTime).TotalMinutes, 1)
                $envReport = Get-Content $latestEnv.FullName -Raw | ConvertFrom-Json
                $kind = $envReport.env_kind
                Add-CheckResult -Category "Capacita" -Name "Environment report" -Status "OK" -Detail "Ultimo: $kind (eta ${envAge}min)"
            } else {
                Add-CheckResult -Category "Capacita" -Name "Environment report" -Status "WARN" -Detail "Nessun report environment trovato"
            }
        } else {
            Add-CheckResult -Category "Capacita" -Name "Environment report" -Status "WARN" -Detail "Directory reports/environment non trovata"
        }

        $corPath = Join-Path $ProjectRoot "data\dynamics\cor\cor_events.jsonl"
        if (Test-Path $corPath) {
            $corLines = Get-Content $corPath -Tail 10 -ErrorAction SilentlyContinue
            $collapses = ($corLines | Where-Object { $_ -match '"collapsed":true' }).Count
            Add-CheckResult -Category "COR" -Name "COR events" -Status "OK" -Detail "$collapses collassi negli ultimi 10 eventi"
        } else {
            Add-CheckResult -Category "COR" -Name "COR events" -Status "INFO" -Detail "Log COR non trovato"
        }

        $dnaPath = Join-Path $ProjectRoot "speace_core\dna\genome\default_genome.yaml"
        if (Test-Path $dnaPath) {
            $dnaText = Get-Content $dnaPath -Raw
            $corEnabled = $dnaText -match "cor_genes:\s*\n\s*enabled:\s*true"
            Add-CheckResult -Category "DNA" -Name "COR genes abilitati" -Status $(if ($corEnabled) { "OK" } else { "WARN" }) -Detail $(if ($corEnabled) { "cor_genes.enabled = true" } else { "cor_genes non abilitato" })
        } else {
            Add-CheckResult -Category "DNA" -Name "Default genome" -Status "FAIL" -Detail "default_genome.yaml non trovato"
        }
    } catch {
        Add-CheckResult -Category "Capacita" -Name "CapacitaCheck" -Status "WARN" -Detail $_.Exception.Message
    }
}

# === REPORT ===
$elapsed = [math]::Round(((Get-Date) - $startTime).TotalSeconds, 1)
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "CHECKLIST COMPLETATA" -ForegroundColor Cyan
Write-Host "Durata: ${elapsed}s" -ForegroundColor Cyan
Write-Host "Totale check: $($checks.Count)" -ForegroundColor Cyan
Write-Host "Warning: $($warnings.Count)" -ForegroundColor Yellow
Write-Host "Errori: $($errors.Count)" -ForegroundColor Red
Write-Host "================================================================" -ForegroundColor Cyan

$report = [PSCustomObject]@{
    Timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff")
    Livello = $Livello
    DurataSec = $elapsed
    CheckCount = $checks.Count
    WarningCount = $warnings.Count
    ErrorCount = $errors.Count
    Checks = $checks
    Esito = if ($errors.Count -eq 0 -and $warnings.Count -eq 0) { "OK" } elseif ($errors.Count -eq 0) { "WARNING" } else { "ERROR" }
}
$report | ConvertTo-Json -Depth 4 | Out-File -FilePath $ReportFile -Encoding utf8
Write-Log "Report salvato: $ReportFile" -Level "OK"

# Markdown report
$md = @"
# Checklist Manutenzione Preventiva SPEACE

**Data:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
**Livello:** $Livello
**Durata:** ${elapsed}s

## Riepilogo
- Check eseguiti: $($checks.Count)
- Warning: $($warnings.Count)
- Errori: $($errors.Count)
- Esito: **$(if ($errors.Count -eq 0 -and $warnings.Count -eq 0) { 'TUTTO OK' } elseif ($errors.Count -eq 0) { 'ATTENZIONE' } else { 'CRITICO' })**

## Dettaglio Check

"@
$categories = $checks | Group-Object -Property Category
foreach ($cat in $categories) {
    $md += "### $($cat.Name)`n`n"
    $md += "| Nome | Stato | Dettaglio |`n"
    $md += "|------|-------|-----------|`n"
    foreach ($c in $cat.Group) {
        $statusIcon = switch ($c.Status) { "OK" { "OK" } "WARN" { "WARN" } "FAIL" { "FAIL" } "INFO" { "INFO" } default { $c.Status } }
        $escapedDetail = ($c.Detail -replace '\|', '/')
        $md += "| $($c.Name) | $statusIcon | $escapedDetail |`n"
    }
    $md += "`n"
}
$md += @"

---
*Report generato automaticamente dall'Ispettore Manutentore Neurologico Organismico di SPEACE*
"@
$md | Out-File -FilePath $ReportMdFile -Encoding utf8
Write-Log "Report Markdown salvato: $ReportMdFile" -Level "OK"

if ($errors.Count -gt 0) {
    Write-Host ""
    Write-Host "ERRORI DETECTED:" -ForegroundColor Red
    foreach ($e in $errors) { Write-Host "  [X] $e" -ForegroundColor Red }
}
if ($warnings.Count -gt 0) {
    Write-Host ""
    Write-Host "WARNING:" -ForegroundColor Yellow
    foreach ($w in $warnings) { Write-Host "  [!] $w" -ForegroundColor Yellow }
}

exit $(if ($errors.Count -eq 0) { 0 } else { 1 })

