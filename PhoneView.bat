@echo off
REM Show the phone camera as a floating, always-on-top window at FULL source quality.
REM It's the scrcpy window itself - no bubble re-rendering, so LESS CPU than PhoneBubble.bat.
REM Drag the title bar to move it, drag the edges to resize. Rectangle (16:9), not a circle.
REM   PhoneView.bat               (asks rotation + rear/front)
REM   PhoneView.bat -Camera front
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-PhoneView.ps1" %*
