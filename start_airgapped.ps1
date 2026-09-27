# ASTRAEA — Air-Gapped Offline Dissemination System Launcher
# Launches both FastAPI Backend and Vite Frontend on Local Loopback (127.0.0.1)

$ErrorActionPreference = "Stop"
$rootDir = $PSScriptRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "      PROJECT ASTRAEA — AIR-GAPPED OFFLINE MODE          " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "SQLite Database: $rootDir\astraea_ledger.db" -ForegroundColor Gray
Write-Host "3-Node DLT Cluster: $rootDir\data\cluster\" -ForegroundColor Gray
Write-Host ""

# Start Backend on Port 8000
Write-Host "[1/2] Launching Backend API server (127.0.0.1:8000)..." -ForegroundColor Yellow
$backendJob = Start-Process -FilePath "python" -ArgumentList "-m uvicorn backend.main:app --host 127.0.0.1 --port 8000" -WorkingDirectory $rootDir -PassThru

Start-Sleep -Seconds 2

# Start Frontend on Port 5173
Write-Host "[2/2] Launching React Frontend (127.0.0.1:5173)..." -ForegroundColor Yellow
$frontendJob = Start-Process -FilePath "npm.cmd" -ArgumentList "run dev -- --host 127.0.0.1" -WorkingDirectory "$rootDir\astraea-frontend" -PassThru

Write-Host ""
Write-Host ">> ASTRAEA Console: http://127.0.0.1:5173" -ForegroundColor Green
Write-Host ">> Backend OpenAPI: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C or close this terminal to stop both servers." -ForegroundColor Gray

try {
    Wait-Process -Id $backendJob.Id, $frontendJob.Id
} finally {
    Write-Host "Shutting down servers..." -ForegroundColor Gray
    Stop-Process -Id $backendJob.Id -ErrorAction SilentlyContinue
    Stop-Process -Id $frontendJob.Id -ErrorAction SilentlyContinue
}
