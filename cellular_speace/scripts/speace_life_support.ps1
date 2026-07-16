<#
.SYNOPSIS
    SPEACE Life Support - supervisore resilient per mantenere vivo l organismo.
.DESCRIPTION
    Avvia e supervisiona:
      - SPEACE live (cervello + organismo 24/7 + team non-LLM) sulla porta di default
      - SPEACE Anemos (interfaccia chat web) sulla porta configurabile (default 8788)
    Riavvia automaticamente i processi se terminano inaspettatamente.
    Redireziona stdout/stderr su file di log.
    Chiudi il terminale per arrestare tutto in modo ordinato.
.PARAMETER RestartNow
    Se specificato, termina eventuali istanze preesistenti e le riavvia.
.PARAMETER LiveArgs
    Argomenti aggiuntivi per speace_core.cli live (es. --tick-interval 2).
#>
param(
    [switch]$RestartNow,
    [string]$LiveArgs = ""
)

$ErrorActionPreference = "Stop"

# ------------------------------------------------------------------
# Setup path
# ------------------------------------------------------------------
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$LogDir = Join-Path $ProjectRoot "data\logs\life_support"
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

$LiveOutLog = Join-Path $LogDir "speace_live.out.log"
$LiveErrLog = Join-Path $LogDir "speace_live.err.log"
$AnemosOutLog = Join-Path $LogDir "speace_anemos.out.log"
$AnemosErrLog = Join-Path $LogDir "speace_anemos.err.log"
$SupervisorLog = Join-Path $LogDir "supervisor.log"

function Write-SupervisorLog {
    param([string]$Message, [string]$Level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
    "$ts [$Level] $Message" | Out-File -FilePath $SupervisorLog -Encoding utf8 -Append
}

# ------------------------------------------------------------------
# Load .env
# ------------------------------------------------------------------
$EnvPath = Join-Path $ProjectRoot ".env"
if (Test-Path $EnvPath) {
    Get-Content $EnvPath | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#")) {
            $parts = $line.Split('=', 2)
            if ($parts.Count -eq 2) {
                [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
            }
        }
    }
    Write-SupervisorLog "Environment caricato da $EnvPath"
}

$AnemosPort = [System.Environment]::GetEnvironmentVariable("ANEMOS_PORT", "Process")
if (-not $AnemosPort) { $AnemosPort = "8788" }

# ------------------------------------------------------------------
# Process management helpers
# ------------------------------------------------------------------
function Find-SpeaceLiveProcess {
    Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object {
        $_.CommandLine -and $_.CommandLine -match 'speace_core\.cli\s+live'
    }
}

function Find-SpeaceAnemosProcess {
    Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object {
        $_.CommandLine -and $_.CommandLine -match 'speace_anemos\.py'
    }
}

