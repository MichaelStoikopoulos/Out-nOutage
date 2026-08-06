# Removes the Out-nOutage Startup-folder shortcuts and stops any running
# monitor/dashboard processes.
#   powershell -ExecutionPolicy Bypass -File uninstall.ps1

$StartupDir = [Environment]::GetFolderPath('Startup')
$Shortcuts = @(
    (Join-Path $StartupDir "OutnOutageMonitor.lnk"),
    (Join-Path $StartupDir "OutnOutageDashboard.lnk")
)

foreach ($lnk in $Shortcuts) {
    if (Test-Path $lnk) {
        Remove-Item $lnk -Force
        Write-Host "Removed startup shortcut: $lnk"
    } else {
        Write-Host "No startup shortcut found at $lnk"
    }
}

Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe'" |
    Where-Object { $_.CommandLine -like '*main.py*run*' -or $_.CommandLine -like '*main.py*dashboard*' } |
    ForEach-Object {
        Write-Host "Stopping running process (PID $($_.ProcessId)): $($_.CommandLine)"
        Stop-Process -Id $_.ProcessId -Force
    }
