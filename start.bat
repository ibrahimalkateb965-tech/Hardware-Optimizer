@echo off
setlocal enabledelayedexpansion

title Windows Hardware Diagnostics & Optimizer
echo ======================================================================
echo    Windows Hardware Diagnostics & Optimizer (Hook 31)
echo    Powered by GLM-5.3-Flash via OpenCode Go ^& FastAPI
echo ======================================================================
echo.

cd /d "%~dp0"

:: 1. Check Python installation
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python 3.12+ was not found on PATH.
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

:: 2. Create virtual environment if missing
if not exist ".venv" (
    echo [*] Initializing virtual environment in .venv...
    python -m venv .venv
)

:: 3. Activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

:: 4. Verify backend dependencies
echo [*] Checking Python dependencies...
python -m pip install -r requirements.txt --quiet

:: 5. Launch through dynamic port manager and auto-browser launcher
echo [*] Launching application runner (Auto-Port Detection active)...
echo.
python run.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [!] Server exited with an error code.
    pause
)
