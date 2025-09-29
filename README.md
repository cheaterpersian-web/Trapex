# Click Multiplier

A small Python app that multiplies your left-clicks. For example, one physical click becomes five clicks.

## Features
- Toggle on/off with a global hotkey
- Configurable multiplier and interval
- Safe-guard to avoid infinite recursion when generating synthetic clicks

## Requirements
- Python 3.8+
- Desktop session with input access
  - Linux: X11 works best; Wayland may restrict global hooks
  - Windows: Works out of the box

## Linux Setup
```bash
cd /workspace
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Linux Run
```bash
python main.py --multiplier 5 --interval 0.015 --toggle "<ctrl>+<alt>+m" --quit "<ctrl>+<alt>+q"
```

## Windows Setup
1. Install Python for Windows from the Microsoft Store or `python.org`.
2. Open PowerShell and run:
```powershell
cd PATH\TO\PROJECT
py -3 -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Windows Run
```powershell
python .\main.py --multiplier 5 --interval 0.015 --toggle "<ctrl>+<alt>+m" --quit "<ctrl>+<alt>+q"
```

## Build Windows EXE
Option A (PowerShell):
```powershell
./build_windows.ps1
```

Option B (Batch):
```bat
build_windows.bat
```

The executable will be at `dist/click-multiplier.exe`.

## Hotkeys
- Toggle: `<ctrl>+<alt>+m`
- Quit: `<ctrl>+<alt>+q`

You can change the multiplier and interval via flags.

## Notes
- Linux Wayland may limit global hooks; use X11 if needed.
- Some apps/games prohibit synthetic input. Use responsibly.