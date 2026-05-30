@echo off
REM Phone camera bubble + gesture control, one launch.
REM   PhoneSuite.bat         (live - gestures press keys)
REM   PhoneSuite.bat --dry   (gesture engine logs only, no keypresses)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-PhoneSuite.ps1" %*
pause
