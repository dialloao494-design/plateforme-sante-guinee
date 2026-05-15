# One-shot: print LAN URLs + reset QA database (pilot accounts only).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

& "$PSScriptRoot\print_lan_urls.ps1"

$candidates = @(
  "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
  "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
  "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
)
$Py = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Py) {
  Write-Error "Python not found."
}

Write-Host "Resetting QA data (appointments, messages, notifications, availabilities)..." -ForegroundColor Yellow
& $Py "$PSScriptRoot\reset_qa_lab.py"
Write-Host "Done. Start backend with -Lan, then frontend dev:lan." -ForegroundColor Green
