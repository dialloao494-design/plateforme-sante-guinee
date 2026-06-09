# Deploy Plateforme Santé to Ubuntu VPS from Windows (SSH + rsync/scp)
# Usage:
#   .\scripts\vps\remote-deploy.ps1 -VpsHost 203.0.113.10 -Domain sante.example.gn -CertbotEmail admin@example.gn
param(
  [Parameter(Mandatory = $true)][string]$VpsHost,
  [Parameter(Mandatory = $true)][string]$Domain,
  [Parameter(Mandatory = $true)][string]$CertbotEmail,
  [string]$VpsUser = "root",
  [string]$SshKey = "",
  [string]$RemoteDir = "/opt/plateforme-sante-guinee"
)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$sshArgs = @("-o", "StrictHostKeyChecking=accept-new")
if ($SshKey) { $sshArgs += @("-i", $SshKey) }
$target = "${VpsUser}@${VpsHost}"

Write-Host "=== Remote deploy → $target ($RemoteDir) ===" -ForegroundColor Cyan

# Sync repo (exclude heavy/local artifacts)
$tarExclude = @(
  "--exclude=.git", "--exclude=venv", "--exclude=node_modules",
  "--exclude=frontend-sante/frontend/node_modules", "--exclude=frontend-sante/frontend/dist",
  "--exclude=*.db", "--exclude=certbot", "--exclude=backups", "--exclude=uploads",
  "--exclude=.env.pilot", "--exclude=deploy/jitsi/docker-jitsi-meet"
)
Push-Location $Root
tar -czf "$env:TEMP\plateforme-sante-deploy.tgz" @tarExclude .
Pop-Location

scp @sshArgs "$env:TEMP\plateforme-sante-deploy.tgz" "${target}:/tmp/plateforme-sante-deploy.tgz"

$remoteScript = @"
set -euo pipefail
mkdir -p '$RemoteDir'
tar -xzf /tmp/plateforme-sante-deploy.tgz -C '$RemoteDir'
cd '$RemoteDir'
chmod +x deploy/vps/*.sh scripts/docker/entrypoint-backend.sh 2>/dev/null || true
export DOMAIN='$Domain'
export CERTBOT_EMAIL='$CertbotEmail'
export INSTALL_DIR='$RemoteDir'
bash deploy/vps/bootstrap-autonomous.sh
"@

ssh @sshArgs $target $remoteScript

Write-Host ""
Write-Host "Deploy finished. Public URL: https://$Domain" -ForegroundColor Green
Write-Host "Verify: `$env:VPS_API_BASE='https://$Domain/api'; python scripts/vps_autonomous_verify.py"
