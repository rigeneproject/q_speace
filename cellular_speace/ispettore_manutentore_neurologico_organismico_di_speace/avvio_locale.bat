@echo off
title ISPETTORE MANUTENTORE NEUROLOGICO ORGANISMICO DI SPEACE - LOCALE [gemma4:12b]
color 0B
setlocal enabledelayedexpansion

set "AGENT_DIR=%~dp0"
set "PROJECT_ROOT=C:\cellular_speace"
set "LOG_DIR=%PROJECT_ROOT%\data\logs\ispettore"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

set "LOG_FILE=%LOG_DIR%\ispettore_locale_%DATE:~-4,4%%DATE:~-7,2%%DATE:~-10,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%.log"
set "LOG_FILE=%LOG_FILE: =0%"

echo [%DATE% %TIME%] ============================================ >> "%LOG_FILE%"
echo [%DATE% %TIME%] AVVIO ISPETTORE - MODALITA LOCALE >> "%LOG_FILE%"
echo [%DATE% %TIME%] Modello: gemma4:12b via Ollama >> "%LOG_FILE%"
echo [%DATE% %TIME%] ============================================ >> "%LOG_FILE%"

cd /d "%PROJECT_ROOT%"

:AVVIO

echo.
echo   +==============================================================+
echo   =  ISPETTORE MANUTENTORE NEUROLOGICO ORGANISMICO DI SPEACE     =
echo   =  MODALITA: LOCALE  ^|  gemma4:12b via Ollama                  =
echo   =  WORKSPACE: C:\cellular_speace                               =
echo   =                                                               =
echo   =  Avvio loop continuo di ispezione, diagnosi e ottimizzazione =
echo   =  Funzionamento OFFLINE (senza connessione internet)          =
echo   =  CTRL+C per arrestare. Riavvio automatico.                   =
echo   +==============================================================+
echo.

echo [%DATE% %TIME%] Verifica Ollama... >> "%LOG_FILE%"

:: Verifica che Ollama sia in esecuzione
curl -s http://localhost:11434/api/tags >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [AVVISO] Ollama non in esecuzione su localhost:11434.
    echo [%DATE% %TIME%] Ollama non in esecuzione, tentativo avvio... >> "%LOG_FILE%"
    start "" "C:\Users\Utente\AppData\Local\Programs\Ollama\ollama.exe" serve
    timeout /t 8 /nobreak >nul
)

echo [%DATE% %TIME%] Avvio ispettore_agent.py (locale)... >> "%LOG_FILE%"

"C:\Python314\python.exe" "%AGENT_DIR%ispettore_agent.py" --mode local --scan-interval 120

set EXIT_CODE=%ERRORLEVEL%
echo [%DATE% %TIME%] Processo terminato con codice: %EXIT_CODE% >> "%LOG_FILE%"

echo.
echo   +==============================================================+
echo   =  RIAVVIO IN CORSO (5s)... Chiudi finestra per fermare       =
echo   +==============================================================+
timeout /t 5 /nobreak >nul
goto AVVIO

