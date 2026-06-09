# Allow inbound LAN QA on Windows (run once as Administrator).
# Opens TCP 5173 (frontend) and 8000 (backend) on Private profile.
param(
  [int]$FrontendPort = 5173,
  [int]$BackendPort = 8000
)
$ErrorActionPreference = "Stop"

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  Write-Host "Re-run PowerShell as Administrator." -ForegroundColor Red
  exit 1
}

$rules = @(
  @{ Name = "PlateformeSante-Frontend-$FrontendPort"; Port = $FrontendPort },
  @{ Name = "PlateformeSante-Backend-$BackendPort"; Port = $BackendPort }
)

foreach ($r in $rules) {
  $existing = Get-NetFirewallRule -DisplayName $r.Name -ErrorAction SilentlyContinue
  if ($existing) {
    Write-Host "Rule exists: $($r.Name)" -ForegroundColor Yellow
    continue
  }
  New-NetFirewallRule -DisplayName $r.Name -Direction Inbound -Action Allow -Protocol TCP -LocalPort $r.Port -Profile Private | Out-Null
  Write-Host "Created: $($r.Name) (TCP $($r.Port), Private)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Done. Phone on same Wi-Fi can reach ports $FrontendPort and $BackendPort." -ForegroundColor Cyan
