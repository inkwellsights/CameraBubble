@echo off
REM One-time pairing for the wireless phone connection (works on Wi-Fi or over Tailscale).
REM Run this ONCE; it pairs, connects, and saves the address so the launchers auto-connect after.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Pair-Phone.ps1" %*
