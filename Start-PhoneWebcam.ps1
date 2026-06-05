# Start-PhoneWebcam.ps1 - phone as a virtual webcam for video calls.
#   PhoneWebcam.bat                 (asks rear/front)
#   PhoneWebcam.bat -Camera front   (skip the prompt)
param([string]$Camera = "", [string]$Connect = "")
$ErrorActionPreference = "Stop"
$Res = "1920x1080"; $Fps = "30"   # full quality - gesture/bubble are off in webcam mode

# --- stop the gesture engine + bubble so this is a clean, dedicated webcam feed ---
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*gesture_control*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Get-Process pythonw,python -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowTitle -eq 'PhoneBubble' } | Stop-Process -Force -ErrorAction SilentlyContinue

# --- locate scrcpy + bundled adb ---
$scrcpy = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter scrcpy.exe -ErrorAction SilentlyContinue |
          Select-Object -First 1 -ExpandProperty FullName
if (-not $scrcpy) { Write-Host "scrcpy not found. Run: winget install Genymobile.scrcpy" -ForegroundColor Red; Read-Host "Enter to exit"; exit 1 }
$dir = Split-Path $scrcpy
$env:ADB = Join-Path $dir "adb.exe"
$Rotate = & "$PSScriptRoot\Get-Rotation.ps1"   # asks at startup, remembers your choice

# --- choose camera (rear = better quality if propped; front = selfie) ---
function Resolve-CamId([string]$c) {
    switch -Regex ($c.Trim().ToLower()) {
        '^(0|rear|back)$'    { '0'; break }
        '^(1|front|selfie)$' { '1'; break }
        default              { $null }
    }
}
$CameraId = Resolve-CamId $Camera
if (-not $CameraId) {
    Write-Host ""
    Write-Host "Which camera?   [1] Rear (default)    [2] Front (selfie)" -ForegroundColor Cyan
    $pick = Read-Host "Choose 1 or 2 (Enter = Rear)"
    $CameraId = if ($pick.Trim() -eq '2') { '1' } else { '0' }
}

# --- ensure phone reachable over Wi-Fi (mDNS auto, else prompt) ---
& $env:ADB start-server | Out-Null
if ($Connect) { & $env:ADB connect $Connect | Out-Null }
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

# --- (re)start the hidden phone feed at webcam resolution + chosen camera ---
Get-Process scrcpy -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 600
Start-Process -FilePath $scrcpy -ArgumentList `
    "--video-source=camera","--camera-id=$CameraId","--camera-size=$Res","--camera-fps=$Fps",`
    "--no-audio","--window-borderless","--window-title=PhoneCam","--window-x=5000","--window-y=5000","--capture-orientation=$Rotate"
Start-Sleep -Seconds 5

# --- feed it to the virtual camera (this console) ---
Write-Host "Starting phone webcam... pick 'OBS Virtual Camera' in your video app." -ForegroundColor Green
$py = (Get-Command python).Source
& $py "$PSScriptRoot\phone_webcam.py"
