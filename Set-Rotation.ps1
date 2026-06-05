# Set-Rotation.ps1 - set the phone camera rotation once (used by every launcher).
param([string]$Value = "")
$valid = @("0", "90", "180", "270", "flip0", "flip90", "flip180", "flip270")
if (-not $Value) {
    Write-Host "Phone camera rotation (clockwise degrees):"
    Write-Host "   0 = none    90    180 = upside down    270"
    Write-Host "(If unsure, try one, run PhoneBubble.bat to check, and adjust.)"
    $Value = Read-Host "Enter 0 / 90 / 180 / 270"
}
$Value = $Value.Trim()
if ($valid -notcontains $Value) {
    Write-Host "Invalid. Use 0, 90, 180, or 270 (optionally flip0..flip270)." -ForegroundColor Red
    Read-Host "Enter to exit"; exit 1
}
Set-Content -Path "$PSScriptRoot\rotation.txt" -Value $Value -NoNewline
Write-Host "Saved rotation = $Value." -ForegroundColor Green
Write-Host "Restart your launcher (PhoneWebcam / PhoneSuite / PhoneBubble / etc.) to apply." -ForegroundColor Green
