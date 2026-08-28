# MediVault demo preflight — run before judges arrive.
# Usage (from repo root):  powershell -File scripts/demo_preflight.ps1
# Optional port overrides when defaults conflict:
#   $env:MEDIVAULT_AUTH_PORT=8011; $env:MEDIVAULT_WEB_PORT=3002

$ErrorActionPreference = "Continue"
$failed = 0

$authPort = if ($env:MEDIVAULT_AUTH_PORT) { $env:MEDIVAULT_AUTH_PORT } else { 8001 }
$healthPort = if ($env:MEDIVAULT_HEALTH_PORT) { $env:MEDIVAULT_HEALTH_PORT } else { 8002 }
$aiPort = if ($env:MEDIVAULT_AI_PORT) { $env:MEDIVAULT_AI_PORT } else { 8003 }
$bffPort = if ($env:MEDIVAULT_BFF_PORT) { $env:MEDIVAULT_BFF_PORT } else { 8000 }
$webPort = if ($env:MEDIVAULT_WEB_PORT) { $env:MEDIVAULT_WEB_PORT } else { 3000 }

function Check-Url($name, $url, $expectKb = $false) {
  try {
    $r = Invoke-RestMethod -Uri $url -TimeoutSec 5
    if ($expectKb) {
      if (-not $r.kb_ready -or [int]$r.kb_chunks -lt 1) {
        Write-Host "[FAIL] $name - kb_ready=$($r.kb_ready) kb_chunks=$($r.kb_chunks)" -ForegroundColor Red
        $script:failed++
        return
      }
      Write-Host "[OK]   $name - kb_chunks=$($r.kb_chunks) embedder=$($r.kb_embedder)" -ForegroundColor Green
      return
    }
    Write-Host "[OK]   $name - $($r.status) ($($r.service))" -ForegroundColor Green
  } catch {
    Write-Host "[FAIL] $name - $url unreachable" -ForegroundColor Red
    $script:failed++
  }
}

Write-Host "`nMediVault preflight`n" -ForegroundColor Cyan

if (-not (Test-Path ".env")) {
  Write-Host "[FAIL] .env missing - copy .env.example to .env" -ForegroundColor Red
  $failed++
} else {
  Write-Host "[OK]   .env present" -ForegroundColor Green
}

Check-Url "postgres (indirect)" "http://127.0.0.1:$authPort/health"
Check-Url "auth-service" "http://127.0.0.1:$authPort/health"
Check-Url "health-service" "http://127.0.0.1:$healthPort/health"
Check-Url "ai-service + KB" "http://127.0.0.1:$aiPort/health" $true
Check-Url "api-gateway" "http://127.0.0.1:$bffPort/health"

try {
  $web = Invoke-WebRequest -Uri "http://127.0.0.1:$webPort" -TimeoutSec 5 -UseBasicParsing
  if ($web.StatusCode -ge 200 -and $web.StatusCode -lt 500) {
    Write-Host "[OK]   web :$webPort" -ForegroundColor Green
  } else {
    Write-Host "[FAIL] web :$webPort status $($web.StatusCode)" -ForegroundColor Red
    $failed++
  }
} catch {
  Write-Host "[FAIL] web :$webPort unreachable (npm run dev?)" -ForegroundColor Red
  $failed++
}

Write-Host ""
if ($failed -gt 0) {
  Write-Host "PREFLIGHT FAILED ($failed). Fix before demo." -ForegroundColor Red
  exit 1
}
Write-Host "PREFLIGHT PASSED - run DEMO_SCRIPT.md" -ForegroundColor Green
exit 0
