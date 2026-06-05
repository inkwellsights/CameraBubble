# Get-Rotation.ps1 - ask for camera rotation at session start, remember it, return the value.
# Called by every launcher. Enter keeps the last choice, so it's one keypress after the first time.
$rotFile = Join-Path $PSScriptRoot "rotation.txt"
$cur = if (Test-Path $rotFile) { (Get-Content $rotFile -Raw).Trim() } else { "0" }
Write-Host ""
Write-Host "Camera rotation:  [1] 0 none   [2] 90   [3] 180 upside-down   [4] 270   [5] mirror" -ForegroundColor Cyan
$rp = (Read-Host "Choose  (Enter = keep $cur)").Trim().ToLower()
$rot = switch ($rp) {
    "1" { "0" }   "2" { "90" }   "3" { "180" }   "4" { "270" }   "5" { "flip0" }
    "0" { "0" }   "90" { "90" }  "180" { "180" }  "270" { "270" }
    "flip0" { "flip0" } "flip90" { "flip90" } "flip180" { "flip180" } "flip270" { "flip270" } "mirror" { "flip0" }
    default { $cur }
}
Set-Content -Path $rotFile -Value $rot -NoNewline
Write-Host "Rotation: $rot  (run again and pick another if it's not upright)" -ForegroundColor Green
return $rot
