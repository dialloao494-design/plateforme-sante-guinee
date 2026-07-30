# Quick LAN QA checks: health, CORS preflight, login.
param(
  [string]$LanIp = "",
  [int]$BackendPort = 8000,
  [int]$FrontendPort = 5173
)
$ErrorActionPreference = "Continue"
$ok = $true

if (-not $LanIp) {
  try {
    $u = New-Object System.Net.Sockets.UdpClient
    $u.Connect("8.8.8.8", 80)
    $LanIp = ($u.Client.LocalEndPoint).Address.ToString()
    $u.Close()
  } catch {}
}
if (-not $LanIp) {
  $LanIp = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -match '^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)' } |
    Select-Object -First 1 -ExpandProperty IPAddress)
}

$backendLocal = "http://127.0.0.1:$BackendPort"
$backendLan = "http://${LanIp}:$BackendPort"
$origin = "http://${LanIp}:$FrontendPort"

Write-Host "LAN IP: $LanIp"
Write-Host ""

function Test-Step($label, $scriptBlock) {
  try {
    & $scriptBlock
    Write-Host "[OK] $label" -ForegroundColor Green
    return $true
  } catch {
    Write-Host "[FAIL] $label - $($_.Exception.Message)" -ForegroundColor Red
    return $false
  }
}

$ok = (Test-Step "Backend health (local)" { $r = Invoke-RestMethod "$backendLocal/health" -TimeoutSec 5; if ($r.status -ne "ok") { throw "bad status" } }) -and $ok
$ok = (Test-Step "Backend health (LAN IP)" { $r = Invoke-RestMethod "$backendLan/health" -TimeoutSec 5; if ($r.status -ne "ok") { throw "bad status" } }) -and $ok

$ok = (Test-Step "CORS preflight (phone origin)" {
  $resp = Invoke-WebRequest -Uri "$backendLan/auth/login-json" -Method OPTIONS -Headers @{
    Origin = $origin
    "Access-Control-Request-Method" = "POST"
    "Access-Control-Request-Headers" = "content-type,authorization"
  } -TimeoutSec 5 -UseBasicParsing
  $acao = $resp.Headers["Access-Control-Allow-Origin"]
  if (-not $acao) { throw "missing Access-Control-Allow-Origin" }
}) -and $ok

$ok = (Test-Step "Login doctor (JSON)" {
  $body = '{"email":"dr.amu@example.com","password":"[REDACTED]"}'
  $login = Invoke-RestMethod -Uri "$backendLocal/auth/login-json" -Method POST -ContentType "application/json" -Body $body -TimeoutSec 8
  if (-not $login.access_token) { throw "no token" }
  $h = @{ Authorization = "Bearer $($login.access_token)" }
  $me = Invoke-RestMethod -Uri "$backendLocal/auth/me" -Headers $h -TimeoutSec 8
  if ($me.role -ne "doctor") { throw "expected doctor role" }
}) -and $ok

$ok = (Test-Step "Login patient (JSON)" {
  $body = '{"email":"test.patient@example.com","password":"[REDACTED]"}'
  $login = Invoke-RestMethod -Uri "$backendLocal/auth/login-json" -Method POST -ContentType "application/json" -Body $body -TimeoutSec 8
  if (-not $login.access_token) { throw "no token" }
}) -and $ok

$listenBAll = @(Get-NetTCPConnection -LocalPort $BackendPort -State Listen -ErrorAction SilentlyContinue)
$backendLanOk = $listenBAll | Where-Object { $_.LocalAddress -eq "0.0.0.0" }
if ($backendLanOk) {
  Write-Host "[OK] Backend bound to 0.0.0.0 (phone can reach)" -ForegroundColor Green
} else {
  $addrs = ($listenBAll | ForEach-Object { $_.LocalAddress }) -join ", "
  Write-Host "[FAIL] Backend not on 0.0.0.0 (seen: $addrs). Run .\scripts\qa_start_backend.ps1" -ForegroundColor Red
  $ok = $false
}

$listenF = Get-NetTCPConnection -LocalPort $FrontendPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listenF.LocalAddress -eq "0.0.0.0") {
  Write-Host "[OK] Frontend bound to 0.0.0.0 (phone can reach)" -ForegroundColor Green
} else {
  Write-Host "[WARN] Frontend on $($listenF.LocalAddress)" -ForegroundColor Yellow
}

Write-Host ""
if ($ok) { Write-Host "All critical checks passed." -ForegroundColor Green; exit 0 }
Write-Host "Some checks failed - fix before phone QA." -ForegroundColor Red
exit 1
