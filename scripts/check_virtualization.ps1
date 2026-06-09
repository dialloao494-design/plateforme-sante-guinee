# Diagnostic virtualisation pour Docker Desktop (WSL2 / Hyper-V / BIOS)
# Exécuter en PowerShell ; certaines lignes nécessitent "Exécuter en tant qu'administrateur".

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Diagnostic virtualisation — Docker" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$proc = Get-CimInstance Win32_Processor | Select-Object -First 1
$virtFw = $proc.VirtualizationFirmwareEnabled
$slat = $proc.SecondLevelAddressTranslationExtensions

Write-Host "[1] Virtualisation CPU (BIOS/firmware)" -ForegroundColor Yellow
Write-Host "    Processeur : $($proc.Name)"
Write-Host "    VirtualizationFirmwareEnabled : $virtFw" `
  -ForegroundColor $(if ($virtFw) { "Green" } else { "Red" })
if (-not $virtFw) {
  Write-Host "    >>> BLOQUANT : activer Intel VT-x / AMD-V dans le BIOS (voir docs\DOCKER_VIRTUALIZATION_FIX.md)" -ForegroundColor Red
}

Write-Host ""
Write-Host "[2] WSL" -ForegroundColor Yellow
$wslOut = wsl --status 2>&1 | Out-String
if ($wslOut -match "n.est pas install") {
  Write-Host "    WSL : NON INSTALLÉ" -ForegroundColor Red
  Write-Host "    >>> Après BIOS OK : wsl --install (admin) puis redémarrage" -ForegroundColor Yellow
} else {
  Write-Host $wslOut
}

Write-Host "[3] Fonctionnalités Windows (nécessite admin)" -ForegroundColor Yellow
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
  [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdmin) {
  Write-Host "    Relancez ce script en administrateur pour voir Hyper-V / WSL / VirtualMachinePlatform." -ForegroundColor DarkYellow
} else {
  @(
    "VirtualMachinePlatform",
    "Microsoft-Windows-Subsystem-Linux",
    "Microsoft-Hyper-V-All",
    "HypervisorPlatform"
  ) | ForEach-Object {
    $f = Get-WindowsOptionalFeature -Online -FeatureName $_ -ErrorAction SilentlyContinue
    if ($f) {
      $color = if ($f.State -eq "Enabled") { "Green" } else { "Red" }
      Write-Host "    $_ : $($f.State)" -ForegroundColor $color
    }
  }
}

Write-Host ""
Write-Host "[4] Docker" -ForegroundColor Yellow
$dockerExe = "$env:ProgramFiles\Docker\Docker\resources\bin\docker.exe"
if (Test-Path $dockerExe) {
  Write-Host "    Docker Desktop : installé" -ForegroundColor Green
  & $dockerExe info 2>&1 | Select-Object -First 3
} else {
  Write-Host "    Docker Desktop : binaire non trouvé" -ForegroundColor Red
}

Write-Host ""
if (-not $virtFw) {
  Write-Host "VERDICT : Corrigez le BIOS (VT-x) AVANT WSL2/Docker." -ForegroundColor Red
} else {
  Write-Host "VERDICT : Virtualisation firmware OK — activez WSL2 + redémarrez si besoin." -ForegroundColor Green
}
Write-Host ""
