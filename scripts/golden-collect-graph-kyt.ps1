# FinSkalp — golden Collect → Graph → KYT path (API smoke).
# Client demo surface is :5173 only. Do NOT point clients at :8877.
param(
  [string]$ApiBase = "http://127.0.0.1:5001",
  [string]$Email = "analyst@example.com",
  [string]$Password = "FinSkalp2026!",
  [string]$Wallet = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
  [string]$Chain = "tron",
  [int]$Depth = 2,
  [int]$TimeoutSec = 120
)

$ErrorActionPreference = 'Stop'

Write-Host ""
Write-Host "=== FinSkalp Golden Path (Collect -> Graph -> KYT) ===" -ForegroundColor Cyan
Write-Host "API: $ApiBase"
Write-Host "Client UI: http://localhost:5173  (NOT :8877)"
Write-Host ""

function Invoke-Api {
  param(
    [string]$Method,
    [string]$Path,
    $Headers = @{},
    $Body = $null,
    [string]$ContentType = "application/json"
  )
  $uri = "$ApiBase$Path"
  $params = @{
    Method         = $Method
    Uri            = $uri
    TimeoutSec     = $TimeoutSec
    UseBasicParsing = $true
  }
  if ($Headers.Count) { $params.Headers = $Headers }
  if ($null -ne $Body) {
    if ($Body -is [string]) {
      $params.Body = $Body
    } else {
      $params.Body = ($Body | ConvertTo-Json -Depth 12 -Compress)
    }
    $params.ContentType = $ContentType
  }
  return Invoke-WebRequest @params
}

function Assert-Ok {
  param([object]$Response, [string]$Step)
  if ($Response.StatusCode -lt 200 -or $Response.StatusCode -ge 300) {
    throw "$Step failed: HTTP $($Response.StatusCode)"
  }
}

# 1) Health
Write-Host "[1/7] Health..." -ForegroundColor Yellow
try {
  $health = Invoke-Api -Method GET -Path "/health"
  Assert-Ok $health "Health"
  Write-Host "  OK: $($health.Content)" -ForegroundColor Green
} catch {
  Write-Host "  FAIL: API unreachable at $ApiBase/health" -ForegroundColor Red
  Write-Host "  Hint: start stack (docker compose -f docker-compose.dev.yml up -d) and seed demo user." -ForegroundColor DarkYellow
  exit 1
}

# 2) Login
Write-Host "[2/7] Login ($Email)..." -ForegroundColor Yellow
$tokenBody = "username=$([uri]::EscapeDataString($Email))&password=$([uri]::EscapeDataString($Password))"
try {
  $login = Invoke-WebRequest -Method POST -Uri "$ApiBase/api/auth/token" `
    -Body $tokenBody -ContentType "application/x-www-form-urlencoded" `
    -TimeoutSec $TimeoutSec -UseBasicParsing
  Assert-Ok $login "Login"
} catch {
  Write-Host "  FAIL: login — $($_.Exception.Message)" -ForegroundColor Red
  Write-Host "  Hint: docker exec flowsint-api-dev python -m app.bootstrap_demo_user" -ForegroundColor DarkYellow
  exit 1
}
$token = ($login.Content | ConvertFrom-Json).access_token
if (-not $token) { throw "No access_token in login response" }
$auth = @{ Authorization = "Bearer $token" }
Write-Host "  OK: token received" -ForegroundColor Green

# 3) Create case
$suffix = "{0}{1}" -f ((Get-Date).ToString("MMdd")), ((Get-Random -Maximum 9999).ToString("0000"))
$caseRef = "GP-$suffix"
Write-Host "[3/7] Create case $caseRef..." -ForegroundColor Yellow
$create = Invoke-Api -Method POST -Path "/api/compliance/cases" -Headers $auth -Body (@{
  case_ref = $caseRef
  investigation_id = $null
})
Assert-Ok $create "Create case"
$case = $create.Content | ConvertFrom-Json
$caseId = $case.id
if (-not $caseId) { throw "No case id returned" }
Write-Host "  OK: case_id=$caseId" -ForegroundColor Green

# 4) Scalpel collect
$collectors = @("onchain_explorer", "sanctions_watchlist", "abuse_scam_registry")
Write-Host "[4/7] Scalpel collect ($Wallet)..." -ForegroundColor Yellow
$collect = Invoke-Api -Method POST -Path "/api/platform/v2/scalpel/collect" -Headers $auth -Body (@{
  address = $Wallet
  chain = $Chain
  depth = $Depth
  collectors = $collectors
  usernames = @()
  counterparties = @()
  case_ref = $caseRef
})
Assert-Ok $collect "Scalpel collect"
$scalpel = $collect.Content | ConvertFrom-Json
$mentions = $scalpel.mentions_count
$graph = $scalpel.evidence_graph
Write-Host "  OK: mentions=$mentions nodes=$($graph.nodes.Count) edges=$($graph.edges.Count)" -ForegroundColor Green

# 5) Merge graph
Write-Host "[5/7] Merge graph..." -ForegroundColor Yellow
if (-not $graph -or -not $graph.nodes) {
  Write-Host "  WARN: empty evidence_graph — skipping merge" -ForegroundColor DarkYellow
} else {
  $merge = Invoke-Api -Method POST -Path "/api/compliance/cases/$caseId/graph/merge" -Headers $auth -Body (@{
    evidence_graph = $graph
    merge_mode = "replace"
  })
  Assert-Ok $merge "Merge graph"
  $merged = $merge.Content | ConvertFrom-Json
  Write-Host "  OK: nodes=$($merged.graph_stats.nodes) edges=$($merged.graph_stats.edges)" -ForegroundColor Green
}

# 6) KYT screen
Write-Host "[6/7] KYT screen..." -ForegroundColor Yellow
$screen = Invoke-Api -Method POST -Path "/api/compliance/wallets/screen" -Headers $auth -Body (@{
  address = $Wallet
  chain = $Chain
  limit = 50
})
Assert-Ok $screen "KYT screen"
$kyt = $screen.Content | ConvertFrom-Json
Write-Host "  OK: risk_score=$($kyt.risk_score) risk_level=$($kyt.risk_level)" -ForegroundColor Green

# 7) Verify persisted graph
Write-Host "[7/7] Verify graph GET..." -ForegroundColor Yellow
$getGraph = Invoke-Api -Method GET -Path "/api/compliance/cases/$caseId/graph" -Headers $auth
Assert-Ok $getGraph "Get graph"
$persisted = $getGraph.Content | ConvertFrom-Json
Write-Host "  OK: persisted nodes=$($persisted.nodes.Count) edges=$($persisted.edges.Count)" -ForegroundColor Green

Write-Host ""
Write-Host "=== GOLDEN PATH PASSED ===" -ForegroundColor Green
Write-Host "case_ref: $caseRef"
Write-Host "Investigation URL: http://localhost:5173/dashboard/fusion/investigation/$caseRef"
Write-Host ""
