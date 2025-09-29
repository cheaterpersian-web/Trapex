# Trapex

## HSV Calibration Tool (Safe)

This repository includes a safe HSV calibration utility to help you tune color thresholds on webcam or video input. It does not automate gameplay or control mouse/keyboard.

### Quick Start

1) Setup environment and install deps

```bash
./scripts/setup.sh
```

2) Run the calibrator (webcam index 0 by default)

```bash
./scripts/run_calibrator.sh
```

To select a different source, pass `--source` with webcam index like `1` or a file path:

```bash
./scripts/run_calibrator.sh --source 0 --width 1280 --height 720
./scripts/run_calibrator.sh --source path/to/video.mp4
```

### Controls

- H_low / S_low / V_low and H_high / S_high / V_high: HSV thresholds
- ROI: Size of the centered square region of interest
- MinPix: Minimum pixel count threshold (display only)
- Blur: Gaussian blur kernel size (odd values)
- OpenIt / CloseIt: Morphological operations (noise removal/fill)
- Keys: ESC or q (quit), space (pause), s (save), l (load)
- Slots: 1..9 تغییر اسلات پروفایل (ذخیره/لود در `calibrations/slot_<n>.json`)
- ROI move: f/h (چپ/راست)، t/g (بالا/پایین)، r (مرکز)
- ROI size: - و = (کوچک/بزرگ با گام `--roi-step`)
- Overlay: o (نمایش کانتور/باکس)، Mask: m (باز/بستن پنجره ماسک)

### Profiles

- Default profile path: `calibrations/default_hsv.json`
- Save (s) and load (l) work when `--profile` is provided (default set).

### Advanced usage

```bash
./scripts/run_calibrator.sh \
  --source 0 \
  --width 1280 --height 720 \
  --profile-dir calibrations \
  --slot 1 \
  --profile calibrations/red_target.json \
  --h-low 0 --s-low 150 --v-low 150 \
  --h-high 10 --s-high 255 --v-high 255 \
  --roi 60 --roi-step 10 --min-pixels 25 --min-area 40 --blur 5 \
  --open-iter 1 --close-iter 1 \
  --log-csv calibrations/events.csv
```

### Notes

- Requires Python 3.9+.
- If you use a video file, the pause (space) key freezes the current frame for inspection.

## Windows .exe

Automated builds produce a standalone `.exe` using PyInstaller.

- CI artifacts: Go to the repository's Actions tab, open the latest "build-windows-exe" run on your branch, and download the `HSVCalibrator-win64.zip` artifact.
- Releases: Push a tag like `v0.1.0` to trigger a release upload of the zip.

### Build locally on Windows

1) Open PowerShell in the repo root and (optional) allow script execution for this session:

```powershell
Set-ExecutionPolicy -Scope Process RemoteSigned
```

2) Build the exe (creates `dist/HSVCalibrator.exe` and zip):

```powershell
./scripts/build_windows.ps1 -Clean
```

Run the program by double-clicking `dist/HSVCalibrator.exe` or from terminal:

```powershell
./dist/HSVCalibrator.exe --source 0 --width 1280 --height 720 --profile-dir calibrations --slot 1
```