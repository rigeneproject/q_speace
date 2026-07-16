<#
.SYNOPSIS
    Registra l'Ispettore Manutentore Neurologico Organismico di SPEACE
    nelle app di avvio di Windows (Task Manager > App di avvio).
.DESCRIPTION
    Crea un collegamento nella cartella di avvio di Windows affinche
    l'Agentic AI parta automaticamente all'avvio del sistema e sia
    visibile/gestibile da Task Manager > App di avvio.
.PARAMETER Mode
    Modalita di avvio: cloud (default) o local.
.PARAMETER Remove
    Se specificato, rimuove l'Ispettore dalle app di avvio.
.PARAMETER AllUsersStartup
    Registra per tutti gli utenti (richiede admin).
#>

param(
    [ValidateSet("cloud", "local")]
    [string]$Mode = "cloud",
    [switch]$Remove,
    [switch]$AllUsersStartup
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $PSCommandPath
$ProjectRoot = Split-Path -Parent $ScriptRoot

if ($AllUsersStartup) {
    $StartupFolder = [Environment]::GetFolderPath("CommonStartup")
} else {
    $StartupFolder = [Environment]::GetFolderPath("Startup")
}

$ShortcutName = "Ispettore SPEACE.lnk"
$ShortcutPath = Join-Path -Path $StartupFolder -ChildPath $ShortcutName

function Write-Status {
    param([string]$Message, [ConsoleColor]$Color = "White")
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] " -NoNewline -ForegroundColor DarkGray
    Write-Host $Message -ForegroundColor $Color
}

function Write-Header {
    Clear-Host
    $host.UI.RawUI.WindowTitle = "Ispettore SPEACE - Registrazione Avvio Windows"
    Write-Host "+==============================================================+" -ForegroundColor Cyan
    Write-Host "|  ISPETTORE MANUTENTORE NEUROLOGICO ORGANISMICO DI SPEACE     |" -ForegroundColor Cyan
    Write-Host "|  Registrazione App di Avvio Windows                          |" -ForegroundColor Cyan
    Write-Host "|  Task Manager > App di avvio                                 |" -ForegroundColor Cyan
    Write-Host "+==============================================================+" -ForegroundColor Cyan
    Write-Host ""
}

function New-Shortcut {
    param(
        [string]$Target,
        [string]$Arguments,
        [string]$ShortcutPath,
        [string]$Description
    )
    $WScriptShell = New-Object -ComObject WScript.Shell
    $shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $Target
    $shortcut.Arguments = $Arguments
    $shortcut.Description = $Description
    $shortcut.WorkingDirectory = $ProjectRoot
    $shortcut.WindowStyle = 1
    $shortcut.Save()
}

