@echo off
title SPEACE Gateway
cd /d "%~dp0\.."
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "scripts\speace_gateway.ps1" -Mode live
