#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Navigate to project root (directory of this script)
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host "==> Preparing virtual environment" -ForegroundColor Cyan
if (-not (Test-Path .venv)) {
    py -3 -m venv .venv
}

$activate = Join-Path .venv 'Scripts' 'Activate.ps1'
if (-not (Test-Path $activate)) {
    throw "Virtual environment activation script not found: $activate"
}
. $activate

Write-Host "==> Installing dependencies" -ForegroundColor Cyan
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

Write-Host "==> Building executable with PyInstaller" -ForegroundColor Cyan
# Build a single-file executable without console window. Remove --noconsole to keep console.
pyinstaller --name click-multiplier --onefile --noconsole main.py

Write-Host "==> Build complete. Output: .\dist\click-multiplier.exe" -ForegroundColor Green