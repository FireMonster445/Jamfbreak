"""
jamfbreak.gui — minimalist black & white desktop GUI.

Launches a pywebview window (EdgeChromium/WebView2 on Windows) with an
embedded HTML/CSS/JS frontend. The Python side exposes an API object that
the JS polls for state (device info, console logs, status).

Usage:
    python -m jamfbreak.gui

The GUI reuses the exact same `rodo_pipeline.run_rodo_pipeline` as the CLI,
so both entry points use the same validation and controlled-reboot checks.

NOTE on how the frontend is loaded: the compiled bundle is decoded to an
HTML file in the user's temp directory and opened as a `file://` URL by
`webview.create_window(url=...)`. We intentionally do not use the
`html=` parameter: pywebview's EdgeChromium backend passes that through
`CoreWebView2.NavigateToString`, which navigates to `about:blank` on an
opaque, insecure origin — and this Vite module bundle refuses to execute
there (React never mounts, no JS error logged). A plain `file://` URL
mounts the same bundle fine.
"""

from __future__ import annotations

import platform
import sys
import tempfile
import threading
import time
import webbrowser
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import webview

from . import device
from . import rodo_pipeline
from .gui_html import HTML

APP_VERSION = "1.0.8"
REPO_URL = "https://github.com/FireMonster445/Jamfbreak"


def _write_html_file() -> Path:
    """Decode the compiled frontend bundle to disk and return its path.

    The file is written under the user's temp directory so no app folder
    needs to be writable and no source tree gets polluted.
    """
    base = Path(tempfile.gettempdir())
    path = base / "Jamfbreak.html"
    path.write_text(HTML, encoding="utf-8")
    return path


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

    def get_about(self) -> dict:
        """Version / build details shown in the Settings dialog."""
        bin_dir = Path(__file__).resolve().parent / "bin"
        if getattr(sys, "frozen", False):
            bin_dir = Path(sys.executable).resolve().parent / "bin"
        backups = Path(__file__).resolve().parent / "backups"
        if getattr(sys, "frozen", False):
            backups = Path(sys.executable).resolve().parent / "backups"

        def donor_search(name: str) -> bool:
            root = backups / name if name else backups
            try:
                for entry in root.iterdir():
                    if entry.is_dir() and (entry / "Manifest.plist").is_file():
                        return True
            except OSError:
                pass
            return False

        webview_version = "pywebview/unknown"
        try:
            import importlib.metadata

            webview_version = "pywebview/" + importlib.metadata.version("pywebview")
        except importlib.metadata.PackageNotFoundError:
            pass

        return {
            "app_version": APP_VERSION,
            "python_version": platform.python_version(),
            "platform": f"{platform.system()} {platform.release()}",
            "webview_version": webview_version,
            "frozen": bool(getattr(sys, "frozen", False)),
            "bin_present": (bin_dir / "idevicebackup2.exe").is_file(),
            "donors": {
                "legacy": donor_search(""),
                "ios26-ipad": donor_search("ios26-ipad"),
                "ios26-iphone": donor_search("ios26-iphone"),
            },
        }

    def open_github(self) -> dict:
        """Open the public repository in the user's browser."""
        webbrowser.open(REPO_URL)
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
    html_path = _write_html_file()
    webview.create_window(
        title="Jamfbreak",
        url="file:///" + str(html_path).replace("\\", "/"),
        js_api=api,
        width=1080,
        height=620,
        min_size=(900, 560),
        background_color="#0A0A0A",
        text_select=False,
    )
    webview.start()
    sys.exit(0)


if __name__ == "__main__":
    main()
