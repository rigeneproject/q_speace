@echo off
title Ispettore SPEACE - Registrazione Avvio Windows
color 0C

:: =====================================================
:: Registra l'Ispettore Manutentore Neurologico
:: Organismico di SPEACE nelle app di avvio di Windows
:: =====================================================

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"

echo.
echo   +==============================================================+
echo   =  ISPETTORE SPEACE - REGISTRAZIONE AVVIO WINDOWS              =
echo   =                                                               =
echo   =  Seleziona la modalita di avvio automatico:                  =
echo   =                                                               =
echo   =  1. Cloud - DeepSeek V4 Flash Free (default)                 =
echo   =  2. Locale - gemma4:12b via Ollama                           =
echo   =                                                               =
echo   +==============================================================+
echo.

set /p CHOICE="Seleziona (1 o 2, default 1): "

if "%CHOICE%"=="2" (
    set "MODE=local"
    echo Modalita locale selezionata.
) else (
    set "MODE=cloud"
    echo Modalita cloud selezionata.
)

echo.
echo Registrazione in corso...
echo.

powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%SCRIPT_DIR%register_startup.ps1" -Mode %MODE%

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRORE] Registrazione fallita.
    pause
    exit /b 1
)

echo.
echo Registrazione completata con successo.
pause
