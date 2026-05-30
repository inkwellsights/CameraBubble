@echo off
REM Run mirror.py with a visible console — use this if mirror.bat appears to do nothing
cd /d "%~dp0"
python mirror.py
echo.
echo --- Script exited. Press any key to close this window. ---
pause >nul
