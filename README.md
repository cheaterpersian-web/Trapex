# Click Multiplier

A small Python app that multiplies your left-clicks. For example, one physical click becomes five clicks.

## Features
- Toggle on/off with a global hotkey
- Configurable multiplier and interval
- Safe-guard to avoid infinite recursion when generating synthetic clicks

## Requirements
- Linux desktop session with input access (X11 works best; Wayland may restrict global hooks)
- Python 3.8+

## Setup
```bash
cd /workspace
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run
```bash
python main.py --multiplier 5 --interval 0.015 --toggle "<ctrl>+<alt>+m" --quit "<ctrl>+<alt>+q"
```

- Toggle hotkey: `<ctrl>+<alt>+m`
- Quit hotkey: `<ctrl>+<alt>+q`

You can change the multiplier and interval via flags.

## Notes
- On Wayland, global hooks may be limited; if hotkeys/listeners do not work, try an X11 session.
- Use responsibly; some applications and games may prohibit synthetic input.