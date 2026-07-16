@echo off
title Ispettore SPEACE - Stato Task Schedulati
color 0A

echo.
echo   +==============================================================+
echo   =  STATO TASK SCHEDULATI MANUTENZIONE SPEACE                   =
echo   +==============================================================+
echo.

echo --- Task Preventiva ---
for %%T in (Preventiva_5min Preventiva_15min Preventiva_1h Preventiva_6h Preventiva_24h) do (
    schtasks /Query /TN "IspettoreSPEACE\%%T" /FO LIST /V 2>nul | findstr /B "Status|TaskName|Next|Schedule|Last" 
    echo.
)

echo --- Task Correttiva ---
for %%T in (Correttiva_Diagnosi Correttiva_AutoRepair Correttiva_RapidScan) do (
    schtasks /Query /TN "IspettoreSPEACE\%%T" /FO LIST /V 2>nul | findstr /B "Status|TaskName|Next|Schedule|Last"
    echo.
)

echo.
echo Per dettagli completi: Task Scheduler > IspettoreSPEACE
echo.
pause
