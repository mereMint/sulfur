@echo off
REM Simple Windows starter for Sulfur Bot (double-clickable)
cd /d %~dp0
echo Starting Sulfur Discord Bot...
echo.
powershell -ExecutionPolicy Bypass -NoExit -File "%cd%\start.ps1" %*