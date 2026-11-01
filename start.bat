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
call .venv\Scripts\activate.bat

:: 4. Install dependencies if needed
echo [*] Verifying backend dependencies...
pip install -r requirements.txt -q

:: 5. Launch FastAPI backend
echo [*] Starting local optimization server on 127.0.0.1:8000...
start /b python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

:: 6. Wait for server and open browser
timeout /t 2 /nobreak >nul
echo [*] Launching web interface...
start http://127.0.0.1:8000/

echo.
echo [✓] System is running. Press any key to stop the server.
pause >nul
taskkill /f /im python.exe >nul 2>nul
