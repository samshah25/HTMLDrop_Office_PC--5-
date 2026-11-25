# Registers the Windows scheduled task "Jaipur tenure grid refresh": run_daily.bat every day at 07:30, 11:30 and 14:30.
#   07:30  deals and HR end the day before yesterday (they load yesterday at about 10:50 / 11:05)
#   11:30  yesterday's deals, HR and calls; yesterday's ME appointments are not in yet
#   14:30  the appointment table loads at about 14:05: yesterday complete
# Run once from PowerShell:  powershell -ExecutionPolicy Bypass -File setup_schedule.ps1
# Remove it again with:       Unregister-ScheduledTask -TaskName "Jaipur tenure grid refresh" -Confirm:$false
$bat = Join-Path $PSScriptRoot "run_daily.bat"
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$bat`"" -WorkingDirectory $PSScriptRoot
$triggers = @(
    New-ScheduledTaskTrigger -Daily -At "07:30"
    New-ScheduledTaskTrigger -Daily -At "11:30"
    New-ScheduledTaskTrigger -Daily -At "14:30"
)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew -WakeToRun
Register-ScheduledTask -TaskName "Jaipur tenure grid refresh" -Action $action -Trigger $triggers -Settings $settings `
    -Description "Jaipur tenure grid: data up to yesterday; morning, midday and afternoon runs" -Force