# === MAIN ===
try {
    Write-Header

    if ($Remove) {
        Write-Status "Rimozione Ispettore SPEACE dalle app di avvio..." -Color Yellow
        if (Test-Path -LiteralPath $ShortcutPath) {
            Remove-Item -LiteralPath $ShortcutPath -Force
            Write-Status "RIMOSSO: $ShortcutPath" -Color Green
        } else {
            Write-Status "Nessuna registrazione trovata." -Color Yellow
        }

        $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
        $regName = "Ispettore SPEACE"
        if (Get-ItemProperty -Path $regPath -Name $regName -ErrorAction SilentlyContinue) {
            Remove-ItemProperty -Path $regPath -Name $regName
            Write-Status "RIMOSSO dal registro di sistema." -Color Green
        }

        $watcherBat = Join-Path -Path $ScriptRoot -ChildPath "watcher_restart.bat"
        if (Test-Path -LiteralPath $watcherBat) {
            Remove-Item -LiteralPath $watcherBat -Force
            Write-Status "RIMOSSO watcher: $watcherBat" -Color Green
        }

        Write-Status "Ispettore SPEACE rimosso dalle app di avvio di Windows." -Color Green
        return
    }

    Write-Status "Registrazione Ispettore SPEACE per avvio automatico..." -Color Yellow
    Write-Status "Modalita: $Mode" -Color Cyan

    $batFile = if ($Mode -eq "cloud") {
        Join-Path -Path $ScriptRoot -ChildPath "avvio_cloud.bat"
    } else {
        Join-Path -Path $ScriptRoot -ChildPath "avvio_locale.bat"
    }

    if (-not (Test-Path -LiteralPath $batFile)) {
        Write-Host "[ERRORE] Script di avvio non trovato: $batFile" -ForegroundColor Red
        exit 1
    }

    Write-Status "Creazione collegamento..." -Color Yellow
    Write-Status "  -> $ShortcutPath" -Color Gray
    Write-Status "  -> Target: $batFile" -Color Gray

    New-Shortcut `
        -Target $batFile `
        -Arguments "" `
        -ShortcutPath $ShortcutPath `
        -Description "Ispettore Manutentore Neurologico Organismico di SPEACE - Avvio automatico ($Mode)"

    if (Test-Path -LiteralPath $ShortcutPath) {
        Write-Status "COLLEGAMENTO CREATO: $ShortcutPath" -Color Green
    } else {
        Write-Host "[ERRORE] Impossibile creare il collegamento." -ForegroundColor Red
        exit 1
    }

    Write-Status "Registrazione nel registro di sistema (backup)..." -Color Yellow
    $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    $regName = "Ispettore SPEACE"
    # Avvia minimizzato tramite cmd /c start /min per non disturbare all'avvio
    $regValue = '"' + $batFile + '"'
    Set-ItemProperty -Path $regPath -Name $regName -Value $regValue
    Write-Status "REGISTRO: $regPath\$regName" -Color Green

    # Crea anche uno script di controllo che garantisce il riavvio se il processo dovesse terminare
    $watcherBat = Join-Path -Path $ScriptRoot -ChildPath "watcher_restart.bat"
    $watcherContent = @"
@echo off
title Ispettore SPEACE Watcher
set "TARGET=$batFile"
:LOOP
for /f "tokens=2 delims=," %%%%i in ('tasklist /fi "WINDOWTITLE eq ISPETTORE MANUTENTORE NEUROLOGICO ORGANISMICO DI SPEACE*" /fo csv /nh') do set PID=%%%%i
if not defined PID (
    start /min "" "%TARGET%"
)
timeout /t 30 /nobreak >nul
goto LOOP
"@
    $watcherContent | Out-File -FilePath $watcherBat -Encoding ASCII
    Write-Status "Watcher creato: $watcherBat" -Color Green

    Write-Host ""
    Write-Status "+==============================================================+" -Color Cyan
    Write-Status "|  REGISTRAZIONE COMPLETATA CON SUCCESSO                        |" -Color Cyan
    Write-Status "|                                                                |" -Color Cyan
    $scope = if ($AllUsersStartup) { "Tutti gli utenti" } else { "Solo utente corrente" }
    Write-Status "|  Ambito:   $($scope.PadRight(56))|" -Color Cyan
    Write-Status "|  Modalita: $($Mode.PadRight(56))|" -Color Cyan
    Write-Status "|                                                                |" -Color Cyan
    Write-Status "|  Per rimuovere:                                                |" -Color Cyan
    Write-Status "|    - Task Manager > App di avvio > Ispettore SPEACE >          |" -Color Cyan
    Write-Status "|      Disabilita/Rimuovi                                        |" -Color Cyan
    Write-Status "|    - Oppure esegui: remove_startup.bat                         |" -Color Cyan
    Write-Status "+==============================================================+" -Color Cyan
    Write-Host ""

    Write-Status "L'Ispettore partira automaticamente al prossimo avvio di Windows." -Color Green
    Write-Status "Per avviarlo immediatamente, esegui avvio_cloud.bat o avvio_locale.bat" -Color Green

} catch {
    Write-Host "[ERRORE] $_" -ForegroundColor Red
    exit 1
}
