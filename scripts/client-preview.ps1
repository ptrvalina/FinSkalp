# FinSkalp client preview — Vite dev + optional Cloudflare named tunnel.
# Client surface: http://localhost:5173 ONLY (do not share :8877).
param(
  [int]$Port = 5173
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host ""
Write-Host "FinSkalp client preview" -ForegroundColor Cyan
Write-Host "UI: http://localhost:$Port" -ForegroundColor Green
Write-Host "Login: analyst@example.com / FinSkalp2026!" -ForegroundColor DarkGray
Write-Host ""

if ($env:CF_TUNNEL_NAME) {
  Write-Host "Cloudflare tunnel: $env:CF_TUNNEL_NAME" -ForegroundColor Yellow
  Start-Process -FilePath "cloudflared" -ArgumentList "tunnel", "run", $env:CF_TUNNEL_NAME -NoNewWindow
}

Set-Location (Join-Path $Root "flowsint-app")
npm run dev -- --host 0.0.0.0 --port $Port
