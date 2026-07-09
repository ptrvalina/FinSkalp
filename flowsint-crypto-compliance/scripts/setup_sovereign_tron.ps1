# FinSkalp — bootstrap sovereign java-tron FullNode (Windows PowerShell)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "==> FinSkalp sovereign TRON setup"
Write-Host "    See docker/tron-fullnode/README.md for snapshot download."

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker required"
}

$DataDir = if ($env:FINSKALP_TRON_DATA) { $env:FINSKALP_TRON_DATA } else { ".\tron-data\output-directory" }
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null

Write-Host "==> Starting java-tron compose"
docker compose -f docker/docker-compose.tron-fullnode.yml up -d

Write-Host "==> Waiting for HTTP API (max 120s)..."
$ok = $false
for ($i = 0; $i -lt 24; $i++) {
    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:8090/wallet/getnowblock" -Method Post -Body "{}" -ContentType "application/json" -TimeoutSec 5 | Out-Null
        $ok = $true
        Write-Host "    Node HTTP is up."
        break
    } catch {
        Start-Sleep -Seconds 5
    }
}
if (-not $ok) { Write-Warning "Node not reachable yet — sync may still be in progress." }

Write-Host "==> Health + snapshot gate"
try {
    uv run python scripts/tron_node_health.py
} catch {
    python scripts/tron_node_health.py
}

Write-Host ""
Write-Host "Set in .env:"
Write-Host "  FINSKALP_TRON_PROVIDER=failover"
Write-Host "  FINSKALP_TRON_SOVEREIGN_URL=http://127.0.0.1:8090"
Write-Host "Verify: curl http://localhost:8877/api/infra/tron-node"
