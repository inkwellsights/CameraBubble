@echo off
REM Just the hidden phone camera feed, for OBS to capture (streaming / recording).
REM Add a Window Capture of "PhoneCam" in OBS with Capture Method = Windows 10 (1903+).
REM   PhoneFeed.bat               (asks rear/front)
REM   PhoneFeed.bat -Camera front (skip the prompt)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-PhoneFeed.ps1" %*
pause
