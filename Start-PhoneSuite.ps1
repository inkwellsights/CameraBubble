# Start-PhoneSuite.ps1 - phone camera view + gesture control, together.
#   PhoneSuite.bat            (live - gestures press keys)
#   PhoneSuite.bat --dry      (gesture engine logs only, no keypresses)
# Asks: rear cam (hands, gestures only) or front cam (face, ALSO a webcam for video
# calls via OBS Virtual Camera); then rectangle or bubble; then runs the gesture engine.
$ErrorActionPreference = "Stop"
$Res = "1280x720"; $Fps = "30"; $CameraId = "0"; $ConnectAddr = ""

# --- locate scrcpy + bundled adb ---
$scrcpy = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter scrcpy.exe -ErrorAction SilentlyContinue |
          Select-Object -First 1 -ExpandProperty FullName
if (-not $scrcpy) { Write-Host "scrcpy not found. Run: winget install Genymobile.scrcpy" -ForegroundColor Red; Read-Host "Enter to exit"; exit 1 }
$dir = Split-Path $scrcpy
$env:ADB = Join-Path $dir "adb.exe"
$Rotate = & "$PSScriptRoot\Get-Rotation.ps1"   # asks at startup, remembers your choice

# Wait for scrcpy's PhoneCam window to ACTUALLY exist before starting anything that
# captures it. A fixed sleep loses the cold-start race (server push + TLS + camera open
# on the phone can take >5s); the gesture engine's WindowsCapture fails instantly if the
# window isn't there yet. Poll for it instead, and fail loudly if scrcpy dies first.
function Wait-PhoneCam {
    param([int]$TimeoutSec = 30)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Get-Process scrcpy -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -eq 'PhoneCam' }) { return $true }
        if (-not (Get-Process scrcpy -ErrorAction SilentlyContinue)) {
            Write-Host "scrcpy exited before the PhoneCam window appeared (camera busy, or phone locked? unlock it and retry)." -ForegroundColor Red
            return $false
        }
        Start-Sleep -Milliseconds 300
    }
    Write-Host "Timed out after $TimeoutSec s waiting for the PhoneCam window." -ForegroundColor Red
    return $false
}

# --- ensure phone reachable over Wi-Fi (mDNS auto, else prompt) ---
. "$PSScriptRoot\Connect-Phone.ps1"

# --- camera + calls: rear cam = hands-only gestures; front cam = your face AND a webcam for calls ---
# One phone camera can only point one way: rear at your hands, or front at your face. Front mode ALSO
# pipes the same feed into "OBS Virtual Camera" so Meet/WhatsApp/Zoom can use the phone as a webcam
# while gestures still fire (raise a hand into the selfie frame). The call sees the same view you do.
Write-Host ""
Write-Host "Camera:  [1] Rear  - point at your hands, gestures only (default)" -ForegroundColor Cyan
Write-Host "         [2] Front - your face; ALSO a webcam for calls (Meet/WhatsApp via OBS Virtual Camera)" -ForegroundColor Cyan
$callMode = ((Read-Host "Choose 1 or 2 (Enter = rear)").Trim() -eq "2")
$CameraId = if ($callMode) { "1" } else { "0" }   # front = 1 (face), rear = 0 (hands)

# --- choose how to SEE the phone: full rectangle (default) or circular bubble ---
Write-Host ""
Write-Host "Display:  [1] Full rectangle, always-on-top (default)   [2] Circle bubble" -ForegroundColor Cyan
$useBubble = ((Read-Host "Choose 1 or 2 (Enter = rectangle)").Trim() -eq "2")

# stop any existing feed/bubble so the chosen mode starts clean
Get-Process scrcpy -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process pythonw,python -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -eq 'PhoneBubble' } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 600

if ($useBubble) {
    # hidden feed + circular bubble
    Start-Process -FilePath $scrcpy -ArgumentList `
        "--video-source=camera","--camera-id=$CameraId","--camera-size=$Res","--camera-fps=$Fps",`
        "--no-audio","--window-borderless","--window-title=PhoneCam","--window-x=5000","--window-y=5000","--capture-orientation=$Rotate"
    if (-not (Wait-PhoneCam)) { Read-Host "Enter to exit"; exit 1 }
    $pyw = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
    if (-not $pyw) { $pyw = (Get-Command python).Source }
    Start-Process -FilePath $pyw -ArgumentList "`"$PSScriptRoot\phone_bubble.py`""
} else {
    # full-quality rectangle, always-on-top, draggable/resizable (no bubble = less CPU).
    # In call mode the window is wider so the webcam capture (which tracks the window's
    # rendered size) is a usable resolution; resize the window bigger anytime for more.
    Start-Process -FilePath $scrcpy -ArgumentList `
        "--video-source=camera","--camera-id=$CameraId","--camera-size=1920x1080","--camera-fps=$Fps",`
        "--no-audio","--always-on-top","--window-title=PhoneCam","--window-width=$(if($callMode){'960'}else{'400'})","--capture-orientation=$Rotate"
    if (-not (Wait-PhoneCam)) { Read-Host "Enter to exit"; exit 1 }
}

# --- call mode: also feed the SAME PhoneCam window into a virtual webcam for video calls ---
# phone_webcam.py reads the same window via Windows Graphics Capture and pushes to OBS Virtual
# Camera, so it coexists with the gesture engine off one feed. Its own window shows the device
# name + a clear error if OBS Virtual Camera isn't installed (gestures keep running regardless).
if ($callMode) {
    Write-Host "Webcam feed for calls starting - pick 'OBS Virtual Camera' in Meet/WhatsApp/Zoom." -ForegroundColor Green
    Start-Process -FilePath (Get-Command python).Source -ArgumentList "`"$PSScriptRoot\phone_webcam.py`""
}

# --- run the gesture engine in THIS console (so you see detections). Pass through args. ---
Write-Host "Phone view + gesture control running. Ctrl+C (or close window) to stop everything." -ForegroundColor Green
$py = (Get-Command python).Source
& $py "$PSScriptRoot\gesture_control.py" @args

# gesture engine exited -> tidy up the bubble + webcam feed + feed too (best effort)
Get-Process pythonw,python -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -eq 'PhoneBubble' } | Stop-Process -Force -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*phone_webcam*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Get-Process scrcpy -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
