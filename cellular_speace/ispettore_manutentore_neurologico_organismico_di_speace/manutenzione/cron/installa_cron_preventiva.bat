@echo off
title Ispettore SPEACE - Installazione Cron Manutenzione Preventiva
color 0A
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "AGENT_DIR=%SCRIPT_DIR%..\.."
set "PROJECT_ROOT=%AGENT_DIR%.."
set "PREVENTIVA_DIR=%AGENT_DIR%\manutenzione\preventiva"
set "POWERSHELL_PATH=powershell.exe"
set "SCRIPT_PATH=%PREVENTIVA_DIR%\pianificatore_preventiva.ps1"

echo.
echo   +==============================================================+
echo   =  INSTALLAZIONE CRON MANUTENZIONE PREVENTIVA                  =
echo   =                                                               =
echo   =  Crea task schedulati di Windows per controlli periodici      =
echo   =  sullo stato di SPEACE.                                       =
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

:: Task 1: Ogni 5 minuti - Controlli rapidi CPU/RAM/processi
echo Installazione task: IspettoreSPEACE_Preventiva_5min...
schtasks /Create /F /TN "IspettoreSPEACE\Preventiva_5min" /SC MINUTE /MO 5 /TR "%POWERSHELL_PATH% -ExecutionPolicy Bypass -NoProfile -File \"%SCRIPT_PATH%\" -TaskName ogni_5min -Mode scheduled" /RL HIGHEST /IT /DELAY 0001:00
if %ERRORLEVEL% EQU 0 ( echo [OK] Task 5min creato ) else ( echo [ERRORE] Task 5min fallito: %ERRORLEVEL% )

:: Task 2: Ogni 15 minuti - Checklist base
echo Installazione task: IspettoreSPEACE_Preventiva_15min...
schtasks /Create /F /TN "IspettoreSPEACE\Preventiva_15min" /SC MINUTE /MO 15 /TR "%POWERSHELL_PATH% -ExecutionPolicy Bypass -NoProfile -File \"%SCRIPT_PATH%\" -TaskName ogni_15min -Mode scheduled" /RL HIGHEST /IT /DELAY 0002:00
if %ERRORLEVEL% EQU 0 ( echo [OK] Task 15min creato ) else ( echo [ERRORE] Task 15min fallito: %ERRORLEVEL% )

:: Task 3: Ogni ora - Checklist estesa
echo Installazione task: IspettoreSPEACE_Preventiva_1h...
schtasks /Create /F /TN "IspettoreSPEACE\Preventiva_1h" /SC HOURLY /MO 1 /TR "%POWERSHELL_PATH% -ExecutionPolicy Bypass -NoProfile -File \"%SCRIPT_PATH%\" -TaskName ogni_1h -Mode scheduled" /RL HIGHEST /IT /DELAY 0005:00
if %ERRORLEVEL% EQU 0 ( echo [OK] Task 1h creato ) else ( echo [ERRORE] Task 1h fallito: %ERRORLEVEL% )

:: Task 4: Ogni 6 ore - Checklist completa
echo Installazione task: IspettoreSPEACE_Preventiva_6h...
schtasks /Create /F /TN "IspettoreSPEACE\Preventiva_6h" /SC HOURLY /MO 6 /TR "%POWERSHELL_PATH% -ExecutionPolicy Bypass -NoProfile -File \"%SCRIPT_PATH%\" -TaskName ogni_6h -Mode scheduled" /RL HIGHEST /IT /DELAY 0010:00
if %ERRORLEVEL% EQU 0 ( echo [OK] Task 6h creato ) else ( echo [ERRORE] Task 6h fallito: %ERRORLEVEL% )

:: Task 5: Ogni 24 ore (alle 03:00) - Checklist profonda
echo Installazione task: IspettoreSPEACE_Preventiva_24h...
schtasks /Create /F /TN "IspettoreSPEACE\Preventiva_24h" /SC DAILY /MO 1 /ST 03:00 /TR "%POWERSHELL_PATH% -ExecutionPolicy Bypass -NoProfile -File \"%SCRIPT_PATH%\" -TaskName ogni_24h -Mode scheduled" /RL HIGHEST /IT
if %ERRORLEVEL% EQU 0 ( echo [OK] Task 24h creato ) else ( echo [ERRORE] Task 24h fallito: %ERRORLEVEL% )

echo.
echo   +==============================================================+
echo   =  INSTALLAZIONE CRON PREVENTIVA COMPLETATA                    =
echo   =                                                               =
echo   =  Task creati:                                                 =
echo   =    - Ogni 5 min  : Controllo rapido CPU/RAM/processi          =
echo   =    - Ogni 15 min : Checklist base                             =
echo   =    - Ogni 1h     : Checklist estesa                           =
echo   =    - Ogni 6h     : Checklist completa                         =
echo   =    - Ogni 24h    : Checklist profonda (03:00)                 =
echo   =                                                               =
echo   =  Visualizza in: Task Scheduler > IspettoreSPEACE\             =
echo   +==============================================================+
echo.

pause
