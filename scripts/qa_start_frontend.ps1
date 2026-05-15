# QA mobile — Vite on 0.0.0.0. Run in dedicated terminal.
param([int]$Port = 5173)
$ErrorActionPreference = "Stop"

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
$lan = Get-LanIPv4
if (-not $lan) { $lan = "YOUR_LAN_IP" }

if ($listen) {
  $addr = $listen.LocalAddress
  Write-Host "[QA] Frontend already listening on ${addr}:$Port (pid $($listen.OwningProcess)) - reusing." -ForegroundColor Green
  Write-Host ""
  Write-Host "  Frontend local: http://localhost:$Port"
  Write-Host "  Frontend LAN:   http://${lan}:$Port"
  Write-Host ""
  exit 0
}

$FrontRoot = Join-Path (Split-Path -Parent $PSScriptRoot) "frontend-sante\frontend"
Set-Location $FrontRoot

Write-Host ""
Write-Host "========== QA FRONTEND (LAN) ==========" -ForegroundColor Cyan
Write-Host "  Local: http://localhost:$Port"
Write-Host "  LAN:   http://${lan}:$Port"
Write-Host "======================================="
Write-Host ""

npm run dev:lan
