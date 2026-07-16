@echo off
title Ispettore SPEACE - Installazione Cron Manutenzione Correttiva
color 0C
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "AGENT_DIR=%SCRIPT_DIR%..\.."
set "PROJECT_ROOT=%AGENT_DIR%.."
set "CORRETTIVA_DIR=%AGENT_DIR%\manutenzione\correttiva"
set "POWERSHELL_PATH=powershell.exe"
set "DIAG_SCRIPT=%CORRETTIVA_DIR%\diagnostica.ps1"

echo.
echo   +==============================================================+
echo   =  INSTALLAZIONE CRON MANUTENZIONE CORRETTIVA                  =
echo   =                                                               =
echo   =  Crea task schedulati per diagnosi tempestiva e              =
echo   =  riparazione automatica di guasti/blocchi.                   =
echo   +==============================================================+
echo.

:: Verifica privilegi amministratore
openfiles >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ATTENZIONE] Eseguire come Amministratore per installare i task.
    echo Tentativo di elevazione...
    powershell start -verb runas '%0'
    exit /b
)

echo [OK] Privilegi amministratore verificati.
echo.

:: MODALITA OFF: Diagnostica senza azioni automatiche
echo Installazione task: IspettoreSPEACE_Correttiva_Diagnosi (ogni 10 min)...
schtasks /Create /F /TN "IspettoreSPEACE\Correttiva_Diagnosi" /SC MINUTE /MO 10 /TR "%POWERSHELL_PATH% -ExecutionPolicy Bypass -NoProfile -File \"%DIAG_SCRIPT%\" -Focus all" /RL HIGHEST /IT /DELAY 0003:00
if %ERRORLEVEL% EQU 0 ( echo [OK] Task Diagnosi 10min creato ) else ( echo [ERRORE] Task Diagnosi 10min fallito: %ERRORLEVEL% )

:: MODALITA ON: Diagnostica + Auto-repair
echo Installazione task: IspettoreSPEACE_Correttiva_AutoRepair (ogni 30 min)...
schtasks /Create /F /TN "IspettoreSPEACE\Correttiva_AutoRepair" /SC MINUTE /MO 30 /TR "%POWERSHELL_PATH% -ExecutionPolicy Bypass -NoProfile -File \"%DIAG_SCRIPT%\" -Focus all -AutoRepair" /RL HIGHEST /IT /DELAY 0005:00
if %ERRORLEVEL% EQU 0 ( echo [OK] Task AutoRepair 30min creato ) else ( echo [ERRORE] Task AutoRepair 30min fallito: %ERRORLEVEL% )

:: MODALITA SCAN: Diagnostica runtime e processi ogni 2 min
echo Installazione task: IspettoreSPEACE_Correttiva_RapidScan (ogni 2 min)...
schtasks /Create /F /TN "IspettoreSPEACE\Correttiva_RapidScan" /SC MINUTE /MO 2 /TR "%POWERSHELL_PATH% -ExecutionPolicy Bypass -NoProfile -File \"%DIAG_SCRIPT%\" -Focus processi -MaxErrors 20" /RL HIGHEST /IT /DELAY 0000:30
if %ERRORLEVEL% EQU 0 ( echo [OK] Task RapidScan 2min creato ) else ( echo [ERRORE] Task RapidScan 2min fallito: %ERRORLEVEL% )

echo.
echo   +==============================================================+
echo   =  INSTALLAZIONE CRON CORRETTIVA COMPLETATA                    =
echo   =                                                               =
echo   =  Task creati:                                                 =
echo   =    - Ogni 2 min  : Scansione rapida processi                  =
echo   =    - Ogni 10 min : Diagnostica completa                       =
echo   =    - Ogni 30 min : Diagnostica + AutoRepair automatico        =
echo   =                                                               =
echo   =  Visualizza in: Task Scheduler > IspettoreSPEACE\             =
echo   +==============================================================+
echo.

pause
