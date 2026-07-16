@echo off
title Ispettore SPEACE - Rimozione Task Schedulati
color 0E
setlocal enabledelayedexpansion

echo.
echo   +==============================================================+
echo   =  RIMOZIONE TASK SCHEDULATI MANUTENZIONE SPEACE               =
echo   =                                                               =
echo   =  Rimuove tutti i task schedulati di manutenzione              =
echo   =  preventiva e correttiva.                                     =
echo   +==============================================================+
echo.

:: Verifica privilegi amministratore
openfiles >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ATTENZIONE] Eseguire come Amministratore per rimuovere i task.
    echo Tentativo di elevazione...
    powershell start -verb runas '%0'
    exit /b
)

echo [OK] Privilegi amministratore verificati.
echo.

echo Rimozione task preventiva...
for %%T in (Preventiva_5min Preventiva_15min Preventiva_1h Preventiva_6h Preventiva_24h) do (
    schtasks /Delete /F /TN "IspettoreSPEACE\%%T" >nul 2>nul
    if !ERRORLEVEL! EQU 0 ( echo [OK] Rimosso: IspettoreSPEACE\%%T ) else ( echo [ - ] Non trovato: IspettoreSPEACE\%%T )
)

echo.
echo Rimozione task correttiva...
for %%T in (Correttiva_Diagnosi Correttiva_AutoRepair Correttiva_RapidScan) do (
    schtasks /Delete /F /TN "IspettoreSPEACE\%%T" >nul 2>nul
    if !ERRORLEVEL! EQU 0 ( echo [OK] Rimosso: IspettoreSPEACE\%%T ) else ( echo [ - ] Non trovato: IspettoreSPEACE\%%T )
)

echo.
echo Rimozione cartella task...
schtasks /Delete /F /TN "IspettoreSPEACE" >nul 2>nul

echo.
echo   +==============================================================+
echo   =  TUTTI I TASK SCHEDULATI SONO STATI RIMOSSI                 =
echo   +==============================================================+
echo.

pause
