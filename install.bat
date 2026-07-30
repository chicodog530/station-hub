@echo off
echo Starting Station Hub Automated Installer...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
pause
