#!/usr/bin/env python3

import argparse
import threading
import time
from dataclasses import dataclass
from typing import Optional

try:
    import tkinter as tk
    from tkinter import ttk
except Exception:
    tk = None  # GUI may not be available in headless environments

try:
    from pynput import mouse, keyboard
except Exception:
    print("Missing dependency or unsupported environment. Install with: pip install -r requirements.txt")
    raise


@dataclass
class ClickConfig:
    click_multiplier: int = 5
    interval_between_clicks_seconds: float = 0.015
    enabled: bool = True
    toggle_hotkey: str = "<ctrl>+<alt>+m"
    quit_hotkey: str = "<ctrl>+<alt>+q"


class ClickService:
    """Manages click multiplication and input hooks with low overhead."""

    def __init__(self, config: ClickConfig) -> None:
        self.config = config
        self._mouse_controller = mouse.Controller()
        self._lock = threading.RLock()
        self._running = True
        self._synthesizing = False
        self._mouse_listener: Optional[mouse.Listener] = None
        self._hotkeys: Optional[keyboard.GlobalHotKeys] = None
        self._hotkeys_thread: Optional[threading.Thread] = None

    # ---------------- Internal click logic ----------------
    def _perform_extra_clicks(self, button: mouse.Button) -> None:
        with self._lock:
            if not self.config.enabled:
                return
            self._synthesizing = True
        try:
            for _ in range(max(0, self.config.click_multiplier - 1)):
                self._mouse_controller.click(button)
                time.sleep(max(0.0, self.config.interval_between_clicks_seconds))
        finally:
            with self._lock:
                self._synthesizing = False

    def on_click(self, _x: int, _y: int, button: mouse.Button, pressed: bool) -> None:
        if not pressed:
            return
        if button != mouse.Button.left:
            return
        with self._lock:
            if self._synthesizing or not self.config.enabled:
                return
        threading.Thread(target=self._perform_extra_clicks, args=(button,), daemon=True).start()

    # ---------------- Hotkeys ----------------
    def _hotkeys_loop(self) -> None:
        # Runs in background to keep hotkeys active
        self._hotkeys = keyboard.GlobalHotKeys({
            self.config.toggle_hotkey: self.toggle_enabled,
            self.config.quit_hotkey: self.quit,
        })
        with self._hotkeys:
            while self._running:
                time.sleep(0.2)

    # ---------------- Public controls ----------------
    def start(self) -> None:
        print("Click Multiplier service starting.")
        print(f" - Multiplier: {self.config.click_multiplier}")
        print(f" - Interval: {self.config.interval_between_clicks_seconds}s")
        print(f" - Toggle: {self.config.toggle_hotkey}")
        print(f" - Quit:   {self.config.quit_hotkey}")
        # Start hotkeys thread
        self._hotkeys_thread = threading.Thread(target=self._hotkeys_loop, daemon=True)
        self._hotkeys_thread.start()
        # Start mouse listener only if enabled to reduce overhead
        if self.config.enabled:
            self._start_mouse_listener()

    def _start_mouse_listener(self) -> None:
        with self._lock:
            if self._mouse_listener is not None:
                return
            self._mouse_listener = mouse.Listener(on_click=self.on_click)
            self._mouse_listener.start()

    def _stop_mouse_listener(self) -> None:
        with self._lock:
            if self._mouse_listener is None:
                return
            try:
                self._mouse_listener.stop()
            finally:
                self._mouse_listener = None

    def toggle_enabled(self) -> None:
        with self._lock:
            self.config.enabled = not self.config.enabled
            enabled = self.config.enabled
        if enabled:
            self._start_mouse_listener()
        else:
            self._stop_mouse_listener()
        print(f"[ClickMultiplier] Toggled: {'ON' if enabled else 'OFF'}")

    def quit(self) -> None:
        print("[ClickMultiplier] Quitting...")
        self._running = False
        self._stop_mouse_listener()

    def apply_multiplier(self, value: int) -> None:
        with self._lock:
            self.config.click_multiplier = max(1, int(value))

    def apply_interval(self, value: float) -> None:
        with self._lock:
            self.config.interval_between_clicks_seconds = max(0.0, float(value))


