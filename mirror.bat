@echo off
REM Launch webcam mirror without a console window
cd /d "%~dp0"
start "" pythonw mirror.py
