@echo off

REM Live FinSkalp stand — http://localhost:8877
REM Требует combat mode + persistent storage.

cd /d "%~dp0..\.."

set COMPLIANCE_COMBAT_MODE=1
set FINSKALP_ENTITY_STORE=postgres
if not defined COMPLIANCE_DEMO_BIND_HOST set COMPLIANCE_DEMO_BIND_HOST=127.0.0.1

echo.
echo  Flowsint Compliance Live Stand
echo  ==============================
echo.
echo  Combat mode: COMPLIANCE_COMBAT_MODE=1
echo  Entity store: FINSKALP_ENTITY_STORE=postgres
echo.
if not defined TRONGRID_API_KEY echo  WARNING: TRONGRID_API_KEY is not set - TRON live collection will be limited.
if not defined DATABASE_URL echo  WARNING: DATABASE_URL is not set - persistent Postgres-backed KG may not initialize.
echo  Optional infra bootstrap from repo root: make infra-dev
echo  Start local Postgres/Redis/Neo4j first if needed.
echo.

REM Завершить предыдущий стенд на 8877
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8877 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }; Get-Process -Name 'flowsint-regulator-stand' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue; Start-Sleep -Seconds 1"

uv sync
uv run flowsint-regulator-stand
