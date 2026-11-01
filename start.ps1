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
    pip install -r requirements.txt --quiet
}

# 5. Launch FastAPI backend
Write-Host "[*] Starting FastAPI Backend on 127.0.0.1:8000..." -ForegroundColor Green
$ProcessInfo = New-Object System.Diagnostics.ProcessStartInfo
$ProcessInfo.FileName = "python"
$ProcessInfo.Arguments = "-m uvicorn backend.main:app --host 127.0.0.1 --port 8000"
$ProcessInfo.UseShellExecute = $false
$Process = [System.Diagnostics.Process]::Start($ProcessInfo)

Start-Sleep -Seconds 2

# 6. Open Browser
Start-Process "http://127.0.0.1:8000/"

Write-Host "[✓] Hardware Optimizer is now active at http://127.0.0.1:8000/" -ForegroundColor Green
Write-Host "Press [Enter] to terminate the local server..." -ForegroundColor Gray
Read-Host

if (-not $Process.HasExited) {
    $Process.Kill()
}
