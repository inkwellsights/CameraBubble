@echo off
REM Hand gestures from the phone camera -> PC actions.
REM   GestureControl.bat         (live - presses keys)
REM   GestureControl.bat --dry   (test - logs only, no keypresses)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-GestureControl.ps1" %*
pause
