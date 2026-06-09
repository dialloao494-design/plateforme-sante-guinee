# Réinitialise les mots de passe des comptes pilote (médecins + patient test).
# Usage: .\scripts\repair_pilot_passwords.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$candidates = @(
  "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
  "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
  "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
)
$Py = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Py) {
  Write-Error "Python introuvable."
}

Write-Host "Réparation des comptes pilote..."
& $Py -c "from services.pilot_seed import seed_pilot_accounts; seed_pilot_accounts()"
Write-Host ""
Write-Host "Comptes médecins : Doctor123!"
Write-Host "Compte patient   : Patient123!"
Write-Host ""
Write-Host "Médecin principal : dr.mamady@example.com"
Write-Host "Patient test      : test.patient@example.com"
Write-Host ""
& $Py scripts/verify_pilot_logins.py
