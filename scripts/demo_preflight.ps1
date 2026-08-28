# MediVault demo preflight — run before judges arrive.
# Usage (from repo root):  powershell -File scripts/demo_preflight.ps1

$ErrorActionPreference = "Continue"
$failed = 0

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

Check-Url "postgres (indirect)" "http://127.0.0.1:8001/health"
Check-Url "auth-service" "http://127.0.0.1:8001/health"
Check-Url "health-service" "http://127.0.0.1:8002/health"
Check-Url "ai-service + KB" "http://127.0.0.1:8003/health" $true
Check-Url "api-gateway" "http://127.0.0.1:8000/health"

try {
  $web = Invoke-WebRequest -Uri "http://127.0.0.1:3000" -TimeoutSec 5 -UseBasicParsing
  if ($web.StatusCode -ge 200 -and $web.StatusCode -lt 500) {
    Write-Host "[OK]   web :3000" -ForegroundColor Green
  } else {
    Write-Host "[FAIL] web :3000 status $($web.StatusCode)" -ForegroundColor Red
    $failed++
  }
} catch {
  Write-Host "[FAIL] web :3000 unreachable (npm run dev?)" -ForegroundColor Red
  $failed++
}

Write-Host ""
if ($failed -gt 0) {
  Write-Host "PREFLIGHT FAILED ($failed). Fix before demo." -ForegroundColor Red
  exit 1
}
Write-Host "PREFLIGHT PASSED - run DEMO_SCRIPT.md" -ForegroundColor Green
exit 0
