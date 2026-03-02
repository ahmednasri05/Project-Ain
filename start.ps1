# Project Ain — Development Launcher
# Opens two separate PowerShell windows:
#   Window 1: FastAPI backend  (uvicorn, port 8000)
#   Window 2: React frontend   (Vite dev server, port 5173)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

# Backend window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "
  Set-Location '$root'
  Write-Host '==================================================' -ForegroundColor Cyan
  Write-Host '  PROJECT AIN - FastAPI Backend (port 8000)' -ForegroundColor Cyan
  Write-Host '==================================================' -ForegroundColor Cyan
  uvicorn app:crimeapp --reload --port 8000
"

# Frontend window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "
  Set-Location '$root\frontend'
  Write-Host '==================================================' -ForegroundColor Green
  Write-Host '  PROJECT AIN - React Frontend (port 3000)' -ForegroundColor Green
  Write-Host '==================================================' -ForegroundColor Green
  npm run dev
"

Write-Host ""
Write-Host "Both servers are starting in separate windows." -ForegroundColor White
Write-Host ""
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor Cyan
  Write-Host "  Frontend: http://127.0.0.1:3000" -ForegroundColor Green
Write-Host "  API docs: http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host ""
