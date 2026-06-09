# Full automated teleconsult validation (Docker + Jitsi + tunnels + API tests)
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:Path = "$env:ProgramFiles\Docker\Docker\resources\bin;$env:Path"
$LogDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$Report = Join-Path $LogDir "teleconsult_validation_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"

function Log($msg) {
  $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
  Write-Host $line
  Add-Content -Path $Report -Value $line
}

Log "=== TELECONSULT VALIDATION ==="

# Docker
try {
  $dv = docker version --format "{{.Server.Version}}" 2>&1
  Log "Docker OK: $dv"
} catch {
  Log "BLOCKER: Docker not running"
  exit 1
}

# Jitsi
$jitsiDir = Join-Path $Root "deploy\jitsi\docker-jitsi-meet"
if (-not (Test-Path $jitsiDir)) {
  Log "Cloning docker-jitsi-meet..."
  git clone --depth 1 https://github.com/jitsi/docker-jitsi-meet.git $jitsiDir
}
& "$Root\scripts\start_jitsi_dev.ps1" 2>&1 | ForEach-Object { Log $_ }

# Wait for 8443
$up = $false
for ($i = 0; $i -lt 60; $i++) {
  try {
    $c = New-Object Net.Sockets.TcpClient
    $c.Connect("127.0.0.1", 8443)
    $c.Close()
    $up = $true
    Log "Jitsi port 8443 UP"
    break
  } catch {
    Start-Sleep -Seconds 10
  }
}
if (-not $up) { Log "WARN: Jitsi 8443 not ready after 10 min" }

# API tests
$py = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
if (Test-Path $py) {
  & $py -m pytest tests/test_teleconsult_access.py -q 2>&1 | ForEach-Object { Log $_ }
  & $py "$Root\scripts\e2e_phase2_embedded_jitsi.py" 2>&1 | ForEach-Object { Log $_ }
}

Log "Report: $Report"
