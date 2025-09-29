# Click Multiplier

A small Python app that multiplies your left-clicks. For example, one physical click becomes five clicks.

## Features
- Toggle on/off with a global hotkey
- Configurable multiplier and interval
- GUI control panel (Tkinter) to enable/disable and adjust settings
- Left-click only; ignores right/middle clicks
- Safe-guard to avoid infinite recursion when generating synthetic clicks
- Windows Game Mode: low-level SendInput + polling for better compatibility in games

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

## Linux Run (GUI)
```bash
python main.py
```

Headless mode (no GUI):
```bash
python main.py --no-gui --multiplier 5 --interval 0.015 --toggle "x" --quit "<ctrl>+<alt>+q"
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

## Windows Run (GUI)
Standard mode:
```powershell
python .\main.py
```

Game Mode (برای بازی‌ها):
```powershell
python .\main.py --game-mode
```
- در Game Mode از SendInput سطح پایین و GetAsyncKeyState برای تشخیص کلیک چپ استفاده می‌شود و سازگاری در بازی‌ها بیشتر است.
- همچنان می‌توانید از GUI برای تغییر multiplier/interval و Toggle استفاده کنید.

Headless mode:
```powershell
python .\main.py --no-gui --multiplier 5 --interval 0.015 --toggle "x" --quit "<ctrl>+<alt>+q"
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

## Download from GitHub Actions
- پس از هر push یا اجرای دستی workflow، GitHub Actions فایل `click-multiplier.exe` را به عنوان artifact آپلود می‌کند.
- برای دانلود:
  1) به تب "Actions" در ریپو بروید.
  2) روی آخرین workflow "Build Windows EXE" کلیک کنید.
  3) بخش Artifacts را باز کرده و `click-multiplier-windows-x64` را دانلود کنید.

## Hotkeys
- Toggle: `x`
- Quit: `<ctrl>+<alt>+q`

You can change the multiplier and interval via flags.

## Notes
- Linux Wayland may limit global hooks; use X11 if needed.
- Some apps/games prohibit synthetic input. Use responsibly.