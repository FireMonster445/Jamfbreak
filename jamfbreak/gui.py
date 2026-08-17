"""
jamfbreak.gui — minimalist black & white desktop GUI.

Launches a pywebview window (EdgeChromium/WebView2 on Windows) with an
embedded HTML/CSS/JS frontend. The Python side exposes an API object that
the JS polls for state (device info, console logs, status).

Usage:
    python -m jamfbreak.gui

The GUI reuses the exact same `rodo_pipeline.run_rodo_pipeline` as the CLI,
so both entry points use the same validation and controlled-reboot checks.
"""

from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

import webview

from . import device
from . import rodo_pipeline
from .gui_html import HTML


@dataclass
class LogEntry:
    text: str
    kind: str   # info | success | error | step
    tag: Optional[str]


class GuiApi:
    """
    Exposed to JavaScript as `window.pywebview.api`.

    Methods called from JS:
      - get_state() -> dict with status, status_text, device, logs
      - refresh()   -> re-detect device
      - start_bypass() -> run the bypass pipeline in a background thread
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._status: str = "searching"
        self._status_text: str = "Searching…"
        self._device: Optional[device.DeviceInfo] = None
        self._logs: list[LogEntry] = []
        self._patching = False
        threading.Thread(target=self._detect_loop, daemon=True).start()

    # ------------------------------------------------------------------ public
    def get_state(self) -> dict:
        with self._lock:
            return {
                "status": self._status,
                "status_text": self._status_text,
                "device": _device_to_dict(self._device) if self._device else None,
                "logs": [asdict(l) for l in self._logs],
            }

    def refresh(self) -> dict:
        self._log("Refreshing device list…", "info", None)
        threading.Thread(target=self._detect_once, daemon=True).start()
        return {"ok": True}

    def start_bypass(self) -> dict:
        """Run the bypass pipeline in a background thread. Returns immediately."""
        if self._patching:
            return {"ok": False, "error": "already bypassing"}
        if not self._device:
            return {"ok": False, "error": "no device"}
        self._patching = True
        with self._lock:
            self._status = "patching"
            self._status_text = "Bypassing…"
        threading.Thread(target=self._run_bypass, daemon=True).start()
        return {"ok": True}

    # -------------------------------------------------------------- internals
    def _log(self, text: str, kind: str = "info", tag: Optional[str] = None) -> None:
        with self._lock:
            self._logs.append(LogEntry(text=text, kind=kind, tag=tag))

    def _set_status(self, status: str, text: str) -> None:
        with self._lock:
            self._status = status
            self._status_text = text

    def _detect_once(self) -> None:
        try:
            info = device.get_device_info()
        except device.DeviceError as exc:
            with self._lock:
                self._device = None
                self._status = "searching"
                self._status_text = "No device"
            self._log(f"No device detected: {exc}", "error", None)
            return
        with self._lock:
            self._device = info
            self._status = "connected"
            self._status_text = "Connected"
        self._log(f"Device connected: {info.product_type} ({info.product_version})", "success", None)
        self._log(f"  UDID: {info.udid}", "info", None)
        self._log(f"  Serial: {info.serial}", "info", None)

    def _detect_loop(self) -> None:
        self._log("Waiting for an iOS device…", "info", None)
        while True:
            with self._lock:
                if self._device is not None or self._patching:
                    return
            self._detect_once()
            with self._lock:
                if self._device is not None:
                    return
            time.sleep(3)

    def _run_bypass(self) -> None:
        """Run the bypass pipeline in this thread."""
        udid = self._device.udid if self._device else None

        def log_fn(text: str, kind: str, tag: Optional[str]) -> None:
            self._log(text, kind, tag)

        try:
            result = rodo_pipeline.run_rodo_pipeline(log_fn, udid_filter=udid)
        except Exception as exc:
            self._log(f"Unexpected error: {exc}", "error", None)
            result = type("R", (), {"exit_code": 5})()

        with self._lock:
            self._patching = False
            if result.exit_code == 0:
                self._status = "success"
                self._status_text = "Success"
            else:
                self._status = "error"
                self._status_text = "Error"

        if result.exit_code == 0:
            self._log("MDM restore flow completed.", "success", None)
        else:
            self._log(
                f"Bypass failed (exit {result.exit_code}). Review the log before "
                "retrying; failed restore state may be uncertain.",
                "error",
                None,
            )


def _device_to_dict(d: device.DeviceInfo) -> dict:
    return {
        "udid": d.udid,
        "serial": d.serial,
        "imei": d.imei,
        "build_version": d.build_version,
        "product_version": d.product_version,
        "product_type": d.product_type,
        "activation_state": d.activation_state,
        "name": d.name,
    }


def main():
    api = GuiApi()
    webview.create_window(
        title="Jamfbreak",
        html=HTML,
        js_api=api,
        width=720,
        height=860,
        min_size=(560, 640),
        background_color="#0A0A0A",
        text_select=False,
    )
    webview.start()
    sys.exit(0)


if __name__ == "__main__":
    main()
