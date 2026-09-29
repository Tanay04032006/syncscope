@echo off
title SyncScope
cd /d "%~dp0"
python app.py --open
if errorlevel 1 (
  echo.
  echo SyncScope could not start. Make sure Python 3.10 or newer is installed.
  pause
)
