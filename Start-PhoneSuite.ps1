# Start-PhoneSuite.ps1 - phone camera bubble + gesture control, together.
#   PhoneSuite.bat            (live - gestures press keys)
#   PhoneSuite.bat --dry      (gesture engine logs only, no keypresses)
# Starts: hidden scrcpy feed + bubble (no console) + gesture engine (this console).
$ErrorActionPreference = "Stop"
$Res = "1920x1080"; $Fps = "30"; $CameraId = "0"; $ConnectAddr = ""

# --- locate scrcpy + bundled adb ---
$scrcpy = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter scrcpy.exe -ErrorAction SilentlyContinue |
          Select-Object -First 1 -ExpandProperty FullName
if (-not $scrcpy) { Write-Host "scrcpy not found. Run: winget install Genymobile.scrcpy" -ForegroundColor Red; Read-Host "Enter to exit"; exit 1 }
$dir = Split-Path $scrcpy
$env:ADB = Join-Path $dir "adb.exe"

# --- ensure phone reachable over Wi-Fi (mDNS auto, else prompt) ---
& $env:ADB start-server | Out-Null
if ($ConnectAddr) { & $env:ADB connect $ConnectAddr | Out-Null }
function Test-Online { (& $env:ADB devices) | Select-String "device$" }
$connected = $false
for ($i = 0; $i -lt 5; $i++) { if (Test-Online) { $connected = $true; break }; Start-Sleep -Milliseconds 700 }
while (-not $connected) {
    Write-Host "Phone not auto-detected. Turn on Wireless debugging (same Wi-Fi)." -ForegroundColor Yellow
    $addr = Read-Host "Enter IP:port  |  Enter = retry  |  q = quit"
    if ($addr -eq 'q') { exit 1 }
    if ($addr) { & $env:ADB connect $addr | Out-Null }
    Start-Sleep -Milliseconds 1000
    if (Test-Online) { $connected = $true }
}

# --- start hidden phone feed if not already running ---
if (-not (Get-Process scrcpy -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath $scrcpy -ArgumentList `
        "--video-source=camera","--camera-id=$CameraId","--camera-size=$Res","--camera-fps=$Fps",`
        "--no-audio","--window-borderless","--window-title=PhoneCam","--window-x=5000","--window-y=5000"
    Start-Sleep -Seconds 5
}

# --- start the bubble (no console) if not already up ---
$pyw = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
if (-not $pyw) { $pyw = (Get-Command python).Source }
if (-not (Get-Process pythonw,python -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -eq 'PhoneBubble' })) {
    Start-Process -FilePath $pyw -ArgumentList "`"$PSScriptRoot\phone_bubble.py`""
}

# --- run the gesture engine in THIS console (so you see detections). Pass through args. ---
Write-Host "Bubble + gesture control running. Ctrl+C (or close window) to stop everything." -ForegroundColor Green
$py = (Get-Command python).Source
& $py "$PSScriptRoot\gesture_control.py" @args

# gesture engine exited -> tidy up the bubble + feed too (best effort)
Get-Process pythonw,python -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -eq 'PhoneBubble' } | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process scrcpy -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
