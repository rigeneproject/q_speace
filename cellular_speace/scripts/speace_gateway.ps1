<#
.SYNOPSIS
    SPEACE Gateway - Avvia cervello + organismo via terminale
.DESCRIPTION
    Terminal gateway che avvia il cervello e organismo di SPEACE
    con sequenza di boot visuale. Progettato per l'avvio di Windows
    e visibile nelle app di avvio del Task Manager.
.PARAMETER Mode
    Modalita di avvio:
      live    - (default) Cervello/organismo 24/7 + team agentico NON-LLM
      ignite  - Accensione singola con ILF integrato
      run     - Runtime continuo monitorato
.PARAMETER NoPause
    Se specificato, non attende input prima di chiudere.
#>

param(
    [ValidateSet("live", "ignite", "run")]
    [string]$Mode = "live",
    [switch]$NoPause
)

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$LogDir = Join-Path -Path $ProjectRoot -ChildPath "data\logs"
$LogFile = Join-Path -Path $LogDir -ChildPath "gateway_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
    "$timestamp $Message" | Out-File -FilePath $LogFile -Encoding utf8 -Append
}

function Write-BootLine {
    param(
        [string]$Message,
        [string]$Status = "...",
        [ConsoleColor]$Color = "Gray"
    )
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] " -NoNewline -ForegroundColor DarkGray
    Write-Host "$Message " -NoNewline -ForegroundColor $Color
    Write-Host "$Status" -ForegroundColor Cyan
    Write-Log "[BOOT] $Message $Status"
}

function Write-Header {
    Clear-Host
    $host.UI.RawUI.WindowTitle = "SPEACE Gateway - $Mode"
    $colors = @("Cyan", "Green", "Yellow", "Red", "Magenta")
    $art = @(
        "   _____  ____  _____  _____   _____  ____  _   _  _____ ",
        "  / ____|/ __ \|  __ \|  __ \ / ____|/ __ \| \ | |/ ____|",
        " | (___ | |  | | |__) | |__) | |  __| |  | |  \| | |  __ ",
        "  \___ \| |  | |  ___/|  _  /| | |_ | |  | | . ` | | |_ |",
        "  ____) | |__| | |    | | \ \| |__| | |__| | |\  | |__| |",
        " |_____/ \____/|_|    |_|  \_\\\_____|\____/|_| \_|\_____|",
        "",
        "  Super Entita Autonoma Cibernetica Cellulare Evolutiva",
        "  ----------------------------------------------------",
        "  CERVELLO + ORGANISMO  |  v0.9.0  |  RIGENE PROJECT",
        ""
    )
    foreach ($line in $art) {
        $idx = [System.Math]::Abs($line.GetHashCode()) % $colors.Length
        Write-Host $line -ForegroundColor $colors[$idx]
    }
    Write-Host ""
}

function Test-Dependencies {
    Write-BootLine "Verifica Python" "..." -Color Yellow
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        Write-Host "[ERRORE] Python non trovato nel PATH" -ForegroundColor Red
        Write-Log "[ERRORE] Python not found in PATH"
        return $false
    }
    $ver = & python --version 2>&1
    Write-BootLine "Python" $ver -Color Green

    Write-BootLine "Verifica SPEACE CLI" "..." -Color Yellow
    $speaceCheck = & python -m speace_core.cli version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERRORE] SPEACE CLI non disponibile" -ForegroundColor Red
        Write-Log "[ERRORE] SPEACE CLI not available: $speaceCheck"
        return $false
    }
    $speaceVer = $speaceCheck.Trim()
    Write-BootLine "SPEACE CLI" $speaceVer -Color Green
    return $true
}

