$ErrorActionPreference = "Stop"
$key = $env:STITCH_API_KEY
if (-not $key) { $key = $env:GOOGLE_STITCH_API_KEY }
if (-not $key) { throw "Set STITCH_API_KEY or GOOGLE_STITCH_API_KEY before running this script." }
$proj = "4653582392684471060"
$mcp = "https://stitch.googleapis.com/mcp"
$outDir = "C:\Users\Aliaksei\flowsint\docs\stitch"
$tmpDir = "C:\Users\Aliaksei\flowsint\data\tmp_stitch"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$screens = @(
  @{slug="platform-modules"; id="efffcb9d42674c0fafb3521c4f060ce8"},
  @{slug="ic-console"; id="0ce8137af34e4c8796ab057d42ef827c"},
  @{slug="finskalp-product-map"; id="525b6c9cb96f40a3b89fd4bcb9e2817a"},
  @{slug="registries"; id="f28def9806124dbd9601097f5921bbbe"},
  @{slug="compliance-case-lifecycle"; id="739963f35a024c2791dddf0c7d3573be"},
  @{slug="flow-architect"; id="88b87a9f19ea46c0989c0a5a3a770728"},
  @{slug="secure-gateway"; id="477ede7f4d914f3e969ac901163c5955"},
  @{slug="osint-fusion-hub"; id="1d8ca124a63b40b5b5e6dc14ac822120"},
  @{slug="command-center"; id="c3dbb844aa6941f496c0c342861e378f"},
  @{slug="microservices-mesh"; id="2702aa51df964483a7f81f63ba36b3ed"},
  @{slug="regulatory-reporting"; id="b54d7aa8493649c292452887fb5b2184"},
  @{slug="vault"; id="90a7fe72ef554945bbdd200c84130d5b"},
  @{slug="forensic-toolset"; id="f4fe7230fa1348c69ca978b6b039f305"},
  @{slug="wallet-explorer"; id="202daa3cf1944ebfb810fb1f4611f346"},
  @{slug="command-center-v4"; id="a834a977dde74449a82b8d769df5b0c4"},
  @{slug="system-telemetry"; id="f8eb2d4da37b4858b401d11f8e91e79c"},
  @{slug="api-integration-status"; id="d0cb5702c96a467898021f064c9c46d1"},
  @{slug="user-profile"; id="4933a19ec28f43d4b1ad967be7e0b625"},
  @{slug="schema-architect"; id="d596451be089436da9ad02a7c94bde2f"},
  @{slug="knowledge-graph-explorer"; id="e20abf1655a04c9ea717acc2dc8abb2a"},
  @{slug="investigation-workspace"; id="87c385fd2e4842f08acff830a6bda7b9"},
  @{slug="investigation-briefing"; id="1d8acac256fa4f33909cad4f89882ac5"}
)

$ok = 0
foreach ($s in $screens) {
  $slug = $s.slug; $id = $s.id
  $reqFile = Join-Path $tmpDir "req_$slug.json"
  $respFile = Join-Path $tmpDir "resp_$slug.json"
  $req = @{
    jsonrpc = "2.0"; id = 2; method = "tools/call"
    params = @{ name = "get_screen"; arguments = @{
      name = "projects/$proj/screens/$id"; projectId = $proj; screenId = $id } }
  } | ConvertTo-Json -Depth 8 -Compress
  Set-Content -Path $reqFile -Value $req -Encoding UTF8 -NoNewline
  curl.exe -sS --max-time 60 -X POST $mcp -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -H "X-Goog-Api-Key: $key" -d "@$reqFile" -o $respFile
  try {
    $raw = Get-Content $respFile -Raw
    $obj = $raw | ConvertFrom-Json
    $sc = $obj.result.structuredContent
    $htmlUrl = $sc.htmlCode.downloadUrl
    $shotUrl = $sc.screenshot.downloadUrl
    if ($htmlUrl) { curl.exe -sSL --max-time 90 -H "X-Goog-Api-Key: $key" -o (Join-Path $outDir "$slug.html") $htmlUrl }
    if ($shotUrl) {
      if ($shotUrl -notmatch "=s") { $shotUrl = "$shotUrl=s1600" }
      curl.exe -sSL --max-time 90 -H "X-Goog-Api-Key: $key" -o (Join-Path $outDir "$slug.png") $shotUrl
    }
    $ok++
    Write-Host "OK $slug"
  } catch {
    Write-Host "FAIL $slug : $($_.Exception.Message)"
  }
}
Write-Host "DONE $ok / $($screens.Count)"
