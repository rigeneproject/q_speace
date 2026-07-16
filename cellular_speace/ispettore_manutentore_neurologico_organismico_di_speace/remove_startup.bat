@echo off
title Ispettore SPEACE - Rimozione Avvio Windows
color 0C

:: =====================================================
:: Rimuove l'Ispettore Manutentore Neurologico
:: Organismico di SPEACE dalle app di avvio di Windows
:: =====================================================

set "SCRIPT_DIR=%~dp0"

echo.
echo   +==============================================================+
echo   =  ISPETTORE SPEACE - RIMOZIONE AVVIO WINDOWS                  =
echo   =                                                               =
echo   =  Rimozione in corso...                                       =
echo   +==============================================================+
echo.

powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%SCRIPT_DIR%register_startup.ps1" -Remove

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRORE] Rimozione fallita.
    pause
    exit /b 1
)

echo.
echo Rimozione completata con successo.
pause
