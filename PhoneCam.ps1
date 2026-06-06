# PhoneCam.ps1 - launch the Galaxy M14 rear camera as the "PhoneCam" window for OBS.
# Wireless (adb over Wi-Fi). No USB cable, nothing installed on the phone, all open-source.
#
# Quick edits:
$Res = "1920x1080"   # webcam-friendly. For max quality use "3840x2160" (4K, add bitrate below).
$Fps = "30"
$CameraId = "0"      # 0 = rear/back, 1 = front
$BitRate = ""        # e.g. "25M" for clean 4K. Empty = scrcpy default (8 Mbps).
# Optional: if mDNS auto-reconnect fails, set the phone's Wireless-debugging IP:port here.
$ConnectAddr = ""    # e.g. "192.168.0.168:40123"

$ErrorActionPreference = "Stop"

# --- locate scrcpy.exe + its bundled adb.exe (survives winget version bumps) ---
$scrcpy = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter scrcpy.exe -ErrorAction SilentlyContinue |
          Select-Object -First 1 -ExpandProperty FullName
if (-not $scrcpy) {
    Write-Host "scrcpy not found. Install it with:  winget install Genymobile.scrcpy" -ForegroundColor Red
    Read-Host "Press Enter to exit"; exit 1
}
$dir = Split-Path $scrcpy
$adb = Join-Path $dir "adb.exe"
$env:ADB = $adb   # make scrcpy use the bundled adb (ignores any stale system ADB var)

# --- make sure the phone is reachable (saved address / mDNS / manual, with a pair option) ---
. "$PSScriptRoot\Connect-Phone.ps1"

# --- launch the PhoneCam window ---
$args = @(
    "--video-source=camera",
    "--camera-id=$CameraId",
    "--camera-size=$Res",
    "--camera-fps=$Fps",
    "--no-audio",
    "--window-borderless",
    "--window-title=PhoneCam"
)
if ($BitRate) { $args += "--video-bit-rate=$BitRate" }

Write-Host "Launching PhoneCam ($Res @ ${Fps}fps, rear camera)..." -ForegroundColor Green
& $scrcpy @args