def parse_args() -> tuple[ClickConfig, bool]:
    parser = argparse.ArgumentParser(description="Multiply left mouse clicks.")
    parser.add_argument("--multiplier", type=int, default=5, help="Number of clicks per physical click (>=1)")
    parser.add_argument("--interval", type=float, default=0.015, help="Seconds between extra clicks")
    parser.add_argument("--toggle", type=str, default="<ctrl>+<alt>+m", help="Global hotkey to toggle on/off")
    parser.add_argument("--quit", type=str, default="<ctrl>+<alt>+q", help="Global hotkey to quit")
    parser.add_argument("--no-gui", action="store_true", help="Run without GUI control panel")
    args = parser.parse_args()

    multiplier = max(1, args.multiplier)
    interval = max(0.0, args.interval)
    cfg = ClickConfig(
        click_multiplier=multiplier,
        interval_between_clicks_seconds=interval,
        enabled=True,
        toggle_hotkey=args.toggle,
        quit_hotkey=args.quit,
    )
    return cfg, bool(args.no_gui)


def run_gui(service: ClickService) -> None:
    if tk is None:
        print("GUI not available; running headless.")
        while service._running:
            time.sleep(0.5)
        return

    root = tk.Tk()
    root.title("Click Multiplier")
    root.resizable(False, False)

    # Vars
    enabled_var = tk.BooleanVar(value=service.config.enabled)
    multiplier_var = tk.IntVar(value=service.config.click_multiplier)
    interval_var = tk.DoubleVar(value=service.config.interval_between_clicks_seconds)

    # Handlers
    def on_toggle() -> None:
        service.toggle_enabled()
        enabled_var.set(service.config.enabled)

    def on_multiplier_change(*_args) -> None:
        try:
            service.apply_multiplier(multiplier_var.get())
        except Exception:
            pass

    def on_interval_change(*_args) -> None:
        try:
            service.apply_interval(interval_var.get())
        except Exception:
            pass

    def on_quit() -> None:
        service.quit()
        root.after(150, root.destroy)

    # Layout
    pad = {"padx": 10, "pady": 6}
    frm = ttk.Frame(root)
    frm.grid(row=0, column=0, sticky="nsew", **pad)

    ttk.Label(frm, text="Status:").grid(row=0, column=0, sticky="w")
    status_lbl = ttk.Label(frm, text="ON" if enabled_var.get() else "OFF", foreground=("green" if enabled_var.get() else "red"))
    status_lbl.grid(row=0, column=1, sticky="w")

    def refresh_status_label() -> None:
        status_lbl.config(text=("ON" if service.config.enabled else "OFF"), foreground=("green" if service.config.enabled else "red"))
        root.after(300, refresh_status_label)

    refresh_status_label()

    ttk.Button(frm, text="Toggle (Enable/Disable)", command=on_toggle).grid(row=1, column=0, columnspan=2, sticky="ew")

    ttk.Label(frm, text="Multiplier:").grid(row=2, column=0, sticky="w")
    spn_mult = tk.Spinbox(frm, from_=1, to=50, textvariable=multiplier_var, width=6, command=on_multiplier_change)
    spn_mult.grid(row=2, column=1, sticky="ew")
    multiplier_var.trace_add("write", on_multiplier_change)

    ttk.Label(frm, text="Interval (s):").grid(row=3, column=0, sticky="w")
    spn_int = tk.Spinbox(frm, from_=0.0, to=0.2, increment=0.005, textvariable=interval_var, width=6, command=on_interval_change)
    spn_int.grid(row=3, column=1, sticky="ew")
    interval_var.trace_add("write", on_interval_change)

    ttk.Label(frm, text=f"Hotkeys: Toggle {service.config.toggle_hotkey} | Quit {service.config.quit_hotkey}").grid(row=4, column=0, columnspan=2, sticky="w")
    ttk.Label(frm, text="Only affects LEFT mouse button").grid(row=5, column=0, columnspan=2, sticky="w")

    ttk.Button(frm, text="Quit", command=on_quit).grid(row=6, column=0, columnspan=2, sticky="ew")

    root.protocol("WM_DELETE_WINDOW", on_quit)
    root.mainloop()


def main() -> int:
    config, no_gui = parse_args()
    service = ClickService(config)
    service.start()
    if no_gui:
        # Headless mode
        try:
            while service._running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            service.quit()
    else:
        run_gui(service)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())