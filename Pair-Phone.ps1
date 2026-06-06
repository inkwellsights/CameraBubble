# Pair-Phone.ps1 - one-time pairing for the wireless phone connection.
# Works on plain home Wi-Fi OR over Tailscale (the phone's 100.x address is reachable from
# anywhere you're both on the tailnet). Run this ONCE per phone, or whenever pairing is lost.
# It pairs, connects, and saves the connect address to phone_addr.txt so every launcher
# auto-connects afterwards.
$ErrorActionPreference = "Stop"

# --- locate the bundled adb (the same one scrcpy uses) ---
$adb = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter adb.exe -ErrorAction SilentlyContinue |
       Select-Object -First 1 -ExpandProperty FullName
if (-not $adb) {
    Write-Host "adb not found. Install scrcpy first:  winget install Genymobile.scrcpy" -ForegroundColor Red
    Read-Host "Enter to exit"; exit 1
}
$env:ADB = $adb
& $adb start-server | Out-Null

Write-Host ""
Write-Host "============== Pair phone (one time) ==============" -ForegroundColor Cyan
Write-Host "On the phone: Settings -> Developer options -> Wireless debugging (ON)." -ForegroundColor Gray
Write-Host "Over Tailscale this works from anywhere; on plain Wi-Fi you must share the same network." -ForegroundColor DarkGray
Write-Host ""
Write-Host "STEP 1  Tap 'Pair device with pairing code'." -ForegroundColor Yellow
Write-Host "        It shows an IP:port AND a 6-digit code. The port rotates, so read them quickly." -ForegroundColor Gray
$pairAddr = (Read-Host "  Pairing IP:port  (e.g. 100.77.106.106:35191)").Trim()
$pairCode = (Read-Host "  6-digit pairing code").Trim()

Write-Host "  pairing..." -ForegroundColor DarkGray
$out = (& $adb pair $pairAddr $pairCode 2>&1) -join "`n"
Write-Host "  $out" -ForegroundColor DarkGray
if ($out -notmatch "Successfully paired") {
    Write-Host ""
    Write-Host "Pairing failed. The code changes every ~30s - reopen the pairing dialog and retry with FRESH values." -ForegroundColor Red
    Read-Host "Enter to exit"; exit 1
}
Write-Host "  paired OK" -ForegroundColor Green

# --- connect: the MAIN Wireless debugging screen shows a DIFFERENT port (no code) ---
$ip = ($pairAddr -split ':')[0]
Write-Host ""
Write-Host "STEP 2  Go BACK one screen to the main 'Wireless debugging' page." -ForegroundColor Yellow
Write-Host "        It shows 'IP address & Port' (no code). Same IP ($ip), different port." -ForegroundColor Gray
$connIn = (Read-Host "  Connect port  (or paste the full IP:port)").Trim()
if ($connIn -match ':') { $connAddr = $connIn } else { $connAddr = "${ip}:${connIn}" }

Write-Host "  connecting to $connAddr ..." -ForegroundColor DarkGray
& $adb connect $connAddr 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
Start-Sleep -Milliseconds 900
$online = (& $adb devices) | Select-String "device$"
if ($online) {
    Set-Content -Path "$PSScriptRoot\phone_addr.txt" -Value $connAddr -NoNewline
    Write-Host ""
    Write-Host "Connected. Saved $connAddr - the launchers will auto-connect from now on." -ForegroundColor Green
    & $adb devices
} else {
    Write-Host ""
    Write-Host "Paired, but the connect address didn't take. Re-check the IP:port on the MAIN screen and run again." -ForegroundColor Red
}
Read-Host "Enter to exit"
