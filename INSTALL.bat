@echo off
REM ============================================================
REM Sulfur Discord Bot - Installation Wizard Launcher
REM ============================================================
REM Double-click this file to start the installation wizard
REM ============================================================

cd /d %~dp0
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║     Sulfur Discord Bot - Installation Wizard Launcher     ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo Starting installation wizard...
echo.

powershell -ExecutionPolicy Bypass -NoExit -File "%cd%\install_wizard.ps1"
