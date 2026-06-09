# Prints the exact 5-terminal procedure for PC ↔ iPhone teleconsultation test.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " TEST APPEL RÉEL — PC + iPhone Safari" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$dockerOk = $false
if (Get-Command docker -ErrorAction SilentlyContinue) {
  docker info *> $null
  $dockerOk = ($LASTEXITCODE -eq 0)
}

$cf = Join-Path $PSScriptRoot "tunnel\cloudflared.exe"
$cfOk = (Test-Path $cf) -or (Get-Command cloudflared -ErrorAction SilentlyContinue)

Write-Host "Prérequis :" -ForegroundColor Yellow
Write-Host "  Docker Desktop : $(if ($dockerOk) { 'OK' } else { 'MANQUANT — installer et démarrer' })" `
  -ForegroundColor $(if ($dockerOk) { 'Green' } else { 'Red' })
Write-Host "  cloudflared    : $(if ($cfOk) { 'OK' } else { 'MANQUANT' })" `
  -ForegroundColor $(if ($cfOk) { 'Green' } else { 'Red' })
Write-Host ""

$jitsiDomain = $null
$envPath = Join-Path $Root ".env"
if (Test-Path $envPath) {
  $line = Select-String -Path $envPath -Pattern '^\s*JITSI_DOMAIN\s*=\s*(.+)$' | Select-Object -Last 1
  if ($line) { $jitsiDomain = $line.Matches.Groups[1].Value.Trim() }
}

if ($jitsiDomain -eq 'meet.jit.si' -or -not $jitsiDomain) {
  Write-Host "JITSI_DOMAIN : pas encore configuré pour tunnel (meet.jit.si interdit)" -ForegroundColor Yellow
} else {
  Write-Host "JITSI_DOMAIN actuel : $jitsiDomain" -ForegroundColor Green
}

Write-Host ""
Write-Host "Ordre des terminaux :" -ForegroundColor White
Write-Host ""
Write-Host "  T4  .\scripts\start_jitsi_dev.ps1" -ForegroundColor Cyan
Write-Host "  T5  .\scripts\tunnel\start-jitsi-cloudflared.ps1" -ForegroundColor Cyan
Write-Host "      .\scripts\apply_jitsi_tunnel_domain.ps1 -TunnelUrl https://....trycloudflare.com" -ForegroundColor Cyan
Write-Host "  T1  .\scripts\qa_start_backend.ps1          (redémarrer après apply)" -ForegroundColor Yellow
Write-Host "  T2  cd frontend-sante\frontend ; npm run dev:tunnel" -ForegroundColor Yellow
Write-Host "  T3  .\scripts\tunnel\start-cloudflared.ps1" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Médecin : http://localhost:5173/consultation/{id}" -ForegroundColor Green
Write-Host "  Patient : https://APP-XXX.trycloudflare.com/consultation/{id}" -ForegroundColor Green
Write-Host ""
Write-Host "Guide complet : docs\TELECONSULT_REAL_CALL_PROCEDURE.md" -ForegroundColor White
Write-Host ""
Write-Host "Verdict : GO seulement si audio+vidéo bidirectionnels ≥ 1 min (grille §6 du guide)." -ForegroundColor Magenta
Write-Host ""
