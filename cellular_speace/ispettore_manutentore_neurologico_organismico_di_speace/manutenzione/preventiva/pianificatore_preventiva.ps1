<#
.SYNOPSIS
    Pianificatore di Manutenzione Preventiva per SPEACE
.DESCRIPTION
    Cron-like scheduler engine che esegue controlli periodici programmati
    sullo stato di SPEACE per prevenire blocchi, degradazione e guasti.
    Progettato per essere eseguito da Windows Task Scheduler (schtasks).
.PARAMETER TaskName
    Nome del task schedulato (ogni_5min, ogni_15min, ogni_1h, ogni_6h, ogni_24h)
.PARAMETER Mode
    Modalita esecuzione: scheduled (default), manual, report
#>

param(
    [ValidateSet("ogni_5min", "ogni_15min", "ogni_1h", "ogni_6h", "ogni_24h", "all")]
    [string]$TaskName = "all",
    [ValidateSet("scheduled", "manual", "report")]
    [string]$Mode = "scheduled"
)

$ScriptRoot = Split-Path -Parent $PSCommandPath
$ModuleRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSCommandPath))
$ProjectRoot = Split-Path -Parent $ModuleRoot
$LogDir = Join-Path -Path $ProjectRoot -ChildPath "data\logs\manutenzione\preventiva"
$ReportDir = Join-Path -Path $ProjectRoot -ChildPath "reports\manutenzione\preventiva"
$ChecklistDir = $ScriptRoot

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null

$LogFile = Join-Path -Path $LogDir -ChildPath "preventiva_$(Get-Date -Format 'yyyyMMdd').log"
$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss.fff') [$Level] $Message" | Out-File -FilePath $LogFile -Encoding utf8 -Append
    $color = switch ($Level) {
        "ERROR"   { "Red" }
        "WARN"    { "Yellow" }
        "OK"      { "Green" }
        "CHECK"   { "Cyan" }
        "SKIP"    { "DarkGray" }
        default   { "Gray" }
    }
    Write-Host "$(Get-Date -Format 'HH:mm:ss') [$Level] $Message" -ForegroundColor $color
}

function Get-SpeaceStatus {
    $status = @{}
    $status.Timestamp = $Timestamp

    $cliPath = Join-Path -Path $ProjectRoot -ChildPath "speace_core\cli.py"
    $status.SpeaceCliPresent = Test-Path $cliPath

    # Su Windows Get-Process non espone CommandLine; usiamo Win32_Process
    $runtimeProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -eq "python.exe" -and (
            $_.CommandLine -match "speace" -or
            $_.CommandLine -match "continuous_organism" -or
            $_.CommandLine -match "speace_core"
        )
    }
    $status.RunningPids = @($runtimeProcesses | ForEach-Object { $_.ProcessId })
    $status.HasRunningProcess = ($status.RunningPids.Count -gt 0)

    $snapshotPath = Join-Path -Path $ProjectRoot -ChildPath "data\runtime\latest_snapshot.json"
    if (Test-Path $snapshotPath) {
        try {
            $snapItem = Get-Item -LiteralPath $snapshotPath -ErrorAction Stop
            $status.SnapshotAge = [math]::Round(((Get-Date) - $snapItem.LastWriteTime).TotalMinutes, 1)
            $status.SnapshotFresh = ($status.SnapshotAge -lt 10)

            # Leggiamo solo le prime righe per evitare di parsare JSON enormi con chiavi duplicate
            $sample = Get-Content -LiteralPath $snapshotPath -TotalCount 30 -ErrorAction SilentlyContinue
            $tickLine = $sample | Where-Object { $_ -match '"tick(_count)?"\s*:\s*(\d+)' } | Select-Object -First 1
            if ($tickLine) {
                $status.SnapshotTick = [int]($tickLine -replace '.*"tick(_count)?"\s*:\s*(\d+).*', '$2')
            } else {
                $status.SnapshotTick = $null
            }
        } catch {
            $status.SnapshotError = $_.Exception.Message
            $status.SnapshotFresh = $false
        }
    } else {
        $status.SnapshotFresh = $false
        $status.SnapshotError = "File non trovato"
    }

    return $status
}

