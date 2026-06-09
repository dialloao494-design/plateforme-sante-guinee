# Installe/active WSL2 pour Docker Desktop — à lancer en PowerShell ADMINISTRATEUR.
# Windows 11 Famille : pas de Hyper-V complet ; Docker utilise le moteur WSL2.

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Activation WSL2 pour Docker Desktop" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$virt = (Get-CimInstance Win32_Processor | Select-Object -First 1).VirtualizationFirmwareEnabled
Write-Host "[1] VirtualizationFirmwareEnabled : $virt"
if (-not $virt) {
  Write-Host "    ATTENTION : WMI indique encore False." -ForegroundColor Yellow
  Write-Host "    Si vous venez d'activer le BIOS, redémarrez Windows puis relancez ce script." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[2] Activation des composants Windows..." -ForegroundColor Yellow
$features = @(
  "VirtualMachinePlatform",
  "Microsoft-Windows-Subsystem-Linux"
)
foreach ($name in $features) {
  $f = Get-WindowsOptionalFeature -Online -FeatureName $name
  if ($f.State -ne "Enabled") {
    Write-Host "    Activation de $name..."
    Enable-WindowsOptionalFeature -Online -FeatureName $name -All -NoRestart | Out-Null
  } else {
    Write-Host "    $name : déjà activé"
  }
}

# Hypervisor Platform (utile pour WSL2 sur toutes éditions)
$hp = Get-WindowsOptionalFeature -Online -FeatureName "HypervisorPlatform" -ErrorAction SilentlyContinue
if ($hp -and $hp.State -ne "Enabled") {
  Write-Host "    Activation de HypervisorPlatform..."
  Enable-WindowsOptionalFeature -Online -FeatureName HypervisorPlatform -All -NoRestart | Out-Null
}

Write-Host ""
Write-Host "[3] Installation WSL (distribution + noyau)..." -ForegroundColor Yellow
$wslExe = "$env:SystemRoot\System32\wsl.exe"
if (-not (Test-Path $wslExe)) {
  Write-Error "wsl.exe introuvable"
}

# --install active WSL + Ubuntu par défaut sur Win11
& $wslExe --install --no-distribution
if ($LASTEXITCODE -ne 0) {
  Write-Warning "wsl --install a retourné $LASTEXITCODE — essayez après redémarrage : wsl --install"
}

Write-Host ""
Write-Host "[4] WSL2 par défaut..." -ForegroundColor Yellow
& $wslExe --set-default-version 2
& $wslExe --update

Write-Host ""
Write-Host "[5] Vérification..." -ForegroundColor Yellow
& $wslExe --status
& $wslExe -l -v

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " Prochaines étapes" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "  1) REDÉMARREZ Windows (souvent obligatoire)."
Write-Host "  2) Ouvrez Docker Desktop."
Write-Host "  3) Settings → General → cochez 'Use the WSL 2 based engine'."
Write-Host "  4) Settings → Resources → WSL integration → activez votre distro."
Write-Host "  5) Vérifiez : docker info"
Write-Host ""
Write-Host "Puis téléconsultation : .\scripts\start_jitsi_dev.ps1" -ForegroundColor Cyan
Write-Host ""

$restart = Read-Host "Redémarrer maintenant ? (o/N)"
if ($restart -match '^[oOyY]') {
  Restart-Computer
}
