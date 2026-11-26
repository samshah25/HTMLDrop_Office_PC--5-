# Registers the Windows scheduled task "Ahmedabad ME Team Performance refresh": run_daily.bat every day at 08:20 and 14:50
# (20 minutes after the Mumbai ME kit's 08:00 / 14:30 runs, so the two never overlap).
#   08:20  yesterday from the live allocation API (provisional); its deals from the system's Dealclosed records (103)
#   14:50  the appointment table loads at about 14:05: yesterday from the table
# Run once from PowerShell:  powershell -ExecutionPolicy Bypass -File setup_schedule.ps1
# Remove it again with:       Unregister-ScheduledTask -TaskName "Ahmedabad ME Team Performance refresh" -Confirm:$false
$bat = Join-Path $PSScriptRoot "run_daily.bat"
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$bat`"" -WorkingDirectory $PSScriptRoot
$triggers = @(
    New-ScheduledTaskTrigger -Daily -At "08:20"
    New-ScheduledTaskTrigger -Daily -At "14:50"
)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew -WakeToRun
Register-ScheduledTask -TaskName "Ahmedabad ME Team Performance refresh" -Action $action -Trigger $triggers -Settings $settings `
    -Description "Ahmedabad ME dashboard: morning provisional day from the allocation API; afternoon from the appointment table" -Force
