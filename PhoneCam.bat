@echo off
REM Double-click to launch the phone rear camera as the "PhoneCam" window for OBS.
REM Runs PhoneCam.ps1 next to this file.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0PhoneCam.ps1"
