<#
.SYNOPSIS
    Registra SPEACE Gateway nelle app di avvio di Windows Task Manager.
.DESCRIPTION
    Crea un collegamento nella cartella di avvio di Windows affinche
    SPEACE Brain + Organismo parta automaticamente all'avvio del sistema
    e sia visibile/gestibile da Task Manager > App di avvio.
.PARAMETER Mode
    Modalita di avvio del gateway (live, ignite, run).
.PARAMETER Remove
    Se specificato, rimuove SPEACE dalle app di avvio.
.PARAMETER AllUsersStartup
    Registra per tutti gli utenti (richiede admin).
#>

param(
    [ValidateSet("live", "ignite", "run")]
    [string]$Mode = "live",
    [switch]$Remove,
    [switch]$AllUsersStartup
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $PSCommandPath
$ProjectRoot = Split-Path -Parent $ScriptRoot
$GatewayScript = Join-Path -Path $ScriptRoot -ChildPath "speace_gateway.ps1"

# Determine startup folder
if ($AllUsersStartup) {
    $StartupFolder = [Environment]::GetFolderPath("CommonStartup")
} else {
    $StartupFolder = [Environment]::GetFolderPath("Startup")
}
$ShortcutName = "SPEACE Gateway.lnk"
$ShortcutPath = Join-Path -Path $StartupFolder -ChildPath $ShortcutName

function Write-Status {
    param([string]$Message, [ConsoleColor]$Color = "White")
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] " -NoNewline -ForegroundColor DarkGray
    Write-Host $Message -ForegroundColor $Color
}

function Write-Header {
    Clear-Host
    $host.UI.RawUI.WindowTitle = "SPEACE - Registrazione Avvio Windows"
    Write-Host "+-------------------------------------------------------+" -ForegroundColor Cyan
    Write-Host "|  SPEACE - Registrazione App di Avvio Windows          |" -ForegroundColor Cyan
    Write-Host "|  Task Manager > App di avvio                          |" -ForegroundColor Cyan
    Write-Host "+-------------------------------------------------------+" -ForegroundColor Cyan
    Write-Host ""
}

function New-Shortcut {
    param(
        [string]$Target,
        [string]$Arguments,
        [string]$ShortcutPath,
        [string]$Description,
        [string]$IconLocation
    )
    $WScriptShell = New-Object -ComObject WScript.Shell
    $shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $Target
    $shortcut.Arguments = $Arguments
    $shortcut.Description = $Description
    $shortcut.WorkingDirectory = $ProjectRoot
    if ($IconLocation) {
        $shortcut.IconLocation = $IconLocation
    }
    $shortcut.WindowStyle = 1
    $shortcut.Save()
}

function Get-PythonIcon {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return "$($python.Source),0"
    }
    return ""
}

# === MAIN ===
try {
    Write-Header

    if ($Remove) {
        Write-Status "Rimozione SPEACE dalle app di avvio..." -Color Yellow
        if (Test-Path -LiteralPath $ShortcutPath) {
            Remove-Item -LiteralPath $ShortcutPath -Force
            Write-Status "RIMOSSO: $ShortcutPath" -Color Green
        } else {
            Write-Status "Nessuna registrazione trovata." -Color Yellow
        }

        $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
        $regName = "SPEACE Gateway"
        if (Get-ItemProperty -Path $regPath -Name $regName -ErrorAction SilentlyContinue) {
            Remove-ItemProperty -Path $regPath -Name $regName
            Write-Status "RIMOSSO dal registro di sistema." -Color Green
        }

        Write-Status "SPEACE rimosso dalle app di avvio di Windows." -Color Green
        return
    }

    Write-Status "Verifica script gateway..." -Color Yellow

    if (-not (Test-Path -LiteralPath $GatewayScript)) {
        Write-Host "[ERRORE] Gateway script non trovato: $GatewayScript" -ForegroundColor Red
        exit 1
    }
    Write-Status "Gateway script: $GatewayScript" -Color Green

    Write-Status "Creazione collegamento in cartella di avvio..." -Color Yellow
    Write-Status "  -> $ShortcutPath" -Color Gray

    $pythonPath = (Get-Command python).Source
    $args = "-ExecutionPolicy Bypass -NoProfile -File `"$GatewayScript`" -Mode $Mode -NoPause"

    New-Shortcut `
        -Target "powershell.exe" `
        -Arguments $args `
        -ShortcutPath $ShortcutPath `
        -Description "SPEACE Gateway - Avvio cervello+organismo (modalita: $Mode)" `
        -IconLocation (Get-PythonIcon)

    if (Test-Path -LiteralPath $ShortcutPath) {
        Write-Status "COLLEGAMENTO CREATO: $ShortcutPath" -Color Green
    } else {
        Write-Host "[ERRORE] Impossibile creare il collegamento." -ForegroundColor Red
        exit 1
    }

    Write-Status "Registrazione nel registro di sistema (backup)..." -Color Yellow
    $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    $regName = "SPEACE Gateway"
    $regValue = "powershell.exe -ExecutionPolicy Bypass -NoProfile -File `"$GatewayScript`" -Mode $Mode -NoPause"
    Set-ItemProperty -Path $regPath -Name $regName -Value $regValue
    Write-Status "REGISTRO: $regPath\$regName" -Color Green

    Write-Host ""
    Write-Status "+-------------------------------------------------------+" -Color Cyan
    Write-Status "|  REGISTRAZIONE COMPLETATA                              |" -Color Cyan
    Write-Status "|                                                        |" -Color Cyan
    $scope = if ($AllUsersStartup) { "Tutti gli utenti" } else { "Solo utente corrente" }
    Write-Status "|  Ambito:   $($scope.PadRight(48))|" -Color Cyan
    Write-Status "|                                                        |" -Color Cyan
    Write-Status "|  Per rimuovere:                                         |" -Color Cyan
    Write-Status "|    - Task Manager > App di avvio > SPEACE Gateway >    |" -Color Cyan
    Write-Status "|      Disabilita/Rimuovi                                 |" -Color Cyan
    Write-Status "|    - Oppure esegui:                                     |" -Color Cyan
    Write-Status "|      scripts\register_speace_startup.ps1 -Remove       |" -Color Cyan
    Write-Status "+-------------------------------------------------------+" -Color Cyan
    Write-Host ""

} catch {
    Write-Host "[ERRORE] $_" -ForegroundColor Red
    exit 1
}
