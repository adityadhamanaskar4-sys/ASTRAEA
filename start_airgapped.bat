@echo off
title ASTRAEA - Offline Air-Gapped Mode
echo ==========================================================
echo       PROJECT ASTRAEA - AIR-GAPPED OFFLINE MODE          
echo ==========================================================
echo Starting Backend (127.0.0.1:8000)...
start "ASTRAEA Backend" python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

echo Starting Frontend (127.0.0.1:5173)...
cd astraea-frontend
start "ASTRAEA Frontend" npm run dev -- --host 127.0.0.1

echo.
echo Servers started in independent airgapped terminals.
echo Frontend: http://127.0.0.1:5173
echo Backend:  http://127.0.0.1:8000
echo ==========================================================
pause
