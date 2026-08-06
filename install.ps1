# Registers Out-nOutage to start monitoring automatically whenever you log in,
# so outage stats accumulate "since your computer is on" without you having
# to remember to launch it. Also opens the live dashboard at login.
#
# Uses a shortcut in the per-user Startup folder rather than Task Scheduler:
# on some machines (this one included) Task Scheduler is locked down to
# admins even for per-user logon tasks, while the Startup folder only needs
# ordinary filesystem access.
#
# Run this once, in a normal (non-admin) PowerShell window:
#   powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
$MainScript = Join-Path $ScriptDir "main.py"

$pythonw = Get-Command pythonw.exe -ErrorAction SilentlyContinue
if (-not $pythonw) {
    $pythonw = Get-Command python.exe -ErrorAction SilentlyContinue
}
if (-not $pythonw) {
    throw "Could not find pythonw.exe or python.exe on PATH. Install Python and try again."
}
$PythonExe = $pythonw.Source

$StartupDir = [Environment]::GetFolderPath('Startup')
$MonitorLnk = Join-Path $StartupDir "OutnOutageMonitor.lnk"
$DashboardLnk = Join-Path $StartupDir "OutnOutageDashboard.lnk"

Write-Host "Using interpreter: $PythonExe"
Write-Host "Main script: $MainScript"
Write-Host "Startup shortcuts: $MonitorLnk"
Write-Host "                   $DashboardLnk"

$wsh = New-Object -ComObject WScript.Shell

$monitorShortcut = $wsh.CreateShortcut($MonitorLnk)
$monitorShortcut.TargetPath = $PythonExe
$monitorShortcut.Arguments = "`"$MainScript`" run"
$monitorShortcut.WorkingDirectory = $ScriptDir
$monitorShortcut.WindowStyle = 7   # minimized (pythonw has no window anyway)
$monitorShortcut.Description = "Out-nOutage internet outage monitor"
$monitorShortcut.Save()

$dashboardShortcut = $wsh.CreateShortcut($DashboardLnk)
$dashboardShortcut.TargetPath = $PythonExe
$dashboardShortcut.Arguments = "`"$MainScript`" dashboard"
$dashboardShortcut.WorkingDirectory = $ScriptDir
$dashboardShortcut.WindowStyle = 7
$dashboardShortcut.Description = "Out-nOutage live dashboard"
$dashboardShortcut.Save()

Write-Host "Installed. The monitor and dashboard will start automatically at your next login."
Write-Host "Starting the monitor now too..."
Start-Process -FilePath $PythonExe -ArgumentList "`"$MainScript`" run" -WorkingDirectory $ScriptDir -WindowStyle Hidden

Write-Host "Done. Check status with: python main.py status"
Write-Host "Open the dashboard any time with: python main.py dashboard"
