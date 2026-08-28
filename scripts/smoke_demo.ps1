# End-to-end API smoke (no browser). From repo root:
#   powershell -File scripts/smoke_demo.ps1
# Requires auth/health/ai/BFF up. Uses judge+timestamp@example.com

$ErrorActionPreference = "Stop"
$base = "http://127.0.0.1:8000"
$email = "judge$(Get-Date -Format 'HHmmss')@example.com"
$password = "password123"

Write-Host "Register $email ..."
$reg = Invoke-RestMethod -Method POST -Uri "$base/auth/register" `
  -ContentType "application/json" `
  -Body (@{ email = $email; password = $password; locale_preference = "en-IN" } | ConvertTo-Json)
$token = $reg.access_token
$headers = @{ Authorization = "Bearer $token" }

Write-Host "Seed LIPID demo ..."
$seed = Invoke-RestMethod -Method POST -Uri "$base/reports/demo/seed?panel=lipid" -Headers $headers
Write-Host "  report_id=$($seed.id) values=$($seed.values.Count)"

Write-Host "Timeline LDL anomaly ..."
$anom = Invoke-RestMethod -Method GET -Uri "$base/timeline/LDL%20Cholesterol/anomaly" -Headers $headers
Write-Host "  trend=$($anom.trend) is_anomaly=$($anom.is_anomaly) method=$($anom.method)"

Write-Host "Q&A guideline ..."
$qa1 = Invoke-RestMethod -Method POST -Uri "$base/qa" -Headers $headers `
  -ContentType "application/json" `
  -Body (@{ question = "What does high LDL mean?"; locale = "en-IN" } | ConvertTo-Json)
Write-Host "  citations=$($qa1.citations.Count) safety=$($qa1.safety_triggered)"

Write-Host "Q&A personal ..."
$qa2 = Invoke-RestMethod -Method POST -Uri "$base/qa" -Headers $headers `
  -ContentType "application/json" `
  -Body (@{ question = "What was my LDL?"; locale = "en-IN" } | ConvertTo-Json)
Write-Host "  answer snippet: $($qa2.answer.Substring(0, [Math]::Min(120, $qa2.answer.Length)))..."

Write-Host "Safety ..."
$qa3 = Invoke-RestMethod -Method POST -Uri "$base/qa" -Headers $headers `
  -ContentType "application/json" `
  -Body (@{ question = "I have chest pain and trouble breathing"; locale = "en-IN" } | ConvertTo-Json)
if (-not $qa3.safety_triggered) { throw "Safety layer did not trigger" }
Write-Host "  safety_triggered=True"

Write-Host "`nSMOKE PASSED" -ForegroundColor Green
