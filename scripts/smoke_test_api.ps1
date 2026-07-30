# Smoke-test critical API routes (requires backend running).
# Usage: .\scripts\smoke_test_api.ps1
#        .\scripts\smoke_test_api.ps1 -BaseUrl "http://127.0.0.1:8080"
param(
  [string]$BaseUrl = "http://127.0.0.1:8000"
)
$ErrorActionPreference = "Stop"
$Base = $BaseUrl.TrimEnd('/')

function Invoke-Json {
  param([string]$Method, [string]$Path, $Body = $null, [hashtable]$Headers = @{})
  $uri = "$Base$Path"
  $params = @{ Uri = $uri; Method = $Method; Headers = $Headers }
  if ($Body -ne $null) {
    $params["Body"] = ($Body | ConvertTo-Json -Compress)
    $params["ContentType"] = "application/json"
  }
  return Invoke-RestMethod @params
}

Write-Host "GET /health"
$h = Invoke-Json GET "/health"
if ($h.status -ne "ok") { throw "health check failed" }

$email = "smoke.$([guid]::NewGuid().ToString('n').Substring(0,12))@example.com"
$password = "SmokeTest1"
Write-Host "POST /auth/register $email"
$reg = Invoke-Json POST "/auth/register" @{ email = $email; password = $password; role = "patient" }
if (-not $reg.id) { throw "register failed" }

Write-Host "POST /auth/login-json"
$login = Invoke-Json POST "/auth/login-json" @{ email = $email; password = $password }
if (-not $login.access_token) { throw "login failed" }
$tok = $login.access_token
$auth = @{ Authorization = "Bearer $tok" }

Write-Host "GET /auth/me"
$me = Invoke-Json GET "/auth/me" -Headers $auth
if ($me.email -ne $email) { throw "/auth/me mismatch" }

Write-Host "GET /appointments/"
$apts = Invoke-Json GET "/appointments/" -Headers $auth
if ($apts -isnot [System.Array]) { throw "appointments response not a list" }

Write-Host "GET /doctors/"
$docs = Invoke-Json GET "/doctors/" -Headers $auth
if ($docs -isnot [System.Array]) { throw "doctors response not a list" }

Write-Host "GET /teleconsultation/sessions"
$sess = Invoke-Json GET "/teleconsultation/sessions" -Headers $auth
if ($null -eq $sess.sessions) { throw "teleconsultation sessions missing" }

Write-Host "GET /doctor/appointments (expect 403 for patient user)"
try {
  Invoke-WebRequest -Uri "$Base/doctor/appointments" -Headers $auth -UseBasicParsing | Out-Null
  throw "expected failure for patient on doctor appointments"
} catch {
  $resp = $_.Exception.Response
  if (-not $resp) { throw $_ }
  $code = [int]$resp.StatusCode
  if ($code -ne 403) {
    throw "unexpected status $code for /doctor/appointments as patient"
  }
}

Write-Host "SMOKE OK"

Write-Host "Case-insensitive login-json (email casing)"
$caseBody = '{"email":"DR.AMU@EXAMPLE.COM","password":"[REDACTED]"}'
$caseLogin = Invoke-RestMethod -Uri "$Base/auth/login-json" -Method Post -Body $caseBody -ContentType "application/json"
if (-not $caseLogin.access_token) { throw "case-insensitive login failed" }

Write-Host "Optional: doctor dashboard (demo account dr.amu@example.com)"
try {
  $docLogin = Invoke-Json POST "/auth/login-json" @{ email = "dr.amu@example.com"; password = "[REDACTED]" }
  $dTok = $docLogin.access_token
  $dAuth = @{ Authorization = "Bearer $dTok" }
  $docApts = Invoke-Json GET "/doctor/appointments" -Headers $dAuth
  if ($docApts -isnot [System.Array]) { throw "doctor appointments not a list" }
  Write-Host "Doctor appointments count:" $docApts.Count
} catch {
  Write-Warning "Doctor demo login skipped or failed: $_"
}
