@echo off
REM Simple Windows starter for Sulfur Bot (double-clickable)
cd /d %~dp0
powershell -ExecutionPolicy Bypass -File "%cd%\start.ps1" %*