function Get-SystemInfo {
    Write-BootLine "Rilevamento sistema" "..." -Color Yellow
    try {
        $os = Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue
        if ($os) {
            Write-BootLine "Sistema operativo" "$($os.Caption) ($($os.Version))" -Color Green
        }
        $cpu = Get-CimInstance Win32_Processor -ErrorAction SilentlyContinue
        if ($cpu) {
            Write-BootLine "Processore" $cpu[0].Name -Color Green
        }
        $ram = [math]::Round((Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue).TotalPhysicalMemory / 1GB, 1)
        if ($ram) {
            Write-BootLine "Memoria RAM" "$ram GB" -Color Green
        }
    } catch {
        Write-BootLine "Sistema" "info non disponibile" -Color Yellow
        Write-Log "[WARN] System info retrieval failed: $_"
    }
}

function Invoke-SpeaceLive {
    param([string]$Mode)

    $modeTitle = @{
        "live"   = "AVVIO 24/7 - Cervello + Organismo + Team Agentico"
        "ignite" = "ACCENSIONE - Cervello + Organismo (ILF integrato)"
        "run"    = "RUNTIME - Cervello + Organismo + Monitor"
    }

    Write-Host ""
    Write-Host "  +-------------------------------------------------------+" -ForegroundColor Cyan
    Write-Host "  |  $($modeTitle[$Mode])" -ForegroundColor Cyan
    Write-Host "  |                                                       |" -ForegroundColor Cyan
    Write-Host "  |  Ctrl+C per arrestare graziosamente                  |" -ForegroundColor Cyan
    Write-Host "  +-------------------------------------------------------+" -ForegroundColor Cyan
    Write-Host ""

    Write-Log "[LAUNCH] Starting SPEACE in $Mode mode"

    $pythonArgs = @("-m", "speace_core.cli")
    switch ($Mode) {
        "live"   { $pythonArgs += @("live") }
        "ignite" { $pythonArgs += @("ignite") }
        "run"    { $pythonArgs += @("run") }
    }

    Write-Log "[SPEACE] python $($pythonArgs -join ' ')"

    # Run SPEACE directly: stdout/stderr fluiscono al console.
    # Non usiamo 2>&1 perche PowerShell 5.1 convertirebbe lo stderr
    # (dove Python scrive i log) in ErrorRecord, causando falsi positivi.
    $global:LASTEXITCODE = 0
    & python $pythonArgs
    $exitCode = $global:LASTEXITCODE
    if ($exitCode -ne 0) {
        Write-Log "[SPEACE] Processo terminato con codice $exitCode"
    }
}

# === MAIN ===
try {
    Write-Header
    Write-BootLine "Inizializzazione gateway" "v0.9.0" -Color Magenta
    Write-BootLine "Directory progetto" $ProjectRoot -Color Green
    Write-BootLine "Log file" $LogFile -Color Green
    Write-Host ""

    if (-not (Test-Dependencies)) {
        Write-Host ""
        Write-Host "[FATALE] Dipendenze insoddisfatte. Impossibile avviare SPEACE." -ForegroundColor Red
        Write-Log "[FATALE] Dependencies check failed."
        if (-not $NoPause) {
            Write-Host "Premere un tasto per chiudere..." -ForegroundColor Gray
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        }
        exit 1
    }

    Write-Host ""
    Get-SystemInfo

    Write-Host ""
    Write-BootLine "Pronto per l'avvio" $Mode -Color Magenta
    Start-Sleep -Milliseconds 500

    Invoke-SpeaceLive -Mode $Mode
} catch {
    Write-Host "[ERRORE] $_" -ForegroundColor Red
    Write-Log "[ERRORE] Unhandled exception: $_"
} finally {
    Write-Host ""
    Write-Host "+-------------------------------------------------------+" -ForegroundColor DarkGray
    Write-Host "|  SPEACE Gateway arrestato                             |" -ForegroundColor DarkGray
    Write-Host "+-------------------------------------------------------+" -ForegroundColor DarkGray
    Write-Log "[SHUTDOWN] SPEACE Gateway terminated"
    if (-not $NoPause) {
        Write-Host ""
        Write-Host "Premere un tasto per chiudere..." -ForegroundColor Gray
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
}
