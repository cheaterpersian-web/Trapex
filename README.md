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
- Keys: ESC or q to quit, space to pause, s to save profile, l to load profile

### Profiles

- Default profile path: `calibrations/default_hsv.json`
- Save (s) and load (l) work when `--profile` is provided (default set).

### Advanced usage

```bash
./scripts/run_calibrator.sh \
  --source 0 \
  --width 1280 --height 720 \
  --profile calibrations/red_target.json \
  --h-low 0 --s-low 150 --v-low 150 \
  --h-high 10 --s-high 255 --v-high 255 \
  --roi 60 --min-pixels 25 --blur 5 \
  --open-iter 1 --close-iter 1
```

### Notes

- Requires Python 3.9+.
- If you use a video file, the pause (space) key freezes the current frame for inspection.