# Print URLs for phone + laptop LAN testing (same Wi-Fi).
param(
  [int]$FrontendPort = 5173,
  [int]$BackendPort = 8000
)
$ErrorActionPreference = "Stop"

function Get-LanIPv4 {
  $ip = $null
  try {
    $udp = New-Object System.Net.Sockets.UdpClient
    $udp.Connect("8.8.8.8", 80)
    $ip = ($udp.Client.LocalEndPoint).Address.ToString()
    $udp.Close()
  } catch {}
  if (-not $ip) {
    $ip = (
      Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
      Where-Object {
        $_.IPAddress -match '^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)' -and
        $_.PrefixOrigin -ne 'WellKnown'
      } |
      Select-Object -First 1 -ExpandProperty IPAddress
    )
  }
  if (-not $ip) { $ip = "YOUR_LAN_IP" }
  return $ip
}

$lan = Get-LanIPv4
Write-Host ""
Write-Host "========== LAN QA - Plateforme Sante Guinee ==========" -ForegroundColor Cyan
Write-Host ""
Write-Host "Laptop - doctor dashboard:" -ForegroundColor Yellow
Write-Host "  Frontend: http://localhost:$FrontendPort"
Write-Host "  Backend:  http://localhost:$BackendPort"
Write-Host ""
Write-Host "Phone - patient app (same Wi-Fi):" -ForegroundColor Green
Write-Host "  Frontend: http://${lan}:$FrontendPort"
Write-Host "  Backend:  http://${lan}:$BackendPort  (auto-detected when using LAN frontend URL)"
Write-Host ""
Write-Host "Pilot accounts:" -ForegroundColor White
Write-Host "  Doctor:  dr.amu@example.com / Doctor123!"
Write-Host "  Patient: test.patient@example.com / Patient123!"
Write-Host ""
Write-Host "Start servers:" -ForegroundColor White
Write-Host "  Terminal 1: .\scripts\run_local_backend.ps1 -Port $BackendPort -Lan"
Write-Host "  Terminal 2: cd frontend-sante\frontend; npm run dev:lan"
Write-Host "  Reset data: python scripts\reset_qa_lab.py"
Write-Host ""
Write-Host "Windows Firewall: .\scripts\open_firewall_lan.ps1 (Admin) if the phone cannot connect."
Write-Host ""
Write-Host "Patient on Orange 4G / different network? Use TUNNEL mode:"
Write-Host "  .\scripts\start_remote_test.ps1 -Mode tunnel"
Write-Host "  See deploy\REAL_NETWORK_TEST.md"
Write-Host "======================================================"
Write-Host ""
