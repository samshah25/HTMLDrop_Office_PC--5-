# One-time setup for the office PC. Works with or without administrator rights:
#   powershell -ExecutionPolicy Bypass -File .\setup_office_pc.ps1
# It starts HTML Drop now and at every login (no window), keeps the PC awake while plugged in,
# and - only when run as administrator - opens its port in the Windows firewall.

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$port = 8150
if (Test-Path "$here\config.json") { $port = (Get-Content "$here\config.json" -Raw | ConvertFrom-Json).port }
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
           ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not (Get-Command python.exe -ErrorAction SilentlyContinue)) {
    throw "Python not found. Install it from python.org and tick 'Add python.exe to PATH'."
}
if ($here -match "OneDrive") {
    Write-Warning "This folder is inside OneDrive ($here). OneDrive syncing can lock HTML Drop's files. Moving the folder to C:\HTMLDrop and running this again is safer."
}

# 1. Firewall (needs administrator). Without it, HTML Drop runs as python.exe like the other
#    dashboard servers, which colleagues can already reach, so it usually works anyway.
if ($isAdmin) {
    Get-NetFirewallRule -DisplayName "HTML Drop" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    New-NetFirewallRule -DisplayName "HTML Drop" -Direction Inbound -Protocol TCP -LocalPort $port `
        -Action Allow -Profile Domain,Private | Out-Null
    Write-Host "Firewall: port $port opened."
} else {
    Write-Host "Firewall: skipped (not running as administrator). If colleagues can't open the link, ask IT to allow TCP port $port."
}

# 2. Start at every login, hidden. A scheduled task (restarts it if it crashes) when Windows
#    allows it; otherwise a shortcut in your Startup folder, which needs no special rights.
$launcher = "$here\run_hidden.vbs"
$started = $false
try {
    $action   = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$launcher`"" -WorkingDirectory $here
    $trigger  = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero)
    Register-ScheduledTask -TaskName "HTML Drop" -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
    Write-Host "Auto-start: scheduled task 'HTML Drop' created."
} catch {
    $startup = [Environment]::GetFolderPath("Startup")
    $lnk = (New-Object -ComObject WScript.Shell).CreateShortcut("$startup\HTML Drop.lnk")
    $lnk.TargetPath = "wscript.exe"; $lnk.Arguments = "`"$launcher`""; $lnk.WorkingDirectory = $here
    $lnk.Save()
    Write-Host "Auto-start: shortcut added to your Startup folder."
}

# Start it now, unless it's already running.
if (-not (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)) {
    Start-Process wscript.exe -ArgumentList "`"$launcher`"" -WorkingDirectory $here
    Start-Sleep 4
}
if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
    Write-Host "HTML Drop: running on port $port."
} else {
    Write-Warning "HTML Drop did not start. Double-click start.bat in $here to see the error."
}

# 3. Keep the PC awake while plugged in (screen can still turn off).
try {
    powercfg /change standby-timeout-ac 0 | Out-Null
    powercfg /change hibernate-timeout-ac 0 | Out-Null
    Write-Host "Power: sleep disabled on AC power."
} catch {
    Write-Host "Power: couldn't change sleep settings. Set 'Sleep: Never' in Windows Settings > Power."
}

$ip = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
       Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } |
       Select-Object -First 1).IPAddress
Write-Host "`nShare this link with colleagues:  http://$($ip):$port/"
Write-Host "Admin login: choose 'Admin'; the PIN is admin_password in $here\config.json"
