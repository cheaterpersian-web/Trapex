#!/usr/bin/env python3
"""
HSV Calibrator (Safe, Non-interactive Tool)

This tool helps you calibrate HSV color thresholds on live webcam input or a video file.
It draws a ROI, applies optional blur and morphology, counts matching pixels, overlays
contours, and shows FPS. You can save/load HSV profiles to a JSON file.

Key bindings:
  - ESC / q: quit; space: pause/resume video
  - s: save profile (to --profile or slot file); l: load profile
  - 1..9: switch profile slot (uses --profile-dir/slot_<n>.json)
  - f/h: move ROI left/right; t/g: move ROI up/down; r: recenter ROI
  - -/=: decrease/increase ROI size by --roi-step
  - o: toggle contour overlay; m: toggle mask window

This script does NOT control mouse/keyboard and is NOT a gameplay automation tool.
"""

from __future__ import annotations

import argparse
import sys
import traceback
import csv
import json
import os
import time
from dataclasses import dataclass
from typing import Tuple, Optional

import cv2
import numpy as np
import mss


# ------------------------- Utility structures -------------------------

@dataclass
class HsvBounds:
    low: Tuple[int, int, int]
    high: Tuple[int, int, int]

    @staticmethod
    def from_arrays(low: np.ndarray, high: np.ndarray) -> "HsvBounds":
        low_t = (int(low[0]), int(low[1]), int(low[2]))
        high_t = (int(high[0]), int(high[1]), int(high[2]))
        return HsvBounds(low=low_t, high=high_t)


def ensure_odd(value: int) -> int:
    return value if value % 2 == 1 else value + 1


def parse_video_source(source: str) -> int | str:
    """Return int for numeric webcam index, else pass through string path."""
    try:
        # If it's an integer string (e.g., "0"), interpret as webcam index
        return int(source)
    except ValueError:
        return source


def map_backend_flag(name: str) -> int:
    name_l = (name or "").strip().lower()
    if name_l in ("msmf", "mf"):
        return cv2.CAP_MSMF
    if name_l in ("dshow", "directshow"):
        return cv2.CAP_DSHOW
    if name_l in ("v4l", "v4l2"):
        return cv2.CAP_V4L2
    if name_l in ("ffmpeg", "av"):
        return cv2.CAP_FFMPEG
    return cv2.CAP_ANY


def try_open_capture(src: int | str, backend: int, width: int, height: int) -> Optional[cv2.VideoCapture]:
    cap = cv2.VideoCapture(src, backend)
    if not cap or not cap.isOpened():
        if cap:
            cap.release()
        return None
    if width > 0:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(width))
    if height > 0:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(height))
    return cap


