@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0START_REGENESIS_AI.ps1"
if errorlevel 1 (
  echo.
  echo REGENESIS AI could not start. Read the error above.
)
pause
