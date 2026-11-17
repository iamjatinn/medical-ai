# Smoke-test several Gemini models against the running Docker stack.
#
# For each model it restarts the backend with GEMINI_MODELS=<model> (a one-model list) and checks
#   1. structured output: upload the sample report -> valid analysis JSON
#   2. tool calling:      "How far below normal is my vitamin D, in percent?"
#                         must call compute_deviation and answer 40
#   3. latency of both calls
# Results are printed and saved to evals/results/model_smoke.json.
#
# Usage (from the repo root, stack already built):
#   powershell -File evals\compare_models.ps1 gemini-2.5-flash gemini-3.5-flash
#   powershell -File evals\compare_models.ps1            # uses the default list

param([string[]]$Models)

if (-not $Models -or $Models.Count -eq 0) {
  $Models = @(
    "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.6-flash",
    "gemini-3.7-flash", "gemini-3.8-flash", "gemini-3-flash-preview",
    "gemini-flash-latest"
  )
}

$ErrorActionPreference = "Continue"
$base = "http://localhost:8000"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# Make sure docker is on PATH in fresh shells.
$env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")

$email = "models-$(Get-Date -Format 'HHmmss')@example.com"
$password = "model-test-password-1"
$sample = Join-Path $root "data\sample_reports\sample_medical_report.pdf"
$results = @()

function Wait-Backend {
  for ($i = 0; $i -lt 40; $i++) {
    try { Invoke-RestMethod "$base/" -TimeoutSec 3 | Out-Null; return $true } catch { Start-Sleep -Seconds 3 }
  }
  return $false
}

function Get-Token {
  # The signing key changes whenever the backend restarts, so log in again each time.
  $body = @{ username = $email; password = $password }
  try { return (Invoke-RestMethod -Uri "$base/auth/login" -Method Post -Body $body -ContentType "application/x-www-form-urlencoded").access_token }
  catch { return $null }
}

foreach ($model in $Models) {

  $row = [ordered]@{ model = $model; started = $false; structured_ok = $false; risk = ""; upload_s = $null;
                     tool_used = ""; answer_ok = $false; chat_s = $null; note = "" }

  $env:GEMINI_MODELS = $model
  docker compose up -d backend 2>&1 | Out-Null

  if (-not (Wait-Backend)) { $row.note = "backend did not start"; $results += [pscustomobject]$row; continue }
  $row.started = $true

  # first model: create the account; afterwards just log in
  $token = Get-Token
  if (-not $token) {
    try {
      $reg = Invoke-RestMethod -Uri "$base/auth/register" -Method Post -ContentType "application/json" `
             -Body (@{ email = $email; password = $password } | ConvertTo-Json)
      $token = $reg.access_token
    } catch { $row.note = "could not log in"; $results += [pscustomobject]$row; continue }
  }

  $auth = "Authorization: Bearer $token"

  # 1) structured output
  $sw = [Diagnostics.Stopwatch]::StartNew()
  $raw = curl.exe -s -m 170 -H $auth -F "file=@$sample;type=application/pdf" "$base/upload-report"
  $sw.Stop(); $row.upload_s = [math]::Round($sw.Elapsed.TotalSeconds, 1)

  try { $up = $raw | ConvertFrom-Json } catch { $up = $null }

  if ($up -and $up.result -and $up.result.analysis) {
    $row.structured_ok = $true
    $row.risk = $up.result.analysis.overall_risk
  } elseif ($up -and $up.result) {
    $row.note = ($up.result.ai_summary -replace "\s+", " ")
    if ($row.note.Length -gt 90) { $row.note = $row.note.Substring(0, 90) }
  } else { $row.note = "upload failed" }

  # 2) tool calling
  if ($up -and $up.result -and $up.result.report_id) {
    $sw.Restart()
    try {
      $chat = Invoke-RestMethod -Uri "$base/chat" -Method Post -ContentType "application/json" `
              -Headers @{ Authorization = "Bearer $token" } -TimeoutSec 170 `
              -Body (@{ report_id = $up.result.report_id; question = "How far below normal is my vitamin D, in percent?" } | ConvertTo-Json)
      $sw.Stop(); $row.chat_s = [math]::Round($sw.Elapsed.TotalSeconds, 1)
      $row.tool_used = ($chat.tools_used -join ",")
      $row.answer_ok = ($chat.answer -match "40")
    } catch { $row.note = ($row.note + " chat failed").Trim() }
  }

  $results += [pscustomobject]$row
  Start-Sleep -Seconds 5
}

# Put the stack back on the default model.
Remove-Item Env:GEMINI_MODELS -ErrorAction SilentlyContinue
docker compose up -d backend 2>&1 | Out-Null

$results | Format-Table model, started, structured_ok, risk, upload_s, tool_used, answer_ok, chat_s, note -AutoSize -Wrap | Out-String -Width 220

$outDir = Join-Path $root "evals\results"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
@{ date = (Get-Date).ToString("s"); results = $results } | ConvertTo-Json -Depth 5 |
  Set-Content -Encoding utf8 (Join-Path $outDir "model_smoke.json")
"Saved evals/results/model_smoke.json"