def save_profile(path: str, hsv: HsvBounds, roi_size: int, min_pixels: int, blur: int) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    payload = {
        "low": list(hsv.low),
        "high": list(hsv.high),
        "roi_size": int(roi_size),
        "min_pixels": int(min_pixels),
        "blur": int(blur),
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_profile(path: str) -> Optional[Tuple[HsvBounds, int, int, int]]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    hsv = HsvBounds(low=tuple(data.get("low", [0, 0, 0])), high=tuple(data.get("high", [179, 255, 255])))
    roi_size = int(data.get("roi_size", 40))
    min_pixels = int(data.get("min_pixels", 12))
    blur = int(data.get("blur", 3))
    return hsv, roi_size, min_pixels, blur


def make_slot_profile_path(profile_dir: str, slot: int) -> str:
    os.makedirs(profile_dir or ".", exist_ok=True)
    return os.path.join(profile_dir or ".", f"slot_{int(slot)}.json")


# ------------------------- Main calibrator -------------------------

def run_calibrator(args: argparse.Namespace) -> None:
    cv2.namedWindow("controls", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("controls", args.controls_width, args.controls_height)

    def _noop(_: int) -> None:
        pass

    # Trackbars for HSV and processing params
    cv2.createTrackbar("H_low",  "controls", args.h_low,  179, _noop)
    cv2.createTrackbar("S_low",  "controls", args.s_low,  255, _noop)
    cv2.createTrackbar("V_low",  "controls", args.v_low,  255, _noop)
    cv2.createTrackbar("H_high", "controls", args.h_high, 179, _noop)
    cv2.createTrackbar("S_high", "controls", args.s_high, 255, _noop)
    cv2.createTrackbar("V_high", "controls", args.v_high, 255, _noop)
    cv2.createTrackbar("ROI",    "controls", args.roi,     800, _noop)
    cv2.createTrackbar("MinPix", "controls", args.min_pixels, 5000, _noop)
    cv2.createTrackbar("Blur",   "controls", args.blur,     31, _noop)
    cv2.createTrackbar("OpenIt", "controls", args.open_iter, 5, _noop)
    cv2.createTrackbar("CloseIt","controls", args.close_iter,5, _noop)

    # State
    current_slot = max(1, min(9, int(args.slot)))
    overlay_on = True
    show_mask_window = True
    roi_cx = None  # initialized on first frame
    roi_cy = None
    above_prev = False
    csv_writer = None
    csv_file = None
    if args.log_csv:
        new_file = not os.path.exists(args.log_csv)
        os.makedirs(os.path.dirname(args.log_csv) or ".", exist_ok=True)
        csv_file = open(args.log_csv, "a", newline="", encoding="utf-8")
        csv_writer = csv.writer(csv_file)
        if new_file:
            csv_writer.writerow([
                "timestamp_utc", "slot", "count", "min_pixels", "largest_area",
                "min_area", "coverage", "fps", "left", "top", "right", "bottom",
            ])

    # Try to load a profile if provided and exists
    if args.profile:
        loaded = load_profile(args.profile)
        if loaded is not None:
            hsv, roi_size, min_pixels, blur = loaded
            cv2.setTrackbarPos("H_low",  "controls", hsv.low[0])
            cv2.setTrackbarPos("S_low",  "controls", hsv.low[1])
            cv2.setTrackbarPos("V_low",  "controls", hsv.low[2])
            cv2.setTrackbarPos("H_high", "controls", hsv.high[0])
            cv2.setTrackbarPos("S_high", "controls", hsv.high[1])
            cv2.setTrackbarPos("V_high", "controls", hsv.high[2])
            cv2.setTrackbarPos("ROI",    "controls", roi_size)
            cv2.setTrackbarPos("MinPix", "controls", min_pixels)
            cv2.setTrackbarPos("Blur",   "controls", blur)
    else:
        # Fallback to slot-based profile
        slot_profile = make_slot_profile_path(args.profile_dir, current_slot)
        loaded = load_profile(slot_profile)
        if loaded is not None:
            hsv, roi_size, min_pixels, blur = loaded
            cv2.setTrackbarPos("H_low",  "controls", hsv.low[0])
            cv2.setTrackbarPos("S_low",  "controls", hsv.low[1])
            cv2.setTrackbarPos("V_low",  "controls", hsv.low[2])
            cv2.setTrackbarPos("H_high", "controls", hsv.high[0])
            cv2.setTrackbarPos("S_high", "controls", hsv.high[1])
            cv2.setTrackbarPos("V_high", "controls", hsv.high[2])
            cv2.setTrackbarPos("ROI",    "controls", roi_size)
            cv2.setTrackbarPos("MinPix", "controls", min_pixels)
            cv2.setTrackbarPos("Blur",   "controls", blur)

    # Determine initial source: explicit --source, else positional input_file, else default '0'
    source_str = args.source if str(args.source).strip() != "" else (args.input_file if str(getattr(args, "input_file", "")).strip() != "" else "0")
    source = parse_video_source(source_str)
    screen_mode = isinstance(source, str) and str(source).strip().lower() == "screen"
    backend_sequence = []
    # Prefer specific backend if provided
    preferred = map_backend_flag(args.backend)
    if preferred != cv2.CAP_ANY:
        backend_sequence.append(preferred)
    # On Windows, try MSMF then DSHOW; on Linux, V4L2 then ANY
    if os.name == 'nt':
        if cv2.CAP_MSMF not in backend_sequence:
            backend_sequence.append(cv2.CAP_MSMF)
        if cv2.CAP_DSHOW not in backend_sequence:
            backend_sequence.append(cv2.CAP_DSHOW)
    else:
        if cv2.CAP_V4L2 not in backend_sequence:
            backend_sequence.append(cv2.CAP_V4L2)
    if cv2.CAP_ANY not in backend_sequence:
        backend_sequence.append(cv2.CAP_ANY)

    cap = None
    sct = None
    screen_mon = None
    if screen_mode:
        sct = mss.mss()
        monitors = sct.monitors
        # 0 = virtual bounding box of all monitors, 1 = primary
        mon_index = int(args.screen_monitor)
        if mon_index < 0 or mon_index >= len(monitors):
            mon_index = 1 if len(monitors) > 1 else 0
        screen_mon = monitors[mon_index]
    else:
        if isinstance(source, int):
            # Probe multiple camera indices if requested
            candidates = [source] if not args.probe else list(range(args.probe_start, args.probe_end + 1))
            for b in backend_sequence:
                for idx in candidates:
                    cap = try_open_capture(idx, b, args.width, args.height)
                    if cap is not None:
                        source = idx
                        break
                if cap is not None:
                    break
        else:
            # File path
            for b in backend_sequence:
                cap = try_open_capture(source, b, args.width, args.height)
                if cap is not None:
                    break

    if cap is None and not screen_mode:
        # On Windows without a camera, offer a file picker if no input_file was provided
        default_like_cam = str(args.source).strip() in ("", "0") and str(getattr(args, "input_file", "")).strip() == ""
        if os.name == 'nt' and default_like_cam:
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                file_path = filedialog.askopenfilename(title="Select a video file",
                                                       filetypes=[
                                                           ("Video Files", ".mp4 .avi .mov .mkv .m4v"),
                                                           ("All Files", "*.*"),
                                                       ])
                root.destroy()
                if file_path:
                    source = file_path
                    for b in backend_sequence:
                        cap = try_open_capture(source, b, args.width, args.height)
                        if cap is not None:
                            break
            except Exception:
                pass
    if cap is None and not screen_mode:
        raise RuntimeError(f"Cannot open video source: {args.source or getattr(args, 'input_file', '')}")

    kernel = np.ones((3, 3), np.uint8)
    prev_time = time.time()
    frame_count = 0
    fps = 0.0
    paused = False

    while True:
        if not paused:
            if screen_mode:
                raw = np.array(sct.grab(screen_mon))  # BGRA
                frame = cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)
                ok = True
            else:
                ok, frame = cap.read()
                if not ok:
                    break
        else:
            # When paused, still show the last frame and UI updates
            ok = True

        h, w = frame.shape[:2]
        roi_size = max(10, cv2.getTrackbarPos("ROI", "controls"))
        if roi_cx is None or roi_cy is None:
            roi_cx, roi_cy = w // 2, h // 2
        half = roi_size // 2
        # Clamp center so ROI stays inside frame
        roi_cx = max(half, min(w - half, roi_cx))
        roi_cy = max(half, min(h - half, roi_cy))
        left = roi_cx - half
        right = roi_cx + half
        top = roi_cy - half
        bottom = roi_cy + half

        roi = frame[top:bottom, left:right]

        blur_k = max(1, cv2.getTrackbarPos("Blur", "controls"))
        blur_k = ensure_odd(blur_k)
        if blur_k > 1:
            roi = cv2.GaussianBlur(roi, (blur_k, blur_k), 0)

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        low = np.array([
            cv2.getTrackbarPos("H_low", "controls"),
            cv2.getTrackbarPos("S_low", "controls"),
            cv2.getTrackbarPos("V_low", "controls"),
        ], dtype=np.uint8)
        high = np.array([
            cv2.getTrackbarPos("H_high", "controls"),
            cv2.getTrackbarPos("S_high", "controls"),
            cv2.getTrackbarPos("V_high", "controls"),
        ], dtype=np.uint8)

        open_it = max(0, cv2.getTrackbarPos("OpenIt", "controls"))
        close_it = max(0, cv2.getTrackbarPos("CloseIt", "controls"))
        # Multi-color support: combine slots if requested
        mask = cv2.inRange(hsv, low, high)
        if args.combine_slots:
            for slot in args.combine_slots:
                slot_path = make_slot_profile_path(args.profile_dir, slot)
                loaded = load_profile(slot_path)
                if loaded is None:
                    continue
                hsv_b, _, _, _ = loaded
                low_b = np.array([hsv_b.low[0], hsv_b.low[1], hsv_b.low[2]], dtype=np.uint8)
                high_b = np.array([hsv_b.high[0], hsv_b.high[1], hsv_b.high[2]], dtype=np.uint8)
                mask_b = cv2.inRange(hsv, low_b, high_b)
                mask = cv2.bitwise_or(mask, mask_b)
        if open_it > 0:
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=open_it)
        if close_it > 0:
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=close_it)

        count = int(cv2.countNonZero(mask))
        min_pixels = max(0, cv2.getTrackbarPos("MinPix", "controls"))

        # Contours and overlay
        largest_area = 0.0
        try:
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                largest = max(contours, key=cv2.contourArea)
                largest_area = float(cv2.contourArea(largest))
                if overlay_on and largest_area >= float(args.min_area):
                    x, y, w_box, h_box = cv2.boundingRect(largest)
                    cv2.rectangle(frame, (left + x, top + y), (left + x + w_box, top + y + h_box), (0, 255, 255), 2)
        except Exception:
            pass

        roi_area = max(1, roi.shape[0] * roi.shape[1])
        coverage = float(count) / float(roi_area)

        color = (0, 255, 0) if count >= min_pixels else (0, 0, 255)
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.putText(
            frame, f"Count: {count} / Min: {min_pixels}", (10, 26),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA,
        )

        # FPS metering
        frame_count += 1
        now = time.time()
        if now - prev_time >= 0.5:
            fps = frame_count / (now - prev_time)
            prev_time = now
            frame_count = 0
        cv2.putText(
            frame, f"FPS: {fps:.1f}", (10, 52),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 255, 200), 2, cv2.LINE_AA,
        )

        cv2.putText(
            frame, f"Area: {largest_area:.0f} Cov: {coverage*100:.1f}%", (10, 78),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 255), 2, cv2.LINE_AA,
        )
        cv2.putText(
            frame, f"Slot:{current_slot} Overlay:{'ON' if overlay_on else 'OFF'}", (10, 104),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 220, 255), 2, cv2.LINE_AA,
        )

        # Rising-edge logging
        above = (count >= min_pixels) and (largest_area >= float(args.min_area))
        if csv_writer is not None and above and not above_prev:
            ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            csv_writer.writerow([
                ts, current_slot, count, min_pixels, int(largest_area), int(args.min_area),
                round(coverage, 4), float(fps), int(left), int(top), int(right), int(bottom),
            ])
        above_prev = above

        cv2.imshow("frame", frame)
        if show_mask_window:
            cv2.imshow("mask", mask)
        else:
            try:
                cv2.destroyWindow("mask")
            except Exception:
                pass

        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord("q")):
            break
        if key == ord(" "):
            paused = not paused
        # Profile slots: 1..9 select current slot and try loading it
        if key in [ord(str(n)) for n in range(1, 10)]:
            current_slot = int(chr(key))
            slot_profile = make_slot_profile_path(args.profile_dir, current_slot)
            loaded = load_profile(slot_profile)
            if loaded is not None:
                hsv_b, roi_size_b, min_pixels_b, blur_b = loaded
                cv2.setTrackbarPos("H_low",  "controls", hsv_b.low[0])
                cv2.setTrackbarPos("S_low",  "controls", hsv_b.low[1])
                cv2.setTrackbarPos("V_low",  "controls", hsv_b.low[2])
                cv2.setTrackbarPos("H_high", "controls", hsv_b.high[0])
                cv2.setTrackbarPos("S_high", "controls", hsv_b.high[1])
                cv2.setTrackbarPos("V_high", "controls", hsv_b.high[2])
                cv2.setTrackbarPos("ROI",    "controls", roi_size_b)
                cv2.setTrackbarPos("MinPix", "controls", min_pixels_b)
                cv2.setTrackbarPos("Blur",   "controls", blur_b)
                print(f"Loaded slot {current_slot}: {slot_profile}")
            else:
                print(f"Slot {current_slot} has no profile yet. Press 's' to save.")

        # ROI movement via keys: f/h (left/right), t/g (up/down)
        if key == ord("f"):
            roi_cx = (roi_cx or 0) - args.roi_step
        if key == ord("h"):
            roi_cx = (roi_cx or 0) + args.roi_step
        if key == ord("t"):
            roi_cy = (roi_cy or 0) - args.roi_step
        if key == ord("g"):
            roi_cy = (roi_cy or 0) + args.roi_step

        # ROI size adjust and recenter
        if key == ord("-"):
            cv2.setTrackbarPos("ROI", "controls", max(10, roi_size - args.roi_step))
        if key == ord("=") or key == ord("+"):
            cv2.setTrackbarPos("ROI", "controls", min(800, roi_size + args.roi_step))
        if key == ord("r"):
            roi_cx, roi_cy = w // 2, h // 2

        # Overlay and mask window toggles
        if key == ord("o"):
            overlay_on = not overlay_on
        if key == ord("m"):
            show_mask_window = not show_mask_window
        if key in (ord("s"), ord("S")):
            target_path = args.profile if args.profile else make_slot_profile_path(args.profile_dir, current_slot)
            save_profile(
                target_path,
                HsvBounds.from_arrays(low, high),
                roi_size=roi_size,
                min_pixels=min_pixels,
                blur=blur_k,
            )
            if args.profile:
                print(f"Saved profile to {args.profile}")
            else:
                print(f"Saved slot {current_slot} profile to {target_path}")
        if key in (ord("l"), ord("L")):
            source_path = args.profile if args.profile else make_slot_profile_path(args.profile_dir, current_slot)
            loaded = load_profile(source_path)
            if loaded is not None:
                hsv_b, roi_size_b, min_pixels_b, blur_b = loaded
                cv2.setTrackbarPos("H_low",  "controls", hsv_b.low[0])
                cv2.setTrackbarPos("S_low",  "controls", hsv_b.low[1])
                cv2.setTrackbarPos("V_low",  "controls", hsv_b.low[2])
                cv2.setTrackbarPos("H_high", "controls", hsv_b.high[0])
                cv2.setTrackbarPos("S_high", "controls", hsv_b.high[1])
                cv2.setTrackbarPos("V_high", "controls", hsv_b.high[2])
                cv2.setTrackbarPos("ROI",    "controls", roi_size_b)
                cv2.setTrackbarPos("MinPix", "controls", min_pixels_b)
                cv2.setTrackbarPos("Blur",   "controls", blur_b)
                if args.profile:
                    print(f"Loaded profile from {args.profile}")
                else:
                    print(f"Loaded slot {current_slot} profile from {source_path}")
            else:
                print(f"Profile not found: {source_path}")

    if cap is not None:
        cap.release()
    if sct is not None:
        try:
            sct.close()
        except Exception:
            pass
    if csv_file is not None:
        try:
            csv_file.close()
        except Exception:
            pass
    cv2.destroyAllWindows()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HSV Calibration tool (safe)")
    parser.add_argument("input_file", nargs="?", default="", help="Optional video file path")
    parser.add_argument("--source", type=str, default="0", help="Webcam index like '0' or a video file path")
    parser.add_argument("--width", type=int, default=0, help="Requested capture width (0 = default)")
    parser.add_argument("--height", type=int, default=0, help="Requested capture height (0 = default)")
    parser.add_argument("--profile", type=str, default="", help="JSON file to save/load a single HSV profile (overrides slots)")
    parser.add_argument("--profile-dir", type=str, default="calibrations", help="Directory to save/load slot profiles like slot_1.json")
    parser.add_argument("--slot", type=int, default=1, help="Initial profile slot (1-9)")

    # Initial defaults
    parser.add_argument("--h-low", dest="h_low", type=int, default=0)
    parser.add_argument("--s-low", dest="s_low", type=int, default=150)
    parser.add_argument("--v-low", dest="v_low", type=int, default=150)
    parser.add_argument("--h-high", dest="h_high", type=int, default=10)
    parser.add_argument("--s-high", dest="s_high", type=int, default=255)
    parser.add_argument("--v-high", dest="v_high", type=int, default=255)
    parser.add_argument("--roi", type=int, default=40, help="ROI square side length in pixels")
    parser.add_argument("--roi-step", type=int, default=10, help="Step size for ROI move/resize keys")
    parser.add_argument("--min-pixels", dest="min_pixels", type=int, default=12)
    parser.add_argument("--blur", type=int, default=3, help="Gaussian blur kernel size (odd values)")
    parser.add_argument("--open-iter", dest="open_iter", type=int, default=1, help="Morphological open iterations")
    parser.add_argument("--close-iter", dest="close_iter", type=int, default=1, help="Morphological close iterations")
    parser.add_argument("--min-area", dest="min_area", type=int, default=0, help="Minimum contour area to draw/report (0 disables)")
    parser.add_argument("--log-csv", type=str, default="", help="Append detection events to this CSV file on rising edge")
    parser.add_argument("--combine-slots", type=int, nargs='*', default=[], help="Combine masks from these profile slots (e.g., --combine-slots 2 3 4)")

    parser.add_argument("--controls-width", type=int, default=420)
    parser.add_argument("--controls-height", type=int, default=360)
    parser.add_argument("--backend", type=str, default="", help="Preferred backend: msmf|dshow|v4l2|ffmpeg|any|screen")
    parser.add_argument("--probe", action="store_true", help="Probe camera indices if initial source fails")
    parser.add_argument("--probe-start", type=int, default=0)
    parser.add_argument("--probe-end", type=int, default=5)
    parser.add_argument("--screen-monitor", type=int, default=1, help="mss monitor index: 0=all, 1=primary, 2=secondary, ...")
    return parser


def _write_error_log(message: str) -> str:
    try:
        base = os.path.dirname(getattr(sys, 'executable', sys.argv[0]))
        path = os.path.join(base or '.', 'hsv_calibrator_error.log')
        with open(path, 'a', encoding='utf-8') as f:
            f.write(time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
            f.write('\n')
            f.write(message)
            f.write('\n' + ('=' * 60) + '\n')
        return path
    except Exception:
        return ''


def main() -> None:
    args = build_arg_parser().parse_args()
    try:
        run_calibrator(args)
    except Exception as exc:
        tb = traceback.format_exc()
        log_path = _write_error_log(tb)
        msg = f"An error occurred. Details were written to: {log_path or 'error log'}"
        print(msg, file=sys.stderr)
        # Best-effort Windows message box
        if os.name == 'nt':
            try:
                import ctypes  # type: ignore
                ctypes.windll.user32.MessageBoxW(0, msg, "HSV Calibrator", 0x10)
            except Exception:
                pass


if __name__ == "__main__":
    main()

