# QA mobile — backend FastAPI on 0.0.0.0 (LAN). Run in dedicated terminal.
param([int]$Port = 8000)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Get-LanIPv4 {
  try {
    $u = New-Object System.Net.Sockets.UdpClient
    $u.Connect("8.8.8.8", 80)
    $ip = ($u.Client.LocalEndPoint).Address.ToString()
    $u.Close()
    if ($ip -and -not $ip.StartsWith("127.")) { return $ip }
  } catch {}
  return (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -match '^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)' } |
    Select-Object -First 1 -ExpandProperty IPAddress)
}

$listen = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listen) {
  $addr = $listen.LocalAddress
  $pidListen = $listen.OwningProcess
  if ($addr -eq "0.0.0.0") {
    Write-Host "[QA] Backend already listening on 0.0.0.0:$Port (pid $pidListen) - reusing." -ForegroundColor Green
    $lan = Get-LanIPv4
    Write-Host ""
    Write-Host "  Backend local: http://localhost:$Port"
    Write-Host "  Backend LAN:   http://${lan}:$Port"
    Write-Host ""
    exit 0
  }
  Write-Host "[QA] Port $Port in use on $addr (pid $pidListen) - not LAN-safe. Stop that terminal (Ctrl+C) then re-run this script." -ForegroundColor Red
  exit 1
}

$candidates = @(
  "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
  "$Root\venv\Scripts\python.exe"
)
$Py = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Py) { throw "Python not found." }

$env:ENABLE_LAN_DEV = "true"
$lan = Get-LanIPv4
if (-not $lan) { $lan = "YOUR_LAN_IP" }

Write-Host ""
Write-Host "========== QA BACKEND (LAN) ==========" -ForegroundColor Cyan
Write-Host "  Local: http://localhost:$Port"
Write-Host "  LAN:   http://${lan}:$Port"
Write-Host "  CORS:  ENABLE_LAN_DEV=true"
Write-Host "======================================"
Write-Host ""

& $Py -m uvicorn main:app --reload --host 0.0.0.0 --port $Port
