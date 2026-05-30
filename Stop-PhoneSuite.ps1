# Stops the gesture engine, the bubble, and the hidden phone feed.
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*gesture_control*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Get-Process pythonw,python -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowTitle -eq 'PhoneBubble' } | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process scrcpy -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "Stopped: gesture engine, bubble, and phone feed."