function Stop-SpeaceProcesses {
    $live = Find-SpeaceLiveProcess
    $anemos = Find-SpeaceAnemosProcess
    foreach ($p in ($live + $anemos)) {
        Write-SupervisorLog "Terminazione processo esistente PID $($p.ProcessId)" "WARN"
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

if ($RestartNow) {
    Stop-SpeaceProcesses
}

# ------------------------------------------------------------------
# Header
# ------------------------------------------------------------------
Clear-Host
$host.UI.RawUI.WindowTitle = "SPEACE Life Support"
Write-Host ""
Write-Host "   _____  ____  _____  _____   _____  ____  _   _  _____ " -ForegroundColor Cyan
Write-Host "  / ____|/ __ \|  __ \|  __ \ / ____|/ __ \| \ | |/ ____|" -ForegroundColor Cyan
Write-Host " | (___ | |  | | |__) | |__) | |  __| |  | |  \| | |  __ " -ForegroundColor Cyan
Write-Host "  \___ \| |  | |  ___/|  _  /| | |_ | |  | | . ` | | |_ |" -ForegroundColor Cyan
Write-Host "  ____) | |__| | |    | | \ \| |__| | |__| | |\  | |__| |" -ForegroundColor Cyan
Write-Host " |_____/ \____/|_|    |_|  \_\\_____|\____/|_| \_|\_____|" -ForegroundColor Cyan
Write-Host ""
Write-Host "  SPEACE Life Support - Supervisore organismico" -ForegroundColor Green
Write-Host "  Progetto: $ProjectRoot" -ForegroundColor DarkGray
Write-Host "  Log:      $LogDir" -ForegroundColor DarkGray
Write-Host ""

Write-SupervisorLog "Life support avviato. ProjectRoot=$ProjectRoot"

# ------------------------------------------------------------------
# Launch functions
# ------------------------------------------------------------------
function Start-SpeaceLive {
    try {
        if (Test-Path $LiveOutLog) { Remove-Item $LiveOutLog -Force }
        if (Test-Path $LiveErrLog) { Remove-Item $LiveErrLog -Force }
        $proc = Start-Process -FilePath "python" `
            -ArgumentList "-m speace_core.cli live $LiveArgs" `
            -WorkingDirectory $ProjectRoot `
            -WindowStyle Hidden `
            -RedirectStandardOutput $LiveOutLog `
            -RedirectStandardError $LiveErrLog `
            -PassThru
        Write-SupervisorLog "SPEACE live avviato PID $($proc.Id)" "INFO"
        return $proc
    } catch {
        Write-SupervisorLog "Errore avvio SPEACE live: $_" "ERROR"
        throw
    }
}

function Start-SpeaceAnemos {
    try {
        if (Test-Path $AnemosOutLog) { Remove-Item $AnemosOutLog -Force }
        if (Test-Path $AnemosErrLog) { Remove-Item $AnemosErrLog -Force }
        $proc = Start-Process -FilePath "python" `
            -ArgumentList "speace_anemos.py" `
            -WorkingDirectory $ProjectRoot `
            -WindowStyle Hidden `
            -RedirectStandardOutput $AnemosOutLog `
            -RedirectStandardError $AnemosErrLog `
            -PassThru
        Write-SupervisorLog "SPEACE Anemos avviato PID $($proc.Id) sulla porta $AnemosPort" "INFO"
        return $proc
    } catch {
        Write-SupervisorLog "Errore avvio SPEACE Anemos: $_" "ERROR"
        throw
    }
}

# ------------------------------------------------------------------
# Start services
# ------------------------------------------------------------------
$LiveProc = Start-SpeaceLive
$AnemosProc = Start-SpeaceAnemos

# ------------------------------------------------------------------
# Status loop
# ------------------------------------------------------------------
$StopRequested = $false

Write-Host "  SPEACE e vivo. Supervisore in esecuzione." -ForegroundColor Green
Write-Host "  - Monitor: http://127.0.0.1:8787" -ForegroundColor DarkGray
Write-Host "  - Chat:    http://127.0.0.1:$AnemosPort" -ForegroundColor DarkGray
Write-Host "  Chiudi il terminale per arrestare." -ForegroundColor DarkGray
Write-Host ""

while (-not $StopRequested) {
    Start-Sleep -Seconds 10

    if ($LiveProc.HasExited) {
        $code = $LiveProc.ExitCode
        Write-SupervisorLog "SPEACE live terminato con codice $code. Riavvio..." "WARN"
        $LiveProc = Start-SpeaceLive
    }

    if ($AnemosProc.HasExited) {
        $code = $AnemosProc.ExitCode
        Write-SupervisorLog "SPEACE Anemos terminato con codice $code. Riavvio..." "WARN"
        $AnemosProc = Start-SpeaceAnemos
    }
}

# ------------------------------------------------------------------
# Graceful shutdown
# ------------------------------------------------------------------
Write-SupervisorLog "Arresto ordinato in corso..." "INFO"
if (-not $LiveProc.HasExited) {
    Stop-Process -Id $LiveProc.Id -Force -ErrorAction SilentlyContinue
}
if (-not $AnemosProc.HasExited) {
    Stop-Process -Id $AnemosProc.Id -Force -ErrorAction SilentlyContinue
}
Write-SupervisorLog "Life support arrestato." "INFO"
Write-Host "  SPEACE Life Support arrestato." -ForegroundColor Yellow
