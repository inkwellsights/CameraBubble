@echo off
REM Double-click: phone rear camera as an always-on-top circle. No OBS needed.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-PhoneBubble.ps1" %*
