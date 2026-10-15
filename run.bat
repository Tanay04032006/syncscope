@echo off
setlocal
title SyncScope - IPC Laboratory
pushd "%~dp0" || goto folder_error
if not exist "app.py" goto files_error
if not exist "static\index.html" goto files_error

rem Prefer a project environment, then the Windows launcher, then PATH.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
  if not errorlevel 1 goto venv
)
py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if not errorlevel 1 goto py_launcher
python -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if not errorlevel 1 goto python_path
echo Python 3.10 or newer was not found.
echo Install Python from https://www.python.org/downloads/ and enable Add Python to PATH.
goto failed

:venv
".venv\Scripts\python.exe" -u app.py --open --auto-port %*
goto finished
:py_launcher
py -3 -u app.py --open --auto-port %*
goto finished
:python_path
python -u app.py --open --auto-port %*
goto finished
:finished
if errorlevel 1 goto failed
popd
exit /b 0
:files_error
echo Project files are missing. Extract the complete project folder before running.
goto failed
:folder_error
echo Could not open the project folder.
pause
exit /b 1
:failed
echo.
echo SyncScope could not start. Check the message above.
pause
popd
exit /b 1
