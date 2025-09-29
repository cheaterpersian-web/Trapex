#!/usr/bin/env python3
"""
HSV Calibrator (Safe, Non-interactive Tool)

This tool helps you calibrate HSV color thresholds on live webcam input or a video file.
It draws a centered ROI, applies optional blur and morphology, counts matching pixels,
and shows FPS. You can save/load HSV profiles to a JSON file.

Key bindings:
  - ESC / q: quit
  - s: save current settings to --profile
  - l: load settings from --profile
  - space: pause/resume video

This script does NOT control mouse/keyboard and is NOT a gameplay automation tool.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from typing import Tuple, Optional

import cv2
import numpy as np


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

    source = parse_video_source(args.source)
    cap = cv2.VideoCapture(source)
    if args.width > 0:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(args.width))
    if args.height > 0:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(args.height))

    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video source: {args.source}")

    kernel = np.ones((3, 3), np.uint8)
    prev_time = time.time()
    frame_count = 0
    fps = 0.0
    paused = False

    while True:
        if not paused:
            ok, frame = cap.read()
            if not ok:
                break
        else:
            # When paused, still show the last frame and UI updates
            ok = True

        h, w = frame.shape[:2]
        roi_size = max(10, cv2.getTrackbarPos("ROI", "controls"))
        cx, cy = w // 2, h // 2
        left = max(0, cx - roi_size // 2)
        right = min(w, cx + roi_size // 2)
        top = max(0, cy - roi_size // 2)
        bottom = min(h, cy + roi_size // 2)

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
        mask = cv2.inRange(hsv, low, high)
        if open_it > 0:
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=open_it)
        if close_it > 0:
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=close_it)

        count = int(cv2.countNonZero(mask))
        min_pixels = max(0, cv2.getTrackbarPos("MinPix", "controls"))

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

        cv2.imshow("frame", frame)
        cv2.imshow("mask", mask)

        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord("q")):
            break
        if key == ord(" "):
            paused = not paused
        if key == ord("s"):
            if args.profile:
                save_profile(
                    args.profile,
                    HsvBounds.from_arrays(low, high),
                    roi_size=roi_size,
                    min_pixels=min_pixels,
                    blur=blur_k,
                )
                print(f"Saved profile to {args.profile}")
            else:
                print("--profile not set; cannot save.")
        if key == ord("l"):
            if args.profile:
                loaded = load_profile(args.profile)
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
                    print(f"Loaded profile from {args.profile}")
                else:
                    print(f"Profile not found: {args.profile}")
            else:
                print("--profile not set; cannot load.")

    cap.release()
    cv2.destroyAllWindows()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HSV Calibration tool (safe)")
    parser.add_argument("--source", type=str, default="0", help="Webcam index like '0' or a video file path")
    parser.add_argument("--width", type=int, default=0, help="Requested capture width (0 = default)")
    parser.add_argument("--height", type=int, default=0, help="Requested capture height (0 = default)")
    parser.add_argument("--profile", type=str, default="calibrations/default_hsv.json", help="JSON file to save/load HSV profile")

    # Initial defaults
    parser.add_argument("--h-low", dest="h_low", type=int, default=0)
    parser.add_argument("--s-low", dest="s_low", type=int, default=150)
    parser.add_argument("--v-low", dest="v_low", type=int, default=150)
    parser.add_argument("--h-high", dest="h_high", type=int, default=10)
    parser.add_argument("--s-high", dest="s_high", type=int, default=255)
    parser.add_argument("--v-high", dest="v_high", type=int, default=255)
    parser.add_argument("--roi", type=int, default=40, help="ROI square side length in pixels")
    parser.add_argument("--min-pixels", dest="min_pixels", type=int, default=12)
    parser.add_argument("--blur", type=int, default=3, help="Gaussian blur kernel size (odd values)")
    parser.add_argument("--open-iter", dest="open_iter", type=int, default=1, help="Morphological open iterations")
    parser.add_argument("--close-iter", dest="close_iter", type=int, default=1, help="Morphological close iterations")

    parser.add_argument("--controls-width", type=int, default=420)
    parser.add_argument("--controls-height", type=int, default=360)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    run_calibrator(args)


if __name__ == "__main__":
    main()

