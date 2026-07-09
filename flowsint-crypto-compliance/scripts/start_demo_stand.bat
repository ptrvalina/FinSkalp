@echo off

REM Демо-стенд FinSkalp — http://localhost:8877
REM По умолчанию — offline dev без Postgres (COMPLIANCE_COMBAT_MODE=0, FINSKALP_ENTITY_STORE=memory).
REM Боевой режим (live on-chain, Postgres для entity_labels): перед запуском задайте:
REM   set COMPLIANCE_COMBAT_MODE=1
REM   make infra-dev          (из корня репо — поднимает Postgres и прочую инфраструктуру)
REM   TRONGRID_API_KEY=...    (TronGrid live / failover)
REM   FINSKALP_TRON_PROVIDER=failover
REM   FINSKALP_TRON_SOVEREIGN_URL=http://127.0.0.1:8090
REM   docker compose -f flowsint-crypto-compliance/docker/docker-compose.tron-fullnode.yml up -d
REM   DATABASE_URL=postgresql://...
REM   FINSKALP_COMBAT_SEED_ADDRESS=T...
REM   FINSKALP_KYT_WATCHLIST=addr1,addr2  (опц., для KYT scan)
REM LAN: set COMPLIANCE_DEMO_BIND_HOST=0.0.0.0 && set COMPLIANCE_DEMO_ALLOW_ALL_CORS=1

cd /d "%~dp0..\.."

REM Offline defaults — не переопределяют уже заданные переменные окружения
if not defined FINSKALP_ENTITY_STORE set FINSKALP_ENTITY_STORE=memory
if not defined COMPLIANCE_COMBAT_MODE set COMPLIANCE_COMBAT_MODE=0
if not defined COMPLIANCE_DEMO_BIND_HOST set COMPLIANCE_DEMO_BIND_HOST=127.0.0.1

echo.

echo  Flowsint Compliance Demo Stand

echo  ==============================

echo  Остановите предыдущий стенд (Ctrl+C), если порт 8877 занят.

echo.

REM Завершить предыдущий стенд на 8877 (иначе uv sync не может обновить .exe)
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8877 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }; Get-Process -Name 'flowsint-regulator-stand' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue; Start-Sleep -Seconds 1"

uv sync

uv run flowsint-regulator-stand

