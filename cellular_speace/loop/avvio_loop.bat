@echo off
chcp 65001 >nul
title LOOP IDO — SPEACE Agentic Loop
call C:\cellular_speace\.venv\Scripts\activate.bat
python -m loop.agentic_loop --interval 300 --verbose
pause