function Get-SystemHealth {
    $health = @{}
    $health.Timestamp = $Timestamp
    try {
        $os = Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue
        if ($os) {
            $health.OSName = $os.Caption
            $health.UptimeDays = [math]::Round(((Get-Date) - $os.LastBootUpTime).TotalDays, 1)
            $health.UptimeOk = ($health.UptimeDays -lt 30)
        }
        $cpu = Get-CimInstance Win32_Processor -ErrorAction SilentlyContinue
        if ($cpu) {
            $health.CpuName = $cpu[0].Name
            $health.CpuLoad = $cpu[0].LoadPercentage
            $health.CpuOk = ($health.CpuLoad -lt 85)
        }
        $ram = Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue
        if ($ram) {
            $health.RamTotalGB = [math]::Round($ram.TotalVisibleMemorySize / 1MB, 1)
            $health.RamFreeGB = [math]::Round($ram.FreePhysicalMemory / 1MB, 1)
            $health.RamUsedPercent = [math]::Round((1 - ($ram.FreePhysicalMemory / $ram.TotalVisibleMemorySize)) * 100, 1)
            $health.RamOk = ($health.RamUsedPercent -lt 90)
        }
        $disks = Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" -ErrorAction SilentlyContinue
        $health.Disks = @()
        foreach ($disk in $disks) {
            $d = @{
                Drive = $disk.DeviceID
                TotalGB = [math]::Round($disk.Size / 1GB, 1)
                FreeGB = [math]::Round($disk.FreeSpace / 1GB, 1)
                UsedPercent = [math]::Round((($disk.Size - $disk.FreeSpace) / $disk.Size) * 100, 1)
            }
            $d.Ok = ($d.UsedPercent -lt 95)
            $health.Disks += $d
        }
    } catch {
        $health.Error = $_.Exception.Message
    }
    return $health
}

