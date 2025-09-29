@echo off
setlocal enabledelayedexpansion

REM Change to the directory where this script resides
cd /d "%~dp0"

echo ==> Preparing virtual environment
if not exist .venv (
    py -3 -m venv .venv
)

call .venv\Scripts\activate.bat

echo ==> Installing dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

echo ==> Building executable with PyInstaller
pyinstaller --name click-multiplier --onefile --noconsole main.py

echo ==> Build complete. Output: .\dist\click-multiplier.exe
endlocal