# Start-PhoneBubble.ps1
# Phone rear camera as an always-on-top circle bubble. No OBS, no virtual camera.
# Starts scrcpy hidden off-screen (WGC still captures it) + the bubble.
#
# Usage:  double-click PhoneBubble.bat                       (asks rear/front, auto-connect via mDNS)
#    or:  PhoneBubble.bat -Camera front                      (skip the prompt)
#    or:  PhoneBubble.bat -Connect 192.168.0.168:40123       (manual IP:port fallback)
param(
    [string]$Camera  = "",   # "rear"/"back"/"0" or "front"/"1"; blank = ask at launch
    [string]$Connect = ""
)
$ErrorActionPreference = "Stop"

# --- tweakables ---
$Res = "1280x720"    # bubble only needs modest res; lower = less CPU. "3840x2160" for 4K.
$Fps = "30"
$ConnectAddr = $Connect   # pass -Connect IP:port if Wi-Fi auto-reconnect fails

# --- choose camera (rear / front) ---
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
    Write-Host "Which camera?   [1] Rear (default)    [2] Front" -ForegroundColor Cyan
    $pick = Read-Host "Choose 1 or 2 (Enter = Rear)"
    $CameraId = if ($pick.Trim() -eq '2') { '1' } else { '0' }
}
$CamName = if ($CameraId -eq '1') { 'front' } else { 'rear' }

# --- locate scrcpy + bundled adb ---
$scrcpy = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter scrcpy.exe -ErrorAction SilentlyContinue |
          Select-Object -First 1 -ExpandProperty FullName
if (-not $scrcpy) { Write-Host "scrcpy not found. Run: winget install Genymobile.scrcpy" -ForegroundColor Red; Read-Host "Enter to exit"; exit 1 }
$dir = Split-Path $scrcpy
$env:ADB = Join-Path $dir "adb.exe"

# --- ensure phone reachable over Wi-Fi ---
& $env:ADB start-server | Out-Null
if ($ConnectAddr) { & $env:ADB connect $ConnectAddr | Out-Null }

function Test-Online { (& $env:ADB devices) | Select-String "device$" }

# Try mDNS auto-discovery (works whenever Wireless debugging is ON and this PC is paired).
$connected = $false
for ($i = 0; $i -lt 5; $i++) {
    if (Test-Online) { $connected = $true; break }
    Start-Sleep -Milliseconds 700
}

# Fallback: ask for the IP:port shown on the phone's Wireless debugging screen.
while (-not $connected) {
    Write-Host ""
    Write-Host "Phone not auto-detected over Wi-Fi." -ForegroundColor Yellow
    Write-Host "On the M14: Developer options -> Wireless debugging (ON). Note the 'IP address & Port' on that screen." -ForegroundColor Yellow
    $addr = Read-Host "Enter IP:port (e.g. 192.168.0.168:40123)  |  Enter = retry  |  q = quit"
    if ($addr -eq 'q') { exit 1 }
    if ($addr) { & $env:ADB connect $addr | Out-Null }
    Start-Sleep -Milliseconds 1000
    if (Test-Online) { $connected = $true }
}

# --- (re)start the hidden phone feed with the chosen camera ---
# Stop any running feed/bubble first so the camera choice always takes effect.
Get-Process scrcpy -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process pythonw,python -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -eq 'PhoneBubble' } | Stop-Process -Force
Start-Sleep -Milliseconds 600
Start-Process -FilePath $scrcpy -ArgumentList `
    "--video-source=camera","--camera-id=$CameraId","--camera-size=$Res","--camera-fps=$Fps",`
    "--no-audio","--window-borderless","--window-title=PhoneCam","--window-x=5000","--window-y=5000"
Start-Sleep -Seconds 5   # let the server push + camera open

# --- launch the bubble (pythonw = no console) ---
$pyw = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
if (-not $pyw) { $pyw = (Get-Command python).Source }
Start-Process -FilePath $pyw -ArgumentList "`"$PSScriptRoot\phone_bubble.py`""
Write-Host "Bubble launched ($CamName camera). Drag to move, right-click for size/quit." -ForegroundColor Green
