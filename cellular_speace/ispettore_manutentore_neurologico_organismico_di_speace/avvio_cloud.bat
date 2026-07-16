@echo off
title ISPETTORE MANUTENTORE NEUROLOGICO ORGANISMICO DI SPEACE - CLOUD [DeepSeek V4 Flash Free]
color 0A
setlocal enabledelayedexpansion

set "AGENT_DIR=%~dp0"
set "PROJECT_ROOT=C:\cellular_speace"
set "LOG_DIR=%PROJECT_ROOT%\data\logs\ispettore"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

set "LOG_FILE=%LOG_DIR%\ispettore_cloud_%DATE:~-4,4%%DATE:~-7,2%%DATE:~-10,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%.log"
set "LOG_FILE=%LOG_FILE: =0%"

echo [%DATE% %TIME%] ============================================ >> "%LOG_FILE%"
echo [%DATE% %TIME%] AVVIO ISPETTORE - MODALITA CLOUD >> "%LOG_FILE%"
echo [%DATE% %TIME%] Modello: DeepSeek V4 Flash Free via OpenCode Zen >> "%LOG_FILE%"
echo [%DATE% %TIME%] ============================================ >> "%LOG_FILE%"

cd /d "%PROJECT_ROOT%"

if "%OPENCODE_API_KEY%"=="" (
    echo [ERRORE] Variabile d'ambiente OPENCODE_API_KEY non impostata.
    echo Impostala prima di avviare la modalita cloud, oppure usa avvio_locale.bat.
    echo [%DATE% %TIME%] ERRORE: OPENCODE_API_KEY mancante >> "%LOG_FILE%"
    pause
    exit /b 1
)

:AVVIO

echo.
echo   +==============================================================+
echo   =  ISPETTORE MANUTENTORE NEUROLOGICO ORGANISMICO DI SPEACE     =
echo   =  MODALITA: CLOUD  ^|  DeepSeek V4 Flash Free via OpenCode    =
echo   =  WORKSPACE: C:\cellular_speace                               =
echo   =                                                               =
echo   =  Avvio loop continuo di ispezione, diagnosi e ottimizzazione =
echo   =  CTRL+C per arrestare. Riavvio automatico.                   =
echo   +==============================================================+
echo.

echo [%DATE% %TIME%] Avvio ispettore_agent.py... >> "%LOG_FILE%"

"C:\Python314\python.exe" "%AGENT_DIR%ispettore_agent.py" --mode cloud --use-llm --scan-interval 120

set EXIT_CODE=%ERRORLEVEL%
echo [%DATE% %TIME%] Processo terminato con codice: %EXIT_CODE% >> "%LOG_FILE%"

echo.
echo   +==============================================================+
echo   =  RIAVVIO IN CORSO (5s)... Chiudi finestra per fermare       =
echo   +==============================================================+
timeout /t 5 /nobreak >nul
goto AVVIO