function Get-SpeaceComponentHealth {
    $components = @{}
    $components.Timestamp = $Timestamp
    $components.ComponentStatus = @{}

    $dirs = @{
        "speace_core" = "Cervello SPEACE"
        "speace_agi_team" = "Team AGI"
        "evolution_daemon" = "Demone Evolutivo"
        "scripts" = "Scripts"
        "tests" = "Test"
        "data" = "Dati"
        "docs" = "Documentazione"
        "reports" = "Report"
    }

    foreach ($entry in $dirs.GetEnumerator()) {
        $path = Join-Path -Path $ProjectRoot -ChildPath $entry.Key
        $label = $entry.Value
        if (Test-Path $path) {
            $items = Get-ChildItem -LiteralPath $path -Recurse -ErrorAction SilentlyContinue
            $pyFiles = ($items | Where-Object { $_.Extension -eq ".py" }).Count
            $totalSize = [math]::Round(($items | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
            $components.ComponentStatus[$label] = @{
                Path = $path
                FileCount = $items.Count
                PythonFiles = $pyFiles
                TotalSizeMB = $totalSize
                Status = "ATTIVO"
            }
        } else {
            $components.ComponentStatus[$label] = @{
                Path = $path
                Status = "NON_TROVATO"
            }
        }
    }
    return $components
}

function Get-LastErrors {
    param([int]$Minutes = 60)
    $errors = @()
    $logDirs = @(
        "$ProjectRoot\data\logs"
        "$ProjectRoot\data\monitoring"
    )
    $cutoff = (Get-Date).AddMinutes(-$Minutes)
    foreach ($logDir in $logDirs) {
        if (Test-Path $logDir) {
            $logFiles = Get-ChildItem -LiteralPath $logDir -Recurse -Filter "*.log" -ErrorAction SilentlyContinue |
                Where-Object { $_.LastWriteTime -gt $cutoff }
            foreach ($file in $logFiles) {
                $content = Get-Content -LiteralPath $file.FullName -Tail 500 -ErrorAction SilentlyContinue
                $errorLines = $content | Where-Object { $_ -match "ERROR|FATAL|CRITICAL|Traceback|Exception" }
                foreach ($line in $errorLines) {
                    $errors += [PSCustomObject]@{
                        File = $file.Name
                        Line = $line
                        Timestamp = $file.LastWriteTime
                    }
                }
            }
        }
    }
    return $errors
}

function Invoke-Checklist {
    param([string]$Frequenza)
    $checks = @()
    $allOk = $true

    Write-Log "Avvio checklist preventiva [$Frequenza]" -Level "CHECK"

    # 1. Verifica sistema operativo
    try {
        $health = Get-SystemHealth
        Write-Log "CPU: $($health.CpuLoad)% | RAM: $($health.RamUsedPercent)% | Uptime: $($health.UptimeDays)g" -Level $(if ($health.CpuOk -and $health.RamOk) { "OK" } else { "WARN" })
        if (-not $health.CpuOk) { $checks += "CPU sopra 85%: $($health.CpuLoad)%"; $allOk = $false }
        if (-not $health.RamOk) { $checks += "RAM sopra 90%: $($health.RamUsedPercent)%"; $allOk = $false }
        foreach ($disk in $health.Disks) {
            if (-not $disk.Ok) { $checks += "Disco $($disk.Drive) sopra 95%: $($disk.UsedPercent)%"; $allOk = $false }
        }
    } catch {
        $checks += "Errore lettura salute sistema: $_"
        $allOk = $false
    }

    # 2. Verifica processi SPEACE
    try {
        $status = Get-SpeaceStatus
        if ($status.HasRunningProcess) {
            Write-Log "Processi SPEACE attivi: $($status.RunningPids -join ',')" -Level "OK"
        } else {
            $checks += "Nessun processo SPEACE in esecuzione"
            $allOk = $false
            Write-Log "Nessun processo SPEACE rilevato" -Level "WARN"
        }
    } catch {
        $checks += "Errore verifica processi: $_"
    }

    # 3. Verifica snapshot recente
    if ($status.SnapshotFresh) {
        Write-Log "Snapshot fresco: tick $($status.SnapshotTick), eta $($status.SnapshotAge)min" -Level "OK"
    } else {
        $checks += "Snapshot non disponibile o vecchio: $($status.SnapshotError)"
        $allOk = $false
        Write-Log "Snapshot non fresco: $($status.SnapshotError)" -Level "WARN"
    }

    # 4. Verifica componenti
    if ($Frequenza -in @("ogni_1h", "ogni_6h", "ogni_24h", "all")) {
        $components = Get-SpeaceComponentHealth
        $inattivi = $components.ComponentStatus.GetEnumerator() | Where-Object { $_.Value.Status -eq "NON_TROVATO" }
        foreach ($comp in $inattivi) {
            $checks += "Componente non trovato: $($comp.Key) ($($comp.Value.Path))"
            Write-Log "Componente NON TROVATO: $($comp.Key)" -Level "WARN"
        }
    }

    # 5. Verifica errori recenti
    $errorWindow = switch ($Frequenza) {
        "ogni_5min" { 10 }
        "ogni_15min" { 30 }
        "ogni_1h" { 120 }
        "ogni_6h" { 480 }
        "ogni_24h" { 1440 }
        default { 60 }
    }
    $recentErrors = Get-LastErrors -Minutes $errorWindow
    if ($recentErrors.Count -gt 0) {
        Write-Log "$($recentErrors.Count) errori rilevati nelle ultime $errorWindow minuti" -Level "WARN"
        $checks += "$($recentErrors.Count) errori nei log (ultimi ${errorWindow}min)"
        if ($recentErrors.Count -gt 10) {
            $allOk = $false
        }
    } else {
        Write-Log "Nessun errore rilevato" -Level "OK"
    }

    # 6. Verifica spazio su disco dei dati critici
    if ($Frequenza -in @("ogni_6h", "ogni_24h", "all")) {
        $dataDir = "$ProjectRoot\data"
        if (Test-Path $dataDir) {
            $dataSize = [math]::Round(((Get-ChildItem -LiteralPath $dataDir -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum) / 1GB, 2)
            Write-Log "Dimensione dati: ${dataSize}GB" -Level "OK"
            if ($dataSize -gt 50) {
                $checks += "Directory dati troppo grande: ${dataSize}GB (>50GB)"
                $allOk = $false
            }
        }
    }

    # Report
    $report = [PSCustomObject]@{
        Timestamp = $Timestamp
        Frequenza = $Frequenza
        AllOk = $allOk
        Checks = @($checks)
        SystemHealth = $health
        SpeaceStatus = $status
        RecentErrors = $recentErrors.Count
        ErrorList = @($recentErrors | Select-Object -First 20)
    }

    $reportFile = Join-Path -Path $ReportDir -ChildPath "report_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
    try {
        $report | ConvertTo-Json -Depth 4 -ErrorAction Stop | Out-File -FilePath $reportFile -Encoding utf8 -ErrorAction Stop
        Write-Log "Report salvato: $reportFile" -Level "OK"
    } catch {
        Write-Log "Impossibile salvare il report JSON: $_" -Level "ERROR"
        $fallbackFile = Join-Path -Path $ReportDir -ChildPath "report_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
        "Report non serializzabile. Riassunto:`n$($report | Out-String)" | Out-File -FilePath $fallbackFile -Encoding utf8
    }

    if ($allOk) {
        Write-Log "Checklist [$Frequenza] COMPLETATA - TUTTO OK" -Level "OK"
    } else {
        Write-Log "Checklist [$Frequenza] COMPLETATA - $($checks.Count) ANOMALIE" -Level "WARN"
        foreach ($c in $checks) {
            Write-Log "  ANOMALIA: $c" -Level "WARN"
        }
    }

    return $report
}

# === MAIN ===
try {
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "PIANIFICATORE MANUTENZIONE PREVENTIVA SPEACE" -ForegroundColor Cyan
    Write-Host "Task: $TaskName | Modalita: $Mode" -ForegroundColor Cyan
    Write-Host "Log: $LogFile" -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan

    $tasks = @{
        "ogni_5min" = @{ Interval = 5; Checks = @("cpu_ram", "processi", "snapshot", "errori_recenti") }
        "ogni_15min" = @{ Interval = 15; Checks = @("cpu_ram", "processi", "snapshot", "errori_recenti", "disco") }
        "ogni_1h" = @{ Interval = 60; Checks = @("completo_base") }
        "ogni_6h" = @{ Interval = 360; Checks = @("completo_esteso") }
        "ogni_24h" = @{ Interval = 1440; Checks = @("completo_profondo") }
    }

    if ($TaskName -eq "all") {
        $results = @()
        foreach ($t in $tasks.Keys) {
            $results += Invoke-Checklist -Frequenza $t
            Start-Sleep -Seconds 1
        }
    } else {
        $result = Invoke-Checklist -Frequenza $TaskName
    }

    if ($Mode -eq "report") {
        Write-Host ""
        Write-Host "=== REPORT PREVENTIVO ===" -ForegroundColor Green
        Write-Host "Log: $LogFile" -ForegroundColor Gray
        Write-Host "Reports: $ReportDir" -ForegroundColor Gray
    }

} catch {
    Write-Log "ERRORE FATALE: $_" -Level "ERROR"
    Write-Host "[FATALE] $_" -ForegroundColor Red
    exit 1
}
