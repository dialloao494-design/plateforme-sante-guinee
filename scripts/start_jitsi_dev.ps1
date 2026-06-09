# Starts local Jitsi (no OAuth, no lobby) for embedded teleconsultation.
# Requires Docker Desktop.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$JitsiDir = Join-Path $Root "deploy\jitsi\docker-jitsi-meet"
$Patches = Join-Path $Root "deploy\jitsi\patches.env"
$env:Path = "$env:ProgramFiles\Docker\Docker\resources\bin;$env:Path"

function Test-DockerCli {
  docker info *> $null
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker daemon not running. Start Docker Desktop." -ForegroundColor Red
    exit 1
  }
}

Write-Host "=== Jitsi dev (no OAuth / no lobby) ===" -ForegroundColor Cyan
Test-DockerCli

if (-not (Test-Path $JitsiDir)) {
  Write-Host "Cloning docker-jitsi-meet (first run)..."
  git clone --depth 1 https://github.com/jitsi/docker-jitsi-meet.git $JitsiDir
}

$EnvFile = Join-Path $JitsiDir ".env"
$UpstreamExample = Join-Path $JitsiDir "env.example"

if (-not (Test-Path $EnvFile)) {
  if (-not (Test-Path $UpstreamExample)) {
    throw "env.example missing in $JitsiDir"
  }
  Copy-Item $UpstreamExample $EnvFile
  Push-Location $JitsiDir
  if (Test-Path ".\gen-passwords.sh") {
    Write-Host "Generating Jitsi passwords..."
    bash ./gen-passwords.sh
  }
  Pop-Location
}

if (Test-Path $Patches) {
  $patchLines = Get-Content $Patches | Where-Object { $_ -match '^\s*[A-Z_]+\s*=' -and $_ -notmatch '^\s*#' }
  $envContent = Get-Content $EnvFile
  foreach ($patch in $patchLines) {
    $key = ($patch -split '=', 2)[0].Trim()
    $envContent = $envContent | Where-Object { $_ -notmatch "^\s*$([regex]::Escape($key))\s*=" }
    $envContent += $patch
  }
  Set-Content -Path $EnvFile -Value $envContent -Encoding utf8
  Write-Host "Applied teleconsult patches"
}

$OverrideSrc = Join-Path $Root "deploy\jitsi\docker-compose.override.yml"
$OverrideDst = Join-Path $JitsiDir "docker-compose.override.yml"
if (Test-Path $OverrideSrc) {
  Copy-Item $OverrideSrc $OverrideDst -Force
}

Write-Host "Starting Jitsi on https://127.0.0.1:8443 (first run may take 5-15 min)..."
Push-Location $JitsiDir
docker compose up -d
if ($LASTEXITCODE -ne 0) {
  Pop-Location
  throw "docker compose up failed"
}
Pop-Location

Write-Host "Local test: https://127.0.0.1:8443" -ForegroundColor Green
Write-Host "iPhone: run scripts\tunnel\start-jitsi-cloudflared.ps1 then apply_jitsi_tunnel_domain.ps1"
