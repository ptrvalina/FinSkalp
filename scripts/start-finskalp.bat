@echo off
setlocal EnableDelayedExpansion

REM FinSkalp — local dev stack (Docker + Vite :5173)
cd /d "%~dp0.."
set ROOT=%CD%

echo.
echo  FinSkalp — dev stack
echo  ====================
echo  Root: %ROOT%
echo  Client UI: http://localhost:5173  (NOT :8877 for demos)
echo.

if not exist "%ROOT%\.env" (
  if exist "%ROOT%\.env.example" copy /Y "%ROOT%\.env.example" "%ROOT%\.env" >nul
)

docker info >nul 2>&1
if errorlevel 1 (
  echo  [!!] Docker Desktop is not running. Start it, then re-run this script.
  exit /b 1
)

echo  [+] docker compose up...
docker compose -f docker-compose.dev.yml up -d --build
if errorlevel 1 exit /b 1

echo.
echo  Done. Open http://localhost:5173/login
echo  Demo: analyst@example.com / FinSkalp2026!
echo.
pause
