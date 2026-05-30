@echo off
REM Closes the bubble and the hidden phone feed.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Process python,pythonw -EA SilentlyContinue | Where-Object { $_.MainWindowTitle -eq 'PhoneBubble' } | Stop-Process -Force; Get-Process scrcpy -EA SilentlyContinue | Stop-Process -Force; Write-Host 'Stopped.'"
