@echo off
REM FVG Scanner Startup Script
REM This batch file starts the Enhanced FVG Scanner

echo.
echo ===============================================
echo           Enhanced FVG Scanner
echo ===============================================
echo.
echo Starting FVG Scanner Dashboard...
echo Dashboard URL: http://127.0.0.1:8000
echo.

REM Change to the script directory
cd /d "%~dp0"

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)

REM Check if main.py exists
if not exist "main.py" (
    echo ERROR: main.py not found in current directory
    echo Please make sure you're running this from the FVG scanner folder
    pause
    exit /b 1
)

REM Display current directory
echo Current directory: %CD%
echo.

REM Start the scanner
echo Starting Python scanner...
echo.
python main.py

REM If we get here, the scanner stopped
echo.
echo ===============================================
echo Scanner has stopped
echo ===============================================
pause