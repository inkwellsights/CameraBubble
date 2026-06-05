# Start-GestureControl.ps1 - hand-gesture -> PC actions from the phone camera.
#   GestureControl.bat            (live: actually presses keys)
#   GestureControl.bat --dry      (test: logs detections, presses nothing)
$ErrorActionPreference = "Stop"
$Res = "1280x720"; $Fps = "30"; $CameraId = "0"; $ConnectAddr = ""

$scrcpy = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter scrcpy.exe -ErrorAction SilentlyContinue |
          Select-Object -First 1 -ExpandProperty FullName
if (-not $scrcpy) { Write-Host "scrcpy not found." -ForegroundColor Red; Read-Host "Enter to exit"; exit 1 }
$dir = Split-Path $scrcpy
$env:ADB = Join-Path $dir "adb.exe"
$Rotate = & "$PSScriptRoot\Get-Rotation.ps1"   # asks at startup, remembers your choice

# ensure phone reachable (mDNS auto, else prompt)
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

# start hidden phone feed if not already running
if (-not (Get-Process scrcpy -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath $scrcpy -ArgumentList `
        "--video-source=camera","--camera-id=$CameraId","--camera-size=$Res","--camera-fps=$Fps",`
        "--no-audio","--window-borderless","--window-title=PhoneCam","--window-x=5000","--window-y=5000","--capture-orientation=$Rotate"
    Start-Sleep -Seconds 5
}

# run the gesture engine in THIS console (so you see live detections). Pass through args (e.g. --dry).
$py = (Get-Command python).Source
& $py "$PSScriptRoot\gesture_control.py" @args
