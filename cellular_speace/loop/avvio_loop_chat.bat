@echo off
chcp 65001 >nul
title LOOP IDO — Chat mode
call C:\cellular_speace\.venv\Scripts\activate.bat
python -m loop.agentic_loop --chat --verbose
pause
