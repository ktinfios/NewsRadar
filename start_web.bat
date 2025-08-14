@echo off
title NewsRadar Web Interface

echo.
echo ========================================
echo    NewsRadar Web Interface Launcher
echo ========================================
echo.

cd /d "%~dp0"

echo [INFO] Checking Python environment...

REM Check if virtual environment exists
if exist "..\..\.venv\Scripts\python.exe" (
    echo [INFO] Using virtual environment
    set PYTHON_CMD=..\..\..venv\Scripts\python.exe
) else (
    echo [INFO] Using system Python
    set PYTHON_CMD=python
)

echo [INFO] Starting NewsRadar Web Interface...
echo [INFO] Web interface will be available at: http://localhost:5000
echo [INFO] Press Ctrl+C to stop the server
echo.

%PYTHON_CMD% start_web.py

echo.
echo [INFO] Web interface stopped.
pause
