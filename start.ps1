# Windows Hardware Diagnostics & Optimizer Launcher (PowerShell)
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-Location -Path $PSScriptRoot

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   Windows Hardware Diagnostics & Optimizer (Hook 31)" -ForegroundColor Green
Write-Host "   Powered by GLM-5.3-Flash via OpenCode Go & FastAPI" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "[!] Python 3.12+ was not found on PATH."
    exit 1
}

# 2. Virtual Environment
if (-not (Test-Path ".venv")) {
    Write-Host "[*] Creating virtual environment (.venv)..." -ForegroundColor Yellow
    python -m venv .venv
}

# 3. Activate
$ActivateScript = Join-Path $PSScriptRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $ActivateScript) {
    & $ActivateScript
}

# 4. Requirements
if (Test-Path "requirements.txt") {
    Write-Host "[*] Checking Python dependencies..." -ForegroundColor Yellow
    python -m pip install -r requirements.txt --quiet
}

# 5. Launch through dynamic port manager
Write-Host "[*] Launching application runner (Auto-Port Detection active)..." -ForegroundColor Green
python run.py
