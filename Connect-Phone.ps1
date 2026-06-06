# Connect-Phone.ps1 - shared adb connector used by every launcher.
# DOT-SOURCE it (note the leading dot) AFTER $env:ADB is set:
#     . "$PSScriptRoot\Connect-Phone.ps1"
# Tries, in order:
#   already-connected  ->  explicit -Connect arg  ->  saved phone_addr.txt  ->  mDNS auto  ->  manual prompt
# mDNS only works on a flat LAN; over Tailscale the saved address (or a manual IP:port) is what connects.
# A good manual address is saved to phone_addr.txt for next time. Sets $connected = $true on success;
# 'p' at the prompt runs Pair-Phone.ps1; 'q' quits the launcher.

if (-not $env:ADB) {
    $found = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter adb.exe -ErrorAction SilentlyContinue |
             Select-Object -First 1 -ExpandProperty FullName
    if ($found) { $env:ADB = $found }
}
& $env:ADB start-server | Out-Null
function Test-Online { (& $env:ADB devices) | Select-String "device$" }
function Connect-Addr([string]$a) {
    if (-not $a) { return $false }
    & $env:ADB connect $a 2>&1 | Out-Null
    Start-Sleep -Milliseconds 800
    [bool](Test-Online)
}
$addrFile = Join-Path $PSScriptRoot "phone_addr.txt"
$connected = $false

# already connected from earlier this session?
if (Test-Online) { $connected = $true }

# 1. explicit address passed to the launcher (-Connect / -ConnectAddr)
if (-not $connected) {
    $pre = if ($ConnectAddr) { $ConnectAddr } elseif ($Connect) { $Connect } else { "" }
    if ($pre) { $connected = Connect-Addr $pre }
}

# 2. saved address from the last successful pair/connect (this is what makes Tailscale seamless)
if (-not $connected -and (Test-Path $addrFile)) {
    $saved = (Get-Content $addrFile -Raw).Trim()
    if ($saved) {
        Write-Host "Reconnecting to saved phone $saved ..." -ForegroundColor Gray
        $connected = Connect-Addr $saved
    }
}

# 3. mDNS auto-discovery (flat LAN only; never crosses Tailscale)
if (-not $connected) {
    for ($i = 0; $i -lt 5; $i++) { if (Test-Online) { $connected = $true; break }; Start-Sleep -Milliseconds 700 }
}

# 4. manual fallback
while (-not $connected) {
    Write-Host ""
    Write-Host "Phone not connected." -ForegroundColor Yellow
    Write-Host "Phone: Developer options -> Wireless debugging (ON). The MAIN screen's 'IP address & Port' goes here." -ForegroundColor Gray
    $addr = Read-Host "IP:port  |  p = pair a phone  |  Enter = retry  |  q = quit"
    if ($addr -eq 'q') { exit 1 }
    if ($addr -eq 'p') {
        & "$PSScriptRoot\Pair-Phone.ps1"
        if (Test-Online) { $connected = $true }
        continue
    }
    if ($addr) {
        if (Connect-Addr $addr) { $connected = $true; Set-Content -Path $addrFile -Value $addr -NoNewline }
    } elseif (Test-Online) { $connected = $true }
}
