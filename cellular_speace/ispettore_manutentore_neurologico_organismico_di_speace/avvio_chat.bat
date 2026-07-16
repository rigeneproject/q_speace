@echo off
title ISPETTORE - CHAT CON ROBERTO [OpenCode TUI]
color 0E
setlocal enabledelayedexpansion

set "AGENT_DIR=%~dp0"
set "PROJECT_ROOT=C:\cellular_speace"

:SCELTA

echo.
echo   +==============================================================+
echo   =  ISPETTORE MANUTENTORE NEUROLOGICO ORGANISMICO DI SPEACE     =
echo   =  MODALITA: CHAT INTERATTIVA  ^|  UTENTE: Roberto (Owner)     =
echo   =                                                               =
echo   =  Avvio OpenCode TUI per dialogare con l'AI sullo stato       =
echo   =  di SPEACE, task attivi, obiettivi, ottimizzazioni.          =
echo   =                                                               =
echo   =  Seleziona il modello:                                       =
echo   =    1. Cloud - DeepSeek V4 Flash Free                         =
echo   =    2. Locale - gemma4:12b (Ollama)                           =
echo   =                                                               =
echo   +==============================================================+
echo.

set /p CHOICE=Seleziona (1 o 2): 

if "%CHOICE%"=="2" (
    set "MODE=local"
    echo.
    echo Modello locale selezionato: gemma4:12b
) else (
    set "MODE=cloud"
    echo.
    echo Modello cloud selezionato: DeepSeek V4 Flash Free
)

echo.
echo WORKSPACE: %PROJECT_ROOT%
echo.
echo Dopo l'avvio, puoi dialogare con l'AI. Esempi:
echo   - "Analizza lo stato corrente di SPEACE"
echo   - "Esegui una scansione completa dei componenti"
echo   - "Quali sono gli errori recenti nei log?"
echo   - "Ottimizza la configurazione del cervello"
echo.
echo Premi un tasto per avviare opencode...
pause >nul

where opencode >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRORE] opencode non trovato nel PATH.
    echo Verifica che sia installato: npm install -g opencode
    echo.
    pause
    goto :EOF
)

cd /d "%PROJECT_ROOT%"

echo.
echo [AVVIO] Sto avviando opencode... Ctrl+C per uscire.
echo.

"C:\Python314\python.exe" "%AGENT_DIR%ispettore_agent.py" --chat --mode %MODE%

set "EXIT_CODE=%ERRORLEVEL%"

if %EXIT_CODE% NEQ 0 (
    echo.
    echo [AVVISO] opencode terminato con codice: %EXIT_CODE%
)

echo.
echo Sessione chat terminata.
pause