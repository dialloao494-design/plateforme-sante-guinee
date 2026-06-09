# Register Docker Compose pilote stack to start at Windows logon.
# Run once as Administrator: .\scripts\windows\register-pilot-autostart.ps1
param(
  [string]$TaskName = "PlateformeSante-PiloteDocker"
)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Compose = "docker compose -f docker-compose.yml -f docker-compose.pilot.yml --env-file .env.pilot up -d"
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -WindowStyle Hidden -Command `"Set-Location '$Root'; $Compose`""
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -RunLevel Highest -Force | Out-Null
Write-Host "Scheduled task '$TaskName' registered — Docker pilote stack starts at logon." -ForegroundColor Green
