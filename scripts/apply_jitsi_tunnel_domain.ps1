# Sync JITSI_DOMAIN across backend + frontend after Jitsi cloudflared tunnel is up.
param(
  [Parameter(Mandatory = $true)]
  [string]$TunnelUrl
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

$uri = [Uri]$TunnelUrl.Trim()
$hostName = $uri.Host
if (-not $hostName) {
  Write-Error "URL tunnel invalide. Exemple : -TunnelUrl https://abc-def.trycloudflare.com"
}

function Set-EnvLine {
  param([string]$FilePath, [string]$Key, [string]$Value)
  if (-not (Test-Path $FilePath)) {
    New-Item -ItemType File -Path $FilePath -Force | Out-Null
  }
  $lines = Get-Content $FilePath -ErrorAction SilentlyContinue
  if (-not $lines) { $lines = @() }
  $pattern = "^\s*$([regex]::Escape($Key))\s*="
  $newLine = "$Key=$Value"
  $found = $false
  $out = foreach ($line in $lines) {
    if ($line -match $pattern) {
      $found = $true
      $newLine
    } else {
      $line
    }
  }
  if (-not $found) {
    $out = @($out) + $newLine
  }
  Set-Content -Path $FilePath -Value $out -Encoding utf8
}

$backendEnv = Join-Path $Root ".env"
$frontendTunnel = Join-Path $Root "frontend-sante\frontend\.env.tunnel"

Set-EnvLine $backendEnv "TELECONSULT_PROVIDER" "jitsi"
Set-EnvLine $backendEnv "JITSI_DOMAIN" $hostName
Set-EnvLine $frontendTunnel "VITE_TELECONSULT_PROVIDER" "jitsi"
Set-EnvLine $frontendTunnel "VITE_JITSI_DOMAIN" $hostName

Write-Host ""
Write-Host "JITSI_DOMAIN appliqué : $hostName" -ForegroundColor Green
Write-Host "  $backendEnv"
Write-Host "  $frontendTunnel"
Write-Host ""
Write-Host "Étapes suivantes :" -ForegroundColor Cyan
Write-Host "  1) Redémarrer le backend (uvicorn)"
Write-Host "  2) Redémarrer Vite : cd frontend-sante\frontend ; npm run dev:tunnel"
Write-Host "  3) Médecin PC + patient iPhone → même RDV /consultation/{id}"
Write-Host ""
