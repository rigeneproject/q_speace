@echo off
chcp 65001 >nul
title LOOP IDO — Single scan
call C:\cellular_speace\.venv\Scripts\activate.bat
python -m loop.agentic_loop --once --verbose
pause
