@echo off
REM Phone as a virtual webcam for video calls (Meet, Zoom, WhatsApp, Telegram, Discord, streaming).
REM Stops the gesture engine + bubble, then feeds the phone camera to OBS Virtual Camera.
REM   PhoneWebcam.bat               (asks rear/front)
REM   PhoneWebcam.bat -Camera front (skip the prompt)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-PhoneWebcam.ps1" %*
pause
