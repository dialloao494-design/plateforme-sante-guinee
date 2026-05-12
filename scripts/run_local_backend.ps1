# Start FastAPI locally (Windows). Uses Python 3.12 if found in default install location.
# If port 8000 fails (WinError 10013 / permission), try: .\scripts\run_local_backend.ps1 -Port 8080
param(
  [int]$Port = 8000
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$candidates = @(
  "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
  "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
  "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
  "${env:ProgramFiles}\Python312\python.exe"
)
$Py = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Py) {
  Write-Error "Python not found. Install Python 3.11+ or set Py to your python.exe path."
}

Write-Host "Using: $Py"
Write-Host "API: http://127.0.0.1:$Port"
& $Py -m pip install -q -r requirements.txt
& $Py -m uvicorn main:app --reload --host 127.0.0.1 --port $Port
