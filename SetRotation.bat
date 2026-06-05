@echo off
REM Set the phone camera rotation once - applies to all launchers (bubble, gestures, webcam, feed).
REM   SetRotation.bat            (asks)
REM   SetRotation.bat 180        (set directly: 0 / 90 / 180 / 270)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Set-Rotation.ps1" %*
pause
